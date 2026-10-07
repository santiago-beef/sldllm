/*
 * scen.c - scenarios, the operator (RUNBOOK B4, B6, C0, C1, D0-D9), the
 * consumers (psposk2, pspmd, the collector's own mouse client), the world
 * loop that runs while the joypad thread sleeps, and main().
 *
 * Boot order modeled: prom_init boot Nop (psp.c:576-580, interrupts off) ->
 * serial init M command pspSysconCtrlHRPower (serial_psp.c:352) -> joypad
 * module init (real psp_joypad_init) -> psc_init (real, late_initcall) ->
 * mount /ms0 (real psc_fat_mounted) -> psposk2 opens /dev/joypad (real
 * fop_open) -> joypad thread starts (3 s) -> collector starts (20 s).
 */
#include "host.h"
#include <stdarg.h>
#include <sys/stat.h>
#include <math.h>

extern int g_in_nop, g_in_boot_nop, g_jp_sleeping, g_jp_runnable;
extern int g_wrk_runnable, g_wrk_started;
extern unsigned long g_jp_wake, g_wrk_wake;
extern int (*g_kthread_fn)(void *);
extern int g_where[T_NTASK];
extern void (*g_after_nop)(unsigned long tick);
extern void (*g_binj_reader)(void);
extern int g_binj_where;
extern void (*g_copy_hook)(void);
extern u32 col_nonce;
extern u64 col_rec_total[5], col_lost_total[5];
extern int g_irq_depth;
unsigned long g_wrk_start_tick = 5000;

void tasks_init(void);
void syms_init(void);
void vram_map(void);
void sim_idle_tick(void);
void col_start(void);
void col_burst(void);
void col_mount(void);
int col_write(const char *dir);
void col_report(FILE *o);
void dev_report(FILE *f);
int jp_host_thread(void);
void jp_host_terminate(void);
int jp_host_init(void);
int jp_host_osk_open(void);
int jp_host_osk_has_data(void);
int jp_host_osk_read(unsigned long *keys, int max);
int jp_host_osk_queued(void);
int host_kind_by_name(const char *n);
const char *host_kind_name(int k);
extern int (*psc_host_late_initcall_psc_init)(void);

enum { WH_DEFAULT, WH_RINGREAD, WH_MSIO, WH_PSC_EXIT, WH_POLL_END, WH_SEG_END, WH_SOFTIRQ };

int g_selftest_tick = 40 * 250;
unsigned long g_mouse_pkts_wrk, g_mouse_press_wrk;
static unsigned long mouse_pending_wrk;
static int mouse_btn_prev;

/* ===================================================== the operator */
struct opev { double t0, t1; int what; };
enum { B_TRI, B_RIGHT, B_SELECT, B_L, B_HOLD, B_VOLUP, B_STICK_R, B_STICK_U };
static struct opev opv[4096];
static int nop_ev;
static double t_c0, t_c0_end, t_d0, t_d_end, t_pull, t_onset;
static int healthy;

static void opadd(double a, double b, int w)
{
	if (nop_ev < 4096) {
		opv[nop_ev].t0 = a;
		opv[nop_ev].t1 = b;
		opv[nop_ev].what = w;
		nop_ev++;
	}
}

/* D1-D7 (and D7a), RUNBOOK section D */
static double op_script(double t, int d7a)
{
	double x = t;
	int i;

	while (x < t + 10.0) { opadd(x, x + 0.1, B_L); x += 0.25; }	/* D1 */
	t += 10.0 + 5.0;						/* D2 */
	for (i = 0; i < 2; i++) { opadd(t, t + 3.0, B_TRI); t += 6.0; }	/* D3 */
	opadd(t, t + 3.0, B_RIGHT); t += 6.0;				/* D4 */
	opadd(t, t + 3.0, B_VOLUP); t += 6.0;				/* D5 */
	opadd(t, t + 3.0, B_STICK_R); t += 6.0;				/* D6 */
	opadd(t, t + 3.0, B_STICK_U); t += 6.0;
	opadd(t, t + 5.0, B_HOLD); t += 10.0;				/* D7 */
	if (d7a) {							/* D7a */
		opadd(t, t + 0.15, B_SELECT);
		x = t + 0.5;
		for (i = 0; i < 5; i++) { opadd(x, x + 0.1, B_L); x += 1.0; }
		t += 6.0;
	}
	return t;
}

