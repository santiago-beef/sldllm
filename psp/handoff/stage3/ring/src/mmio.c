/*
 * mmio.c - SPI (PL022-like, 0xbe580000) and GPIO (0xbe240000) model behind
 * syscon.c's REG32, the syscon chip behind them, and the observer that
 * classifies every access of a Syscon_cmd call into its step (recon/syscon.md
 * 1.2 S5..S20; release listing addresses from BUILD/vmlinux, see kind_epc[]).
 *
 * MODEL ASSUMPTIONS (all UNVERIFIED on hardware; the host cannot model the
 * real SPI/GPIO controller or syscon firmware):
 *  - SR 0xbe58000c: b0 TX FIFO empty, b1 TX FIFO not full, b2 RX not empty
 *    (PL022 SSPSR layout; syscon.c only tests b2, syscon.c:158,163,256).
 *  - CR1 0xbe580004: bit 1 = enable; RX words arriving while disabled are lost.
 *  - A request is the TX FIFO content at a G3 rising edge (write of 0x08 to
 *    0xbe240008, syscon.c:192). The syscon answers after a latency, pushing the
 *    reply words into the RX FIFO (depth 8) and setting the ACK latch
 *    (0xbe240020 b4); 0x10 to 0xbe240024 clears the latch (syscon.c:211).
 *  - 0xbe240004 reads gpio_in_base | G3 output level (bit 3).
 *  - A DR read with the RX FIFO empty returns EMPTY_READ (0xFFFF).
 *  - Each register access costs MMIO_COST Count units (12, about 54 ns), so
 *    a -4 (1,000,001 ACK polls) lasts about 54 ms (recon: each -4 >= 50 ms).
 *  - Reply frames: [status 0x22, len, code = cmd, payload..., checksum]; the
 *    0x08 payload is the 4 active-low button bytes and x, y (5 words);
 *    0x33, 0x34 and 0x00 replies are 2 words.
 */
#include "host.h"
#include <stdarg.h>

#define MMIO_COST	12u
#define EMPTY_READ	0xFFFFu

/* ------------------------------------------------------------ kinds */
enum {
	K_NONE, K_S5, K_S6, K_S7, K_S8C1, K_S8D, K_S8C2, K_S9, K_S10, K_S11S,
	K_S11P, K_S12, K_S13, K_S14, K_S14T1, K_S14T2, K_S15, K_S18S, K_S18D,
	K_S19, K_S20, K_N
};
/* Release Syscon_cmd (BUILD/vmlinux, 880ceed0..880cf300): the instruction of
 * each register access, in source order. */
static const u32 kind_epc[K_N] = {
	0,
	0x880cefb0,	/* S5   lw  be240004 (dmy)            syscon.c:154 */
	0x880cefbc,	/* S6   sw  be24000c = 8              :156 */
	0x880cefc0,	/* S7   lw  be58000c (if)             :158 */
	0x880cefd4,	/* S8   lw  be58000c (while, first)   :163 */
	0x880cf020,	/* S8   lw  be580008 (dlast)          :166 */
	0x880cf02c,	/* S8   lw  be58000c (while, again)   :163 */
	0x880cf03c,	/* S9   lw  be58000c (st9)            :171 */
	0x880cf050,	/* S10  sw  be580020 = 3              :173 */
	0x880cf064,	/* S11  lw  be58000c (sttx)           :182 */
	0x880cf084,	/* S11  sw  be580008 (push)           :184 */
	0x880cf094,	/* S12  sw  be580004 = 6              :188 */
	0x880cf098,	/* S13  sw  be240008 = 8 (G3 high)    :192 */
	0x880cf0a0,	/* S14  lw  be240020 (ACK poll)       :204 */
	0x880cf0dc,	/* S14  sw  be580004 = 4 (-4)         :206 */
	0x880cf0e4,	/* S14  sw  be24000c = 8 (-4)         :206 */
	0x880cf21c,	/* S15  sw  be240024 = 0x10           :211 */
	0x880cf220,	/* S18  lw  be58000c (rx status)      :256 */
	0x880cf234,	/* S18  lw  be580008 (rx data)        :259 */
	0x880cf274,	/* S19  sw  be580004 = 4              :271 */
	0x880cf278,	/* S20  sw  be24000c = 8 (G3 low)     :274 */
};
static const char *const kind_name[K_N] = {
	"-", "S5", "S6", "S7", "S8c1", "S8d", "S8c2", "S9", "S10", "S11s",
	"S11p", "S12", "S13", "S14", "S14t1", "S14t2", "S15", "S18s", "S18d",
	"S19", "S20",
};
const char *host_kind_name(int k) { return (k >= 0 && k < K_N) ? kind_name[k] : "?"; }
u32 host_kind_epc(int k) { return (k > 0 && k < K_N) ? kind_epc[k] : 0; }

