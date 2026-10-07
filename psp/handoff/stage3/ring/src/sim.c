/*
 * sim.c - time, the timer-interrupt path, the scheduler and the kernel
 * services the code under test calls (Stage 3 ring test).
 *
 * Timer interrupt = model of work/linux arch/mips/psp/psp.c:353-394
 * (psp_cputimer_handler + psp_watchdog_tick, unchanged order):
 *     c_pre = Count; Count = 0; psc_k.c_pre_cur = c_pre;           :356-365
 *     psp_local_tick++; every 1250 ticks: wd_ctx = 2; Nop; wd_ctx = 0 :385-393
 *     psc_tick_hook(c_pre);                                         :371
 *     do_IRQ: irq_enter, jiffies++, irq_exit -> softirq (timers)    :375
 * The Nop is the real pspSysconNop() (syscon.h:101 -> syscon.c:362 ->
 * psc_syscon_cmd -> Syscon_cmd -> psc_sc_exit). The boot Nop is the model of
 * prom_init (psp.c:576-580). psc_tick_hook, the Nop path, the scheduler
 * hooks, the LED and Memory Stick hooks are the real psc.c functions.
 *
 * Time only advances (a) per register access (mmio.c), (b) where the
 * harness models work (idle until the next tick, collector work, Memory
 * Stick sectors, the handler's own overhead). An interrupt therefore lands
 * either before a register access, at a harness work step, or at a forced
 * injection point (barrier, copy_to_user). Every such point is logged.
 */
#include "host.h"
#include <stdarg.h>
#include <sys/mman.h>
#include <unistd.h>

u32 g_count;
u64 g_abs;
int g_ie;
unsigned long psp_local_tick;			/* psp.c: watchdog localTick */
volatile unsigned long jiffies = INITIAL_JIFFIES;
int psc_host_preempt_count;
struct task_struct *psc_host_current;
int g_cur;
int console_blanked;
FILE *g_ev;
struct binj g_binj;
extern int g_in_nop, g_in_boot_nop;

/* hook used by scenarios after a targeted Nop */
void (*g_after_nop)(unsigned long tick);
/* jiffies at which the thread / the collector wake (0 = not sleeping) */
unsigned long g_jp_wake, g_wrk_wake;
int g_jp_sleeping, g_jp_runnable, g_wrk_runnable, g_wrk_started;
unsigned long g_kupd_next = 1250 + 600;		/* wb_kupdate cadence model */

#define HANDLER_COST	400u	/* timer handler, not counting the Nop */

void ev(const char *fmt, ...)
{
	va_list ap;

	if (!g_ev)
		return;
	va_start(ap, fmt);
	vfprintf(g_ev, fmt, ap);
	va_end(ap);
}

/* ------------------------------------------------------------- CP0 */
/* Every Count read by a PSC capture point is logged with its calling
 * function, so the oracle knows the exact capture instants (RC events). */
int g_log_reads = 1;
int g_tsr_fire;			/* unit test: a tick inside the next entry ts_read */
const char *host_fn_of(unsigned long ra, unsigned long *off);
extern int g_irq_depth;

unsigned int psc_host_read_c0_count(void)
{
	if (g_tsr_fire && g_ie && !g_irq_depth) {
		const char *fn = host_fn_of((unsigned long)__builtin_return_address(0), NULL);

		if (fn && !strcmp(fn, "psc_syscon_cmd")) {
			struct ipt p;

			g_tsr_fire = 0;
			ipt_for_current(&p);
			if (g_count < CPT)
				g_count = CPT;
			fire_tick(&p);
		}
	}
	if (g_log_reads && g_ev) {
		const char *fn = host_fn_of((unsigned long)__builtin_return_address(0), NULL);

		if (fn && !strncmp(fn, "psc_", 4))
			ev("RC %s %lu %u\n", fn, psp_local_tick, g_count);
	}
	return g_count;
}
unsigned int psc_host_read_c0_status(void)
{
	return ST0_CU0 | 0xff00 | (g_ie ? 1u : 0u);
}