static void op_init(double onset, double d0_control)
{
	double x;

	opadd(36.0, 38.0, B_TRI);			/* B4 */
	opadd(45.0, 45.15, B_SELECT);			/* B6: mouse mode on */
	t_c0 = 50.0;
	t_c0_end = op_script(t_c0, 0);			/* C0 = D1..D7 */
	t_d0 = onset > 0 ? onset + 3.0 : d0_control;
	x = t_c0_end + 1.0;				/* C1: L 4/s, stick now and then */
	while (x < (onset > 0 ? onset - 0.3 : t_d0 - 0.3)) {
		opadd(x, x + 0.1, B_L);
		if (((int)(x * 4)) % 28 == 0)
			opadd(x, x + 0.5, B_STICK_R);
		x += 0.25;
	}
	t_d_end = op_script(t_d0 + 2.0, 1);
	t_pull = t_d_end + 30.0 + 6.0;			/* D8 hands off, check, D9 */
}

static double now_s(void)
{
	return (double)psp_local_tick / 250.0 + (double)g_count / (double)CPT / 250.0;
}

void op_buttons(u8 b[4], u8 *x, u8 *y)
{
	double s = now_s();
	int i, on[8] = { 0 };

	for (i = 0; i < nop_ev; i++)
		if (opv[i].t0 <= s && s < opv[i].t1)
			on[opv[i].what] = 1;
	b[0] = 0xFF; b[1] = 0xFF; b[2] = 0xFF; b[3] = 0xFF;
	if (on[B_TRI]) b[0] &= ~0x10;			/* rx[3] b4 */
	if (on[B_RIGHT]) b[0] &= ~0x02;			/* rx[3] b1 */
	if (on[B_SELECT]) b[1] &= ~0x01;		/* rx[4] b0 */
	if (on[B_L]) b[1] &= ~0x02;			/* rx[4] b1 (LTRG) */
	if (on[B_HOLD]) b[1] &= ~0x20;			/* rx[4] b5 */
	if (on[B_VOLUP]) b[2] &= ~0x01;			/* rx[5] b0 */
	*x = on[B_STICK_R] ? 0xF8 : 0x80;
	*y = on[B_STICK_U] ? 0x05 : 0x80;
}

/* ============================================ input core / mousedev model */
/* input_event() passes EV_REL only when value != 0 and EV_KEY only on a
 * change; SYN_REPORT reaches mousedev only after a passed event
 * (drivers/input/input.c 2.6.22). mousedev hooks: md_event_syn
 * (mousedev.c:343), md_notify_calls (:239), md_read_ret (:669) - modeled
 * here because mousedev.c is not compiled. */
static int in_changed, key_state[3], osk_stopped, md_stopped, osk_runnable;
static struct input_dev mdev;

struct input_dev *input_allocate_device(void) { return &mdev; }
int input_register_device(struct input_dev *dev) { (void)dev; return 0; }
void input_unregister_device(struct input_dev *dev) { (void)dev; }
void input_free_device(struct input_dev *dev) { (void)dev; }

void psc_host_input_event(struct input_dev *dev, unsigned int type, unsigned int code, int value)
{
	(void)dev;
	if (type == EV_REL && value)
		in_changed = 1;
	if (type == EV_KEY && code >= BTN_LEFT && code <= BTN_MIDDLE) {
		int i = code - BTN_LEFT;

		if (key_state[i] != value) {
			key_state[i] = value;
			in_changed = 1;
		}
	}
}

void psc_host_input_sync(struct input_dev *dev)
{
	int b;

	(void)dev;
	if (!in_changed)
		return;
	in_changed = 0;
	psc_st.md_event_syn++;			/* mousedev.c:343 */
	psc_st.md_notify_calls++;		/* mousedev.c:239 */
	if (!md_stopped)
		psc_st.md_read_ret++;		/* pspmd's read, mousedev.c:669 */
	mouse_pending_wrk++;
	b = key_state[0] | (key_state[1] << 1) | (key_state[2] << 2);
	if (b && !mouse_btn_prev)
		g_mouse_press_wrk++;		/* telem.c:270 press edge */
	mouse_btn_prev = b;
	ev("MOUSE %d %lu\n", b, psp_local_tick);
}

void psc_host_wake_up_interruptible(wait_queue_head_t *q)
{
	(void)q;
	if (!osk_stopped)
		osk_runnable = 1;
}