enum {
	ST_IDLE, ST_S6, ST_S7, ST_D1, ST_DPOP, ST_D2, ST_S9, ST_S10, ST_TXS,
	ST_TXP, ST_TXS_OR_S12, ST_S13, ST_ACK, ST_T2, ST_S15, ST_RXS, ST_RXD,
	ST_S19, ST_S20, ST_DONE, ST_TO4
};

/* ------------------------------------------------- per-context observer */
struct xctx {
	int active;
	int cmd;		/* command byte (aiming and register synthesis only) */
	char origin;		/* 'P', 'M', 'T' (WT), 'B' (WB) by the harness */
	int state;
	int attempt;
	u32 tick0, c0;
	int pid, ie, pcnt, sig;
	/* final-attempt captures */
	u32 gin, st9, sttx, dlast, drain_n, ack_fail;
	int drain_entered, rx_entered;
	u16 txw[8]; int ntx;
	u16 rxw[8]; int nrx;
	int kind_count[K_N];	/* occurrences per kind (this attempt) */
	u32 last_rd;		/* last value read */
	u32 tx_buf_va, rx_buf_va;
};
static struct xctx xc_task[T_NTASK];
static struct xctx xc_irq;
int g_in_nop;			/* the timer Nop is running */
int g_in_boot_nop;

static struct xctx *xc_cur(void)
{
	if (g_in_nop || g_in_boot_nop)
		return &xc_irq;
	return &xc_task[g_cur];
}

/* ------------------------------------------------------------ device */
struct req { u16 w[8]; int n; int cmd; u64 due; int deliver; };
static struct {
	u32 gpio_out;		/* output latch: b3 G3, b6/b7 LEDs */
	u32 gpio_in_base;
	int latch;		/* 0xbe240020 b4 */
	int latch_stuck;
	u32 cr1;
	u16 txq[16]; int ntx;
	u16 rxq[8]; int nrx;
	struct req q[16]; int nq;
	int mode;
	u8 frozen[16]; int frozen_valid;
	u8 lastreply[16]; int lastreply_n; int lastreply_valid;
	/* unit-test forcing (tests.c) */
	int f_armed, f_n, f_noack, f_busy, f_rx_stuck;
	u16 f_w[8];
	u32 rng;
	unsigned long n_requests, n_replies, n_lost_words;
} D;

u32 host_rand(void)
{
	D.rng = D.rng * 1103515245u + 12345u;
	return (D.rng >> 8) & 0xFFFFFF;
}
void host_srand(u32 s) { D.rng = s ? s : 1; }

void dev_init(u32 seed)
{
	memset(&D, 0, sizeof(D));
	D.gpio_in_base = 0x0002;
	D.cr1 = 4;
	host_srand(seed);
}
void dev_set_mode(int mode)
{
	D.mode = mode;
	if (mode == DM_LATCH) {
		D.latch_stuck = 1;
		D.gpio_in_base = 0x0006;
	}
	ev("DEVMODE %d\n", mode);
}
int dev_get_mode(void) { return D.mode; }
u32 dev_gpio_out(void) { return D.gpio_out; }

/* build a reply frame: rx[0] status, rx[1] = len (bytes before the
 * checksum), rx[2] code, payload, rx[len] = ~sum(rx[0..len-1]) */