/* ------------------------------------------------------------- tasks */
struct task_struct *g_task[T_NTASK];
static struct task_struct tasks[T_NTASK];
int g_where[T_NTASK];		/* WH_* below */
enum { WH_DEFAULT, WH_RINGREAD, WH_MSIO, WH_PSC_EXIT, WH_POLL_END, WH_SEG_END, WH_SOFTIRQ,
       WH_BYRA, WH_HANDOFF };

/* ------------------------------------------------ symbol maps (EPC labels)
 * An interrupt at a harness point inside a psc.c function reports, as EPC,
 * the RELEASE address of the same function (BUILD/System.map), found from
 * the host return address through the host binary's own nm listing. */
struct sym { unsigned long a; char n[64]; };
static struct sym *hsym, *rsym;
static int nhsym, nrsym;
unsigned long g_last_ra;

static int load_syms(const char *path, struct sym **out)
{
	FILE *f = fopen(path, "r");
	char line[256], t;
	unsigned long a;
	char n[200];
	int cap = 0, cnt = 0;

	if (!f)
		return 0;
	while (fgets(line, sizeof(line), f)) {
		if (sscanf(line, "%lx %c %199s", &a, &t, n) != 3)
			continue;
		if (t != 'T' && t != 't' && t != 'W')
			continue;
		if (cnt == cap) {
			cap = cap ? 2 * cap : 4096;
			*out = realloc(*out, cap * sizeof(struct sym));
		}
		(*out)[cnt].a = a;
		snprintf((*out)[cnt].n, sizeof((*out)[cnt].n), "%s", n);
		cnt++;
	}
	fclose(f);
	return cnt;
}

void syms_init(void)
{
	const char *h = getenv("PSC_HOST_SYMS"), *r = getenv("PSC_RELEASE_MAP");
	char self[1024], path[1100];
	ssize_t n = readlink("/proc/self/exe", self, sizeof(self) - 1);

	if (n > 0) {
		self[n] = 0;
		snprintf(path, sizeof(path), "%s.syms", self);	/* nm -n of this binary */
	} else {
		snprintf(path, sizeof(path), "build/ringsim.syms");
	}
	nhsym = load_syms(h ? h : path, &hsym);
	if (nhsym < 100) {
		fprintf(stderr, "syms: %s not loaded\n", h ? h : path);
		exit(2);
	}
	nrsym = load_syms(r ? r : "/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD/System.map", &rsym);
}

const char *host_fn_of(unsigned long ra, unsigned long *off)
{
	int lo = 0, hi = nhsym - 1, best = -1;

	while (lo <= hi) {
		int mid = (lo + hi) / 2;

		if (hsym[mid].a <= ra) { best = mid; lo = mid + 1; }
		else hi = mid - 1;
	}
	if (best < 0)
		return NULL;
	if (off)
		*off = ra - hsym[best].a;
	return hsym[best].n;
}

static u32 release_addr(const char *n)
{
	int i;

	for (i = 0; i < nrsym; i++)
		if (!strcmp(rsym[i].n, n))
			return (u32)rsym[i].a;
	return 0;
}
static const struct {
	int pid; const char *name; int mm;
	u32 epc, ra, sp, ti;
} tinfo[T_NTASK] = {
	/* idle: r4k_wait (System.map 88000a78), cpu_idle 8800301c */
	{ 0, "swapper", 0, 0x88000a7c, 0x88003050, 0x88123f00, 0x88122000 },
	{ 1, "init", 0, 0x880100b0, 0x880100a0, 0x81fffe60, 0x81ffe000 },
	{ 25, "kjoypad", 0, 0x881182a0, 0x88118258, 0x81f3bf80, 0x81f3a000 },
	{ 77, "pscol", 1, 0x81a41230, 0x81a41100, 0x81a7fe00, 0x81c0a000 },
	{ 76, "pscol", 1, 0x81a40e10, 0x81a40d00, 0x81b7fe00, 0x81c1a000 },
	{ 30, "psposk2", 1, 0x81804560, 0x81804400, 0x8183fe00, 0x81c2a000 },
	{ 31, "pspmd", 1, 0x81904560, 0x81904400, 0x8193fe00, 0x81c3a000 },
	{ 9, "pdflush", 0, 0x8804a000, 0x8804a100, 0x81c4bf00, 0x81c4a000 },
};
static void *stack_block[T_NTASK];
static void *karena_alloc(size_t size, size_t align);

