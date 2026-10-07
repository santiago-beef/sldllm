/*
 * arch/mips/psp/psc.c - PSC trace: rings, records, stats, /proc/psc.
 *
 * Specification: handoff/design/DESIGN.md revision 6 (G1 PASS 2026-10-06).
 * Record formats: <linux/psc_format.h>; kernel state: <asm/psc.h>. Comments
 * cite DESIGN sections. Rules kept everywhere in this file (3.4, 7.1, D9,
 * D10, G2 C3): no lock, no interrupt masking, no sleeping or allocation
 * outside the /proc file operations, no MMIO, no floating point, and exactly
 * one printk (psc_init).
 */
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/sched.h>
#include <linux/string.h>
#include <linux/jiffies.h>
#include <linux/fs.h>
#include <linux/proc_fs.h>
#include <linux/hardirq.h>
#include <asm/uaccess.h>
#include <asm/div64.h>
#include <asm/mipsregs.h>
#include <asm/ptrace.h>
#include <asm/psp.h>
#include <asm/ipl_sdk/syscon.h>
#include <asm/psc.h>

/* ------------------------------------------------------------------ */
/* Memory (3.1)                                                        */
/* ------------------------------------------------------------------ */

/*
 * All rings, the stats block and the kernel state in one BSS object, zeroed
 * by head.S before start_kernel (arch/mips/kernel/head.S:182-187), so a
 * record can be appended from the first Syscon_cmd call (the boot Nop in
 * prom_init) on. Nothing is ever allocated (3.1, G2 C5).
 */
struct psc_mem psc_mem;
struct task_struct *psc_jp_task;

/* Guard words (3.1, A2 OE4): seven distinct constants, set once by psc_init
 * and compared by T2d once a second; a change is counted, never repaired. */
#define PSC_GUARD(n)	(0x50534730u + (n))	/* "0GSP".."6GSP" */

static u32 *const psc_guard_word[7] = {
	&psc_mem.g0, &psc_mem.g1, &psc_mem.g2, &psc_mem.g3,
	&psc_mem.g4, &psc_mem.g5, &psc_mem.g6,
};

/* ------------------------------------------------------------------ */
/* Small helpers                                                        */
/* ------------------------------------------------------------------ */

static inline u32 psc_sat8(u32 v)  { return v > 0xFF ? 0xFF : v; }
static inline u32 psc_sat16(u32 v) { return v > 0xFFFF ? 0xFFFF : v; }
static inline u32 psc_sat_add(u32 a, u32 b) { return a + b < a ? 0xFFFFFFFFu : a + b; }

/* Count units between two (tick, Count) stamps, saturating; 0 if negative
 * (a Count read in a long tick can exceed CPT, 1.1). */
static u32 psc_dcount(u32 t0, u32 c0, u32 t1, u32 c1)
{
	u32 dt = t1 - t0;
	unsigned long long v;

	if (dt > 4861)				/* 4861 x 883651 >= 2^32 */
		return 0xFFFFFFFFu;
	v = (unsigned long long)dt * PSC_CPT + c1;
	if (v < c0)
		return 0;
	v -= c0;
	return v > 0xFFFFFFFFull ? 0xFFFFFFFFu : (u32)v;
}

/* Outcome counter index (1.7 words 31-51). */
static inline int psc_oc_index(int ret, u32 nwords)
{
	if (ret > 0)
		return PSC_OC_POS;
	if (ret == 0)
		return nwords ? PSC_OC_ZERO_WORDS : PSC_OC_ZERO_NOWORDS;
	switch (ret) {
	case -2: return PSC_OC_E2;
	case -3: return PSC_OC_E3;
	case -4: return PSC_OC_E4;
	default: return PSC_OC_E5;
	}
}

/*
 * EPC "inside Syscon_cmd" (SC lc_flags b2, W ext_flags b3): the transaction
 * function, from its first instruction to the next function of syscon.c in
 * the link (gcc does not keep source order; one object's functions are
 * contiguous, so the lowest syscon.c function above Syscon_cmd ends it).
 * Computed once, on first use; pure arithmetic, safe in any context.
 */
static u32 psc_syscon_end;

static u32 psc_syscon_end_calc(void)
{
	const u32 start = (u32)(unsigned long)Syscon_cmd;
	const u32 f[] = {
		(u32)(unsigned long)pspSyscon_init,
		(u32)(unsigned long)pspSyscon_tx_dword,
		(u32)(unsigned long)pspSyscon_rx_dword,
		(u32)(unsigned long)pspSyscon_tx_noparam,
		(u32)(unsigned long)Syscon_wait,
		(u32)(unsigned long)pspSysconCtrlLED,
		(u32)(unsigned long)_pspSysconGetCtrl2,
	};
	u32 end = start + 0x1000;	/* Syscon_cmd is < 0x500 bytes */
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(f); i++)
		if (f[i] > start && f[i] < end)
			end = f[i];
	return end;
}

static inline int psc_epc_in_syscon(u32 epc)
{
	u32 end = PSC_RD(psc_syscon_end);

	if (unlikely(!end)) {
		end = psc_syscon_end_calc();
		PSC_WR(psc_syscon_end, end);
	}
	return epc >= (u32)(unsigned long)Syscon_cmd && epc < end;
}

/* The interrupted context's registers (1.3): used only when the frame lies
 * inside the current task's kernel stack. */
static struct pt_regs *psc_cur_regs(void)
{
	struct thread_info *ti = current_thread_info();
	unsigned long r = (unsigned long)ti->regs;
	unsigned long lo = (unsigned long)ti + sizeof(*ti);
	unsigned long hi = (unsigned long)ti + THREAD_SIZE;

	if ((r & 3) || r < lo || r + sizeof(struct pt_regs) > hi)
		return NULL;
	return (struct pt_regs *)r;
}

/* Registers 2..15, then 24, 25 (1.3 `r`). */
static inline void psc_copy_regs(u32 *dst, const struct pt_regs *regs)
{
	int i;

	for (i = 0; i < 14; i++)
		dst[i] = regs->regs[2 + i];
	dst[14] = regs->regs[24];
	dst[15] = regs->regs[25];
}

/* Task class (2.11): the collector's table, else 6 kernel thread, else 7. */
static u32 psc_class(struct task_struct *t)
{
	u32 pid = (u32)t->pid & 0x00FFFFFFu;
	int i;

	for (i = 0; i < PSC_PIDCLASS_SLOTS; i++) {
		u32 w = PSC_RD(psc_st.pid_class[i]);

		if (w && PSC_PIDCLASS_PID(w) == pid)
			return PSC_PIDCLASS_CLASS(w);
	}
	return t->mm ? PSC_CLASS_OTHER : PSC_CLASS_KTHREAD;
}