static void osk_run(void)
{
	unsigned long keys[16];
	int n;

	do_switch(g_cur, T_OSK);
	sim_advance(8000);
	if (jp_host_osk_has_data()) {
		n = jp_host_osk_read(keys, 16);		/* real fop_read */
		if (n > 0)
			psc_st.vcs_putchar += (u32)n;	/* vc_screen.c:576 (modeled) */
		ev("OSK %d %lu\n", n, psp_local_tick);
	}
	sim_advance(4000);
	osk_runnable = 0;
	g_task[T_OSK]->state = TASK_INTERRUPTIBLE;
	do_switch(T_OSK, T_IDLE);
	g_task[T_OSK]->state = TASK_RUNNING;
}

/* ================================================ aiming and injection */
struct aim {
	int k;			/* watchdog Nop index (tick 1250 k) */
	int type;		/* 1 MMIO point, 2 P append, 3 POLL append, 4 S append, 5 W read */
	int kind, nth, cmd, need_latch;
	u32 epc_override;
	int barrier;		/* barrier index for types 2-4 */
	int set_mode_after;	/* device mode after the aimed Nop (-1 none) */
	int done;
};
static struct aim aims[64];
static int naims;
static u32 g_end08_off = 6000;	/* offset of the 0x08 end from loop top, measured */
static u32 poll_top_count;
static int poll_index;
static int armed_append = 0;
u32 g_epc_override;

static struct aim *aim_for_tick(unsigned long t)
{
	int i;

	for (i = 0; i < naims; i++)
		if (!aims[i].done && (unsigned long)aims[i].k * WD_CYCLE == t)
			return &aims[i];
	return NULL;
}

/* the next aimed Nop (lowest k not done) */
static struct aim *next_aim(void)
{
	struct aim *best = NULL;
	int i;

	for (i = 0; i < naims; i++)
		if (!aims[i].done && (!best || aims[i].k < best->k))
			best = &aims[i];
	return best;
}

static void after_nop(unsigned long tick)
{
	struct aim *a = aim_for_tick(tick);

	if (!a)
		return;
	a->done = 1;
	ev("AIMDONE %d type %d trig %d binj %d\n", a->k, a->type, g_trig.fired,
	   g_binj.done && g_binj.armed);
	g_binj.armed = 0;
	if (a->type == 1 && !g_trig.fired)
		fprintf(stderr, "aim k=%d: trigger did not fire\n", a->k);
	g_trig.armed = 0;
	g_epc_override = 0;
	if (a->set_mode_after >= 0)
		dev_set_mode(a->set_mode_after);
}

/* called from mmio.c at each transaction end of the thread */
void scen_xfer_end(char origin, int cmd)
{
	struct aim *a = next_aim();

	/* type 6 (P entry): armed at the end of the poll's 0x33 so that the
	 * barrier count runs through the 0x33's psc_sc_exit (barriers 0..8) into
	 * the 0x08's psc_sc_entry (9 = psc.c:240, 10 = psc.c:245) */
	if (origin == 'P' && cmd == 0x33 && armed_append && a && a->type == 6 &&
	    psp_local_tick == (unsigned long)a->k * WD_CYCLE - 1) {
		binj_arm(9 + a->barrier, 1);
		armed_append = 0;
	}
	if (origin != 'P' || cmd != 0x08)
		return;
	if (!(a && a->type == 1))
		g_end08_off = g_count - poll_top_count;
	if (armed_append && a && (a->type == 2 || a->type == 3) &&
	    psp_local_tick == (unsigned long)a->k * WD_CYCLE - 1) {
		binj_arm(a->type == 2 ? a->barrier : 9 + a->barrier, 1);
		armed_append = 0;
	}
}

/* S append: arm right before the real psc_ms_seg_end of a data segment */
void scen_before_seg_end(void)
{
	struct aim *a = next_aim();

	if (a && a->type == 4 && psp_local_tick == (unsigned long)a->k * WD_CYCLE - 1 &&
	    (!g_binj.armed || g_binj.done)) {
		binj_arm(a->barrier, 1);
	}
}

/* W read: a forced tick at the first record copy of the W ring read */
static void copy_hook(void)
{
	struct aim *a = next_aim();
	struct ipt p;

	if (!a || a->type != 5 || psp_local_tick != (unsigned long)a->k * WD_CYCLE - 1 ||
	    g_irq_depth)
		return;
	if (g_where[g_cur] != WH_RINGREAD || g_cur != T_WRK)
		return;
	ipt_for_current(&p);
	if (g_count < CPT) {
		g_abs += CPT - g_count;
		g_count = CPT;
	}
	ev("CINJ %d\n", a->k);
	fire_tick(&p);
}

/* ===================================================== the world */
static unsigned long end_tick;
static int ended;

