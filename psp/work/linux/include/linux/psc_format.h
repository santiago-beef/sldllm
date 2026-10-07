/*
 * psc_format.h - PSC trace record and file format, shared by the kernel
 * (arch/mips/psp/psc.c and the capture hooks), the collector pscol and,
 * through decoder/psc_format.py, the host decoder.
 *
 * Specification: handoff/design/DESIGN.md revision 6 (G1 PASS 2026-10-06),
 * section 1 (records, stats), 2.8 (/proc/psc), 3.1 (rings), 3.4 (seq
 * sentinel), 4.2-4.4 (collector constants), 10.2-10.4 (chunk framing, UHB,
 * FILEHDR, struct strings). Every definition below cites its section.
 * This file adds no format of its own: if it disagrees with DESIGN.md,
 * DESIGN.md is right and this file is a bug.
 *
 * Rules (DESIGN 1.0, G2 C9):
 *   - little-endian only; every on-disk/on-proc struct is
 *     __attribute__((packed, aligned(4))) with explicit-width members;
 *     no bitfields; sub-byte fields are masks on whole bytes/words.
 *   - reserved bytes are written as 0.
 *   - C89 + GNU extensions only (gcc 4.2.1): no // comments, no C99
 *     declarations, no designated initialisers, no FP.
 *   - every size and every field offset is asserted at compile time below
 *     (PSC_STATIC_ASSERT), in kernel and userland builds alike.
 *
 * Userland (pscol) includes this file by path from the kernel tree; there is
 * deliberately no copy (see work/pscol/README).
 */
#ifndef _LINUX_PSC_FORMAT_H
#define _LINUX_PSC_FORMAT_H

#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <asm/types.h>		/* __u8 .. __u32 without libc clashes */
#endif

#if defined(__MIPSEB__) || defined(__BIG_ENDIAN__) || defined(__ARMEB__)
#error "psc_format.h: the PSC format is little-endian only (DESIGN 1.0)"
#endif

/* ---------------------------------------------------------------------- */
/* Helpers                                                                 */
/* ---------------------------------------------------------------------- */

#define PSC_PACKED	__attribute__((packed, aligned(4)))	/* DESIGN 1.0 */

/* File-scope compile-time assertion, valid in C89 kernel and userland. */
#define PSC_SA_CAT2(a, b)	a##b
#define PSC_SA_CAT(a, b)	PSC_SA_CAT2(a, b)
#define PSC_STATIC_ASSERT(name, cond) \
	typedef char PSC_SA_CAT(psc_static_assert_, name)[(cond) ? 1 : -1]