static inline int psc_xfer_index(void)
{
	if (PSC_RD(psc_k.wd_ctx))
		return PSC_XFER_W;
	if (current == PSC_RD(psc_jp_task))
		return PSC_XFER_P;
	return PSC_XFER_M;
}

/* ------------------------------------------------------------------ */
/* Syscon_cmd recording (2.1)                                           */
/* ------------------------------------------------------------------ */

/*
 * The transaction's exit label (syscon.c PSC_XFER_OUT) calls this with its
 * capture slots and two registers. The area is chosen by the same rule as
 * the origin (1.8); its only writer is that context (P thread, W Nop, M
 * other threads).
 */
void psc_xfer_out(const struct psc_xfer_raw *raw)
{
	psc_k.xfer[psc_xfer_index()] = *raw;
}

/*
 * A1 (2.1): origin (1.8), entry time, snapshots for wn, ms_delta and
 * preempt_delta, ctx bits; P: in-flight words. Inline, no call.
 */
static inline void psc_sc_entry(struct psc_scratch *sc, const u8 *tx, const u8 *rx)
{
	struct task_struct *tsk = current;
	u32 tick, count, origin, ctx, wd;

	wd = PSC_RD(psc_k.wd_ctx);
	if (wd == PSC_WDCTX_TIMER)
		origin = PSC_ORIGIN_WT;
	else if (wd == PSC_WDCTX_BOOT)
		origin = PSC_ORIGIN_WB;
	else if (tsk == PSC_RD(psc_jp_task))
		origin = PSC_ORIGIN_P;
	else
		origin = PSC_ORIGIN_M;

	sc->tx = tx;
	sc->rx = rx;
	psc_ts_read(&tick, &count);
	sc->tick_in = tick;
	sc->c_in = count;
	sc->wd_calls0 = PSC_RD(psc_st.wd_calls);
	sc->led_calls0 = PSC_RD(psc_st.led_calls);
	sc->nivcsw0 = tsk->nivcsw;

	ctx = origin;
	if (read_c0_status() & 1)
		ctx |= PSC_CTX_IE;
	if (in_interrupt())
		ctx |= PSC_CTX_IN_INTERRUPT;
	if (tsk == PSC_RD(psc_jp_task))
		ctx |= PSC_CTX_JP_TASK;
	if (preempt_count())
		ctx |= PSC_CTX_PREEMPT_CNT;
	if (origin <= PSC_ORIGIN_M && signal_pending(tsk))
		ctx |= PSC_CTX_SIGPENDING;
	sc->ctx = ctx;
	sc->origin = origin;

	if (origin == PSC_ORIGIN_P) {
		psc_k.t_cmd = tx[0];
		psc_k.t_entry_tick = tick;
		psc_k.t_entry_c = count;
		sc->cmd_id = ++psc_k.t_cmd_id;
		barrier();
		PSC_WR(psc_k.t_busy_p, 1);
	} else if (origin == PSC_ORIGIN_M) {
		PSC_WR(psc_k.t_busy_m, 1);
	}
	barrier();
}

/*
 * The common 80-byte SC part (1.2) from the scratch and the hand-off.
 * Derived sentinels (2.1 A2, A4): spin_ack is not reset per attempt, so
 * ack_polls = 0xFFFFFFFF ("loop not reached") whenever ret is -3, the one
 * exit that does not reach the ACK loop; spi_st9 and spi_sttx are 0 on -3;
 * drain is 0 when the drain loop was not entered (spin left at its per-
 * attempt 0), and drain_last is 0 when drain is 0. nwords from i + 2 of the
 * receive loop (t0): k words leave t0 = 2k + 2 for k <= 7; after 8 words
 * t0 = 16 as after 7, and 8 is reported when rx[14..15] is not the 0xff
 * prefill (see IMPLEMENTATION notes, nwords 7/8).
 */
static void psc_fill_sc(struct psc_sc *r, const struct psc_scratch *sc,
			const struct psc_xfer_raw *x, u32 tick_out, u32 c_out,
			u32 wn, u32 w_head, u32 ms_delta, u32 pdelta)
{
	int ret = sc->result;
	u32 nwords, drain;

	memset((char *)r + 4, 0, sizeof(*r) - 4);	/* seq stays invalid */
	r->tick_in = sc->tick_in;
	r->c_in = sc->c_in;
	r->c_out = c_out;
	r->dtick = psc_sat16(tick_out - sc->tick_in);
	r->cmd = sc->tx[0];
	r->txlen = sc->tx[1];
	r->ret = ret;

	if (ret == -3 || ret == -4 || x->t0 < 2)
		nwords = 0;
	else if (x->t0 < 16)
		nwords = (x->t0 - 2) >> 1;
	else
		nwords = (sc->rx[14] == 0xff && sc->rx[15] == 0xff) ? 7 : 8;
	r->nwords = nwords;
	r->retries = psc_sat8(x->t8);

	r->ack_polls = (ret == -3) ? PSC_ACK_POLLS_NOT_REACHED
				   : PSC_SYSCON_SPIN_MAX - x->spin_ack;
	drain = x->spin ? psc_sat16(PSC_SYSCON_SPIN_MAX - x->spin) : 0;
	r->drain = drain;
	r->drain_last = drain ? (u16)x->dlast : 0;
	r->gpio_in = (u16)x->gin;
	r->spi_st9 = (ret == -3) ? 0 : (u16)x->st9;
	r->spi_sttx = (ret == -3) ? 0 : (u16)x->sttx;

	r->ctx = sc->ctx;
	r->wn = psc_sat8(wn);
	r->w_head_lo = (u16)w_head;
	r->ms_delta = psc_sat8(ms_delta);
	r->preempt_delta = psc_sat8(pdelta);
	memcpy(r->rx, sc->rx, PSC_RX_LEN);
}

/* The thread-only parts of a P record: lc (2.3), LED (2.4), preemption
 * holder (2.11), panel flag (2.10). psc_t_busy_p is already 0, so none of
 * these words can change for this cmd_id any more. */