static int frame(u8 *f, u8 code, const u8 *pl, int npl)
{
	int len = 3 + npl, i;
	u8 sum = 0;

	f[0] = 0x22;
	f[1] = (u8)len;
	f[2] = code;
	for (i = 0; i < npl; i++)
		f[3 + i] = pl[i];
	for (i = 0; i < len; i++)
		sum += f[i];
	f[len] = (u8)~sum;
	return len + 1;			/* bytes */
}

void dev_force_reply(const u16 *w, int n) { D.f_armed = 1; D.f_n = n; memcpy(D.f_w, w, sizeof(u16) * n); }
void dev_force_noack(int on) { D.f_noack = on; }
void dev_force_busy(int times) { D.f_busy = times; }
void dev_force_rx_stuck(int on) { D.f_rx_stuck = on; }
int dev_pending(void) { return D.nq; }
void dev_flush(void) { D.nq = 0; D.nrx = 0; D.ntx = 0; D.latch = 0; }

static void make_reply(struct req *r)
{
	u8 f[16], pl[6], x, y;
	int nb = 0, i, cmd = r->cmd;

	r->deliver = 1;			/* push words and set the latch */
	if (D.f_noack) {
		r->deliver = 0;
		return;
	}
	if (D.f_busy > 0) {
		D.f_busy--;
		nb = frame(f, 0x80, pl, 0);
		r->n = (nb + 1) / 2;
		for (i = 0; i < r->n; i++)
			r->w[i] = (u16)((f[2 * i] << 8) | (2 * i + 1 < nb ? f[2 * i + 1] : 0xff));
		return;
	}
	if (D.f_armed) {
		D.f_armed = 0;
		r->n = D.f_n;
		memcpy(r->w, D.f_w, sizeof(u16) * D.f_n);
		return;
	}
	if (cmd == 0x08) {
		op_buttons(pl, &x, &y);
		pl[4] = x;
		pl[5] = y;
		nb = frame(f, 0x08, pl, 6);
		switch (D.mode) {
		case DM_NOACK:
			r->deliver = 0;
			break;
		case DM_ZERO:
			memset(f, 0, 10);
			nb = 10;
			break;
		case DM_EMPTY:
			nb = 0;
			break;
		case DM_BUSY:
			nb = frame(f, 0x80, pl, 0);
			break;
		case DM_FROZEN:
			if (!D.frozen_valid) {
				memcpy(D.frozen, f, 16);
				D.frozen_valid = 1;
			}
			memcpy(f, D.frozen, 10);
			nb = 10;
			break;
		case DM_CODE42:
			if (!D.frozen_valid) {
				memcpy(D.frozen, f, 16);
				D.frozen_valid = 1;
			}
			nb = frame(f, 0x42, D.frozen + 3, 6);
			break;
		default:
			break;
		}
	} else {
		nb = frame(f, (u8)cmd, pl, 0);
		if (D.mode == DM_NOACK && cmd == 0x33)
			r->deliver = 0;
	}
	if (D.mode == DM_LAG) {
		/* N2b: this request gets the previous request's reply */
		u8 prev[16];
		int pn = D.lastreply_n;

		memcpy(prev, D.lastreply, 16);
		memcpy(D.lastreply, f, 16);
		D.lastreply_n = nb;
		if (D.lastreply_valid) {
			memcpy(f, prev, 16);
			nb = pn;
		}
	} else {
		memcpy(D.lastreply, f, 16);
		D.lastreply_n = nb;
	}
	D.lastreply_valid = 1;
	r->n = (nb + 1) / 2;
	for (i = 0; i < r->n; i++)
		r->w[i] = (u16)((f[2 * i] << 8) | (2 * i + 1 < nb ? f[2 * i + 1] : 0xff));
}