static void maybe_hold_for_aim(void)
{
	struct aim *a = next_aim();
	u32 c_top;

	if (!a || (a->type != 1 && a->type != 2 && a->type != 3 && a->type != 6))
		return;
	if (psp_local_tick != (unsigned long)a->k * WD_CYCLE - 1)
		return;
	/* the collector holds the CPU until the thread can just reach its
	 * target before the tick edge (the 7.3 late-start exposure) */
	c_top = CPT - (g_end08_off + 2500);
	if (c_top > g_count) {
		do_switch(g_cur, T_WRK);
		sim_advance(c_top - g_count);
		g_task[T_WRK]->state = TASK_INTERRUPTIBLE;
		do_switch(T_WRK, T_IDLE);
		g_task[T_WRK]->state = TASK_RUNNING;
	}
	if (a->type == 1) {
		memset(&g_trig, 0, sizeof(g_trig));
		g_trig.armed = 1;
		g_trig.kind = a->kind;
		g_trig.nth = a->nth;
		g_trig.cmd = a->cmd;
		g_trig.ctx_origin = 'P';
		g_trig.need_latch = a->need_latch;
		g_epc_override = a->epc_override;
	} else {
		armed_append = 1;
	}
	ev("AIM %d type %d kind %s nth %d c_top %u\n", a->k, a->type,
	   a->type == 1 ? host_kind_name(a->kind) : "-", a->nth, c_top);
}

void scen_tick_check(void);

/* type 4/5 aims: the collector's burst runs in the tick before the Nop */
static void align_collector_for_aim(void)
{
	struct aim *a = next_aim();
	unsigned long tgt;

	if (!a || (a->type != 4 && a->type != 5) || !g_wrk_started)
		return;
	tgt = (unsigned long)a->k * WD_CYCLE - 1;
	if (psp_local_tick < tgt && tgt - psp_local_tick <= 60 &&
	    (long)(g_wrk_wake - (INITIAL_JIFFIES + tgt)) > 0)
		g_wrk_wake = INITIAL_JIFFIES + tgt;
}

static void world_until_jp(void)
{
	for (;;) {
		scen_tick_check();
		align_collector_for_aim();
		if (!g_wrk_started && psp_local_tick >= g_wrk_start_tick && g_cur == T_IDLE && !ended) {
			do_switch(T_IDLE, T_WRK);
			col_start();
			g_wrk_started = 1;
			col_burst();
			g_task[T_WRK]->state = TASK_INTERRUPTIBLE;
			do_switch(T_WRK, T_IDLE);
			g_task[T_WRK]->state = TASK_RUNNING;
			continue;
		}
		if (!ended && psp_local_tick >= end_tick) {
			ended = 1;
			jp_host_terminate();
		}
		if (ended && !g_jp_runnable) {
			/* the thread is woken to let its loop end (simulation end) */
			g_jp_sleeping = 0;
			g_jp_runnable = 1;
			g_task[T_JP]->state = TASK_RUNNING;
		}
		if (g_cur == T_IDLE && g_wrk_runnable && !ended) {
			g_wrk_runnable = 0;
			do_switch(T_IDLE, T_WRK);
			col_burst();
			g_task[T_WRK]->state = TASK_INTERRUPTIBLE;
			do_switch(T_WRK, T_IDLE);
			g_task[T_WRK]->state = TASK_RUNNING;
			continue;
		}
		if (g_cur == T_IDLE && osk_runnable && !osk_stopped) {
			osk_run();
			continue;
		}
		if (g_cur == T_IDLE && g_jp_runnable) {
			sim_advance(1200);		/* schedule() path */
			maybe_hold_for_aim();
			g_jp_runnable = 0;
			do_switch(g_cur, T_JP);
			return;
		}
		sim_idle_tick();
	}
}

void psc_host_msleep(unsigned int ms)
{
	/* msleep: msecs_to_jiffies(ms) + 1 (kernel/timer.c); 50 ms -> 14 */
	unsigned long to = ((unsigned long)ms * HZ + MSEC_PER_SEC - 1) / MSEC_PER_SEC + 1;
	struct aim *a = next_aim();
	unsigned long w = psp_local_tick + to;

	ev("LE %lu %u\n", psp_local_tick, g_count);
	/* aiming: wake in the tick before the aimed Nop (one period stretched) */
	if (a && ((a->type >= 1 && a->type <= 3) || a->type == 6)) {
		unsigned long tgt = (unsigned long)a->k * WD_CYCLE - 1;

		if (tgt >= w && tgt < w + 14)
			to += tgt - w;
	}
	g_jp_wake = jiffies + to;
	g_jp_sleeping = 1;
	g_task[T_JP]->state = TASK_UNINTERRUPTIBLE;
	do_switch(T_JP, T_IDLE);
	world_until_jp();
	poll_top_count = g_count;
	poll_index++;
	ev("LT %lu %u\n", psp_local_tick, g_count);
}