static void psc_fill_thread(struct psc_sc *r, const struct psc_scratch *sc)
{
	u32 id = sc->cmd_id, s1, s2, flags, epc, tick, n, cause, wdt, valid;
	u32 tot, wrk, pf, c0, c1;

	do {
		s1 = PSC_RD(psc_k.lc_seq);
		barrier();
		valid = (psc_k.lc_cmd_id == id) && psc_k.lc_n;
		epc = psc_k.lc_epc;
		tick = psc_k.lc_tick;
		n = psc_k.lc_n;
		cause = psc_k.lc_cause;
		wdt = psc_k.lc_wdtick;
		barrier();
		s2 = PSC_RD(psc_k.lc_seq);
	} while (s1 != s2 || (s1 & 1));

	flags = 0;
	r->lc_dtick = PSC_LC_DTICK_NONE;
	if (valid) {
		flags |= PSC_LC_F_VALID;
		if (cause & 0x80000000u)
			flags |= PSC_LC_F_BD;
		if (psc_epc_in_syscon(epc))
			flags |= PSC_LC_F_IN_SYSCON;
		if (wdt)
			flags |= PSC_LC_F_WD_TICK;
		r->lc_epc = epc;
		r->lc_dtick = psc_sat16(tick - sc->tick_in);
		r->lc_n = psc_sat8(n);
	}
	if (PSC_RD(psc_k.lc_nest_id) == id)
		flags |= PSC_LC_F_NESTED_SEEN;
	if (PSC_RD(psc_k.panel_cmd_id) == id)
		flags |= PSC_LC_F_PANEL;
	r->lc_flags = flags;

	if (PSC_RD(psc_k.led_cmd_id) == id) {
		r->led_or = psc_k.led_cmd_or;
		r->led_pid = (u16)psc_k.led_cmd_pid;
	}

	do {
		s1 = PSC_RD(psc_k.pre_seq);
		barrier();
		valid = (psc_k.pre_cmd_id == id);
		tot = psc_k.pre_tot;
		wrk = psc_k.pre_wrk;
		pf = psc_k.pre_flags;
		c0 = psc_k.pre_cls0;
		c1 = psc_k.pre_cls1;
		n = psc_k.pre_n;
		barrier();
		s2 = PSC_RD(psc_k.pre_seq);
	} while (s1 != s2 || (s1 & 1));
	if (valid) {
		pf |= PSC_PRE_F_VALID;
		if ((tot >> 8) > 0xFFFF || (wrk >> 8) > 0xFFFF)
			pf |= PSC_PRE_F_SAT;
		r->pre_tot = psc_sat16(tot >> 8);
		r->pre_wrk = psc_sat16(wrk >> 8);
		r->pre_cls = PSC_PRE_CLS_MAKE(c0, c1);
		r->pre_flags = pf;
	}
}

/* W extension (1.3), timer Nop only, interrupts off. */
static void psc_fill_wext(struct psc_wext *e)
{
	struct pt_regs *regs = psc_cur_regs();
	u32 f = 0, pc = preempt_count();

	if (regs) {
		f |= PSC_EXT_F_REGS_VALID;
		e->epc = regs->cp0_epc;
		e->cause = regs->cp0_cause;
		e->status = regs->cp0_status;
		e->ra = regs->regs[31];
		e->sp = regs->regs[29];
		psc_copy_regs(e->r, regs);
		if (regs->cp0_status & ST0_CU0)
			f |= PSC_EXT_F_KMODE;
		if (psc_epc_in_syscon(regs->cp0_epc))
			f |= PSC_EXT_F_IN_SYSCON;
	}
	e->pid = current->pid;
	e->p_head = psc_k.head[PSC_RING_P];
	e->jp_loop = psc_st.jp_loop;
	e->t_entry_tick = psc_k.t_entry_tick;
	e->t_entry_c = psc_k.t_entry_c;
	e->t_busy = (psc_k.t_busy_p ? PSC_TBUSY_P : 0) | (psc_k.t_busy_m ? PSC_TBUSY_M : 0);
	e->jp_stage = (u8)psc_st.jp_stage;
	if (current == psc_jp_task)
		f |= PSC_EXT_F_JP_TASK;
	if (psc_k.t_busy_p && psc_k.lc_cmd_id == psc_k.t_cmd_id && psc_k.lc_n)
		f |= PSC_EXT_F_LC_VALID;
	if (psc_st.ms_ip_word & PSC_MSIP_ACTIVE)
		f |= PSC_EXT_F_MS_ACTIVE;
	if (pc & (SOFTIRQ_MASK | HARDIRQ_MASK))
		f |= PSC_EXT_F_NESTED;
	e->ext_flags = f;
	e->cur_pcnt = (u8)pc;
	e->c_pre = psc_k.c_pre_cur;
	/* the lc block as the previous ticks left it (T2 runs after the Nop) */
	e->lc_tick = psc_k.lc_tick;
	e->lc_c_pre = psc_k.lc_c_pre;
	e->lc_cmd_id = psc_k.lc_cmd_id;
	e->lc_epc = psc_k.lc_epc;
	e->lc_cause = psc_k.lc_cause;
	e->lc_ra = psc_k.lc_ra;
	e->lc_sp = psc_k.lc_sp;
	memcpy(e->lc_r, psc_k.lc_r, sizeof(e->lc_r));
	e->lc_n = (u16)psc_sat16(psc_k.lc_n);
}

/*
 * psc_sc_exit (2.1): one record per Syscon_cmd call in every context.
 * Order: exit time and the wn/ms_delta/preempt_delta snapshots first, then
 * the in-flight flag is cleared, so a Nop, an LED operation or a preemption
 * either falls before the snapshots and the cleared flag or after both
 * (W t_busy and the record's wn agree). Then invalidate, fill, publish (3.4).
 */