void tasks_init(void)
{
	int i;

	for (i = 0; i < T_NTASK; i++) {
		struct thread_info *ti;

		stack_block[i] = karena_alloc(THREAD_SIZE, THREAD_SIZE);
		memset(stack_block[i], 0, THREAD_SIZE);
		ti = (struct thread_info *)stack_block[i];
		memset(&tasks[i], 0, sizeof(tasks[i]));
		tasks[i].pid = tinfo[i].pid;
		tasks[i].host_name = tinfo[i].name;
		tasks[i].mm = tinfo[i].mm ? (void *)&tasks[i] : NULL;
		tasks[i].thread_info = ti;
		tasks[i].state = TASK_RUNNING;
		ti->task = &tasks[i];
		g_task[i] = &tasks[i];
	}
	g_cur = T_IDLE;
	psc_host_current = g_task[T_IDLE];
}

int task_index_of_pid(int pid)
{
	int i;

	for (i = 0; i < T_NTASK; i++)
		if (tinfo[i].pid == pid)
			return i;
	return -1;
}

/* the interrupted point of a task that is not inside Syscon_cmd */
void ipt_for_current(struct ipt *p)
{
	int t = g_cur;

	memset(p, 0, sizeof(*p));
	p->epc = tinfo[t].epc;
	p->ra = tinfo[t].ra;
	p->sp = tinfo[t].sp;
	p->cause = 0x00008000;
	p->status = 0x1000ff03;
	switch (g_where[t]) {
	case WH_RINGREAD:	/* psc_ring_read (System.map 880d22fc) */
		p->epc = 0x880d22fc + 0x1a0; p->ra = 0x8805f000; p->sp = tinfo[t].ti + 0x1d00;
		break;
	case WH_MSIO:		/* psp_ms_make_request (88111a7c) */
		p->epc = 0x88111a7c + 0x120; p->ra = 0x88111b00; p->sp = tinfo[t].ti + 0x1c00;
		break;
	case WH_PSC_EXIT:	/* psc_sc_exit (880d2b04) */
		p->epc = 0x880d2b04 + 0x80; p->ra = 0x880d3548; p->sp = 0x81f3bd48;
		break;
	case WH_POLL_END:	/* psc_poll_end (880d3c04) */
		p->epc = 0x880d3c04 + 0x40; p->ra = 0x881182b0; p->sp = 0x81f3bf60;
		break;
	case WH_SEG_END:	/* psc_ms_seg_end (880d3d04) */
		p->epc = 0x880d3d04 + 0x60; p->ra = 0x88111bb0; p->sp = tinfo[t].ti + 0x1c00;
		break;
	case WH_SOFTIRQ:	/* __do_softirq (88028d40) */
		p->epc = 0x88028d40 + 0x60; p->ra = 0x88028e00; p->sp = tinfo[t].sp - 0x200;
		break;
	case WH_HANDOFF:	/* Syscon_cmd exit hand-off (REC 880cf0e8..880cf1dc) */
		p->epc = 0x880cf150; p->ra = 0x880d3544; p->sp = 0x81f3bd10 - 128;
		break;
	case WH_BYRA: {		/* the release address of the same function */
		unsigned long off = 0;
		const char *fn = host_fn_of(g_last_ra, &off);
		u32 ra = fn ? release_addr(fn) : 0;

		if (ra) {
			p->epc = ra + (u32)(off < 0x40 ? off & ~3UL : 0x40);
			p->ra = ra;
			if (t == T_JP)
				p->sp = 0x81f3bd48;
		}
		break;
	}
	default:
		break;
	}
	p->pcnt = psc_host_preempt_count;
}