static void dev_request(void)
{
	struct req *r;
	u32 lat;

	if (D.ntx == 0 || D.nq >= 16)
		return;			/* G3 raised with nothing to send */
	r = &D.q[D.nq++];
	memset(r, 0, sizeof(*r));
	r->cmd = D.txq[0] >> 8;
	D.ntx = 0;			/* the TX FIFO is shifted out */
	lat = (r->cmd == 0x08) ? 1500 : 1150;
	lat += host_rand() % 300;
	r->due = g_abs + lat;
	make_reply(r);
	D.n_requests++;
	ev("DREQ %d %u\n", r->cmd, lat);
}

static void dev_process(void)
{
	while (D.nq && D.q[0].due <= g_abs) {
		struct req *r = &D.q[0];
		int i;

		if (r->deliver) {
			for (i = 0; i < r->n; i++) {
				if ((D.cr1 & 2) && D.nrx < 8)
					D.rxq[D.nrx++] = r->w[i];
				else
					D.n_lost_words++;
			}
			D.latch = 1;
			D.n_replies++;
		}
		memmove(&D.q[0], &D.q[1], (D.nq - 1) * sizeof(D.q[0]));
		D.nq--;
	}
}

static u32 dev_read(unsigned long a)
{
	switch (a) {
	case 0xbe240004:
		return D.gpio_in_base | (D.gpio_out & 0x08);
	case 0xbe240008:
	case 0xbe24000c:
		return D.gpio_out;	/* LED read-back model (UNVERIFIED) */
	case 0xbe240020:
		return (D.latch || D.latch_stuck) ? 0x10 : 0;
	case 0xbe58000c:
		return (D.ntx == 0 ? 1 : 0) | (D.ntx < 8 ? 2 : 0) | ((D.nrx || D.f_rx_stuck) ? 4 : 0);
	case 0xbe580008:
		if (D.f_rx_stuck)
			return 0x1234;
		if (D.nrx) {
			u16 v = D.rxq[0];

			memmove(&D.rxq[0], &D.rxq[1], (D.nrx - 1) * sizeof(u16));
			D.nrx--;
			return v;
		}
		return EMPTY_READ;
	default:
		return 0;
	}
}

static void dev_write(unsigned long a, u32 v)
{
	switch (a) {
	case 0xbe240008:
		if ((v & 0x08) && !(D.gpio_out & 0x08)) {
			D.gpio_out |= v;
			dev_request();
		} else {
			D.gpio_out |= v;
		}
		break;
	case 0xbe24000c:
		D.gpio_out &= ~v;
		break;
	case 0xbe240024:
		if (v & 0x10)
			D.latch = 0;
		break;
	case 0xbe580004:
		D.cr1 = v;
		break;
	case 0xbe580008:
		if (D.ntx < 16)
			D.txq[D.ntx++] = (u16)v;
		break;
	default:
		break;
	}
}

/* psp_gpio_set/clear (psp.c:410-428) as seen by the device: one load of the
 * SET or CLEAR register, one store of (value | mask). The real code's
 * psc_note_led() is then called by the harness with the loaded value. */
void dev_led_rmw(int set, u32 mask, u32 *readback)
{
	u32 v = dev_read(set ? 0xbe240008 : 0xbe24000c);

	dev_write(set ? 0xbe240008 : 0xbe24000c, v | mask);
	*readback = v;
}