int psc_sc_exit(struct psc_scratch *sc)
{
	u32 origin = sc->origin, tout, cout, wd1, wh1, led1, niv1, s, t2, c2, cost;
	const struct psc_xfer_raw *x;
	struct psc_sc *r;
	u32 *oc;

	psc_ts_read(&tout, &cout);
	wd1 = PSC_RD(psc_st.wd_calls);		/* wd_calls and the W head move */
	wh1 = PSC_RD(psc_k.head[PSC_RING_W]);	/* together, inside the Nop */
	led1 = PSC_RD(psc_st.led_calls);
	niv1 = current->nivcsw;
	barrier();
	if (origin == PSC_ORIGIN_P)
		PSC_WR(psc_k.t_busy_p, 0);
	else if (origin == PSC_ORIGIN_M)
		PSC_WR(psc_k.t_busy_m, 0);
	barrier();

	if (origin == PSC_ORIGIN_P) {
		x = &psc_k.xfer[PSC_XFER_P];
		s = psc_k.head[PSC_RING_P];
		r = &psc_mem.p[s & (PSC_P_ENTRIES - 1)];
		PSC_WR(r->seq, PSC_SEQ_WRITING);
		barrier();
		psc_fill_sc(r, sc, x, tout, cout, wd1 - sc->wd_calls0, wh1,
			    led1 - sc->led_calls0, niv1 - sc->nivcsw0);
		psc_fill_thread(r, sc);
		barrier();
		PSC_WR(r->seq, s);
		barrier();
		PSC_WR(psc_k.head[PSC_RING_P], s + 1);

		oc = r->cmd == 0x08 ? psc_st.oc_p08 : r->cmd == 0x33 ? psc_st.oc_p33 : NULL;
		if (oc)
			oc[psc_oc_index(r->ret, r->nwords)]++;
		if (r->wn)
			psc_st.p_nested++;
		if (r->dtick)
			psc_st.p_ticked++;
		if (r->cmd == 0x08)
			psc_k.last_p08 = s + 1;
		psc_ts_read(&t2, &c2);
		cost = psc_dcount(tout, cout, t2, c2);
		psc_st.p_rec_cost_last = cost;
		if (cost > psc_st.p_rec_cost_max)
			psc_st.p_rec_cost_max = cost;
	} else if (origin == PSC_ORIGIN_M) {
		/* fill-once (3.1); concurrent M writers are not known (3.4) */
		s = psc_k.head[PSC_RING_M];
		if (s >= PSC_M_ENTRIES) {
			psc_st.m_dropped++;
		} else {
			x = &psc_k.xfer[PSC_XFER_M];
			r = &psc_mem.m[s];
			PSC_WR(r->seq, PSC_SEQ_WRITING);
			barrier();
			psc_fill_sc(r, sc, x, tout, cout, wd1 - sc->wd_calls0, wh1,
				    led1 - sc->led_calls0, niv1 - sc->nivcsw0);
			r->lc_dtick = PSC_LC_DTICK_NONE;
			barrier();
			PSC_WR(r->seq, s);
			barrier();
			PSC_WR(psc_k.head[PSC_RING_M], s + 1);
		}
	} else {
		/* WT (timer Nop, IE off) or WB (boot Nop): the W ring (1.3) */
		struct psc_w *w;

		x = &psc_k.xfer[PSC_XFER_W];
		s = psc_k.head[PSC_RING_W];
		w = &psc_mem.w[s & (PSC_W_ENTRIES - 1)];
		PSC_WR(w->sc.seq, PSC_SEQ_WRITING);
		barrier();
		psc_fill_sc(&w->sc, sc, x, tout, cout, 0, s /* its own seq */,
			    led1 - sc->led_calls0, 0);
		memset(&w->ext, 0, sizeof(w->ext));
		if (origin == PSC_ORIGIN_WT)
			psc_fill_wext(&w->ext);
		barrier();
		PSC_WR(w->sc.seq, s);
		barrier();
		PSC_WR(psc_k.head[PSC_RING_W], s + 1);

		psc_st.wd_calls++;
		psc_st.wd_last_tick = sc->tick_in;
		psc_st.oc_w[psc_oc_index(w->sc.ret, w->sc.nwords)]++;
		psc_ts_read(&t2, &c2);
		cost = psc_dcount(tout, cout, t2, c2);
		if (cost > psc_st.w_rec_cost_max)
			psc_st.w_rec_cost_max = cost;
	}
	return sc->result;
}

/*
 * The recording wrapper (2.1): every caller of Syscon_cmd in syscon.c calls
 * this instead. A1 inline, the unchanged transaction, then psc_sc_exit.
 */
int psc_syscon_cmd(u8 *tx_buf, u8 *rx_buf)
{
	struct psc_scratch sc;

	psc_sc_entry(&sc, tx_buf, rx_buf);
	sc.result = Syscon_cmd(tx_buf, rx_buf);
	return psc_sc_exit(&sc);
}

/* ------------------------------------------------------------------ */
/* Timer interrupt: T1 accounting, T2a, T2d (2.3)                       */
/* ------------------------------------------------------------------ */

static void psc_t2d(u32 tick)
{
	int i;

	psc_panel_t2d(tick);			/* 2.10 */

	if (psc_k.guards_armed) {		/* 3.1 */
		for (i = 0; i < 7; i++) {
			if (*psc_guard_word[i] != PSC_GUARD(i)) {
				if (!psc_st.kguard_bad)
					psc_st.kguard_first_tick = tick;
				psc_st.kguard_bad++;
			}
		}
	}
}

/*
 * T2 (2.3): after psp_watchdog_tick(), before psp_uart3_txrx_tick(), in the
 * timer interrupt with IE off and before irq_enter(), so preempt_count()
 * still describes the interrupted context.
 */
void psc_tick_hook(u32 c_pre)
{
	u32 tick = psp_local_tick, lo;

	/* T1 accounting (c_pre was read before the Count reset) */
	lo = psc_st.total_counts_lo + c_pre;
	if (lo < c_pre)
		psc_st.total_counts_hi++;
	psc_st.total_counts_lo = lo;
	if (c_pre > psc_st.c_pre_max)
		psc_st.c_pre_max = c_pre;
	if (c_pre > PSC_CPT + PSC_CPT / 2)
		psc_st.long_ticks++;

	/* T2a: lc words, uncapped, never from a nested tick (1.2) */
	if (psc_k.t_busy_p && current == psc_jp_task) {
		if (preempt_count() & (SOFTIRQ_MASK | HARDIRQ_MASK)) {
			psc_st.lc_nested++;
			psc_k.lc_nest_id = psc_k.t_cmd_id;
		} else {
			struct pt_regs *regs = psc_cur_regs();

			psc_k.lc_seq++;
			barrier();
			psc_k.lc_tick = tick;
			psc_k.lc_c_pre = c_pre;
			if (regs) {
				psc_k.lc_epc = regs->cp0_epc;
				psc_k.lc_cause = regs->cp0_cause;
				psc_k.lc_ra = regs->regs[31];
				psc_k.lc_sp = regs->regs[29];
				psc_copy_regs(psc_k.lc_r, regs);
			} else {
				psc_k.lc_epc = 0;
				psc_k.lc_cause = 0;
				psc_k.lc_ra = 0;
				psc_k.lc_sp = 0;
				memset(psc_k.lc_r, 0, sizeof(psc_k.lc_r));
			}
			if (psc_k.lc_cmd_id != psc_k.t_cmd_id) {
				psc_k.lc_cmd_id = psc_k.t_cmd_id;
				psc_k.lc_n = 0;
			}
			if (psc_k.lc_n < 0xFFFF)
				psc_k.lc_n++;
			psc_k.lc_wdtick = (psc_st.wd_calls && psc_st.wd_last_tick == tick);
			barrier();
			psc_k.lc_seq++;
		}
	}

	/* T2d: once a second at ticks = 125 mod 250, never a watchdog tick */
	if (unlikely(psc_k.t2d_due == 0))
		psc_k.t2d_due = 125;
	if (unlikely(tick == psc_k.t2d_due)) {
		psc_k.t2d_due = tick + 250;
		psc_t2d(tick);
	}
}