/* ------------------------------------------------------- the scheduler */
/* schedule() prev != next (kernel/sched.c:3700-3713): ++*switch_count
 * (nivcsw if prev is still runnable, else nvcsw), then hook S, with the
 * runqueue lock held and interrupts off. */
void do_switch(int prev, int next)
{
	struct task_struct *p = g_task[prev], *n = g_task[next];
	int ie = g_ie;

	(void)ie;
	if (prev == next)
		return;
	g_ie = 0;
	if (p->state == TASK_RUNNING)
		p->nivcsw++;
	else
		p->nvcsw++;
	ev("SW %d %d %ld %lu %u\n", p->pid, n->pid, p->state, psp_local_tick, g_count);
	psc_sched_switch(p, n);			/* real inline, asm/psc.h:241 */
	g_cur = next;
	psc_host_current = n;
	g_ie = 1;
}

/* try_to_wake_up() of the thread (kernel/sched.c:1661 hook W), rq lock */
void sched_wake_jp(void)
{
	int ie = g_ie;

	g_ie = 0;
	g_task[T_JP]->state = TASK_RUNNING;
	ev("WK %d %lu %u\n", g_task[T_JP]->pid, psp_local_tick, g_count);
	psc_sched_wake(g_task[T_JP]);		/* real inline, asm/psc.h:235 */
	g_ie = ie;
}

/* ------------------------------------------------- timer-interrupt model */
static unsigned long wd_lastTick;		/* psp.c:383 static lastTick */
int g_irq_depth;

/* unit tests: make the next tick a watchdog tick */
void sim_align_wd(void)
{
	psp_local_tick = wd_lastTick + WD_CYCLE - 1;
	jiffies = INITIAL_JIFFIES + psp_local_tick;
}

int irq_due(void)
{
	return g_count >= CPT;
}

static void run_timers(void)
{
	/* msleep expiry of the joypad thread (schedule_timeout) */
	if (g_jp_sleeping && (long)(jiffies - g_jp_wake) >= 0) {
		g_jp_sleeping = 0;
		g_jp_runnable = 1;
		sched_wake_jp();
	}
	/* the collector's nanosleep */
	if (g_wrk_started && !g_wrk_runnable && (long)(jiffies - g_wrk_wake) >= 0)
		g_wrk_runnable = 1;
	/* pdflush wb_kupdate every 5 s (mm/page-writeback.c:452-455 hook) */
	if (psp_local_tick >= g_kupd_next) {
		g_kupd_next += 1250;
		psc_st.kupd_count++;			/* modeled kernel line :453 */
		psc_st.kupd_last_tick = psp_local_tick;	/* :454 */
		ev("KUPD %lu\n", psp_local_tick);
	}
}

static void frame_fill(struct pt_regs *f, const struct ipt *p)
{
	int i;

	memset(f, 0, sizeof(*f));
	for (i = 0; i < 14; i++)
		f->regs[2 + i] = p->r[i];
	f->regs[24] = p->r[14];
	f->regs[25] = p->r[15];
	f->regs[29] = p->sp;
	f->regs[31] = p->ra;
	f->cp0_epc = p->epc;
	f->cp0_cause = p->cause;
	f->cp0_status = p->status;
}

extern int g_ms_active;