/* ------------------------------------------------------- classification */
static int classify(struct xctx *x, unsigned long a, int w)
{
	switch (x->state) {
	case ST_IDLE: case ST_DONE:
		if (!w && a == 0xbe240004) return K_S5;
		break;
	case ST_S6: if (w && a == 0xbe24000c) return K_S6; break;
	case ST_S7: if (!w && a == 0xbe58000c) return K_S7; break;
	case ST_D1: if (!w && a == 0xbe58000c) return K_S8C1; break;
	case ST_DPOP: if (!w && a == 0xbe580008) return K_S8D; break;
	case ST_D2: if (!w && a == 0xbe58000c) return K_S8C2; break;
	case ST_S9: if (!w && a == 0xbe58000c) return K_S9; break;
	case ST_S10: if (w && a == 0xbe580020) return K_S10; break;
	case ST_TXS: if (!w && a == 0xbe58000c) return K_S11S; break;
	case ST_TXP: if (w && a == 0xbe580008) return K_S11P; break;
	case ST_TXS_OR_S12:
		if (!w && a == 0xbe58000c) return K_S11S;
		if (w && a == 0xbe580004) return K_S12;
		break;
	case ST_S13: if (w && a == 0xbe240008) return K_S13; break;
	case ST_ACK:
		if (!w && a == 0xbe240020) return K_S14;
		if (w && a == 0xbe580004) return K_S14T1;
		break;
	case ST_T2: if (w && a == 0xbe24000c) return K_S14T2; break;
	case ST_S15: if (w && a == 0xbe240024) return K_S15; break;
	case ST_RXS:
		if (!w && a == 0xbe58000c) return K_S18S;
		if (w && a == 0xbe580004) return K_S19;
		break;
	case ST_RXD: if (!w && a == 0xbe580008) return K_S18D; break;
	case ST_S19: if (w && a == 0xbe580004) return K_S19; break;
	case ST_S20: if (w && a == 0xbe24000c) return K_S20; break;
	}
	return K_NONE;
}

static void attempt_reset(struct xctx *x)
{
	x->gin = x->st9 = x->sttx = x->dlast = x->drain_n = x->ack_fail = 0;
	x->drain_entered = x->rx_entered = 0;
	x->ntx = x->nrx = 0;
	memset(x->kind_count, 0, sizeof(x->kind_count));
}

/* synthetic MIPS stack addresses of _pspSysconGetCtrl2 / tx_dword frames on
 * the joypad thread's kernel stack (thread_info at 0x81f3a000), UNVERIFIED */
#define JP_TI		0x81f3a000u
#define SC_SP		0x81f3bd10u	/* Syscon_cmd's sp */
#define TX_BUF		0x81f3bda0u
#define RX_BUF		0x81f3bdb0u
#define RA_SYSCON	0x880d3544u	/* after jal Syscon_cmd in psc_syscon_cmd */

/* The registers the release code holds at the instruction of access `k`
 * (read off the listing; regmap.txt rows for i, ptr, cnt, result). */
static void synth_regs(const struct xctx *x, int k, u32 wv, struct ipt *p)
{
	u32 *r = p->r;
	u32 cnt = (x->cmd == 0x33 || x->cmd == 0x34) ? 3 : 2;	/* tx_buf[1] */
	u32 i_tx = 2u * (u32)x->kind_count[K_S11P];	/* bytes pushed */
	u32 j = (u32)x->nrx;				/* words popped */

	memset(p, 0, sizeof(*p));
	p->epc = kind_epc[k];
	p->cause = 0x00008000;		/* IP7 pending, ExcCode Int, BD 0 */
	p->status = 0x1000ff03;		/* CU0, IM, EXL, IE */
	p->ra = RA_SYSCON;
	p->sp = SC_SP;
	r[3] = RX_BUF;			/* a1 = rx_buf */
	r[4] = 0xbe580020;		/* a2 after the prologue */
	r[8] = 0xbe58000c;		/* t2 */
	r[10] = 0xbe580008;		/* t4 */
	r[11] = TX_BUF;			/* t5 = tx_buf */
	r[12] = TX_BUF + 1;		/* t6 */
	r[13] = 0xbe240020;		/* t7 */
	r[14] = (u32)x->attempt;	/* t8 = retry_cnt */
	r[15] = RX_BUF + 2;		/* t9 = rx_buf + 2 */
	r[0] = x->last_rd;
	r[1] = 0xffffffffu;
	r[2] = 0xffffffffu;
	r[5] = 0xffffffffu;
	r[6] = cnt;			/* t0 = cnt from +0x78 */
	switch (k) {
	case K_S10:
		r[1] = 3; r[7] = cnt + 1;
		break;
	case K_S11S:
		r[6] = i_tx; r[5] = TX_BUF + i_tx; r[7] = cnt + 1;
		break;
	case K_S11P:
		r[6] = i_tx + 2; r[5] = TX_BUF + i_tx + 2; r[7] = cnt + 1;
		r[0] = wv; r[1] = x->sttx & 0xffff;
		r[2] = (i_tx + 2 < cnt + 1);
		break;
	case K_S12: case K_S13: case K_S14:
		r[6] = i_tx; r[5] = TX_BUF + i_tx; r[7] = cnt + 1;
		r[0] = (k == K_S14) ? (x->last_rd & 0x10) : 6;
		r[1] = SPIN_MAX - x->ack_fail;
		break;
	case K_S14T1: case K_S14T2:
		r[6] = i_tx; r[5] = TX_BUF + i_tx;
		r[3] = 0xbe24000c; r[2] = 4; r[0] = 0xbe580004; r[1] = 8;
		if (k == K_S14T2) r[9] = (u32)-4;
		break;
	case K_S15:
		r[6] = 2; r[5] = RX_BUF + 2; r[9] = 0; r[0] = 16;
		break;
	case K_S18S:
		r[6] = 2 * j + 2; r[5] = RX_BUF + 2 * j + 2;
		r[9] = j ? (x->rxw[0] >> 8) : 0;
		break;
	case K_S18D:
		r[6] = 2 * j + 2; r[5] = RX_BUF + 2 * j + 2;
		r[9] = j ? (x->rxw[0] >> 8) : 0;
		r[0] = 4; r[7] = (2 * j + 2 < 16); r[2] = 2 * j;
		break;
	case K_S19: case K_S20:
		r[6] = (2 * j + 2 < 16) ? 2 * j + 2 : 16;
		r[5] = RX_BUF + r[6];
		r[9] = j ? (x->rxw[0] >> 8) : 0;
		r[0] = 4; r[1] = 0xbe580004;
		break;
	default:
		break;
	}
}