/* the collector's mouse client: its non-blocking drain of /dev/input/mice */
void col_mouse_drain(void)
{
	g_mouse_pkts_wrk += mouse_pending_wrk;
	psc_st.md_read_ret += (u32)mouse_pending_wrk;	/* mousedev.c:669 */
	mouse_pending_wrk = 0;
}

/* ===================================================== scenarios */
static void plan_point(int k, const char *kind, int nth, int latch, u32 epc_ovr, int after)
{
	struct aim *a = &aims[naims++];

	memset(a, 0, sizeof(*a));
	a->k = k;
	a->type = 1;
	a->kind = host_kind_by_name(kind);
	a->nth = nth;
	a->cmd = 0x08;
	a->need_latch = latch;
	a->epc_override = epc_ovr;
	a->set_mode_after = after;
}

static void plan_append(int k, int type, int barrier)
{
	struct aim *a = &aims[naims++];

	memset(a, 0, sizeof(*a));
	a->k = k;
	a->type = type;
	a->barrier = barrier;
	a->set_mode_after = -1;
}

static const char *expect_text;
static long truth_onset_tick = -1;	/* truth.json only; no effect on the run */
static int onset_mode = DM_NORMAL;

static int setup(const char *name)
{
	double onset = 0, d0c = 110.0;
	int mode = DM_NORMAL, h7 = 0;

	t_onset = 0;
	if (!strcmp(name, "H1")) { onset = 131.3; mode = DM_NOACK;
		expect_text = "state H1 (dossier 9.5 variant: P33/P08 ret -4 with ack_polls 1000001, lc_epc at S14, W records keep ret > 0); trigger none (onset not at a 1250 boundary)"; }
	else if (!strcmp(name, "H2")) { onset = 131.3; mode = DM_ZERO;
		expect_text = "state H2 (P08 ret 0, nwords 5, rx[0..9] = 00, ri_branch 4 HOLD)"; }
	else if (!strcmp(name, "H3")) { onset = 131.3; mode = DM_EMPTY;
		expect_text = "state H3 (P08 ret 0, nwords 0, rx all ff, finite ack_polls, ri_branch 5, mouse dx = dy = +16)"; }
	else if (!strcmp(name, "H4")) { onset = 130.0;
		plan_point(26, "S14", 0, 0, 0, DM_LAG);
		expect_text = "trigger H4 at Nop k=26 (tick 32500): W ext_flags b4, t_busy 1, W.p_head = the in-flight P08, step S14 P4 (W ack_polls > 0, drain 0; the Nop receives the P08 reply and its own, nwords 7); thread result -4 (allowed for P4, DESIGN 10.7 step 5); from the next command on the device lags one reply: state N2b (persistent, P08 rx[2] = 0x33, P33 rx[2] = 0x08)"; }
	else if (!strcmp(name, "H5")) { onset = 131.3; mode = DM_BUSY;
		expect_text = "state H5 (P08 ret -5, retries 16, rx[2] = 0x80, nwords 2)"; }
	else if (!strcmp(name, "H6")) { onset = 131.3; mode = DM_FROZEN;
		expect_text = "state H6 (P08 valid, rx[3..8] frozen through D1-D7 while C0 shows the presses; POLL dedupe)"; }
	else if (!strcmp(name, "H7")) { onset = 131.3; h7 = 1;
		expect_text = "state H7 (raw rx follows the presses; (a) push_fail full rises, psposk2 stopped reading; (c) pspmd stopped reading: md_read_ret minus the collector's reads flat)"; }
	else if (!strcmp(name, "H8")) { onset = 131.3; mode = DM_LATCH;
		expect_text = "H8 flags beside state H3 (ACK latch stuck: P08 ack_polls 0, ret 0, nwords 0; gpio_in 0x0002 -> 0x0006; drain 0: in the model the late replies arrive with RX disabled (CR1 = 4) and are lost, so nothing is left to drain; P33 ret 0, W ret 0)"; }
	else if (!strcmp(name, "unclassified")) { onset = 131.3; mode = DM_CODE42;
		expect_text = "H0 / unclassified (P08 valid checksum, rx[2] = 0x42 unknown code, buttons frozen; no row matches)"; }
	else if (!strncmp(name, "mid-irq-", 8)) {
		const char *p = name + 8;

		if (!strcmp(p, "P0")) plan_point(20, "S5", 0, 0, 0x880cef90, -1);
		else if (!strcmp(p, "P1")) plan_point(20, "S7", 0, 0, 0, -1);
		else if (!strcmp(p, "P2")) plan_point(20, "S11p", 1, 0, 0, -1);
		else if (!strcmp(p, "P3")) plan_point(20, "S13", 0, 0, 0, -1);
		else if (!strcmp(p, "P4")) plan_point(20, "S14", 0, 0, 0, -1);
		else if (!strcmp(p, "P5a")) plan_point(20, "S14", -1, 1, 0, -1);
		else if (!strcmp(p, "P5b")) plan_point(20, "S15", 0, 0, 0, -1);
		else if (!strcmp(p, "P6")) plan_point(20, "S18s", 2, 0, 0, -1);
		else if (!strcmp(p, "P6pop")) plan_point(20, "S18d", 2, 0, 0, -1);
		else if (!strcmp(p, "P7")) plan_point(20, "S20", 0, 0, 0, -1);
		else if (!strcmp(p, "append")) {
			int b, k = 10;

			for (b = 0; b < 9; b++) plan_append(k++, 2, b);
			for (b = 0; b < 3; b++) plan_append(k++, 3, b);
			for (b = 0; b < 4; b++) plan_append(k++, 4, b);
			plan_append(k++, 5, 0);
			d0c = 120.0;
		} else if (!strcmp(p, "entry")) {
			plan_append(10, 6, 0);
			plan_append(11, 6, 1);
		} else
			return -1;
		expect_text = "healthy control run (no death) with one Nop aimed into the thread (see truth.json aims)";
		if (!strcmp(p, "P0"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) t_busy 1 at S3 (EPC 0x880cef90) -> P0; both results valid (W ret 34 nwords 2, P08 ret 34 nwords 5)";
		else if (!strcmp(p, "P1"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S7 -> P1; both results valid";
		else if (!strcmp(p, "P2"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S11 (second TX push) -> P2; replies swap: W gets the P08 reply (ret 34, nwords 5), P08 gets the Nop reply (ret 34, nwords 2, a foreign reply, allowed for P2)";
		else if (!strcmp(p, "P3"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S13 -> P3; W gets the P08 reply (nwords 5), P08 ends -4 (allowed for P3); the next poll is healthy";
		else if (!strcmp(p, "P4"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S14 first ACK poll -> P4 (W ack_polls > 0, drain 0, nwords 7); P08 ends -4 (allowed for P4)";
		else if (!strcmp(p, "P5a"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S14 with the ACK latch set -> P5a (W ack_polls 0, drain 5, reply-shaped drain_last); W and P08 end E3 (ret 0, nwords 0); the thread's ACK poll absorbs the Nop's late latch and the next poll is healthy";
		else if (!strcmp(p, "P6"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S18 RX status test, j = 2 -> P6; W drains the rest (drain 3), P08 ends -2 with nwords 2 = j";
		else if (!strcmp(p, "P6pop"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S18 between status test and data read, j = 2 -> P6 (anything allowed); P08 ends -2 with nwords 3";
		else if (!strcmp(p, "P7"))
			expect_text = "healthy control, no death. One straddle: W k=20 (tick 25000) at S20 -> P7; both results valid";
		else if (!strcmp(p, "append"))
			expect_text = "healthy control, no death. Nops k=10..26 aimed at the ring appends (P exit barriers 0..8, POLL 0..2, S 0..3, W reader copy); W k=10 lands in psc_sc_exit (P0, P.wn 0); every record valid";
		else if (!strcmp(p, "entry"))
			expect_text = "healthy control, no death. Nop k=10 (tick 12500) at the P08 entry barrier psc.c:240 (after the wd_calls0 snapshot, before t_busy_p = 1): W t_busy 0, the P08 record wn 1 with no W record linked to it (EPC in ENTRY, P0); Nop k=11 (tick 13750) at psc.c:245 (t_busy_p = 1, before Syscon_cmd): W t_busy 1, W.p_head = that P08, P08 wn 1, step ENTRY = P0, both valid";
		if (!strcmp(p, "P5b")) {
			/* not a healthy control: the late Nop reply leaves the ACK latch set (device model) */
			expect_text = "trigger H4 at Nop k=20 (tick 25000): W t_busy 1, W.p_head = the in-flight P08, step S15 P5b (W ack_polls 0, drain 5, reply-shaped drain_last); W and the thread end E3. "
				"Then, under the device model (UNVERIFIED: a reply arriving after the transaction, with RX disabled, loses its words but still sets the ACK latch), "
				"the Nop's late reply leaves the latch set and the run settles into a persistent one-command lag in which every second reply is lost: "
				"P33 ret 0, nwords 0, ack_polls 0, rx all ff; P08 ret 34, nwords 2, rx[2] = 0x33 (the P33 reply); every later W ret 0, nwords 0. "
				"No DESIGN 6 / 6.1 row covers this state (not N2b: P33 and W carry no frame; not H3: P08 ret > 0), so the DESIGN outcome is trigger H4, state H0 / UNCLASSIFIED with the raw windows";
			truth_onset_tick = 25000;
		}
	} else
		return -1;
	t_onset = onset;
	healthy = onset == 0;
	op_init(onset, d0c);
	end_tick = (unsigned long)(t_pull * 250.0);
	if (mode != DM_NORMAL || h7) {
		/* the device or consumer change happens at onset (world check) */
	}
	onset_mode = mode;
	osk_stopped = 0;
	md_stopped = 0;
	return h7 ? 1 : 0;
}

/* ===================================================== main */
static int scen_h7;
static int onset_applied;

void scen_tick_check(void)
{
	if (!onset_applied && t_onset > 0 && now_s() >= t_onset && !next_aim()) {
		onset_applied = 1;
		if (onset_mode != DM_NORMAL)
			dev_set_mode(onset_mode);
		if (scen_h7) {
			osk_stopped = 1;
			md_stopped = 1;
		}
		ev("ONSET %lu\n", psp_local_tick);
	}
}

static void write_times(const char *dir)
{
	char p[1024];
	FILE *f;
	double off = 10.0;

	snprintf(p, sizeof(p), "%s/times.txt", dir);
	f = fopen(p, "w");
	if (!f)
		return;
#define SW(s) (int)(((s) + off) / 60), fmod((s) + off, 60.0)
	fprintf(f, "uptime_offset=10\nselftest_pass=%d:%05.2f\nc0_start=%d:%05.2f\nc0_end=%d:%05.2f\n",
		SW(40.0), SW(t_c0), SW(t_c0_end));
	if (!healthy)
		fprintf(f, "t_death=%d:%05.2f\n", SW(t_onset + 1.0));
	fprintf(f, "d0_start=%d:%05.2f\npull=%d:%05.2f\n", SW(t_d0), SW(t_pull));
	fclose(f);
}

static void write_truth(const char *dir, const char *name)
{
	char p[1024];
	FILE *f;
	int i;

	snprintf(p, sizeof(p), "%s/truth.json", dir);
	f = fopen(p, "w");
	if (!f)
		return;
	fprintf(f, "{\n  \"scenario\": \"%s\",\n  \"generator\": \"handoff/stage3/ring (real psc.c, syscon.c, joypad_psp.c compiled on the host)\",\n", name);
	fprintf(f, "  \"expected\": \"%s\",\n", expect_text);
	fprintf(f, "  \"onset_uptime_s\": %.3f,\n  \"onset_tick\": %ld,\n",
		truth_onset_tick >= 0 ? truth_onset_tick / 250.0 : t_onset,
		truth_onset_tick >= 0 ? truth_onset_tick : t_onset > 0 ? (long)(t_onset * 250.0) : -1L);
	fprintf(f, "  \"nonce\": \"0x%08x\",\n  \"run\": 1,\n", col_nonce);
	fprintf(f, "  \"build\": \"use the packaged BUILD (deploy/uClinux_TRACE/BUILD): stats words 2, 20-22 carry the release build_id 0x045b27d9 and the release addresses of Syscon_cmd, psc_sc_exit, _pspSysconGetCtrl2\",\n");
	fprintf(f, "  \"aims\": [");
	for (i = 0; i < naims; i++)
		fprintf(f, "%s{\"nop_k\": %d, \"tick\": %d, \"type\": \"%s\", \"kind\": \"%s\", \"nth\": %d, \"barrier\": %d, \"done\": %d}",
			i ? ", " : "", aims[i].k, aims[i].k * WD_CYCLE,
			aims[i].type == 1 ? "mmio-point" : aims[i].type == 2 ? "P-append" :
			aims[i].type == 3 ? "POLL-append" : aims[i].type == 4 ? "S-append" :
			aims[i].type == 6 ? "P-entry" : "W-read",
			aims[i].type == 1 ? host_kind_name(aims[i].kind) : "-", aims[i].nth,
			aims[i].barrier, aims[i].done);
	fprintf(f, "],\n  \"records\": {\"P\": %llu, \"POLL\": %llu, \"W\": %llu, \"S\": %llu, \"M\": %llu},\n",
		(unsigned long long)col_rec_total[0], (unsigned long long)col_rec_total[1],
		(unsigned long long)col_rec_total[2], (unsigned long long)col_rec_total[3],
		(unsigned long long)col_rec_total[4]);
	fprintf(f, "  \"lost\": {\"P\": %llu, \"POLL\": %llu, \"W\": %llu, \"S\": %llu, \"M\": %llu}\n}\n",
		(unsigned long long)col_lost_total[0], (unsigned long long)col_lost_total[1],
		(unsigned long long)col_lost_total[2], (unsigned long long)col_lost_total[3],
		(unsigned long long)col_lost_total[4]);
	fclose(f);
}

static void final_flush(void)
{
	/* the collector's last flush before the pull */
	do_switch(g_cur, T_WRK);
	col_burst();
	g_task[T_WRK]->state = TASK_INTERRUPTIBLE;
	do_switch(T_WRK, T_IDLE);
	g_task[T_WRK]->state = TASK_RUNNING;
}

#ifndef SCEN_NO_MAIN
int main(int argc, char **argv)
{
	const char *name, *out, *evpath;
	u32 seed = 1, i;

	if (argc < 4) {
		fprintf(stderr, "usage: ringsim SCENARIO OUTDIR EVENTS.log\n");
		return 2;
	}
	name = argv[1];
	out = argv[2];
	evpath = argv[3];
	for (i = 0; name[i]; i++)
		seed = seed * 31 + (u8)name[i];
	g_ev = fopen(evpath, "w");
	if (!g_ev) {
		perror(evpath);
		return 2;
	}
	scen_h7 = setup(name);
	if (scen_h7 < 0) {
		fprintf(stderr, "unknown scenario %s\n", name);
		return 2;
	}
	col_nonce = 0x5C000000u ^ (seed & 0x00FFFFFFu);
	ev("SCENARIO %s seed %u nonce %08x end_tick %lu\n", name, seed, col_nonce, end_tick);
	vram_map();
	syms_init();
	tasks_init();
	dev_init(seed);
	g_after_nop = after_nop;
	g_copy_hook = copy_hook;

	/* prom_init: the boot Nop, interrupts off (psp.c:576-580) */
	g_ie = 0;
	g_count = 2000;
	g_abs = 2000;
	psc_k.wd_ctx = PSC_WDCTX_BOOT;
	g_in_boot_nop = 1;
	pspSysconNop();
	g_in_boot_nop = 0;
	psc_k.wd_ctx = PSC_WDCTX_NONE;
	g_ie = 1;
	sim_advance(200000);
	/* serial initcall: pspSysconCtrlHRPower(1) (serial_psp.c:352), M ring */
	do_switch(T_IDLE, T_INIT);
	pspSysconCtrlHRPower(1);
	/* joypad module init (real): registers, creates the thread */
	jp_host_init();
	/* psc_init (real late_initcall): /proc/psc, guards, build_id, printk */
	psc_host_late_initcall_psc_init();
	sim_advance(300000);
	do_switch(T_INIT, T_IDLE);
	while (psp_local_tick < 500)
		sim_idle_tick();
	/* rc.sysinit: mount /ms0 (psc_fat_mounted), psposk2 opens /dev/joypad */
	do_switch(T_IDLE, T_OSK);
	col_mount();
	jp_host_osk_open();
	do_switch(T_OSK, T_IDLE);
	while (psp_local_tick < 750)
		sim_idle_tick();
	/* the joypad thread starts (3 s) and runs until the scenario ends;
	 * the collector starts at 20 s (inside the world loop) */
	g_wrk_started = 0;
	sim_advance(1200);
	do_switch(T_IDLE, T_JP);
	poll_top_count = g_count;
	ev("LT %lu %u\n", psp_local_tick, g_count);
	jp_host_thread();
	/* D8 ends, the pull: one last flush, then write the files */
	do_switch(g_cur, T_IDLE);
	final_flush();
	col_write(out);
	write_times(out);
	write_truth(out, name);
	col_report(stdout);
	dev_report(stdout);
	fprintf(stdout, "scenario %s end tick %lu aims %d\n", name, psp_local_tick, naims);
	for (i = 0; i < (u32)naims; i++)
		if (!aims[i].done)
			fprintf(stdout, "WARNING aim k=%d not done\n", aims[i].k);
	fclose(g_ev);
	return 0;
}
#endif /* SCEN_NO_MAIN */
