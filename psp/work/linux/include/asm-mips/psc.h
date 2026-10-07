/*
 * asm-mips/psc.h - PSC trace: kernel-internal state, timestamps and hooks.
 *
 * Specification: handoff/design/DESIGN.md revision 6 (G1 PASS 2026-10-06).
 * The record and stats formats are in <linux/psc_format.h>; this header only
 * declares the kernel's own bookkeeping (not a format) and the hooks the
 * instrumented files call. Section numbers in comments are DESIGN's.
 *
 * Context rules (3.4, D9): every variable here has one writer context, named
 * in its comment: T joypad thread, W timer interrupt (IE off), B boot (before
 * the scheduler runs), L Memory Stick path (under s_psp_ms_rw_sem, preemption
 * off), X scheduler hooks (rq lock held, IE off), C collector through
 * /proc/psc/ctl, F vfat hooks, R the /proc reader, P any process
 * (informational counters only). Nothing here takes a lock, masks interrupts,
 * sleeps or allocates. No floating point.
 */
#ifndef _ASM_PSC_H
#define _ASM_PSC_H

#include <linux/psc_format.h>
#include <linux/sched.h>
#include <linux/hardirq.h>
#include <asm/mipsregs.h>

/* One aligned word or byte, read or written with one access (3.4). */
#define PSC_RD(x)	(*(volatile typeof(x) *)&(x))
#define PSC_WR(x, v)	(*(volatile typeof(x) *)&(x) = (v))

/* ------------------------------------------------------------------ */
/* Time base (1.1)                                                     */
/* ------------------------------------------------------------------ */

/* psp.c: the watchdog's localTick, moved to file scope (1.1, 2.2). [W] */
extern unsigned long psp_local_tick;

/*
 * ts_read() (1.1): a (tick, Count) pair that cannot straddle a tick. Count
 * is zeroed first in every timer interrupt (psp.c:351-352).
 */
static inline void psc_ts_read(u32 *tick, u32 *count)
{
	u32 t1, t2, c;

	do {
		t1 = PSC_RD(psp_local_tick);
		c = read_c0_count();
		t2 = PSC_RD(psp_local_tick);
	} while (t1 != t2);
	*tick = t1;
	*count = c;
}

/* ------------------------------------------------------------------ */
/* Syscon_cmd capture (2.1)                                            */
/* ------------------------------------------------------------------ */

/*
 * What the transaction's exit label hands over (syscon.c PSC_XFER_OUT):
 * its six stack capture slots (2.1 A3) and two registers, the receive
 * loop's i + 2 (for nwords, A4) and retry_cnt. Word layout fixed by the asm.
 */
struct psc_xfer_raw {
	u32	gin;		/* syscon.c:102 load (gpio_in) */
	u32	spin;		/* drain counter: 0 = loop not entered (A2) */
	u32	spin_ack;	/* ACK loop counter */
	u32	dlast;		/* syscon.c:114 load */
	u32	st9;		/* syscon.c:119 load */
	u32	sttx;		/* syscon.c:130 load */
	u32	t0;		/* receive loop i + 2 at exit */
	u32	t8;		/* retry_cnt */
};

#define PSC_XFER_P	0	/* joypad thread [T] */
#define PSC_XFER_M	1	/* other threads [P] */
#define PSC_XFER_W	2	/* watchdog Nop [W, B] */

/* Per-call entry snapshot, on the recording wrapper's stack (2.1 A1). */
struct psc_scratch {
	const u8	*tx;
	const u8	*rx;
	s32		result;
	u32		origin;		/* PSC_ORIGIN_* */
	u32		ctx;		/* record byte 38 */
	u32		tick_in, c_in;
	u32		cmd_id;		/* P only */
	u32		wd_calls0;	/* for wn */
	u32		led_calls0;	/* for ms_delta */
	u32		nivcsw0;	/* for preempt_delta */
};

/* ------------------------------------------------------------------ */
/* Ring and state memory: one static BSS object (3.1)                  */
/* ------------------------------------------------------------------ */

/* Kernel bookkeeping that is not part of any record format. */
struct psc_kstate {
	u32	head[PSC_NRINGS];	/* next seq per ring; one writer per ring (3.4) */

	/* in-flight commands (2.1 A1, 3.4) */
	u32	t_busy_p;		/* [T] 1 while a P command is in flight */
	u32	t_cmd;			/* [T] its cmd (stats 65) */
	u32	t_entry_tick;		/* [T] stats 66 */
	u32	t_entry_c;		/* [T] stats 67 */
	u32	t_cmd_id;		/* [T] ++ per P command */
	u32	t_busy_m;		/* [P] 1 while an M command is in flight */

	u32	wd_ctx;			/* [W, B] PSC_WDCTX_* (1.8, 2.2) */
	u32	c_pre_cur;		/* [W] Count before the reset, this tick (T1) */

	struct psc_xfer_raw xfer[3];	/* PSC_XFER_*; writer as the index */

	/* lc overwrite words (1.2, 1.3, 2.3 T2a) [W], bracketed by lc_seq */
	u32	lc_seq;
	u32	lc_tick;
	u32	lc_c_pre;
	u32	lc_cmd_id;
	u32	lc_epc;
	u32	lc_cause;
	u32	lc_ra;
	u32	lc_sp;
	u32	lc_r[PSC_NREGS];
	u32	lc_n;			/* saturating at 0xFFFF */
	u32	lc_wdtick;		/* that tick ran a Nop (SC lc_flags b3) */
	u32	lc_nest_id;		/* cmd_id that saw a nested tick (b4) */