/* ------------------------------------------------------------------ */
/* LED read-modify-write and Memory Stick segments (2.4)                */
/* ------------------------------------------------------------------ */

void psc_note_led(int set, u32 v)
{
	psc_st.led_calls++;
	if (PSC_RD(psc_k.t_busy_p) | PSC_RD(psc_k.t_busy_m))
		psc_st.led_calls_t_busy++;
	if (set) {
		psc_st.led_or_set_run |= v;
		psc_k.seg_set_or |= v;
		if (v & 0x08)
			psc_k.seg_flags |= PSC_S_F_SET_B3;
	} else {
		psc_st.led_or_clr_run |= v;
		psc_k.seg_clr_or |= v;
		if (v & 0x08)
			psc_k.seg_flags |= PSC_S_F_CLR_B3;
	}
	psc_k.seg_led_ops++;
	if (PSC_RD(psc_k.t_busy_p)) {
		u32 id = PSC_RD(psc_k.t_cmd_id);

		if (psc_k.led_cmd_id != id) {
			psc_k.led_cmd_or = 0;
			psc_k.led_cmd_id = id;
		}
		psc_k.led_cmd_or |= v;
		psc_k.led_cmd_pid = current->pid;
	}
}

/* After down() of s_psp_ms_rw_sem (ms_psp.c:333, :360). */
void psc_ms_seg_begin(u32 sector, u32 nsect, int write)
{
	u32 t, c;

	psc_ts_read(&t, &c);
	psc_k.s_tick_on = t;
	psc_k.s_c_on = c;
	psc_k.s_p_head = PSC_RD(psc_k.head[PSC_RING_P]);
	psc_k.s_busy_in = (PSC_RD(psc_k.t_busy_p) ? 1 : 0) | (PSC_RD(psc_k.t_busy_m) ? 2 : 0);
	psc_k.seg_led_ops = 0;
	psc_k.seg_set_or = 0;
	psc_k.seg_clr_or = 0;
	psc_k.seg_flags = 0;
	psc_st.ms_ip_tick = t;
	psc_st.ms_ip_sector = sector;
	barrier();
	PSC_WR(psc_st.ms_ip_word, ((u32)current->pid & 0xFFFF) | ((nsect & 0xFF) << 16) |
	       PSC_MSIP_ACTIVE | (write ? PSC_MSIP_WRITE : 0));
}

/* Before up() (ms_psp.c:351, :378): the S record (1.5), marker cleared. */
void psc_ms_seg_end(u32 sector, u32 nsect, int write, int rt, int meta)
{
	u32 t, c, s, f;
	struct psc_s *r;

	psc_ts_read(&t, &c);
	s = psc_k.head[PSC_RING_S];
	r = &psc_mem.s[s & (PSC_S_ENTRIES - 1)];
	PSC_WR(r->seq, PSC_SEQ_WRITING);
	barrier();
	memset((char *)r + 4, 0, sizeof(*r) - 4);
	r->tick_on = psc_k.s_tick_on;
	r->c_on = psc_k.s_c_on;
	r->c_off = c;
	r->sector = sector;
	r->dtick = psc_sat16(t - psc_k.s_tick_on);
	r->pid = (u16)current->pid;
	r->nsect = psc_sat8(nsect);
	f = psc_k.seg_flags;
	if (write)
		f |= PSC_S_F_WRITE;
	if (rt < 0)
		f |= PSC_S_F_ERROR;
	if (psc_k.s_busy_in & 1)
		f |= PSC_S_F_P_ENTRY;
	if (PSC_RD(psc_k.t_busy_p))
		f |= PSC_S_F_P_EXIT;
	if ((psc_k.s_busy_in & 2) || PSC_RD(psc_k.t_busy_m))
		f |= PSC_S_F_M;
	if (meta)
		f |= PSC_S_F_META;
	r->flags = f;
	r->p_head_lo = (u16)psc_k.s_p_head;
	r->led_ops = psc_sat8(psc_k.seg_led_ops);
	r->rd_set_or = psc_k.seg_set_or;
	r->rd_clr_or = psc_k.seg_clr_or;
	barrier();
	PSC_WR(r->seq, s);
	barrier();
	PSC_WR(psc_k.head[PSC_RING_S], s + 1);

	if (write)
		psc_st.ms_seg_wr++;
	else
		psc_st.ms_seg_rd++;
	if (rt < 0)
		psc_st.ms_err++;
	barrier();
	PSC_WR(psc_st.ms_ip_word, psc_st.ms_ip_word & ~PSC_MSIP_ACTIVE);
}

/* ------------------------------------------------------------------ */
/* Scheduler hooks (2.11): rq lock held, interrupts off                 */
/* ------------------------------------------------------------------ */

/* Hook W: try_to_wake_up(), just before success = 1, p == the thread. */
void psc_sched_wake_slow(void)
{
	u32 t, c;

	psc_ts_read(&t, &c);
	psc_k.wk_seq++;
	barrier();
	psc_k.wk_t0_tick = psc_k.wk_last_tick = t;
	psc_k.wk_t0_c = psc_k.wk_last_c = c;
	psc_k.wk_acc = 0;
	psc_k.wk_nsw = 0;
	psc_k.wk_cls0 = psc_class(current);
	psc_k.wk_pending = 1;
	barrier();
	psc_k.wk_seq++;
}