void fire_tick(const struct ipt *p)
{
	struct task_struct *t = current;
	struct thread_info *ti = t->thread_info;
	struct pt_regs *saved = ti->regs, *f;
	int saved_ie = g_ie;
	int nested = (psc_host_preempt_count & (SOFTIRQ_MASK | HARDIRQ_MASK)) != 0;
	u32 c_pre, i;
	char rh[16 * 9 + 1];

	/* the exception frame on the interrupted task's kernel stack */
	f = (struct pt_regs *)((char *)ti + THREAD_SIZE - 400 * (g_irq_depth + 1));
	frame_fill(f, p);
	ti->regs = f;
	g_irq_depth++;
	g_ie = 0;
	c_pre = g_count;				/* psp.c:356 */
	g_count = 0;					/* psp.c:360 */
	for (i = 0; i < 16; i++)
		sprintf(rh + 9 * i, "%08x,", p->r[i]);
	rh[16 * 9 - 1] = 0;
	ev("TK %lu %u %d %d %08x %08x %08x %08x %08x %d %d %s\n",
	   psp_local_tick + 1, c_pre, t->pid, nested, p->epc, p->cause,
	   p->status, p->ra, p->sp, psc_host_preempt_count, g_ms_active, rh);
	psc_k.c_pre_cur = c_pre;			/* psp.c:365 */
	/* psp_watchdog_tick (psp.c:383-394) */
	psp_local_tick++;
	if (psp_local_tick - wd_lastTick >= WD_CYCLE) {
		wd_lastTick = psp_local_tick;
		psc_k.wd_ctx = PSC_WDCTX_TIMER;		/* :390 */
		ev("NOP %lu\n", psp_local_tick);
		g_in_nop = 1;
		pspSysconNop();				/* :391 -> :405 */
		g_in_nop = 0;
		psc_k.wd_ctx = PSC_WDCTX_NONE;		/* :392 */
		if (g_after_nop)
			g_after_nop(psp_local_tick);
	}
	psc_tick_hook(c_pre);				/* psp.c:371 (real T2) */
	g_count += HANDLER_COST;
	g_abs += HANDLER_COST;
	/* do_IRQ -> irq_enter / do_timer / irq_exit */
	psc_host_preempt_count += HARDIRQ_OFFSET;
	jiffies++;
	psc_host_preempt_count -= HARDIRQ_OFFSET;
	if (!nested) {
		/* __do_softirq with interrupts enabled (kernel/softirq.c:217,225) */
		psc_host_preempt_count += SOFTIRQ_OFFSET;
		g_ie = 1;
		if (g_count >= CPT) {			/* a tick nested in the softirq */
			struct ipt q;
			int w = g_where[g_cur];

			g_where[g_cur] = WH_SOFTIRQ;
			ipt_for_current(&q);
			g_where[g_cur] = w;
			fire_tick(&q);
		}
		g_ie = 0;
		run_timers();
		psc_host_preempt_count -= SOFTIRQ_OFFSET;
	}
	ev("TKX %lu %u\n", psp_local_tick, g_count);
	g_irq_depth--;
	ti->regs = saved;
	g_ie = saved_ie;
}

/* advance time by dc at a harness work step of the current task */
void sim_advance(u32 dc)
{
	while (dc) {
		u32 step = dc;

		if (g_count < CPT && g_count + step > CPT)
			step = CPT - g_count;
		g_count += step;
		g_abs += step;
		dc -= step;
		if (g_ie && g_count >= CPT) {
			struct ipt p;

			ipt_for_current(&p);
			fire_tick(&p);
		}
	}
}

/* idle until the next tick, then take it */
void sim_idle_tick(void)
{
	struct ipt p;
	u32 jit = host_rand() % 160;

	if (g_count < CPT) {
		g_abs += CPT - g_count;
		g_count = CPT;
	}
	g_count += jit;
	g_abs += jit;
	ipt_for_current(&p);
	fire_tick(&p);
}

/* ------------------------------------------------------- barrier hook */
void binj_arm(int target, int action)
{
	g_binj.armed = 1;
	g_binj.count = 0;
	g_binj.target = target;
	g_binj.action = action;
	g_binj.done = 0;
}