/* point of an interrupt that arrives before access `k` of `x` */
static void point_for(const struct xctx *x, int k, u32 wv, struct ipt *p)
{
	if (x->origin == 'P' || x->origin == 'M') {
		synth_regs(x, k, wv, p);
		p->pcnt = psc_host_preempt_count;
	} else {
		ipt_for_current(p);
	}
}

struct trig g_trig;
extern u32 g_epc_override;
void scen_xfer_end(char origin, int cmd);
void (*g_xfer_hook)(char origin, int cmd);	/* unit tests */

/* register access entry points (psptypes.h proxy) */
int psc_host_is_mmio(unsigned long a)
{
	return (a & ~0xFFUL) == 0xbe240000UL || (a & ~0xFFUL) == 0xbe580000UL ||
	       a == 0xbc100078UL;
}

static int access_common(unsigned long a, int w, u32 wv, u32 *rv)
{
	struct xctx *x = xc_cur();
	int k = classify(x, a, w);
	int fire = 0;
	struct ipt p;

	if (k == K_NONE) {
		ev("MMIO-UNEXPECTED ctx=%c state=%d addr=%08lx w=%d\n",
		   x->origin ? x->origin : '?', x->state, a, w);
		fprintf(stderr, "mmio: unexpected access %08lx w=%d state %d\n", a, w, x->state);
	}
	if (k == K_S5) {
		if (!x->active) {
			memset(x, 0, sizeof(*x));
			x->active = 1;
			if (g_in_nop)
				x->origin = 'T';
			else if (g_in_boot_nop)
				x->origin = 'B';
			else if (g_cur == T_JP)
				x->origin = 'P';
			else
				x->origin = 'M';
			/* aiming/register synthesis only: P commands publish
			 * their cmd in psc_k.t_cmd at entry (psc.c:236) */
			x->cmd = (x->origin == 'P') ? (int)psc_k.t_cmd :
				 (x->origin == 'M') ? 0x34 : 0x00;
			x->tick0 = (u32)psp_local_tick;
			x->c0 = g_count;
			x->pid = current->pid;
			x->ie = g_ie;
			x->pcnt = psc_host_preempt_count;
			x->sig = current->host_sigpending;
			ev("XS %c %u %u %d %d %d %d\n", x->origin, x->tick0, x->c0,
			   x->pid, x->ie, x->pcnt, x->sig);
		} else {
			x->attempt++;
		}
		attempt_reset(x);
	}
	/* an interrupt before this access: a due tick, or the forced trigger */
	if (g_ie && !g_in_nop && !g_in_boot_nop) {
		if (g_trig.armed && !g_trig.fired && x->origin == g_trig.ctx_origin &&
		    k == g_trig.kind && x->cmd == g_trig.cmd &&
		    (g_trig.nth < 0 || x->kind_count[k] == g_trig.nth) &&
		    (!g_trig.need_latch || D.latch || D.latch_stuck ||
		     (D.nq && D.q[0].due <= g_abs))) {
			g_trig.fired = 1;
			if (g_count < CPT)
				g_count = CPT;
			fire = 1;
			ev("TRIG %s %d\n", kind_name[k], g_trig.nth);
		}
		if (g_count >= CPT)
			fire = 1;
	}
	if (fire) {
		point_for(x, k, wv, &p);
		if (g_trig.fired == 1 && g_epc_override && x->origin == 'P') {
			p.epc = g_epc_override;		/* e.g. P0: before S5, in S3 */
			g_trig.fired = 2;
		}
		fire_tick(&p);
	}
	dev_process();
	if (w) {
		dev_write(a, wv);
	} else {
		*rv = dev_read(a);
		x->last_rd = *rv;
	}
	if (k != K_NONE)
		x->kind_count[k]++;
	/* transitions and captures */
	switch (k) {
	case K_S5: x->gin = *rv & 0xffff; x->state = ST_S6; break;
	case K_S6: x->state = ST_S7; break;
	case K_S7:
		if (*rv & 4) { x->state = ST_D1; x->drain_entered = 1; }
		else x->state = ST_S9;
		break;
	case K_S8C1: case K_S8C2: x->state = (*rv & 4) ? ST_DPOP : ST_S9; break;
	case K_S8D: x->drain_n++; x->dlast = *rv & 0xffff; x->state = ST_D2; break;
	case K_S9: x->st9 = *rv & 0xffff; x->state = ST_S10; break;
	case K_S10: x->state = ST_TXS; break;
	case K_S11S: x->sttx = *rv & 0xffff; x->state = ST_TXP; break;
	case K_S11P:
		if (x->ntx < 8) x->txw[x->ntx++] = (u16)wv;
		x->state = ST_TXS_OR_S12;
		break;
	case K_S12: x->state = ST_S13; break;
	case K_S13: x->state = ST_ACK; x->ack_fail = 0; break;
	case K_S14:
		if (*rv & 0x10) x->state = ST_S15;
		else x->ack_fail++;
		break;
	case K_S14T1: x->state = ST_T2; break;
	case K_S14T2: x->state = ST_TO4; break;
	case K_S15: x->state = ST_RXS; x->rx_entered = 1; x->nrx = 0; break;
	case K_S18S: x->state = (*rv & 4) ? ST_RXD : ST_S19; break;
	case K_S18D:
		if (x->nrx < 8) x->rxw[x->nrx++] = (u16)(*rv & 0xffff);
		x->state = (x->nrx == 8) ? ST_S19 : ST_RXS;
		break;
	case K_S19: x->state = ST_S20; break;
	case K_S20: x->state = ST_DONE; break;
	default: break;
	}
	g_count += MMIO_COST;
	g_abs += MMIO_COST;
	return k;
}