/* Hook S: schedule(), prev != next, before context_switch(). */
void psc_sched_switch_slow(struct task_struct *prev, struct task_struct *next)
{
	u32 t, c, d, cls, delay;

	psc_ts_read(&t, &c);

	if (psc_k.wk_pending) {
		d = psc_dcount(psc_k.wk_last_tick, psc_k.wk_last_c, t, c);
		cls = psc_class(prev);
		if (cls == PSC_CLASS_WRK || cls == PSC_CLASS_SUP)
			psc_k.wk_acc = psc_sat_add(psc_k.wk_acc, d);
		psc_k.wk_last_tick = t;
		psc_k.wk_last_c = c;
		psc_k.wk_nsw++;
		if (next == psc_jp_task) {
			delay = psc_dcount(psc_k.wk_t0_tick, psc_k.wk_t0_c, t, c) >> 8;
			psc_k.wk_seq++;
			barrier();
			psc_k.wk_pub_delay = psc_sat16(delay);
			psc_k.wk_pub_wrk = psc_sat16(psc_k.wk_acc >> 8);
			psc_k.wk_pub_cls0 = psc_k.wk_cls0;
			psc_k.wk_pub_cls1 = cls;
			psc_k.wk_pub_nsw = psc_sat8(psc_k.wk_nsw);
			psc_st.wk_count++;
			if (delay > psc_st.wk_max)
				psc_st.wk_max = delay;
			barrier();
			psc_k.wk_seq++;
			psc_k.wk_pending = 0;
		}
	}

	if (prev == psc_jp_task && prev->state == TASK_RUNNING && PSC_RD(psc_k.t_busy_p)) {
		/* the thread is switched out involuntarily inside a command */
		u32 id = PSC_RD(psc_k.t_cmd_id);

		psc_k.pre_seq++;
		barrier();
		if (psc_k.pre_cmd_id != id) {
			psc_k.pre_cmd_id = id;
			psc_k.pre_tot = 0;
			psc_k.pre_wrk = 0;
			psc_k.pre_n = 0;
			psc_k.pre_flags = 0;
			psc_k.pre_cls0 = psc_class(next);
			psc_k.pre_cls1 = 0;
		} else {
			psc_k.pre_flags |= PSC_PRE_F_MULTI;
		}
		psc_k.pre_t0_tick = psc_k.pre_last_tick = t;
		psc_k.pre_t0_c = psc_k.pre_last_c = c;
		psc_k.pre_on = 1;
		psc_st.pre_count++;
		barrier();
		psc_k.pre_seq++;
	} else if (psc_k.pre_on) {
		psc_k.pre_seq++;
		barrier();
		d = psc_dcount(psc_k.pre_last_tick, psc_k.pre_last_c, t, c);
		cls = psc_class(prev);
		if (cls == PSC_CLASS_WRK || cls == PSC_CLASS_SUP)
			psc_k.pre_wrk = psc_sat_add(psc_k.pre_wrk, d);
		else
			psc_k.pre_flags |= PSC_PRE_F_OTHER_HOLDER;
		if (cls >= PSC_CLASS_OSK && cls <= PSC_CLASS_PDFLUSH)
			psc_k.pre_flags |= PSC_PRE_F_CLS345;
		psc_k.pre_last_tick = t;
		psc_k.pre_last_c = c;
		if (next == psc_jp_task) {
			psc_k.pre_tot = psc_sat_add(psc_k.pre_tot,
				psc_dcount(psc_k.pre_t0_tick, psc_k.pre_t0_c, t, c));
			psc_k.pre_cls1 = cls;
			psc_k.pre_n++;
			psc_k.pre_on = 0;
		}
		barrier();
		psc_k.pre_seq++;
	}
}

/* ------------------------------------------------------------------ */
/* The joypad thread (1.4, 2.5) [T]                                     */
/* ------------------------------------------------------------------ */

void psc_jp_thread_start(void)
{
	psc_st.jp_pid = current->pid;
	barrier();
	PSC_WR(psc_jp_task, current);
}

/* Loop top (joypad_psp.c:458). */
void psc_poll_begin(void)
{
	struct psc_poll *p = &psc_k.poll;
	u32 t, c, cnt, s1, s2;

	psc_st.jp_loop++;
	psc_ts_read(&t, &c);
	memset(p, 0, sizeof(*p));
	p->tick_start = t;
	p->c_start = c;
	psc_k.poll_p_head0 = PSC_RD(psc_k.head[PSC_RING_P]);
	p->sc_seq_lo = (u16)psc_k.poll_p_head0;
	p->sig = signal_pending(current) ? PSC_SIG_PENDING : 0;
	p->period = psc_k.poll_started ? psc_sat8(t - psc_k.poll_prev_tick) : 0;
	psc_k.poll_prev_tick = t;
	psc_k.poll_started = 1;
	psc_k.poll_nivcsw0 = current->nivcsw;

	cnt = PSC_RD(psc_st.wk_count);
	if (cnt != psc_k.poll_wk_count) {
		do {
			s1 = PSC_RD(psc_k.wk_seq);
			barrier();
			p->wk_delay = (u16)psc_k.wk_pub_delay;
			p->wk_wrk = (u16)psc_k.wk_pub_wrk;
			p->wk_cls0 = (u8)psc_k.wk_pub_cls0;
			p->wk_cls1 = (u8)psc_k.wk_pub_cls1;
			p->wk_nsw = (u8)psc_k.wk_pub_nsw;
			barrier();
			s2 = PSC_RD(psc_k.wk_seq);
		} while (s1 != s2 || (s1 & 1));
		psc_k.poll_wk_count = cnt;
	}
	psc_jp_stage(PSC_STAGE_LOOP_TOP);
}

/* Just before msleep (joypad_psp.c:468): stage 17, the POLL record. */
void psc_poll_end(void)
{
	struct psc_poll *p = &psc_k.poll;
	struct psc_poll *r;
	u32 t, c, s;

	psc_jp_stage(PSC_STAGE_BEFORE_MSLEEP);
	psc_ts_read(&t, &c);
	p->c_end = c;
	p->body_ticks = psc_sat8(t - p->tick_start);
	p->preempt_delta = psc_sat8(current->nivcsw - psc_k.poll_nivcsw0);
	p->nsc = psc_sat8(PSC_RD(psc_k.head[PSC_RING_P]) - psc_k.poll_p_head0);

	s = psc_k.head[PSC_RING_POLL];
	r = &psc_mem.poll[s & (PSC_POLL_ENTRIES - 1)];
	PSC_WR(r->seq, PSC_SEQ_WRITING);
	barrier();
	memcpy((char *)r + 4, (char *)p + 4, sizeof(*r) - 4);
	barrier();
	PSC_WR(r->seq, s);
	barrier();
	PSC_WR(psc_k.head[PSC_RING_POLL], s + 1);
}

/* ------------------------------------------------------------------ */
/* vfat (2.12) [F]                                                      */
/* ------------------------------------------------------------------ */

#include <linux/msdos_fs.h>

static struct super_block *psc_fat_sb;