void (*g_binj_reader)(void);		/* action 3 */
int g_binj_where = WH_BYRA;

#define B_COST	40u	/* code between two ordering points (~40 instructions) */

void psc_host_barrier(void)
{
	g_last_ra = (unsigned long)__builtin_return_address(0);
	/* time passes, but a due tick is taken at the next register access or
	 * harness step, not here (interrupts AT barriers are the injection
	 * tests' job, where each one is controlled and labelled) */
	g_count += B_COST;
	g_abs += B_COST;
	if (!g_binj.armed || g_binj.done || g_in_nop || g_irq_depth || !g_ie)
		return;
	if (g_binj.count++ != g_binj.target)
		return;
	g_binj.done = 1;
	g_binj.ra = (unsigned long)__builtin_return_address(0);
	{
		unsigned long off = 0;
		const char *fn = host_fn_of(g_binj.ra, &off);

		ev("BINJ %d %d %lx %s+0x%lx\n", g_binj.target, g_binj.action, g_binj.ra,
		   fn ? fn : "?", off);
	}
	if (g_binj.action == 1 || g_binj.action == 2) {
		struct ipt p;
		int w = g_where[g_cur];

		g_where[g_cur] = g_binj_where;
		ipt_for_current(&p);
		g_where[g_cur] = w;
		if (g_count < CPT) {
			g_abs += CPT - g_count;
			g_count = CPT;
		}
		fire_tick(&p);
	} else if (g_binj.action == 3 && g_binj_reader) {
		g_binj_reader();
	}
}

/* ------------------------------------------------------- printk, /proc */
char g_kmsg[8192];
int g_kmsg_len;

int printk(const char *fmt, ...)
{
	va_list ap;
	char b[512];
	int n;

	va_start(ap, fmt);
	n = vsnprintf(b, sizeof(b), fmt, ap);
	va_end(ap);
	if (n < 0)
		return n;
	if (n > (int)sizeof(b) - 1)
		n = sizeof(b) - 1;
	if (g_kmsg_len + n + 4 < (int)sizeof(g_kmsg)) {
		if (b[0] != '<')
			g_kmsg_len += sprintf(g_kmsg + g_kmsg_len, "<4>");
		memcpy(g_kmsg + g_kmsg_len, b, n);
		g_kmsg_len += n;
		g_kmsg[g_kmsg_len] = 0;
	}
	ev("PRINTK %s", b);
	if (n && b[n - 1] != '\n')
		ev("\n");
	return n;
}

struct proc_dir_entry g_pde[16];
int g_npde;

struct proc_dir_entry *proc_mkdir(const char *name, struct proc_dir_entry *parent)
{
	struct proc_dir_entry *e = &g_pde[g_npde++];

	memset(e, 0, sizeof(*e));
	e->name = name;
	e->parent = parent;
	return e;
}

struct proc_dir_entry *create_proc_entry(const char *name, mode_t mode,
					 struct proc_dir_entry *parent)
{
	struct proc_dir_entry *e = &g_pde[g_npde++];

	memset(e, 0, sizeof(*e));
	e->name = name;
	e->mode = mode;
	e->parent = parent;
	return e;
}

struct proc_dir_entry *host_pde(const char *name)
{
	int i;

	for (i = 0; i < g_npde; i++)
		if (g_pde[i].parent && !strcmp(g_pde[i].name, name))
			return &g_pde[i];
	return NULL;
}

/* copy_to_user: the record copy of psc_ring_read (psc.c:1017) and the stats
 * copy. An interruption point of the reader (the collector's work time). */
u32 g_copy_cost_div = 4;
int g_copy_inject;			/* fire a forced tick at the next copy */
void (*g_copy_hook)(void);

unsigned long psc_host_copy_to_user(void *to, const void *from, unsigned long n)
{
	if (g_copy_hook)
		g_copy_hook();
	memcpy(to, from, n);
	if (g_ie && !g_irq_depth)
		sim_advance((u32)(n / g_copy_cost_div));
	return 0;
}