#define PSC_OFFSETOF(type, member)	__builtin_offsetof(type, member)
#define PSC_ASSERT_OFF(tag, type, member, off) \
	PSC_STATIC_ASSERT(tag##__##member, PSC_OFFSETOF(type, member) == (off))

/* ---------------------------------------------------------------------- */
/* Format identity, time base (DESIGN 1.1, 1.7 words 0-4, 10.2)            */
/* ---------------------------------------------------------------------- */

#define PSC_FORMAT_VERSION	5		/* stats version, chunk hver, FILEHDR fmt */
#define PSC_HZ			250		/* stats word 3 */
#define PSC_CPT			883651u		/* counts per tick, psp.c:39; word 4 */
#define PSC_COUNTS_PER_SEC	220912896u	/* psp.c:38 (UNVERIFIED rate, 1.1) */
#define PSC_WD_CYCLE		1250		/* ticks per watchdog Nop (1.1) */

/* Saturation values used by the "saturating" fields of section 1. */
#define PSC_SAT_U8		0xFFu
#define PSC_SAT_U16		0xFFFFu
#define PSC_SAT_U32		0xFFFFFFFFu

/* ---------------------------------------------------------------------- */
/* Rings (DESIGN 3.1, 2.8, 10.2 block header ring codes)                   */
/* ---------------------------------------------------------------------- */

/*
 * Ring ids. The same order indexes stats head[] (words 14-18),
 * durable_next[] (113-117), slot_bad[] (128-132), ctl op 1 arguments
 * 1..5, and is the RECS block header `ring` code (10.2).
 */
#define PSC_RING_P		0	/* thread Syscon_cmd records (SC)   */
#define PSC_RING_POLL		1	/* thread loop records (POLL)       */
#define PSC_RING_W		2	/* watchdog Nop records (W)         */
#define PSC_RING_S		3	/* Memory Stick segment records (S) */
#define PSC_RING_M		4	/* other-thread SC records (M)      */
#define PSC_NRINGS		5

/* Entries per ring (3.1; power of two, index = seq & (N-1), 3.4). */
#define PSC_P_ENTRIES		4096
#define PSC_POLL_ENTRIES	2048
#define PSC_W_ENTRIES		256
#define PSC_S_ENTRIES		4096
#define PSC_M_ENTRIES		64	/* fill-once; later records only counted (m_dropped) */

/* Record sizes in bytes (1.0, 10.3). */
#define PSC_SC_SIZE		80
#define PSC_WEXT_SIZE		208
#define PSC_W_SIZE		288	/* SC 80 + WEXT 208 */
#define PSC_POLL_SIZE		40
#define PSC_S_SIZE		40
#define PSC_M_SIZE		80	/* M record = SC format (1.6) */
#define PSC_P_SIZE		PSC_SC_SIZE

/* Ring bytes (3.1): 327,680 + 81,920 + 73,728 + 163,840 + 5,120 = 652,288 */
#define PSC_RINGS_TOTAL_BYTES	652288

/* Slot sentinel: a slot whose seq is this is being written (1.0, 3.4). */
#define PSC_SEQ_WRITING		0xFFFFFFFFu

/* ---------------------------------------------------------------------- */
/* /proc/psc (DESIGN 2.8)                                                  */
/* ---------------------------------------------------------------------- */

#define PSC_PROC_DIRNAME	"psc"
#define PSC_PROC_NAME_P		"p"
#define PSC_PROC_NAME_POLL	"poll"
#define PSC_PROC_NAME_W		"w"
#define PSC_PROC_NAME_S		"s"
#define PSC_PROC_NAME_M		"m"
#define PSC_PROC_NAME_STATS	"stats"
#define PSC_PROC_NAME_CTL	"ctl"

#define PSC_PROC_DIR		"/proc/psc"
#define PSC_PROC_P		"/proc/psc/p"
#define PSC_PROC_POLL		"/proc/psc/poll"
#define PSC_PROC_W		"/proc/psc/w"
#define PSC_PROC_S		"/proc/psc/s"
#define PSC_PROC_M		"/proc/psc/m"
#define PSC_PROC_STATS		"/proc/psc/stats"
#define PSC_PROC_CTL		"/proc/psc/ctl"

/* The one printk of the instrumentation, at init, from W seq 0 (2.8). */
#define PSC_BOOT_PRINTK_FMT \
	"PSC5 P4096 POLL2048 W256 S4096 M64 bootnop ret=%d nw=%d rx2=%02x\n"

/* ---------------------------------------------------------------------- */
/* SC record: one per Syscon_cmd call, 80 bytes (DESIGN 1.2, 10.3 'SC')    */
/* Rings P, M; also the first 80 bytes of every W record.                  */
/* ---------------------------------------------------------------------- */

#define PSC_RX_LEN		16	/* rx_buf[0x10], syscon.c */
#define PSC_NWORDS_MAX		8

struct psc_sc {
	__u32	seq;		/*  0 per-ring sequence number                     */
	__u32	tick_in;	/*  4 ts_read() tick at entry                      */
	__u32	c_in;		/*  8 CP0 Count, same read                         */
	__u32	c_out;		/* 12 Count at the record                          */
	__u16	dtick;		/* 16 tick_out - tick_in, saturating               */
	__u8	cmd;		/* 18 tx_buf[0]                                    */
	__u8	txlen;		/* 19 tx_buf[1]                                    */
	__s16	ret;		/* 20 -5,-4,-3,-2 or 0..255                        */
	__u8	nwords;		/* 22 16-bit words received, 0..8                  */
	__u8	retries;	/* 23 retry_cnt 0..15, 16 on -5                    */
	__u32	ack_polls;	/* 24 SYSCON_SPIN_MAX - spin_ack (see sentinels)   */
	__u16	drain;		/* 28 SYSCON_SPIN_MAX - spin, saturating           */
	__u16	drain_last;	/* 30 last word popped by the drain                */
	__u16	gpio_in;	/* 32 0xbe240004 at S5, low 16                     */
	__u16	spi_st9;	/* 34 0xbe58000c at syscon.c:119                   */
	__u16	spi_sttx;	/* 36 0xbe58000c at syscon.c:130                   */
	__u8	ctx;		/* 38 PSC_CTX_*                                    */
	__u8	wn;		/* 39 Nops during this command, saturating         */
	__u16	w_head_lo;	/* 40 W head at record time, low 16                */
	__u16	pre_wrk;	/* 42 collector share of preempted time, Count/256 */
	__u8	pre_cls;	/* 44 PSC_PRE_CLS_*                                */
	__u8	ms_delta;	/* 45 LED RMWs during the command, saturating      */
	__u8	pre_flags;	/* 46 PSC_PRE_F_*                                  */
	__u8	preempt_delta;	/* 47 nivcsw delta                                 */
	__u8	rx[PSC_RX_LEN];	/* 48 whole rx_buf after the final attempt         */
	__u32	lc_epc;		/* 64 thread EPC at last running tick, 0 = none    */
	__u16	lc_dtick;	/* 68 that tick - tick_in; 0xFFFF = none           */
	__u8	lc_n;		/* 70 ticks with the thread running, sat. 255      */
	__u8	lc_flags;	/* 71 PSC_LC_F_*                                   */
	__u32	led_or;		/* 72 OR of LED read-backs during the command      */
	__u16	led_pid;	/* 76 pid (low 16) of the last LED RMW task        */
	__u16	pre_tot;	/* 78 total preempted time, Count/256, saturating  */
} PSC_PACKED;

/* ctx (1.2 offset 38; classification 1.8) */
#define PSC_CTX_ORIGIN_MASK	0x03
#define PSC_ORIGIN_P		0	/* joypad thread                     */
#define PSC_ORIGIN_M		1	/* other thread                      */
#define PSC_ORIGIN_WB		2	/* boot Nop, psp.c:557               */
#define PSC_ORIGIN_WT		3	/* timer Nop, psp.c:379              */
#define PSC_CTX_IE		0x04	/* b2 CP0 Status.IE at entry         */
#define PSC_CTX_IN_INTERRUPT	0x08	/* b3 in_interrupt() != 0            */
#define PSC_CTX_JP_TASK		0x10	/* b4 current == joypad task         */
#define PSC_CTX_PREEMPT_CNT	0x20	/* b5 preempt_count() != 0           */
#define PSC_CTX_SIGPENDING	0x40	/* b6 signal_pending(current) (P, M) */
					/* b7 0                              */

/*
 * Kernel-internal watchdog-context flag psc_wd_ctx (1.8). NOT the origin
 * code above: psc_wd_ctx == 2 gives origin WT (3), == 1 gives WB (2).
 */
#define PSC_WDCTX_NONE		0
#define PSC_WDCTX_BOOT		1
#define PSC_WDCTX_TIMER		2

/* ret (1.2 offset 20; recon/syscon.md 1.3). -1 cannot occur. */
#define PSC_RET_BADFRAME	(-2)	/* E5/E6: rx_buf[1] < 3 or checksum mismatch */
#define PSC_RET_DRAIN_TIMEOUT	(-3)	/* E1: RX pre-drain timeout, syscon.c:113    */
#define PSC_RET_ACK_TIMEOUT	(-4)	/* E2: ACK wait timeout, syscon.c:154        */
#define PSC_RET_BUSY		(-5)	/* E8: 16 BUSY/resend attempts, syscon.c:254 */

#define PSC_RETRIES_E5		16	/* retries on -5 (1.2 offset 23) */

/* ack_polls sentinels (1.2 offset 24); SYSCON_SPIN_MAX = 1000000 */
#define PSC_SYSCON_SPIN_MAX		1000000u
#define PSC_ACK_POLLS_TIMEOUT		1000001u	/* the -4 timeout */
#define PSC_ACK_POLLS_NOT_REACHED	0xFFFFFFFFu	/* loop not reached */
/*
 * drain (1.2 offset 28): 0xFFFF = -3. The field also saturates at 0xFFFF,
 * so 0xFFFF with ret != -3 means ">= 65535 polls"; ret disambiguates.
 */
#define PSC_DRAIN_E3			0xFFFFu

/* pre_cls (1.2 offset 44): low nibble first preempter class, high nibble last holder */
#define PSC_PRE_CLS_FIRST(b)	((b) & 0x0F)
#define PSC_PRE_CLS_LAST(b)	(((b) >> 4) & 0x0F)
#define PSC_PRE_CLS_MAKE(first, last)	((__u8)(((first) & 0x0F) | (((last) & 0x0F) << 4)))

/* pre_flags (1.2 offset 46) */
#define PSC_PRE_F_VALID		0x01	/* b0 pre_* belong to this command        */
#define PSC_PRE_F_MULTI		0x02	/* b1 >= 2 preemptions                    */
#define PSC_PRE_F_SAT		0x04	/* b2 pre_tot or pre_wrk saturated        */
#define PSC_PRE_F_OTHER_HOLDER	0x08	/* b3 a holder outside classes 1-2 ran    */
#define PSC_PRE_F_CLS345	0x10	/* b4 a holder of class 3, 4 or 5 ran     */

/* lc_dtick / lc_n (1.2 offsets 68, 70) */
#define PSC_LC_DTICK_NONE	0xFFFFu
#define PSC_LC_N_SAT		0xFFu

/* lc_flags (1.2 offset 71) */
#define PSC_LC_F_VALID		0x01	/* b0 lc words belong to this cmd_id      */
#define PSC_LC_F_BD		0x02	/* b1 Cause.BD at that tick               */
#define PSC_LC_F_IN_SYSCON	0x04	/* b2 EPC inside Syscon_cmd               */
#define PSC_LC_F_WD_TICK	0x08	/* b3 that tick was a watchdog tick       */
#define PSC_LC_F_NESTED_SEEN	0x10	/* b4 a nested tick was seen, not used    */
#define PSC_LC_F_PANEL		0x20	/* b5 panel painted while in flight (r3)  */

/* ---------------------------------------------------------------------- */
/* W record: SC 80 + extension 208 = 288 bytes (DESIGN 1.3, 10.3 'WEXT')   */
/* ---------------------------------------------------------------------- */

#define PSC_NREGS		16	/* regs 2..15, then 24, 25 */

struct psc_wext {
	__u32	epc;		/*  80 regs->cp0_epc of the interrupted context */
	__u32	cause;		/*  84 regs->cp0_cause (b31 BD)                 */
	__u32	status;		/*  88 regs->cp0_status                         */
	__u32	ra;		/*  92 regs->regs[31]                           */
	__u32	sp;		/*  96 regs->regs[29]                           */
	__u32	r[PSC_NREGS];	/* 100 regs 2..15, 24, 25                       */
	__u32	pid;		/* 164 current->pid (interrupted task)          */
	__u32	p_head;		/* 168 P head                                   */
	__u32	jp_loop;	/* 172 thread loop counter                      */
	__u32	t_entry_tick;	/* 176 tick at entry of in-flight P command     */
	__u32	t_entry_c;	/* 180 Count at that entry                      */
	__u8	t_busy;		/* 184 PSC_TBUSY_*                              */
	__u8	jp_stage;	/* 185 PSC_STAGE_*                              */
	__u8	ext_flags;	/* 186 PSC_EXT_F_*                              */
	__u8	cur_pcnt;	/* 187 preempt_count() low 8                    */
	__u32	c_pre;		/* 188 Count at handler entry, before reset     */
	__u32	lc_tick;	/* 192 tick of the thread's last running tick   */
	__u32	lc_c_pre;	/* 196 Count before reset at that tick          */
	__u32	lc_cmd_id;	/* 200 cmd_id the lc words belong to            */
	__u32	lc_epc;		/* 204 thread EPC at that tick                  */
	__u32	lc_cause;	/* 208 its Cause                                */
	__u32	lc_ra;		/* 212 its ra                                   */
	__u32	lc_sp;		/* 216 its sp                                   */
	__u32	lc_r[PSC_NREGS];/* 220 its regs 2..15, 24, 25                   */
	__u16	lc_n;		/* 284 ticks with the thread running so far     */
	__u16	rsv;		/* 286 reserved, 0                              */
} PSC_PACKED;
/* (offsets in the comments above are within the W record; within
 *  struct psc_wext subtract 80) */

struct psc_w {
	struct psc_sc	sc;	/*   0 the Nop's own SC record */
	struct psc_wext	ext;	/*  80 interrupted context     */
} PSC_PACKED;

/* t_busy (1.3 offset 184; stats word 64) */
#define PSC_TBUSY_P		0x01
#define PSC_TBUSY_M		0x02

/* ext_flags (1.3 offset 186) */
#define PSC_EXT_F_REGS_VALID	0x01	/* b0 regs valid                           */
					/* b1 0                                    */
#define PSC_EXT_F_KMODE		0x04	/* b2 interrupted context in kernel mode   */
#define PSC_EXT_F_IN_SYSCON	0x08	/* b3 EPC inside Syscon_cmd                */
#define PSC_EXT_F_JP_TASK	0x10	/* b4 current == joypad task               */
#define PSC_EXT_F_LC_VALID	0x20	/* b5 lc block belongs to in-flight cmd    */
#define PSC_EXT_F_MS_ACTIVE	0x40	/* b6 Memory Stick transfer in progress    */
#define PSC_EXT_F_NESTED	0x80	/* b7 interrupted ctx had softirq/hardirq  */

/* Thread stage codes (2.5), W jp_stage, stats jp_stage, POLL stage_max */
#define PSC_STAGE_NOT_STARTED	0
#define PSC_STAGE_LOOP_TOP	1
#define PSC_STAGE_ASTICKPOWER	2
#define PSC_STAGE_GETCTRL2	3
#define PSC_STAGE_RI_RETURNED	4
#define PSC_STAGE_PI_ENTRY	5
#define PSC_STAGE_DEDUPE_RET	6
#define PSC_STAGE_BEFORE_LCD_ON	7
#define PSC_STAGE_AFTER_LCD_ON	8
#define PSC_STAGE_BEFORE_LISTSEM	9
#define PSC_STAGE_LISTSEM_HELD	10
#define PSC_STAGE_BEFORE_QSEM	11	/* arg = queue pointer */
#define PSC_STAGE_PUSHING	12	/* arg = queue pointer */
#define PSC_STAGE_AFTER_UP_LIST	13
#define PSC_STAGE_AFTER_WAKEUP	14
#define PSC_STAGE_MOUSE_ENTRY	15
#define PSC_STAGE_BEFORE_SYNC	16
#define PSC_STAGE_BEFORE_MSLEEP	17

/* ---------------------------------------------------------------------- */
/* POLL record: one per thread loop iteration, 40 bytes (DESIGN 1.4)       */
/* ---------------------------------------------------------------------- */

struct psc_poll {
	__u32	seq;		/*  0                                          */
	__u32	tick_start;	/*  4 ts_read() at loop top                    */
	__u32	c_start;	/*  8 same                                     */
	__u32	c_end;		/* 12 Count just before msleep                 */
	__u16	sc_seq_lo;	/* 16 P head at loop top, low 16               */
	__u8	body_ticks;	/* 18 tick at msleep - tick_start, saturating  */
	__u8	ri_branch;	/* 19 PSC_RI_*                                 */
	__u8	pi_flags;	/* 20 PSC_PI_F_*                               */
	__u8	nqueues;	/* 21 queues walked                            */
	__u8	push_ok;	/* 22 pushes that returned TRUE                */
	__u8	push_fail;	/* 23 low nibble full, high nibble -EINTR      */
	__u8	mouse_flags;	/* 24 PSC_MOUSE_F_*                            */
	__s8	dx;		/* 25 passed to REL_X                          */
	__s8	dy;		/* 26 dy (REL_Y is reported as -dy)            */
	__u8	sig;		/* 27 PSC_SIG_PENDING                          */
	__u8	period;		/* 28 tick_start - previous, saturating        */
	__u8	preempt_delta;	/* 29 nivcsw delta over the loop body          */
	__u8	stage_max;	/* 30 highest stage reached                    */
	__u8	nsc;		/* 31 SC records produced this iteration       */
	__u16	wk_delay;	/* 32 wake-up to switch-in, Count/256, sat.    */
	__u16	wk_wrk;		/* 34 collector part of that delay             */
	__u8	wk_cls0;	/* 36 class running when the thread was woken  */
	__u8	wk_cls1;	/* 37 class switched out to run the thread     */
	__u8	wk_nsw;		/* 38 context switches during the wait, sat.   */
	__u8	rsv;		/* 39 reserved, 0                              */
} PSC_PACKED;

/* ri_branch (1.4 offset 19) */
#define PSC_RI_R1		1	/* :483-484                 */
#define PSC_RI_R3		3	/* GetCtrl2 < 0, :487-488   */
#define PSC_RI_R4		4	/* HOLD, :492-493           */
#define PSC_RI_R5		5	/* TRUE, :495               */

/* pi_flags (1.4 offset 20) */
#define PSC_PI_F_CALLED		0x01	/* b0 process_input called         */
#define PSC_PI_F_DEDUPE		0x02	/* b1 returned at dedupe           */
#define PSC_PI_F_BLANKED	0x04	/* b2 console_blanked at lcd_on    */
#define PSC_PI_F_SELECT_TOGGLE	0x08	/* b3 SELECT toggle executed       */
#define PSC_PI_F_MOUSEMODE	0x10	/* b4 mouseMode after              */
#define PSC_PI_F_LISTSEM	0x20	/* b5 list_sem acquired            */
#define PSC_PI_F_LISTSEM_FAIL	0x40	/* b6 list_sem down failed         */
#define PSC_PI_F_WAKE		0x80	/* b7 wake_up_interruptible called */

/* push_fail (1.4 offset 23) */
#define PSC_PUSH_FAIL_FULL(b)	((b) & 0x0F)
#define PSC_PUSH_FAIL_EINTR(b)	(((b) >> 4) & 0x0F)
#define PSC_PUSH_FAIL_MAKE(full, eintr)	((__u8)(((full) & 0x0F) | (((eintr) & 0x0F) << 4)))

/* mouse_flags (1.4 offset 24) */
#define PSC_MOUSE_F_CALLED	0x01	/* b0 called                */
#define PSC_MOUSE_F_NODEV	0x02	/* b1 M1 no device          */
#define PSC_MOUSE_F_NOOP	0x04	/* b2 M2 no-op              */
#define PSC_MOUSE_F_REPORTED	0x08	/* b3 reported              */
#define PSC_MOUSE_F_LEFT	0x10	/* b4 left                  */
#define PSC_MOUSE_F_MIDDLE	0x20	/* b5 middle                */
#define PSC_MOUSE_F_RIGHT	0x40	/* b6 right                 */

/* sig (1.4 offset 27) */
#define PSC_SIG_PENDING		0x01	/* b0 signal_pending at loop top */

/* ---------------------------------------------------------------------- */
/* S record: one per Memory Stick segment transfer, 40 bytes (DESIGN 1.5)  */
/* ---------------------------------------------------------------------- */

struct psc_s {
	__u32	seq;		/*  0                                          */
	__u32	tick_on;	/*  4 at entry, after the semaphore            */
	__u32	c_on;		/*  8                                          */
	__u32	c_off;		/* 12 at exit, before up()                     */
	__u32	sector;		/* 16 first sector (absolute)                  */
	__u16	dtick;		/* 20                                          */
	__u16	pid;		/* 22 task doing the I/O                       */
	__u8	nsect;		/* 24                                          */
	__u8	flags;		/* 25 PSC_S_F_*                                */
	__u16	p_head_lo;	/* 26 P head at entry                          */
	__u8	led_ops;	/* 28 LED RMWs in this segment                 */
	__u8	rsv29;		/* 29 reserved, 0                              */
	__u16	rsv30;		/* 30 reserved, 0                              */
	__u32	rd_set_or;	/* 32 OR of words read from 0xbe240008         */
	__u32	rd_clr_or;	/* 36 OR of words read from 0xbe24000c         */
} PSC_PACKED;

/* S flags (1.5 offset 25) */
#define PSC_S_F_WRITE		0x01	/* b0 write                                */
#define PSC_S_F_ERROR		0x02	/* b1 error (rt < 0)                       */
#define PSC_S_F_SET_B3		0x04	/* b2 an LED set read had bit 3            */
#define PSC_S_F_CLR_B3		0x08	/* b3 an LED clear read had bit 3          */
#define PSC_S_F_P_ENTRY		0x10	/* b4 P command in flight at entry         */
#define PSC_S_F_P_EXIT		0x20	/* b5 P command in flight at exit          */
#define PSC_S_F_M		0x40	/* b6 M command in flight at either        */
#define PSC_S_F_META		0x80	/* b7 block-device page cache (r4)         */

/* ---------------------------------------------------------------------- */
/* Stats block: 768 bytes = 192 x u32, /proc/psc/stats (DESIGN 1.7)        */
/* Writer tags as in 1.7: T thread, W timer, L MS path, R reader,          */
/* P any process, K pdflush, C collector (ctl), X sched hooks, F vfat.     */
/* ---------------------------------------------------------------------- */

#define PSC_STATS_MAGIC		0x54535350u	/* 'PSST' little-endian */
#define PSC_STATS_WORDS		192
#define PSC_STATS_SIZE		768
#define PSC_STATS_VERSION_SIZE	((__u32)((PSC_STATS_SIZE << 16) | PSC_FORMAT_VERSION))

/* Outcome counter index within oc_p08[], oc_p33[], oc_w[] (words 31-51) */
#define PSC_OC_POS		0	/* ret > 0                  */
#define PSC_OC_ZERO_WORDS	1	/* ret == 0 && nwords > 0   */
#define PSC_OC_ZERO_NOWORDS	2	/* ret == 0 && nwords == 0  */
#define PSC_OC_E2		3	/* -2                       */
#define PSC_OC_E3		4	/* -3                       */
#define PSC_OC_E4		5	/* -4                       */
#define PSC_OC_E5		6	/* -5                       */
#define PSC_OC_N		7

struct psc_stats {
	/* 0-4 */
	__u32	magic;			/*   0 PSC_STATS_MAGIC                  */
	__u32	version_size;		/*   1 version low 16, size high 16     */
	__u32	build_id;		/*   2 value not specified by DESIGN:
					 *     open interface item, see report */
	__u32	hz;			/*   3 250                              */
	__u32	counts_per_tick;	/*   4 883651                           */
	/* 5-9 */
	__u32	last_reader_tick;	/*   5 [R] ring-file reads only         */
	__u32	initial_jiffies;	/*   6                                  */
	__u32	now_tick;		/*   7 [R]                              */
	__u32	now_count;		/*   8 [R]                              */
	__u32	now_jiffies;		/*   9 [R]                              */
	/* 10-13 [W] */
	__u32	total_counts_lo;	/*  10                                  */
	__u32	total_counts_hi;	/*  11                                  */
	__u32	c_pre_max;		/*  12                                  */
	__u32	long_ticks;		/*  13                                  */
	/* 14-23 */
	__u32	head[PSC_NRINGS];	/*  14-18 [R] P, POLL, W, S, M          */
	__u32	m_dropped;		/*  19 [P]                              */
	__u32	addr_syscon_cmd;	/*  20 &Syscon_cmd                      */
	__u32	addr_psc_sc_exit;	/*  21 &psc_sc_exit                     */
	__u32	addr_getctrl2;		/*  22 &_pspSysconGetCtrl2              */
	__u32	proc_opens;		/*  23 [R]                              */
	/* 24-30 */
	__u32	p_rec_cost_last;	/*  24 [T] Count units                  */
	__u32	p_rec_cost_max;		/*  25 [T]                              */
	__u32	w_rec_cost_max;		/*  26 [W]                              */
	__u32	wd_calls;		/*  27 [W]                              */
	__u32	wd_last_tick;		/*  28 [W]                              */
	__u32	p_nested;		/*  29 [T] P with wn > 0                */
	__u32	p_ticked;		/*  30 [T] P with dtick > 0             */
	/* 31-51 outcome counters, index PSC_OC_* */
	__u32	oc_p08[PSC_OC_N];	/*  31-37 [T] P cmd 0x08                */
	__u32	oc_p33[PSC_OC_N];	/*  38-44 [T] P cmd 0x33                */
	__u32	oc_w[PSC_OC_N];		/*  45-51 [W] W                         */
	/* 52-55 [T] */
	__u32	jp_pid;			/*  52                                  */
	__u32	jp_loop;		/*  53                                  */
	__u32	jp_stage;		/*  54                                  */
	__u32	jp_stage_arg;		/*  55 queue pointer at stages 11-12    */
	/* 56-59 [R] */
	__u32	jp_state;		/*  56 task->state, 0xFFFFFFFF if none  */
	__u32	jp_sigpending;		/*  57 TIF_SIGPENDING                   */
	__u32	jp_sigword;		/*  58 pending.signal.sig[0]            */
	__u32	jp_nivcsw;		/*  59                                  */
	/* 60-63 */
	__u32	jp_keys;		/*  60 [T] value stored at :527         */
	__u32	console_blanked;	/*  61 [R]                              */
	__s32	console_sem_count;	/*  62 [R] signed (10.4)                */
	__s32	list_sem_count;		/*  63 [R] signed (10.4)                */
	/* 64-67 */
	__u32	t_busy;			/*  64 [R] PSC_TBUSY_*                  */
	__u32	t_cmd;			/*  65 [T]                              */
	__u32	t_entry_tick;		/*  66 [T]                              */
	__u32	t_entry_c;		/*  67 [T]                              */
	/* 68-75 [T] */
	__u32	jp_r3;			/*  68                                  */
	__u32	jp_r4;			/*  69                                  */
	__u32	jp_r5;			/*  70                                  */
	__u32	jp_proc_calls;		/*  71                                  */
	__u32	jp_dedupe;		/*  72                                  */
	__u32	jp_changed;		/*  73                                  */
	__u32	jp_lcd_unblank;		/*  74                                  */
	__u32	jp_mode_toggles;	/*  75                                  */
	/* 76-83 [T] */
	__u32	jp_listsem_fail;	/*  76                                  */
	__u32	jp_push_ok;		/*  77                                  */
	__u32	jp_push_full;		/*  78                                  */
	__u32	jp_push_eintr;		/*  79                                  */
	__u32	jp_wake;		/*  80                                  */
	__u32	jp_mouse_calls;		/*  81                                  */
	__u32	jp_mouse_noop;		/*  82                                  */
	__u32	jp_mouse_reports;	/*  83                                  */
	/* 84-89 [P] */
	__u32	fop_open;		/*  84                                  */
	__u32	fop_release;		/*  85                                  */
	__u32	fop_read_enter;		/*  86                                  */
	__u32	fop_read_ret;		/*  87                                  */
	__u32	fop_read_eintr;		/*  88                                  */
	__u32	fop_ioctl;		/*  89                                  */
	/* 90-92 [P] */
	__u32	qfree_stage;		/*  90 PSC_QFREE_*                      */
	__u32	qfree_queue;		/*  91                                  */
	__u32	qfree_pid;		/*  92                                  */
	/* 93-96 [P] */
	__u32	vcs_putchar;		/*  93                                  */
	__u32	vcs_changecon;		/*  94                                  */
	__u32	vcs_updscr;		/*  95                                  */
	__u32	vcs_getsize;		/*  96                                  */
	/* 97-99 */
	__u32	md_event_syn;		/*  97 [T]                              */
	__u32	md_notify_calls;	/*  98 [T]                              */
	__u32	md_read_ret;		/*  99 [P]                              */
	/* 100-103 [L] */
	__u32	led_calls;		/* 100                                  */
	__u32	led_calls_t_busy;	/* 101                                  */
	__u32	led_or_set_run;		/* 102                                  */
	__u32	led_or_clr_run;		/* 103                                  */
	/* 104-111 */
	__u32	ms_seg_wr;		/* 104 [L]                              */
	__u32	ms_seg_rd;		/* 105 [L]                              */
	__u32	ms_err;			/* 106 [L]                              */
	__u32	ms_ip_tick;		/* 107 [L] in-progress marker           */
	__u32	ms_ip_sector;		/* 108 [L]                              */
	__u32	ms_ip_word;		/* 109 [L] PSC_MSIP_*                   */
	__u32	kupd_count;		/* 110 [K]                              */
	__u32	kupd_last_tick;		/* 111 [K]                              */
	/* 112-117 [C] */
	__u32	durable_tick;		/* 112                                  */
	__u32	durable_next[PSC_NRINGS];	/* 113-117 P, POLL, W, S, M     */
	/* 118-124 */
	__u32	ctl_writes;		/* 118 [C]                              */
	__u32	panel_paints;		/* 119 [W]                              */
	__u32	panel_last_tick;	/* 120 [W]                              */
	__u32	panel_test_seq;		/* 121 [C]                              */
	__u32	panel_test_done;	/* 122 [W]                              */
	__u32	panel_cost_max;		/* 123 [W]                              */
	__u32	lc_nested;		/* 124 [W]                              */
	/* 125-127 */
	__u32	kguard_bad;		/* 125 [W]                              */
	__u32	ring_rewinds;		/* 126 [R]                              */
	__u32	head_regress;		/* 127 [R]                              */
	/* 128-132 [R] */
	__u32	slot_bad[PSC_NRINGS];	/* 128-132 P, POLL, W, S, M             */
	/* 133-135 */
	__u32	fat_panics;		/* 133 [F]                              */
	__u32	fat_panic_tick;		/* 134 [F] first                        */
	__u32	ms_rdonly;		/* 135 [R]                              */
	/* 136-139 */
	__u32	wk_count;		/* 136 [X]                              */
	__u32	wk_max;			/* 137 [X] Count/256                    */
	__u32	jp_exit_tick;		/* 138 [P]                              */
	__u32	kguard_first_tick;	/* 139 [W]                              */
	/* 140-147 [C] */
	__u32	pid_class[8];		/* 140-147 PSC_PIDCLASS_*               */
	/* 148-149 [W] */
	__u32	panel_cost_last;	/* 148                                  */
	__u32	panel_state;		/* 149 PSC_PANEL_*                      */
	/* 150-152 */
	__u32	meta_sector;		/* 150 [C] 0 none                       */
	__u32	meta_tick;		/* 151 [C] first detection              */
	__u32	pre_count;		/* 152 [X]                              */
	/* 153-159 geometry, written once (r5, 4.8) */
	__u32	ms_part_start;		/* 153 [L] start sector of /dev/ms0     */
	__u32	fat_start;		/* 154 [F] s_blocksize units            */
	__u32	fat_length;		/* 155 [F]                              */
	__u32	fats;			/* 156 [F]                              */
	__u32	fsinfo_sector;		/* 157 [F]                              */
	__u32	data_start;		/* 158 [F]                              */
	__u32	sec_per_clus_bits;	/* 159 [F] PSC_GEOM_*                   */
	/* 160-191 */
	__u32	reserved[32];		/* 160-191 0                            */
} PSC_PACKED;

/* ms_ip_word (word 109) */
#define PSC_MSIP_PID(w)		((w) & 0xFFFFu)
#define PSC_MSIP_NSECT(w)	(((w) >> 16) & 0xFFu)
#define PSC_MSIP_ACTIVE		0x01000000u	/* b24 */
#define PSC_MSIP_WRITE		0x02000000u	/* b25 */

/* qfree_stage (word 90) */
#define PSC_QFREE_ENTRY		1
#define PSC_QFREE_AFTER_348	2
#define PSC_QFREE_AFTER_353	3
#define PSC_QFREE_AFTER_LISTDEL	4
#define PSC_QFREE_BEFORE_KFREE	5

/* panel_state (word 149) */
#define PSC_PANEL_NEVER		0
#define PSC_PANEL_CLEARED	1
#define PSC_PANEL_SHOWING	2

/* sec_per_clus_bits (word 159) */
#define PSC_GEOM_SEC_PER_CLUS(w)	((w) & 0xFFFFu)
#define PSC_GEOM_BLOCKSIZE_BITS(w)	(((w) >> 16) & 0xFFFFu)

/* Task classes (2.11): pid_class[] (words 140-147), POLL wk_cls*, SC pre_cls */
#define PSC_CLASS_NONE		0
#define PSC_CLASS_WRK		1	/* active collector         */
#define PSC_CLASS_SUP		2	/* supervisor               */
#define PSC_CLASS_OSK		3	/* psposk2                  */
#define PSC_CLASS_MD		4	/* pspmd                    */
#define PSC_CLASS_PDFLUSH	5	/* pdflush                  */
#define PSC_CLASS_KTHREAD	6	/* mm == NULL (kthread/idle) */
#define PSC_CLASS_OTHER		7
#define PSC_PIDCLASS_SLOTS	8
#define PSC_PIDCLASS_PID(w)	((w) & 0x00FFFFFFu)
#define PSC_PIDCLASS_CLASS(w)	(((w) >> 24) & 0xFFu)
#define PSC_PIDCLASS_MAKE(pid, cls)	((__u32)(((pid) & 0x00FFFFFFu) | (((__u32)(cls) & 0xFFu) << 24)))

/* ---------------------------------------------------------------------- */
/* /proc/psc/ctl command: 32 bytes '<I7I' (DESIGN 2.8)                     */
/* ---------------------------------------------------------------------- */

struct psc_ctl {
	__u32	op;		/*  0 PSC_CTL_OP_*                    */
	__u32	arg[7];		/*  4 arguments, in the order of 2.8   */
} PSC_PACKED;

#define PSC_CTL_SIZE		32
#define PSC_CTL_OP_DURABLE	1	/* arg0 durable_tick, arg1..5 durable_next[ring] */
#define PSC_CTL_OP_CLASS	2	/* arg0 slot 0..7, arg1 pid, arg2 class          */
#define PSC_CTL_OP_PANEL_TEST	3	/* arg0 seconds 1..10                            */
#define PSC_CTL_OP_META		4	/* arg0 meta_sector (0 clears), arg1 meta_tick   */
#define PSC_CTL_PANEL_SECS_MIN	1
#define PSC_CTL_PANEL_SECS_MAX	10

/* ---------------------------------------------------------------------- */
/* Files, chunks, blocks (DESIGN 10.2, 4.3, 4.4)                           */
/* ---------------------------------------------------------------------- */

#define PSC_SECTOR_SIZE		512

/* Chunk header: 20 bytes '<4sHHIII' (10.2) */
struct psc_chunk_hdr {
	__u8	magic[4];	/*  0 "PSCK"                               */
	__u16	type;		/*  4 PSC_CHUNK_*                           */
	__u16	hver;		/*  6 PSC_FORMAT_VERSION                    */
	__u32	len;		/*  8 payload bytes (padding not counted)   */
	__u32	fseq;		/* 12 per file from 0; PSC_FSEQ_PREALLOC    */
	__u32	crc;		/* 16 CRC-32/IEEE of the len payload bytes  */
} PSC_PACKED;

#define PSC_CHUNK_MAGIC		"PSCK"
#define PSC_CHUNK_MAGIC_U32	0x4B435350u	/* "PSCK" read as LE u32 */
#define PSC_CHUNK_HDR_SIZE	20
#define PSC_CHUNK_LEN_MAX	65536		/* decoder sanity bound */
#define PSC_FSEQ_PREALLOC	0xFFFFFFFFu	/* fseq of preallocation PAD sectors */
/* payload is followed by zero padding to a multiple of 4, not in len */
#define PSC_CHUNK_PAD4(len)	(((len) + 3u) & ~3u)
#define PSC_CHUNK_TOTAL(len)	(PSC_CHUNK_HDR_SIZE + PSC_CHUNK_PAD4(len))

/* Chunk types (10.2) */
#define PSC_CHUNK_PAD		0
#define PSC_CHUNK_FILEHDR	1
#define PSC_CHUNK_RECS		2
#define PSC_CHUNK_STATS		3
#define PSC_CHUNK_KMSG		4
#define PSC_CHUNK_PROCS		5
#define PSC_CHUNK_UHB		6
#define PSC_CHUNK_EVENT		7
#define PSC_CHUNK_NTYPES	8

/*
 * PAD: every flush ends with a PAD chunk to the next 512-byte boundary.
 * Payload length of the PAD chunk whose header starts at file offset `off`
 * (off a multiple of 4): fills to the next boundary after its header.
 * A preallocation PAD sector is a whole 512-byte PAD chunk, len 492,
 * fseq PSC_FSEQ_PREALLOC, CRC of 492 zero bytes seeded with the nonce (4.4 step 3).
 */
#define PSC_PAD_LEN_AT(off) \
	((PSC_SECTOR_SIZE - (((off) + PSC_CHUNK_HDR_SIZE) % PSC_SECTOR_SIZE)) % PSC_SECTOR_SIZE)
#define PSC_PAD_SECTOR_LEN	492

/* Writer guarantees (10.2, 4.3), payload bytes unless stated */
#define PSC_FLUSH_MAX		40960	/* whole flush, starts at a multiple of 512 */
#define PSC_KMSG_MAX		4096
#define PSC_EVENT_MAX		1024
#define PSC_PROCS_MAX		2400
#define PSC_UHB_SIZE		84
#define PSC_EVENT_QUEUE		8192	/* collector EVENT queue (4.3) */
/*
 * RECS chunk bound: OPEN, see the interface report. 4.3 and 10.2 give
 * 34,364 B = 34,304 record bytes + 40 (5 block headers) + 20, but 10.2/4.6
 * also allow a re-send block before each ring's new-records block (up to
 * 10 block headers). Only the record-byte part is defined here.
 */
#define PSC_RECS_RECORD_BYTES_MAX	34304	/* 4 x 8,576 (4.3) */

/* Collector drain caps per tick (4.3): records per unit of m, m <= 4 */
#define PSC_CAP_P		48
#define PSC_CAP_POLL		24
#define PSC_CAP_W		2
#define PSC_CAP_S		64
#define PSC_CAP_M		8
#define PSC_CAP_M_MAX		4

/* RECS block header: 8 bytes '<BBHI' (10.2) */
struct psc_block_hdr {
	__u8	ring;		/* 0 PSC_RING_* | PSC_BLK_RESEND              */
	__u8	recsize_div4;	/* 1 record size / 4                          */
	__u16	count;		/* 2 records that follow                      */
	__u32	lost;		/* 4 seq values skipped; 0 in a re-send block */
} PSC_PACKED;

#define PSC_BLK_HDR_SIZE	8
#define PSC_BLK_RESEND		0x80	/* b7: re-send block (r5, 4.6) */
#define PSC_BLK_RING_MASK	0x7F
#define PSC_P_DIV4		20
#define PSC_POLL_DIV4		10
#define PSC_W_DIV4		72
#define PSC_S_DIV4		10
#define PSC_M_DIV4		20

/* FILEHDR chunk payload: fixed part 44 bytes '<8sIIIIIIIII' (10.2, r5) */
struct psc_filehdr {
	__u8	magic[8];	/*  0 "PSCLOG5\0"                      */
	__u32	fmt;		/*  8 PSC_FORMAT_VERSION                */
	__u32	run;		/* 12 rrr                               */
	__u32	seg;		/* 16 nnn                               */
	__u32	inst;		/* 20 PSC_INST_*                        */
	__u32	writer_pid;	/* 24                                   */
	__u32	sup_pid;	/* 28 supervisor pid                    */
	__u32	now_tick;	/* 32                                   */
	__u32	now_jiffies;	/* 36                                   */
	__u32	nonce;		/* 40 boot nonce (4.2)                  */
} PSC_PACKED;

#define PSC_FILEHDR_MAGIC	"PSCLOG5"	/* 8 bytes with the NUL */
#define PSC_FILEHDR_FIXED	44
#define PSC_FILEHDR_VERSION_LEN	256		/* /proc/version, NUL-padded */
#define PSC_FILEHDR_PAYLOAD	1068		/* 44 + 768 + 256 */
#define PSC_INST_WORKER		1
#define PSC_INST_SUPERVISOR	2		/* supervisor after takeover */

/* Whole FILEHDR payload (1,068 bytes) */
struct psc_filehdr_payload {
	struct psc_filehdr	hdr;				/*   0 */
	struct psc_stats	stats;				/*  44 */
	__u8			version[PSC_FILEHDR_VERSION_LEN];	/* 812 */
} PSC_PACKED;

/* UHB chunk payload: 84 bytes '<21I' (10.2, r5) */
struct psc_uhb {
	__u32	tickno;			/*  0 */
	__u32	stats_now_tick;		/*  4 */
	__u32	gtod_sec;		/*  8 */
	__u32	gtod_usec;		/* 12 */
	__u32	uptime_cs;		/* 16 */
	__u32	memfree_kb;		/* 20 */
	__u32	mouse_pkts_total;	/* 24 */
	__u32	mouse_press_total;	/* 28 IN */
	__u32	bytes_synced_total;	/* 32 */
	__u32	last_write_ms;		/* 36 */
	__u32	last_fsync_ms;		/* 40 */
	__u32	max_fsync_ms_60s;	/* 44 */
	__u32	max_tick_ms_60s;	/* 48 */
	__u32	write_errs;		/* 52 FAILED flushes and creation steps */
	__u32	last_errno;		/* 56 */
	__u32	flags;			/* 60 PSC_UHB_F_* */
	__u32	durable_tick;		/* 64 */
	__u32	lag_max;		/* 68 */
	__u32	seg;			/* 72 PSC_UHB_SEG_* */
	__u32	drain_stuck;		/* 76 */
	__u32	nonce;			/* 80 */
} PSC_PACKED;

/* UHB flags (10.2) */
#define PSC_UHB_F_HOLDING	(1u << 0)
#define PSC_UHB_F_ST_KRN	(1u << 1)	/* self-test checks b1-b8 (8.2) */
#define PSC_UHB_F_ST_WDOG	(1u << 2)
#define PSC_UHB_F_ST_STICK	(1u << 3)
#define PSC_UHB_F_ST_REC	(1u << 4)
#define PSC_UHB_F_ST_PANEL	(1u << 5)
#define PSC_UHB_F_ST_SUP	(1u << 6)
#define PSC_UHB_F_ST_POLL	(1u << 7)
#define PSC_UHB_F_ST_BTN	(1u << 8)
#define PSC_UHB_F_SUP_ALIVE	(1u << 9)
#define PSC_UHB_F_NO_STICK	(1u << 10)
#define PSC_UHB_F_DRAIN_COMPLETE (1u << 11)
#define PSC_UHB_F_CATCHUP	(1u << 12)
#define PSC_UHB_F_FILE_AHEAD	(1u << 13)
#define PSC_UHB_F_TAKEOVER	(1u << 14)	/* writer is supervisor after takeover */
#define PSC_UHB_F_RESEND_PEND	(1u << 15)
#define PSC_UHB_F_GUARD		(1u << 16)
#define PSC_UHB_F_ABANDONED	(1u << 17)
#define PSC_UHB_F_CREATING	(1u << 18)
#define PSC_UHB_F_SWITCHED	(1u << 19)
#define PSC_UHB_F_MS_RED	(1u << 20)
#define PSC_UHB_F_RDONLY	(1u << 21)
#define PSC_UHB_F_REC_ALARM	(1u << 22)
#define PSC_UHB_F_META		(1u << 23)	/* r4 */
#define PSC_UHB_F_GROWTH_STOP	(1u << 24)
#define PSC_UHB_F_PREFIX	(1u << 25)	/* active file not complete */
#define PSC_UHB_F_ABANDON_WAIT	(1u << 26)	/* r5 */
#define PSC_UHB_F_RETIRED	(1u << 27)	/* region bad */
#define PSC_UHB_F_ALIAS		(1u << 28)
#define PSC_UHB_F_SPEED_OK	(1u << 29)
#define PSC_UHB_F_FSYNC_ERR	(1u << 30)	/* DURABLE flush, fsync error */

/* UHB seg word (10.2, r5 layout; r7 A6-3 decode) */
#define PSC_UHB_SEG_ACTIVE(w)	((w) & 0x3FFu)			/* bits 0-9   */
#define PSC_UHB_SEG_CREATING(w)	(((w) >> 10) & 0x3FFu)		/* bits 10-19 */
#define PSC_UHB_SEG_CONFV(w)	(((w) >> 20) & 0x1FFu)		/* bits 20-28 */
#define PSC_UHB_SEG_AHEAD(w)	(((w) >> 29) & 0x3u)		/* bits 29-30 */
#define PSC_UHB_SEG_CREATING_F	0x80000000u			/* b31        */
#define PSC_UHB_SEG_MAKE(active, creating, conf, ahead, inprog) \
	((__u32)(((active) & 0x3FFu) | (((creating) & 0x3FFu) << 10) | \
	 ((((conf) / 8192u) & 0x1FFu) << 20) | (((ahead) & 0x3u) << 29) | \
	 ((inprog) ? 0x80000000u : 0u)))
/* decoder rule: conf = SEG for v = 256, else 8,192 * v + 1,536 */
#define PSC_UHB_SEG_CONF(v)	((v) == 256u ? (__u32)PSC_SEG_SIZE : (__u32)(8192u * (v) + 1536u))

/* Segment files (4.4) */
#define PSC_LOG_DIR		"/ms0/PSCLOG"
#define PSC_SEG_NAME_FMT	"T%03u%03u.BIN"		/* T<rrr><nnn>.BIN */
#define PSC_SEG_SIZE		2097152			/* 4,096 sectors */
#define PSC_FILEHDR_AREA	1536			/* FILEHDR + PAD, step 0 */
#define PSC_STEP_SMALL		8192
#define PSC_STEP_LARGE		65536
#define PSC_ROOM_LARGE_BELOW	81920			/* 64 KB steps below this room */
#define PSC_CONFIRMED_CAP	(64u * 1024u * 1024u)	/* 64 MB (4.4 step 8) */
#define PSC_NAMES_MAX		999
#define PSC_RUN_MAX		999

/* ---------------------------------------------------------------------- */
/* Chunk CRC (10.2): CRC-32/IEEE, reflected, poly 0xEDB88320, identical to */
/* Python zlib.crc32(data, seed). seed = boot nonce for every chunk type   */
/* except FILEHDR (seed 0). Chainable: crc(a+b, s) = crc(b, crc(a, s)).    */
/* Bitwise (no table) so it costs no data; userland only needs it.         */
/* ---------------------------------------------------------------------- */

static __inline__ __u32 psc_crc32(__u32 seed, const void *buf, unsigned long len)
{
	const __u8 *p = (const __u8 *)buf;
	__u32 c = seed ^ 0xFFFFFFFFu;
	int k;

	while (len--) {
		c ^= *p++;
		for (k = 0; k < 8; k++)
			c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
	}
	return c ^ 0xFFFFFFFFu;
}

/* ---------------------------------------------------------------------- */
/* Compile-time size and offset assertions (DESIGN 1.0, 10.3, 15.6)        */
/* ---------------------------------------------------------------------- */

PSC_STATIC_ASSERT(sc_size,	sizeof(struct psc_sc) == PSC_SC_SIZE);
PSC_STATIC_ASSERT(wext_size,	sizeof(struct psc_wext) == PSC_WEXT_SIZE);
PSC_STATIC_ASSERT(w_size,	sizeof(struct psc_w) == PSC_W_SIZE);
PSC_STATIC_ASSERT(poll_size,	sizeof(struct psc_poll) == PSC_POLL_SIZE);
PSC_STATIC_ASSERT(s_size,	sizeof(struct psc_s) == PSC_S_SIZE);
PSC_STATIC_ASSERT(m_size,	sizeof(struct psc_sc) == PSC_M_SIZE);
PSC_STATIC_ASSERT(stats_size,	sizeof(struct psc_stats) == PSC_STATS_SIZE);
PSC_STATIC_ASSERT(stats_words,	sizeof(struct psc_stats) == 4 * PSC_STATS_WORDS);
PSC_STATIC_ASSERT(ctl_size,	sizeof(struct psc_ctl) == PSC_CTL_SIZE);
PSC_STATIC_ASSERT(chunk_size,	sizeof(struct psc_chunk_hdr) == PSC_CHUNK_HDR_SIZE);
PSC_STATIC_ASSERT(block_size,	sizeof(struct psc_block_hdr) == PSC_BLK_HDR_SIZE);
PSC_STATIC_ASSERT(filehdr_size,	sizeof(struct psc_filehdr) == PSC_FILEHDR_FIXED);
PSC_STATIC_ASSERT(fhpay_size,	sizeof(struct psc_filehdr_payload) == PSC_FILEHDR_PAYLOAD);
PSC_STATIC_ASSERT(uhb_size,	sizeof(struct psc_uhb) == PSC_UHB_SIZE);
PSC_STATIC_ASSERT(div4_p,	PSC_P_DIV4 * 4 == PSC_SC_SIZE);
PSC_STATIC_ASSERT(div4_poll,	PSC_POLL_DIV4 * 4 == PSC_POLL_SIZE);
PSC_STATIC_ASSERT(div4_w,	PSC_W_DIV4 * 4 == PSC_W_SIZE);
PSC_STATIC_ASSERT(div4_s,	PSC_S_DIV4 * 4 == PSC_S_SIZE);
PSC_STATIC_ASSERT(div4_m,	PSC_M_DIV4 * 4 == PSC_M_SIZE);
PSC_STATIC_ASSERT(ring_bytes,	PSC_P_ENTRIES * PSC_P_SIZE + PSC_POLL_ENTRIES * PSC_POLL_SIZE +
				PSC_W_ENTRIES * PSC_W_SIZE + PSC_S_ENTRIES * PSC_S_SIZE +
				PSC_M_ENTRIES * PSC_M_SIZE == PSC_RINGS_TOTAL_BYTES);
PSC_STATIC_ASSERT(ring_pow2,	(PSC_P_ENTRIES & (PSC_P_ENTRIES - 1)) == 0 &&
				(PSC_POLL_ENTRIES & (PSC_POLL_ENTRIES - 1)) == 0 &&
				(PSC_W_ENTRIES & (PSC_W_ENTRIES - 1)) == 0 &&
				(PSC_S_ENTRIES & (PSC_S_ENTRIES - 1)) == 0 &&
				(PSC_M_ENTRIES & (PSC_M_ENTRIES - 1)) == 0);
PSC_STATIC_ASSERT(pad_sector,	PSC_CHUNK_HDR_SIZE + PSC_PAD_SECTOR_LEN == PSC_SECTOR_SIZE);
PSC_STATIC_ASSERT(fh_area,	PSC_FILEHDR_AREA % PSC_SECTOR_SIZE == 0 &&
				PSC_CHUNK_HDR_SIZE + PSC_FILEHDR_PAYLOAD + PSC_CHUNK_HDR_SIZE <= PSC_FILEHDR_AREA);
PSC_STATIC_ASSERT(recs_bytes,	PSC_RECS_RECORD_BYTES_MAX == PSC_CAP_M_MAX *
				(PSC_CAP_P * PSC_P_SIZE + PSC_CAP_POLL * PSC_POLL_SIZE +
				 PSC_CAP_W * PSC_W_SIZE + PSC_CAP_S * PSC_S_SIZE + PSC_CAP_M * PSC_M_SIZE));

/* SC (1.2) */
PSC_ASSERT_OFF(sc, struct psc_sc, seq, 0);
PSC_ASSERT_OFF(sc, struct psc_sc, tick_in, 4);
PSC_ASSERT_OFF(sc, struct psc_sc, c_in, 8);
PSC_ASSERT_OFF(sc, struct psc_sc, c_out, 12);
PSC_ASSERT_OFF(sc, struct psc_sc, dtick, 16);
PSC_ASSERT_OFF(sc, struct psc_sc, cmd, 18);
PSC_ASSERT_OFF(sc, struct psc_sc, txlen, 19);
PSC_ASSERT_OFF(sc, struct psc_sc, ret, 20);
PSC_ASSERT_OFF(sc, struct psc_sc, nwords, 22);
PSC_ASSERT_OFF(sc, struct psc_sc, retries, 23);
PSC_ASSERT_OFF(sc, struct psc_sc, ack_polls, 24);
PSC_ASSERT_OFF(sc, struct psc_sc, drain, 28);
PSC_ASSERT_OFF(sc, struct psc_sc, drain_last, 30);
PSC_ASSERT_OFF(sc, struct psc_sc, gpio_in, 32);
PSC_ASSERT_OFF(sc, struct psc_sc, spi_st9, 34);
PSC_ASSERT_OFF(sc, struct psc_sc, spi_sttx, 36);
PSC_ASSERT_OFF(sc, struct psc_sc, ctx, 38);
PSC_ASSERT_OFF(sc, struct psc_sc, wn, 39);
PSC_ASSERT_OFF(sc, struct psc_sc, w_head_lo, 40);
PSC_ASSERT_OFF(sc, struct psc_sc, pre_wrk, 42);
PSC_ASSERT_OFF(sc, struct psc_sc, pre_cls, 44);
PSC_ASSERT_OFF(sc, struct psc_sc, ms_delta, 45);
PSC_ASSERT_OFF(sc, struct psc_sc, pre_flags, 46);
PSC_ASSERT_OFF(sc, struct psc_sc, preempt_delta, 47);
PSC_ASSERT_OFF(sc, struct psc_sc, rx, 48);
PSC_ASSERT_OFF(sc, struct psc_sc, lc_epc, 64);
PSC_ASSERT_OFF(sc, struct psc_sc, lc_dtick, 68);
PSC_ASSERT_OFF(sc, struct psc_sc, lc_n, 70);
PSC_ASSERT_OFF(sc, struct psc_sc, lc_flags, 71);
PSC_ASSERT_OFF(sc, struct psc_sc, led_or, 72);
PSC_ASSERT_OFF(sc, struct psc_sc, led_pid, 76);
PSC_ASSERT_OFF(sc, struct psc_sc, pre_tot, 78);

/* W (1.3): offsets within the W record */
PSC_ASSERT_OFF(w, struct psc_w, sc, 0);
PSC_ASSERT_OFF(w, struct psc_w, ext, 80);
PSC_ASSERT_OFF(wext, struct psc_wext, epc, 80 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, cause, 84 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, status, 88 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, ra, 92 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, sp, 96 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, r, 100 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, pid, 164 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, p_head, 168 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, jp_loop, 172 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, t_entry_tick, 176 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, t_entry_c, 180 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, t_busy, 184 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, jp_stage, 185 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, ext_flags, 186 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, cur_pcnt, 187 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, c_pre, 188 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_tick, 192 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_c_pre, 196 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_cmd_id, 200 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_epc, 204 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_cause, 208 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_ra, 212 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_sp, 216 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_r, 220 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, lc_n, 284 - 80);
PSC_ASSERT_OFF(wext, struct psc_wext, rsv, 286 - 80);

/* POLL (1.4) */
PSC_ASSERT_OFF(poll, struct psc_poll, seq, 0);
PSC_ASSERT_OFF(poll, struct psc_poll, tick_start, 4);
PSC_ASSERT_OFF(poll, struct psc_poll, c_start, 8);
PSC_ASSERT_OFF(poll, struct psc_poll, c_end, 12);
PSC_ASSERT_OFF(poll, struct psc_poll, sc_seq_lo, 16);
PSC_ASSERT_OFF(poll, struct psc_poll, body_ticks, 18);
PSC_ASSERT_OFF(poll, struct psc_poll, ri_branch, 19);
PSC_ASSERT_OFF(poll, struct psc_poll, pi_flags, 20);
PSC_ASSERT_OFF(poll, struct psc_poll, nqueues, 21);
PSC_ASSERT_OFF(poll, struct psc_poll, push_ok, 22);
PSC_ASSERT_OFF(poll, struct psc_poll, push_fail, 23);
PSC_ASSERT_OFF(poll, struct psc_poll, mouse_flags, 24);
PSC_ASSERT_OFF(poll, struct psc_poll, dx, 25);
PSC_ASSERT_OFF(poll, struct psc_poll, dy, 26);
PSC_ASSERT_OFF(poll, struct psc_poll, sig, 27);
PSC_ASSERT_OFF(poll, struct psc_poll, period, 28);
PSC_ASSERT_OFF(poll, struct psc_poll, preempt_delta, 29);
PSC_ASSERT_OFF(poll, struct psc_poll, stage_max, 30);
PSC_ASSERT_OFF(poll, struct psc_poll, nsc, 31);
PSC_ASSERT_OFF(poll, struct psc_poll, wk_delay, 32);
PSC_ASSERT_OFF(poll, struct psc_poll, wk_wrk, 34);
PSC_ASSERT_OFF(poll, struct psc_poll, wk_cls0, 36);
PSC_ASSERT_OFF(poll, struct psc_poll, wk_cls1, 37);
PSC_ASSERT_OFF(poll, struct psc_poll, wk_nsw, 38);
PSC_ASSERT_OFF(poll, struct psc_poll, rsv, 39);

/* S (1.5) */
PSC_ASSERT_OFF(s, struct psc_s, seq, 0);
PSC_ASSERT_OFF(s, struct psc_s, tick_on, 4);
PSC_ASSERT_OFF(s, struct psc_s, c_on, 8);
PSC_ASSERT_OFF(s, struct psc_s, c_off, 12);
PSC_ASSERT_OFF(s, struct psc_s, sector, 16);
PSC_ASSERT_OFF(s, struct psc_s, dtick, 20);
PSC_ASSERT_OFF(s, struct psc_s, pid, 22);
PSC_ASSERT_OFF(s, struct psc_s, nsect, 24);
PSC_ASSERT_OFF(s, struct psc_s, flags, 25);
PSC_ASSERT_OFF(s, struct psc_s, p_head_lo, 26);
PSC_ASSERT_OFF(s, struct psc_s, led_ops, 28);
PSC_ASSERT_OFF(s, struct psc_s, rsv29, 29);
PSC_ASSERT_OFF(s, struct psc_s, rsv30, 30);
PSC_ASSERT_OFF(s, struct psc_s, rd_set_or, 32);
PSC_ASSERT_OFF(s, struct psc_s, rd_clr_or, 36);

/* Stats (1.7): byte offset = 4 x word index */
PSC_ASSERT_OFF(st, struct psc_stats, magic, 4 * 0);
PSC_ASSERT_OFF(st, struct psc_stats, build_id, 4 * 2);
PSC_ASSERT_OFF(st, struct psc_stats, last_reader_tick, 4 * 5);
PSC_ASSERT_OFF(st, struct psc_stats, total_counts_lo, 4 * 10);
PSC_ASSERT_OFF(st, struct psc_stats, head, 4 * 14);
PSC_ASSERT_OFF(st, struct psc_stats, m_dropped, 4 * 19);
PSC_ASSERT_OFF(st, struct psc_stats, addr_syscon_cmd, 4 * 20);
PSC_ASSERT_OFF(st, struct psc_stats, addr_getctrl2, 4 * 22);
PSC_ASSERT_OFF(st, struct psc_stats, proc_opens, 4 * 23);
PSC_ASSERT_OFF(st, struct psc_stats, p_rec_cost_last, 4 * 24);
PSC_ASSERT_OFF(st, struct psc_stats, p_ticked, 4 * 30);
PSC_ASSERT_OFF(st, struct psc_stats, oc_p08, 4 * 31);
PSC_ASSERT_OFF(st, struct psc_stats, oc_p33, 4 * 38);
PSC_ASSERT_OFF(st, struct psc_stats, oc_w, 4 * 45);
PSC_ASSERT_OFF(st, struct psc_stats, jp_pid, 4 * 52);
PSC_ASSERT_OFF(st, struct psc_stats, jp_state, 4 * 56);
PSC_ASSERT_OFF(st, struct psc_stats, jp_keys, 4 * 60);
PSC_ASSERT_OFF(st, struct psc_stats, console_sem_count, 4 * 62);
PSC_ASSERT_OFF(st, struct psc_stats, list_sem_count, 4 * 63);
PSC_ASSERT_OFF(st, struct psc_stats, t_busy, 4 * 64);
PSC_ASSERT_OFF(st, struct psc_stats, jp_r3, 4 * 68);
PSC_ASSERT_OFF(st, struct psc_stats, jp_listsem_fail, 4 * 76);
PSC_ASSERT_OFF(st, struct psc_stats, fop_open, 4 * 84);
PSC_ASSERT_OFF(st, struct psc_stats, qfree_stage, 4 * 90);
PSC_ASSERT_OFF(st, struct psc_stats, vcs_putchar, 4 * 93);
PSC_ASSERT_OFF(st, struct psc_stats, md_event_syn, 4 * 97);
PSC_ASSERT_OFF(st, struct psc_stats, led_calls, 4 * 100);
PSC_ASSERT_OFF(st, struct psc_stats, ms_seg_wr, 4 * 104);
PSC_ASSERT_OFF(st, struct psc_stats, ms_ip_word, 4 * 109);
PSC_ASSERT_OFF(st, struct psc_stats, kupd_count, 4 * 110);
PSC_ASSERT_OFF(st, struct psc_stats, durable_tick, 4 * 112);
PSC_ASSERT_OFF(st, struct psc_stats, durable_next, 4 * 113);
PSC_ASSERT_OFF(st, struct psc_stats, ctl_writes, 4 * 118);
PSC_ASSERT_OFF(st, struct psc_stats, lc_nested, 4 * 124);
PSC_ASSERT_OFF(st, struct psc_stats, kguard_bad, 4 * 125);
PSC_ASSERT_OFF(st, struct psc_stats, slot_bad, 4 * 128);
PSC_ASSERT_OFF(st, struct psc_stats, fat_panics, 4 * 133);
PSC_ASSERT_OFF(st, struct psc_stats, wk_count, 4 * 136);
PSC_ASSERT_OFF(st, struct psc_stats, kguard_first_tick, 4 * 139);
PSC_ASSERT_OFF(st, struct psc_stats, pid_class, 4 * 140);
PSC_ASSERT_OFF(st, struct psc_stats, panel_cost_last, 4 * 148);
PSC_ASSERT_OFF(st, struct psc_stats, meta_sector, 4 * 150);
PSC_ASSERT_OFF(st, struct psc_stats, pre_count, 4 * 152);
PSC_ASSERT_OFF(st, struct psc_stats, ms_part_start, 4 * 153);
PSC_ASSERT_OFF(st, struct psc_stats, fat_start, 4 * 154);
PSC_ASSERT_OFF(st, struct psc_stats, sec_per_clus_bits, 4 * 159);
PSC_ASSERT_OFF(st, struct psc_stats, reserved, 4 * 160);

/* CTL (2.8), chunk and block headers, FILEHDR, UHB (10.2) */
PSC_ASSERT_OFF(ctl, struct psc_ctl, op, 0);
PSC_ASSERT_OFF(ctl, struct psc_ctl, arg, 4);
PSC_ASSERT_OFF(ch, struct psc_chunk_hdr, magic, 0);
PSC_ASSERT_OFF(ch, struct psc_chunk_hdr, type, 4);
PSC_ASSERT_OFF(ch, struct psc_chunk_hdr, hver, 6);
PSC_ASSERT_OFF(ch, struct psc_chunk_hdr, len, 8);
PSC_ASSERT_OFF(ch, struct psc_chunk_hdr, fseq, 12);
PSC_ASSERT_OFF(ch, struct psc_chunk_hdr, crc, 16);
PSC_ASSERT_OFF(bh, struct psc_block_hdr, ring, 0);
PSC_ASSERT_OFF(bh, struct psc_block_hdr, recsize_div4, 1);
PSC_ASSERT_OFF(bh, struct psc_block_hdr, count, 2);
PSC_ASSERT_OFF(bh, struct psc_block_hdr, lost, 4);
PSC_ASSERT_OFF(fh, struct psc_filehdr, magic, 0);
PSC_ASSERT_OFF(fh, struct psc_filehdr, fmt, 8);
PSC_ASSERT_OFF(fh, struct psc_filehdr, run, 12);
PSC_ASSERT_OFF(fh, struct psc_filehdr, seg, 16);
PSC_ASSERT_OFF(fh, struct psc_filehdr, inst, 20);
PSC_ASSERT_OFF(fh, struct psc_filehdr, writer_pid, 24);
PSC_ASSERT_OFF(fh, struct psc_filehdr, sup_pid, 28);
PSC_ASSERT_OFF(fh, struct psc_filehdr, now_tick, 32);
PSC_ASSERT_OFF(fh, struct psc_filehdr, now_jiffies, 36);
PSC_ASSERT_OFF(fh, struct psc_filehdr, nonce, 40);
PSC_ASSERT_OFF(fhp, struct psc_filehdr_payload, stats, 44);
PSC_ASSERT_OFF(fhp, struct psc_filehdr_payload, version, 812);
PSC_ASSERT_OFF(uhb, struct psc_uhb, flags, 60);
PSC_ASSERT_OFF(uhb, struct psc_uhb, seg, 72);
PSC_ASSERT_OFF(uhb, struct psc_uhb, drain_stuck, 76);
PSC_ASSERT_OFF(uhb, struct psc_uhb, nonce, 80);

#endif /* _LINUX_PSC_FORMAT_H */