/* fat_fill_super success (fs/fat/inode.c:1415): pointer and geometry (4.8). */
void psc_fat_mounted(struct super_block *sb)
{
	struct msdos_sb_info *sbi = MSDOS_SB(sb);

	psc_st.fat_start = sbi->fat_start;
	psc_st.fat_length = sbi->fat_length;
	psc_st.fats = sbi->fats;
	psc_st.fsinfo_sector = sbi->fsinfo_sector;
	psc_st.data_start = sbi->data_start;
	psc_st.sec_per_clus_bits = (sbi->sec_per_clus & 0xFFFF) |
				   ((u32)sb->s_blocksize_bits << 16);
	barrier();
	PSC_WR(psc_fat_sb, sb);
}

/* fat_fs_panic (fs/fat/misc.c:18). */
void psc_fat_panic(void)
{
	if (!psc_st.fat_panics)
		psc_st.fat_panic_tick = psp_local_tick;
	psc_st.fat_panics++;
}

/* MS_RDONLY of the vfat mount: one pointer load and one flag load. */
int psc_fat_rdonly(void)
{
	struct super_block *sb = PSC_RD(psc_fat_sb);

	return sb && (sb->s_flags & MS_RDONLY);
}

/* ------------------------------------------------------------------ */
/* /proc/psc (2.8, 3.5)                                                 */
/* ------------------------------------------------------------------ */

struct psc_ring_desc {
	u32		id;
	u32		entries;
	u32		size;
	unsigned char	*base;
};

static const struct psc_ring_desc psc_ring_desc[PSC_NRINGS] = {
	{ PSC_RING_P,    PSC_P_ENTRIES,    PSC_P_SIZE,    (unsigned char *)psc_mem.p },
	{ PSC_RING_POLL, PSC_POLL_ENTRIES, PSC_POLL_SIZE, (unsigned char *)psc_mem.poll },
	{ PSC_RING_W,    PSC_W_ENTRIES,    PSC_W_SIZE,    (unsigned char *)psc_mem.w },
	{ PSC_RING_S,    PSC_S_ENTRIES,    PSC_S_SIZE,    (unsigned char *)psc_mem.s },
	{ PSC_RING_M,    PSC_M_ENTRIES,    PSC_M_SIZE,    (unsigned char *)psc_mem.m },
};

static int psc_ring_open(struct inode *inode, struct file *file)
{
	file->private_data = PDE(inode)->data;
	file->f_pos = 0;			/* the oldest valid record (2.8) */
	psc_st.proc_opens++;
	return 0;
}

/*
 * read() of a ring file (3.5): whole records only, at most `count` bytes,
 * never blocks, no lock; sets *ppos only (fs/read_write.c:364-366 copies it
 * to f_pos for read(); pread passes a local position, :404-405), so a pread
 * window leaves the drain position alone (2.8, A6-4).
 */
static ssize_t psc_ring_read(struct file *file, char __user *buf, size_t count,
			     loff_t *ppos)
{
	const struct psc_ring_desc *d = file->private_data;
	u32 n = d->entries, size = d->size, s, h, q1, q2, skips = 0;
	unsigned char tmp[PSC_W_SIZE];
	unsigned long long pos;
	size_t done = 0;
	const unsigned char *slot;

	PSC_WR(psc_st.last_reader_tick, psp_local_tick);	/* even for 0 bytes */
	if (*ppos < 0)
		return -EINVAL;
	pos = *ppos;
	if (do_div(pos, size))
		return -EINVAL;
	if (pos > 0xFFFFFFFFull) {
		psc_st.head_regress++;
		return 0;
	}
	s = (u32)pos;

	for (;;) {
		h = PSC_RD(psc_k.head[d->id]);
		if (s > h) {				/* step 1: head moved back */
			psc_st.head_regress++;
			break;
		}
		if (s == h)
			break;
		if (h - s > n)				/* step 2: overwritten */
			s = h - n;
		if (done + size > count)		/* step 5 */
			break;
		slot = d->base + (s & (n - 1)) * size;
		q1 = PSC_RD(*(const u32 *)slot);
		barrier();
		memcpy(tmp, slot, size);
		barrier();
		q2 = PSC_RD(*(const u32 *)slot);
		if (q1 == s && q2 == s) {		/* step 3 */
			if (copy_to_user(buf + done, tmp, size))
				return done ? (ssize_t)done : -EFAULT;
			done += size;
			s++;
			continue;
		}
		/* step 4: skip and count */
		h = PSC_RD(psc_k.head[d->id]);
		if (h - s < n)
			psc_st.slot_bad[d->id]++;
		s++;
		if (++skips > n)
			break;
	}
	*ppos = (loff_t)s * size;
	return done;
}

static loff_t psc_ring_llseek(struct file *file, loff_t off, int whence)
{
	const struct psc_ring_desc *d = file->private_data;
	unsigned long long q;

	switch (whence) {
	case SEEK_SET:
		if (off < 0)
			return -EINVAL;
		q = off;
		if (do_div(q, d->size))
			return -EINVAL;
		if (off < file->f_pos)
			psc_st.ring_rewinds++;
		file->f_pos = off;
		return off;
	case SEEK_CUR:
		if (off != 0)
			return -EINVAL;
		return file->f_pos;
	default:
		return -EINVAL;
	}
}

static const struct file_operations psc_ring_fops = {
	.open		= psc_ring_open,
	.read		= psc_ring_read,
	.llseek		= psc_ring_llseek,
};

extern int console_blanked;