unsigned long psc_host_copy_from_user(void *to, const void *from, unsigned long n)
{
	memcpy(to, from, n);
	return 0;
}

/* ------------------------------------------------------- misc services */
/* Kernel memory (kmalloc and the 8 KB task stacks) comes from one arena
 * mapped at a fixed address inside the target's KSEG0 RAM range, so that
 * pointer values the kernel code records (stats word 55 jp_stage_arg, the
 * queue pointer, psc_format.h:475) are 32-bit target-like values and the same
 * on every run: a run is a pure function of its scenario name. Bump
 * allocation, kfree a no-op; a full arena stops the run. */
#define KARENA_BASE	0x89c00000UL
#define KARENA_SIZE	(4UL << 20)
static unsigned char *karena;
static size_t karena_off;

static void *karena_alloc(size_t size, size_t align)
{
	void *p;

	if (!karena) {
		karena = mmap((void *)KARENA_BASE, KARENA_SIZE, PROT_READ | PROT_WRITE,
			      MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
		if (karena != (void *)KARENA_BASE) {
			perror("mmap kernel arena at 0x89c00000");
			exit(2);
		}
	}
	karena_off = (karena_off + align - 1) & ~(align - 1);
	if (karena_off + size > KARENA_SIZE) {
		fprintf(stderr, "kernel arena full (%zu + %zu)\n", karena_off, size);
		exit(2);
	}
	p = karena + karena_off;
	karena_off += size;
	return p;			/* zero: fresh anonymous memory, never reused */
}

void *psc_host_kmalloc(size_t size, gfp_t flags) { (void)flags; return karena_alloc(size, 16); }
void psc_host_kfree(const void *p) { (void)p; }
int psc_host_down_interruptible(struct semaphore *sem)
{
	if (sem->count.counter > 0) {
		sem->count.counter--;
		return 0;
	}
	ev("SEM-CONTENDED\n");
	return -EINTR;
}
void psc_host_up(struct semaphore *sem) { sem->count.counter++; }
int psc_host_would_block(void) { ev("WOULD-BLOCK\n"); return -ERESTARTSYS; }

int (*g_kthread_fn)(void *);
int psc_host_kernel_thread(int (*fn)(void *), void *arg, unsigned long flags)
{
	(void)arg; (void)flags;
	g_kthread_fn = fn;
	return g_task[T_JP]->pid;
}

int register_chrdev_region(dev_t from, unsigned count, const char *name)
{ (void)from; (void)count; (void)name; return 0; }
void unregister_chrdev_region(dev_t from, unsigned count) { (void)from; (void)count; }
void cdev_init(struct cdev *c, const struct file_operations *fops) { c->ops = fops; }
int cdev_add(struct cdev *c, dev_t dev, unsigned count) { (void)c; (void)dev; (void)count; return 0; }
void cdev_del(struct cdev *c) { (void)c; }

/* psp.c:254 psp_lcd_on: does not touch the syscon (dossier 6.4) */
void psp_lcd_on(void) { }
/* kernel/printk.c:72 accessor */
int psc_console_sem_count(void) { return 1; }
/* arch/mips/psp/ipl_sdk/cache.c: D-cache write-back (panel) */
void pspClearDcache(void) { }
void pspClearIcache(void) { }
u32 sceSysregSpiClkSelect(int a1, int a2) { (void)a1; (void)a2; return 0; }
u32 sceSysregSpiClkEnable(u32 bit) { (void)bit; return 0; }

/* the stall panel's VRAM (PSP_VRAM_BASE = 0x84000000, asm/psp.h:36) */
void vram_map(void)
{
	void *want = (void *)0x84000000UL;
	void *got = mmap(want, 512 * 272 * 4, PROT_READ | PROT_WRITE,
			 MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);

	if (got != want) {
		perror("mmap VRAM at 0x84000000");
		exit(2);
	}
}