	/* LED read-backs and the current segment (2.4) [L] */
	u32	led_cmd_id;
	u32	led_cmd_or;
	u32	led_cmd_pid;
	u32	seg_led_ops;
	u32	seg_set_or;
	u32	seg_clr_or;
	u32	seg_flags;		/* S flags b2, b3 */
	u32	s_tick_on;
	u32	s_c_on;
	u32	s_p_head;
	u32	s_busy_in;		/* t_busy at entry: b0 P, b1 M */

	/* scheduler hooks (2.11) [X]; published words bracketed by wk_seq */
	u32	wk_seq;
	u32	wk_pending;
	u32	wk_t0_tick, wk_t0_c;
	u32	wk_last_tick, wk_last_c;
	u32	wk_acc;			/* Count units, saturating */
	u32	wk_nsw;
	u32	wk_cls0;
	u32	wk_pub_delay;		/* Count/256, 16-bit saturated */
	u32	wk_pub_wrk;
	u32	wk_pub_cls0;
	u32	wk_pub_cls1;
	u32	wk_pub_nsw;

	/* preemption branch of hook S (2.11, A4 F5) [X], bracketed by pre_seq */
	u32	pre_seq;
	u32	pre_cmd_id;
	u32	pre_on;
	u32	pre_t0_tick, pre_t0_c;
	u32	pre_last_tick, pre_last_c;
	u32	pre_tot;		/* Count units, saturating */
	u32	pre_wrk;		/* Count units, saturating */
	u32	pre_n;
	u32	pre_flags;
	u32	pre_cls0;
	u32	pre_cls1;

	/* thread loop (1.4, 2.5) [T] */
	struct psc_poll poll;
	u32	poll_prev_tick;
	u32	poll_started;
	u32	poll_nivcsw0;
	u32	poll_p_head0;
	u32	poll_wk_count;
	u32	last_p08;		/* 1 + seq of the newest P record with cmd 0x08 */

	/* stall panel (2.10) [W], except panel_test_secs [C] */
	u32	t2d_due;		/* next tick at which T2d runs */
	u32	panel_cmd_id;
	u32	panel_test_secs;
	u32	panel_test_seen;
	u32	panel_test_until;
	u32	guards_armed;		/* [B] */
	u32	build_id;		/* [B] */
};

struct psc_mem {
	u32			g0;
	struct psc_sc		p[PSC_P_ENTRIES];
	u32			g1;
	struct psc_poll		poll[PSC_POLL_ENTRIES];
	u32			g2;
	struct psc_w		w[PSC_W_ENTRIES];
	u32			g3;
	struct psc_s		s[PSC_S_ENTRIES];
	u32			g4;
	struct psc_sc		m[PSC_M_ENTRIES];
	u32			g5;
	struct psc_stats	st;	/* live counters; [R] words filled at read */
	struct psc_kstate	k;
	u32			g6;
};

extern struct psc_mem psc_mem;

#define psc_st	(psc_mem.st)
#define psc_k	(psc_mem.k)

/*
 * The joypad thread (1.8): set by the thread at start, cleared once in
 * do_exit (2.6). Read everywhere with one load.
 */
extern struct task_struct *psc_jp_task;

/* ------------------------------------------------------------------ */
/* Hooks (bodies in arch/mips/psp/psc.c)                                */
/* ------------------------------------------------------------------ */

/* 2.1: recording wrapper around Syscon_cmd; the transaction's exit hand-off. */
extern int psc_syscon_cmd(u8 *tx_buf, u8 *rx_buf);
extern void psc_xfer_out(const struct psc_xfer_raw *raw);

/* 2.3: T2, after psp_watchdog_tick() in the timer interrupt. */
extern void psc_tick_hook(u32 c_pre);

/* 2.4: after an LED read-modify-write store; set = 1 for 0xbe240008. */
extern void psc_note_led(int set, u32 v);

/* 2.4: one Memory Stick segment transfer. */
extern void psc_ms_seg_begin(u32 sector, u32 nsect, int write);
extern void psc_ms_seg_end(u32 sector, u32 nsect, int write, int rt, int meta);

/* 2.11: scheduler hooks. */
extern void psc_sched_wake_slow(void);
extern void psc_sched_switch_slow(struct task_struct *prev, struct task_struct *next);

static inline void psc_sched_wake(struct task_struct *p)
{
	if (unlikely(p == psc_jp_task))		/* one compare per wake-up */
		psc_sched_wake_slow();
}

static inline void psc_sched_switch(struct task_struct *prev, struct task_struct *next)
{
	/* one load and one compare per switch otherwise (2.11, 5.4) */
	if (unlikely(psc_k.wk_pending | psc_k.pre_on) || unlikely(prev == psc_jp_task))
		psc_sched_switch_slow(prev, next);
}

/* 2.5: the joypad thread. */
extern void psc_jp_thread_start(void);
extern void psc_poll_begin(void);
extern void psc_poll_end(void);

static inline void psc_jp_stage(u32 stage)
{
	psc_st.jp_stage = stage;
	if (stage > psc_k.poll.stage_max && stage < PSC_STAGE_BEFORE_MSLEEP)
		psc_k.poll.stage_max = (u8)stage;
}

static inline void psc_jp_stage_arg(u32 stage, void *arg)
{
	psc_st.jp_stage_arg = (u32)(unsigned long)arg;
	psc_jp_stage(stage);
}

/* 1.7 words 62-63: read-only accessors for the stats reader. */
extern int psc_console_sem_count(void);
extern int psc_jp_list_sem_count(void);

/* 2.12: vfat. */
struct super_block;
extern void psc_fat_mounted(struct super_block *sb);
extern void psc_fat_panic(void);
extern int psc_fat_rdonly(void);

/* 2.10: the stall panel, from T2d (arch/mips/psp/psc_panel.c). */
extern void psc_panel_t2d(u32 tick);

#endif /* _ASM_PSC_H */