unsigned int psc_host_mmio_rd(unsigned long a)
{
	u32 v = 0;

	if (a == 0xbc100078UL)
		return 0;
	access_common(a, 0, 0, &v);
	return v;
}

void psc_host_mmio_wr(unsigned long a, unsigned int val)
{
	u32 dummy;

	if (a == 0xbc100078UL)
		return;
	access_common(a, 1, val, &dummy);
}

/* syscon.c `out:` hand-off (see syscon_host.cc) */
void psc_host_xfer_out(unsigned gin, unsigned spin, unsigned spin_ack,
		       unsigned dlast, unsigned st9, unsigned sttx,
		       unsigned retry_cnt)
{
	struct xctx *x = xc_cur();
	struct psc_xfer_raw raw;
	int how;		/* 0 normal, 3 drain timeout, 4 ack timeout */
	u32 t0, i;
	char rxhex[33];
	u8 rx[16];

	memset(rx, 0xff, sizeof(rx));
	for (i = 0; i < (u32)x->nrx && i < 8; i++) {
		rx[2 * i] = (u8)(x->rxw[i] >> 8);
		rx[2 * i + 1] = (u8)x->rxw[i];
	}
	if (x->state == ST_DPOP) {
		how = 3;
		t0 = x->txw[0] ? (x->txw[0] & 0xff) : 2;	/* lbu t0 = tx_buf[1] */
	} else if (x->state == ST_TO4) {
		how = 4;
		t0 = 2u * (u32)x->ntx;				/* TX loop i */
	} else {
		how = 0;
		t0 = x->rx_entered ? (2u * (u32)x->nrx + 2u > 16u ? 16u : 2u * (u32)x->nrx + 2u) : 2u;
	}
	/* the hand-off asm and psc_xfer_out (62 + 32 instructions, 18.1) */
	{
		extern int g_where[T_NTASK];
		extern int g_irq_depth;

		if (g_ie && !g_in_nop && !g_in_boot_nop) {
			int w = g_where[g_cur];

			g_where[g_cur] = 8;	/* WH_HANDOFF */
			sim_advance(94);
			g_where[g_cur] = w;
		} else {
			g_count += 94;
			g_abs += 94;
		}
	}
	raw.gin = gin;
	raw.spin = spin;
	raw.spin_ack = spin_ack;
	raw.dlast = dlast;
	raw.st9 = st9;
	raw.sttx = sttx;
	raw.t0 = t0;
	raw.t8 = retry_cnt;
	psc_xfer_out(&raw);		/* the real hand-off target (psc.c:188) */

	for (i = 0; i < 16; i++)
		sprintf(rxhex + 2 * i, "%02x", rx[i]);
	ev("XE %c %u %u %d %u %u %u %u %u %u %u %u %u %d %s %u %u %u\n",
	   x->origin, (u32)psp_local_tick, g_count, how, x->attempt,
	   (u32)x->txw[0], (u32)x->txw[1], x->gin, x->drain_entered ? x->drain_n : 0,
	   x->drain_entered ? x->dlast : 0, x->st9, x->sttx, x->ack_fail,
	   x->nrx, rxhex, (u32)x->rx_entered, t0, retry_cnt);
	/* cross-check the observer against the transaction's own slots */
	if ((gin & 0xffff) != x->gin ||
	    retry_cnt != (unsigned)x->attempt + ((how == 0 && x->nrx >= 2 &&
	    ((x->rxw[1] >> 8) == 0x80 || (x->rxw[1] >> 8) == 0x81)) ? 1u : 0u) ||
	    (how != 3 && (sttx & 0xffff) != x->sttx) || (how != 3 && (st9 & 0xffff) != x->st9))
		ev("OBS-MISMATCH gin %u/%u retry %u/%d st9 %u/%u sttx %u/%u\n",
		   gin, x->gin, retry_cnt, x->attempt, st9, x->st9, sttx, x->sttx);
	x->active = 0;
	x->state = ST_IDLE;
	if (g_xfer_hook)
		g_xfer_hook(x->origin, x->cmd);
	scen_xfer_end(x->origin, x->cmd);
}

/* syscon state for reports */
void dev_report(FILE *f)
{
	fprintf(f, "device requests %lu replies %lu lost_words %lu\n",
		D.n_requests, D.n_replies, D.n_lost_words);
}

/* used by the scenario code to aim a trigger */
int host_kind_by_name(const char *n)
{
	int k;

	for (k = 1; k < K_N; k++)
		if (!strcmp(kind_name[k], n))
			return k;
	return -1;
}
