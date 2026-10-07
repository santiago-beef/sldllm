/*
 * host.h - shared declarations of the Stage 3 ring-test harness.
 * The harness is test code; the kernel code under test is psc.c,
 * psc_panel.c, syscon.c and joypad_psp.c, compiled unmodified.
 */
#ifndef PSC_HOST_H
#define PSC_HOST_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "stubinc/host_kernel.h"
#include <asm/psc.h>			/* the real include/asm-mips/psc.h */
#include <asm/ipl_sdk/syscon.h>		/* the real syscon.h (inline wrappers) */

#define CPT		883651u		/* psp.c:39, PSC_CPT */
#define WD_CYCLE	1250		/* PSP_WATCHDOG_CYCLE * HZ, psp.c:42,387 */
#define SPIN_MAX	1000000u	/* syscon.c:12 */

/* ---------------------------------------------------------------- time */
extern u32 g_count;			/* CP0 Count model */
extern u64 g_abs;			/* monotonic counts since boot */
extern int g_ie;			/* CP0 Status.IE of the running context */
extern unsigned long psp_local_tick;	/* psp.c: watchdog localTick (file scope) */

/* --------------------------------------------------------------- tasks */
enum { T_IDLE, T_INIT, T_JP, T_WRK, T_SUP, T_OSK, T_MD, T_PDF, T_NTASK };
extern struct task_struct *g_task[T_NTASK];

/* ------------------------------------------------- interrupted context */
struct ipt {				/* what an interrupt frame holds */
	u32 epc, cause, status, ra, sp;
	u32 r[16];			/* regs 2..15, 24, 25 (DESIGN 1.3) */
	int pcnt;			/* preempt_count of the interrupted ctx */
};
void ipt_for_current(struct ipt *p);	/* task-level point (not in syscon) */

/* ------------------------------------------------------- syscon device */
enum devmode {
	DM_NORMAL = 0,
	DM_NOACK,	/* H1 (9.5 variant): no ACK for 0x08/0x33, Nop answered */
	DM_ZERO,	/* H2: 0x08 answered with all-zero words */
	DM_EMPTY,	/* H3: ACK, RX FIFO empty, for 0x08 */
	DM_BUSY,	/* H5: 0x08 answered BUSY (rx[2] = 0x80) every try */
	DM_FROZEN,	/* H6: 0x08 answered with one frozen valid frame */
	DM_LATCH,	/* H8: ACK latch stuck set, GPIO input changed */
	DM_LAG,		/* N2b: each request gets the previous request's reply */
	DM_CODE42,	/* none: valid frame, unknown response code, frozen keys */
};
void dev_init(u32 seed);
void dev_set_mode(int mode);
int dev_get_mode(void);
u32 dev_gpio_out(void);			/* output latch (LED read-back model) */
void dev_led_rmw(int set, u32 mask, u32 *readback);

/* operator buttons (active-low raw bytes rx[3..6], analog x, y) */
void op_buttons(u8 b[4], u8 *x, u8 *y);

/* --------------------------------------------- interrupt / tick model */
void fire_tick(const struct ipt *p);	/* psp.c timer handler model */
void sim_advance(u32 dc);		/* advance time; fire a due tick */
int irq_due(void);

/* access-point trigger (forced interrupt at an exact point) */
struct trig {
	int armed;
	int kind;		/* access kind (mmio.c K_*) or -1 */
	int nth;		/* occurrence index within the transaction */
	int ctx_origin;		/* 'P' only */
	int cmd;		/* 0x08 or 0x33 */
	int need_latch;		/* fire only when the device latch is set */
	int fired;
};
extern struct trig g_trig;

/* --------------------------------------------------------------- events */
extern FILE *g_ev;
void ev(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

/* ----------------------------------------------------------- scheduler */
void do_switch(int prev, int next);
extern int g_cur;			/* index of current task */
void sched_wake_jp(void);

/* ------------------------------------------------------------- barrier */
struct binj {
	int armed;			/* 1: count barriers after the arm point */
	int count;
	int target;			/* inject at this barrier index */
	int action;			/* 1 watchdog tick, 2 plain tick, 3 reader */
	int done;
	unsigned long ra;		/* caller of the injected barrier */
};
extern struct binj g_binj;
void binj_arm(int target, int action);

/* ---------------------------------------------------------------- misc */
u32 host_rand(void);
void host_srand(u32 s);
#define EV_HEX16(r) (r)

#endif