/* The stats block (1.7), evaluated at each read. */
static void psc_stats_snapshot(struct psc_stats *st)
{
	struct task_struct *t;
	u32 h1, h2, lo, tick, count;
	int i;

	memcpy(st, &psc_st, sizeof(*st));
	st->magic = PSC_STATS_MAGIC;
	st->version_size = PSC_STATS_VERSION_SIZE;
	st->build_id = psc_k.build_id;
	st->hz = PSC_HZ;
	st->counts_per_tick = PSC_CPT;
	st->initial_jiffies = (u32)INITIAL_JIFFIES;
	psc_ts_read(&tick, &count);
	st->now_tick = tick;
	st->now_count = count;
	st->now_jiffies = (u32)jiffies;
	do {					/* high-low-high (1.7) */
		h1 = PSC_RD(psc_st.total_counts_hi);
		lo = PSC_RD(psc_st.total_counts_lo);
		h2 = PSC_RD(psc_st.total_counts_hi);
	} while (h1 != h2);
	st->total_counts_lo = lo;
	st->total_counts_hi = h1;
	for (i = 0; i < PSC_NRINGS; i++)
		st->head[i] = PSC_RD(psc_k.head[i]);
	st->addr_syscon_cmd = (u32)(unsigned long)Syscon_cmd;
	st->addr_psc_sc_exit = (u32)(unsigned long)psc_sc_exit;
	st->addr_getctrl2 = (u32)(unsigned long)_pspSysconGetCtrl2;

	t = PSC_RD(psc_jp_task);
	if (t) {
		st->jp_state = (u32)t->state;
		st->jp_sigpending = test_tsk_thread_flag(t, TIF_SIGPENDING) ? 1 : 0;
		st->jp_sigword = (u32)t->pending.signal.sig[0];
		st->jp_nivcsw = (u32)t->nivcsw;
	} else {
		st->jp_state = 0xFFFFFFFFu;
		st->jp_sigpending = 0;
		st->jp_sigword = 0;
		st->jp_nivcsw = 0;
	}
	st->console_blanked = (u32)console_blanked;
	st->console_sem_count = psc_console_sem_count();
	st->list_sem_count = psc_jp_list_sem_count();
	st->t_busy = (PSC_RD(psc_k.t_busy_p) ? PSC_TBUSY_P : 0) |
		     (PSC_RD(psc_k.t_busy_m) ? PSC_TBUSY_M : 0);
	st->t_cmd = psc_k.t_cmd;
	st->t_entry_tick = psc_k.t_entry_tick;
	st->t_entry_c = psc_k.t_entry_c;
	st->ms_rdonly = psc_fat_rdonly() ? 1 : 0;
}

static ssize_t psc_stats_read(struct file *file, char __user *buf, size_t count,
			      loff_t *ppos)
{
	struct psc_stats st;
	size_t n;

	if (*ppos < 0)
		return -EINVAL;
	if (*ppos >= PSC_STATS_SIZE)
		return 0;
	psc_stats_snapshot(&st);
	n = PSC_STATS_SIZE - (size_t)*ppos;
	if (n > count)
		n = count;
	if (copy_to_user(buf, (char *)&st + *ppos, n))
		return -EFAULT;
	*ppos += n;
	return n;
}

static const struct file_operations psc_stats_fops = {
	.read		= psc_stats_read,
};

/* ctl (2.8): whole 32-byte commands '<I7I'; one writer, the active collector. */
static ssize_t psc_ctl_write(struct file *file, const char __user *buf, size_t count,
			     loff_t *ppos)
{
	struct psc_ctl c;
	size_t done = 0;
	int i;

	if (count == 0 || count % PSC_CTL_SIZE)
		return -EINVAL;
	while (done < count) {
		if (copy_from_user(&c, buf + done, PSC_CTL_SIZE))
			return done ? (ssize_t)done : -EFAULT;
		switch (c.op) {
		case PSC_CTL_OP_DURABLE:
			for (i = 0; i < PSC_NRINGS; i++)
				PSC_WR(psc_st.durable_next[i], c.arg[1 + i]);
			barrier();
			PSC_WR(psc_st.durable_tick, c.arg[0]);
			break;
		case PSC_CTL_OP_CLASS:
			if (c.arg[0] >= PSC_PIDCLASS_SLOTS)
				return done ? (ssize_t)done : -EINVAL;
			PSC_WR(psc_st.pid_class[c.arg[0]], PSC_PIDCLASS_MAKE(c.arg[1], c.arg[2]));
			break;
		case PSC_CTL_OP_PANEL_TEST:
			if (c.arg[0] < PSC_CTL_PANEL_SECS_MIN || c.arg[0] > PSC_CTL_PANEL_SECS_MAX)
				return done ? (ssize_t)done : -EINVAL;
			PSC_WR(psc_k.panel_test_secs, c.arg[0]);
			barrier();
			PSC_WR(psc_st.panel_test_seq, psc_st.panel_test_seq + 1);
			break;
		case PSC_CTL_OP_META:
			PSC_WR(psc_st.meta_tick, c.arg[1]);
			barrier();
			PSC_WR(psc_st.meta_sector, c.arg[0]);
			break;
		default:
			return done ? (ssize_t)done : -EINVAL;
		}
		psc_st.ctl_writes++;
		done += PSC_CTL_SIZE;
	}
	return done;
}

static const struct file_operations psc_ctl_fops = {
	.write		= psc_ctl_write,
};

/* ------------------------------------------------------------------ */
/* Init (2.8): late_initcall                                            */
/* ------------------------------------------------------------------ */

static int __init psc_init(void)
{
	static const char *const names[PSC_NRINGS] = {
		PSC_PROC_NAME_P, PSC_PROC_NAME_POLL, PSC_PROC_NAME_W,
		PSC_PROC_NAME_S, PSC_PROC_NAME_M,
	};
	struct proc_dir_entry *dir, *e;
	const struct psc_w *boot = &psc_mem.w[0];
	int i;

	/* guard words (3.1) */
	for (i = 0; i < 7; i++)
		*psc_guard_word[i] = PSC_GUARD(i);
	barrier();
	psc_k.guards_armed = 1;

	/*
	 * build_id (1.7 word 2; not defined by DESIGN, see IMPLEMENTATION
	 * notes): CRC-32 (zlib) of linux_banner, i.e. of the exact bytes of
	 * /proc/version and of the build's banner.txt.
	 */
	psc_k.build_id = psc_crc32(0, linux_banner, strlen(linux_banner));

	dir = proc_mkdir(PSC_PROC_DIRNAME, NULL);
	if (dir) {
		for (i = 0; i < PSC_NRINGS; i++) {
			e = create_proc_entry(names[i], S_IRUSR | S_IRGRP | S_IROTH, dir);
			if (e) {
				e->data = (void *)&psc_ring_desc[i];
				e->proc_fops = &psc_ring_fops;
			}
		}
		e = create_proc_entry(PSC_PROC_NAME_STATS, S_IRUSR | S_IRGRP | S_IROTH, dir);
		if (e) {
			e->proc_fops = &psc_stats_fops;
			e->size = PSC_STATS_SIZE;
		}
		e = create_proc_entry(PSC_PROC_NAME_CTL, S_IWUSR, dir);
		if (e)
			e->proc_fops = &psc_ctl_fops;
	}

	/* the one printk (2.8, 8.1), from the boot W record (W seq 0) */
	printk(PSC_BOOT_PRINTK_FMT, (int)boot->sc.ret, (int)boot->sc.nwords,
	       (unsigned int)boot->sc.rx[2]);
	return 0;
}
late_initcall(psc_init);
