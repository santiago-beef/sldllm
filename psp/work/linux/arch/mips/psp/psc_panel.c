/*
 * arch/mips/psp/psc_panel.c - PSC trace: the kernel stall panel (DESIGN 2.10).
 *
 * Painted only from T2d of the timer interrupt (ticks = 125 mod 250, never
 * a watchdog tick, interrupts off), by plain stores into framebuffer RAM at
 * PSP_VRAM_BASE (include/asm-mips/psp.h:36) followed by pspClearDcache()
 * as pspfb_sync does (drivers/video/pspfb.c:348-352). No SPI, GPIO or
 * syscon register, no lock, printk or allocation. Rows 176-271 (the bottom
 * band) belong to this code alone (2.10, 8.2). Columns: panellayout.txt
 * (10.8, handoff/impl/panellayout.txt).
 */
#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/string.h>
#include <asm/psp.h>
#include <asm/ipl_sdk/cache.h>
#include <asm/psc.h>

#define PANEL_Y0	176		/* first row of the band */
#define PANEL_ROWS	96		/* rows 176..271 */
#define PANEL_W		480
#define PANEL_STRIDE	512		/* pixels per line (pspfb.c:28-39) */
#define PANEL_BORDER	2
#define PANEL_COLS	40
#define PANEL_LINES	6
#define PANEL_TX0	20		/* text x origin: (480 - 40 * 11) / 2 */
#define PANEL_TY0	179		/* text y origin */
#define PANEL_CW	11		/* glyph 10 px wide at scale 2, + 1 */
#define PANEL_LH	15		/* glyph 14 px high at scale 2, + 1 */

/* 32-bit pixels, red in bits 0-7, green 8-15, blue 16-23 (pspfb.c:31-33). */
#define PX_BLACK	0x00000000u
#define PX_WHITE	0x00FFFFFFu
#define PX_MAGENTA	0x00FF00FFu

/* 5x7 font, rows top to bottom, bit 4 = leftmost column: 0-9, A-Z, ' ', '-', '.' */
static const unsigned char psc_font[39][7] = {
	{0x0E,0x11,0x13,0x15,0x19,0x11,0x0E}, {0x04,0x0C,0x04,0x04,0x04,0x04,0x0E},
	{0x0E,0x11,0x01,0x02,0x04,0x08,0x1F}, {0x1F,0x02,0x04,0x02,0x01,0x11,0x0E},
	{0x02,0x06,0x0A,0x12,0x1F,0x02,0x02}, {0x1F,0x10,0x1E,0x01,0x01,0x11,0x0E},
	{0x06,0x08,0x10,0x1E,0x11,0x11,0x0E}, {0x1F,0x01,0x02,0x04,0x08,0x08,0x08},
	{0x0E,0x11,0x11,0x0E,0x11,0x11,0x0E}, {0x0E,0x11,0x11,0x0F,0x01,0x02,0x0C},
	{0x0E,0x11,0x11,0x11,0x1F,0x11,0x11}, {0x1E,0x11,0x11,0x1E,0x11,0x11,0x1E}, /* A B */
	{0x0E,0x11,0x10,0x10,0x10,0x11,0x0E}, {0x1C,0x12,0x11,0x11,0x11,0x12,0x1C}, /* C D */
	{0x1F,0x10,0x10,0x1E,0x10,0x10,0x1F}, {0x1F,0x10,0x10,0x1E,0x10,0x10,0x10}, /* E F */
	{0x0E,0x11,0x10,0x17,0x11,0x11,0x0F}, {0x11,0x11,0x11,0x1F,0x11,0x11,0x11}, /* G H */
	{0x0E,0x04,0x04,0x04,0x04,0x04,0x0E}, {0x07,0x02,0x02,0x02,0x02,0x12,0x0C}, /* I J */
	{0x11,0x12,0x14,0x18,0x14,0x12,0x11}, {0x10,0x10,0x10,0x10,0x10,0x10,0x1F}, /* K L */
	{0x11,0x1B,0x15,0x15,0x11,0x11,0x11}, {0x11,0x11,0x19,0x15,0x13,0x11,0x11}, /* M N */
	{0x0E,0x11,0x11,0x11,0x11,0x11,0x0E}, {0x1E,0x11,0x11,0x1E,0x10,0x10,0x10}, /* O P */
	{0x0E,0x11,0x11,0x11,0x15,0x12,0x0D}, {0x1E,0x11,0x11,0x1E,0x14,0x12,0x11}, /* Q R */
	{0x0F,0x10,0x10,0x0E,0x01,0x01,0x1E}, {0x1F,0x04,0x04,0x04,0x04,0x04,0x04}, /* S T */
	{0x11,0x11,0x11,0x11,0x11,0x11,0x0E}, {0x11,0x11,0x11,0x11,0x11,0x0A,0x04}, /* U V */
	{0x11,0x11,0x11,0x15,0x15,0x15,0x0A}, {0x11,0x11,0x0A,0x04,0x0A,0x11,0x11}, /* W X */
	{0x11,0x11,0x11,0x0A,0x04,0x04,0x04}, {0x1F,0x01,0x02,0x04,0x08,0x10,0x1F}, /* Y Z */
	{0x00,0x00,0x00,0x00,0x00,0x00,0x00}, {0x00,0x00,0x00,0x1F,0x00,0x00,0x00}, /* ' ' - */
	{0x00,0x00,0x00,0x00,0x00,0x0C,0x0C},                                       /* . */
};

static int psc_glyph(char c)
{
	if (c >= '0' && c <= '9')
		return c - '0';
	if (c >= 'A' && c <= 'Z')
		return 10 + c - 'A';
	if (c == '-')
		return 37;
	if (c == '.')
		return 38;
	return 36;
}

/* ------------------------------------------------------------------ */
/* Line formatting (integers only)                                      */
/* ------------------------------------------------------------------ */

struct psc_line {
	char	c[PANEL_COLS];
	int	n;
};

static void pl_ch(struct psc_line *l, char c)
{
	if (l->n < PANEL_COLS)
		l->c[l->n++] = c;
}

static void pl_str(struct psc_line *l, const char *s)
{
	while (*s)
		pl_ch(l, *s++);
}

static void pl_hex(struct psc_line *l, u32 v, int digits)
{
	int i;

	for (i = digits - 1; i >= 0; i--)
		pl_ch(l, "0123456789ABCDEF"[(v >> (4 * i)) & 15]);
}

static void pl_dec(struct psc_line *l, u32 v, int digits)
{
	char t[10];
	int i;

	for (i = digits - 1; i >= 0; i--) {
		t[i] = '0' + v % 10;
		v /= 10;
	}
	for (i = 0; i < digits; i++)
		pl_ch(l, t[i]);
}

/* An age in ticks as seconds: "ddd.d" below 1000 s, else "ddddd" (5 chars). */
static void pl_age(struct psc_line *l, u32 ticks)
{
	u32 tenths = ticks / 25;

	if (tenths < 10000) {
		pl_dec(l, tenths / 10, 3);
		pl_ch(l, '.');
		pl_dec(l, tenths % 10, 1);
	} else {
		u32 s = ticks / PSC_HZ;

		pl_dec(l, s > 99999 ? 99999 : s, 5);
	}
}

/* ------------------------------------------------------------------ */
/* Painting                                                             */
/* ------------------------------------------------------------------ */

static void psc_panel_fill(int framed)
{
	u32 *vram = (u32 *)PSP_VRAM_BASE;
	u32 *row;
	int y, x;

	for (y = 0; y < PANEL_ROWS; y++) {
		row = vram + (PANEL_Y0 + y) * PANEL_STRIDE;
		if (framed && (y < PANEL_BORDER || y >= PANEL_ROWS - PANEL_BORDER)) {
			for (x = 0; x < PANEL_W; x++)
				row[x] = PX_MAGENTA;
			continue;
		}
		for (x = 0; x < PANEL_W; x++)
			row[x] = PX_BLACK;
		if (framed) {
			row[0] = row[1] = PX_MAGENTA;
			row[PANEL_W - 2] = row[PANEL_W - 1] = PX_MAGENTA;
		}
	}
}

static void psc_panel_text(const struct psc_line *lines)
{
	u32 *vram = (u32 *)PSP_VRAM_BASE;
	const unsigned char *g;
	u32 *p;
	int li, k, r, b, x0, y0;

	for (li = 0; li < PANEL_LINES; li++) {
		for (k = 0; k < lines[li].n; k++) {
			g = psc_font[psc_glyph(lines[li].c[k])];
			x0 = PANEL_TX0 + k * PANEL_CW;
			y0 = PANEL_TY0 + li * PANEL_LH;
			for (r = 0; r < 7; r++) {
				if (!g[r])
					continue;
				p = vram + (y0 + 2 * r) * PANEL_STRIDE + x0;
				for (b = 0; b < 5; b++) {
					if (g[r] & (0x10 >> b)) {
						p[2 * b] = p[2 * b + 1] = PX_WHITE;
						p[PANEL_STRIDE + 2 * b] = PX_WHITE;
						p[PANEL_STRIDE + 2 * b + 1] = PX_WHITE;
					}
				}
			}
		}
	}
}

static void psc_panel_lines(struct psc_line *l, u32 tick, int test_active, int rdonly)
{
	struct pt_regs *regs = current_thread_info()->regs;
	struct thread_info *ti = current_thread_info();
	unsigned long r = (unsigned long)regs;
	u32 epc = 0, s, w, m;
	int i;

	memset(l, 0, PANEL_LINES * sizeof(*l));

	/* 1: title, DUR, RDR, PNT */
	pl_str(&l[0], rdonly ? "PSC MS RO" : test_active ? "PSC TEST " : "PSC STALL");
	pl_str(&l[0], " DUR ");
	pl_age(&l[0], tick - PSC_RD(psc_st.durable_tick));
	pl_str(&l[0], " RDR ");
	pl_age(&l[0], tick - PSC_RD(psc_st.last_reader_tick));
	pl_str(&l[0], " PNT ");
	pl_dec(&l[0], (psc_st.panel_paints + 1) % 100000, 5);

	/* 2: NOW, running task pid, its EPC (bounds-checked regs), preempt_count */
	if (!(r & 3) && r >= (unsigned long)ti + sizeof(*ti) &&
	    r + sizeof(struct pt_regs) <= (unsigned long)ti + THREAD_SIZE)
		epc = regs->cp0_epc;
	pl_str(&l[1], "NOW ");
	pl_hex(&l[1], tick, 8);
	pl_str(&l[1], " P");
	pl_dec(&l[1], (u32)current->pid % 100000, 5);
	pl_str(&l[1], " E");
	pl_hex(&l[1], epc, 8);
	pl_str(&l[1], " C");
	pl_hex(&l[1], (u32)preempt_count(), 8);

	/* 3: jp_loop, jp_stage, t_busy, t_entry_tick, lc_epc */
	pl_str(&l[2], "JL ");
	pl_hex(&l[2], psc_st.jp_loop, 4);
	pl_str(&l[2], " S ");
	pl_dec(&l[2], psc_st.jp_stage % 100, 2);
	pl_str(&l[2], " B ");
	pl_dec(&l[2], (psc_k.t_busy_p ? 1 : 0) | (psc_k.t_busy_m ? 2 : 0), 1);
	pl_str(&l[2], " TE ");
	pl_hex(&l[2], psc_k.t_entry_tick, 8);
	pl_str(&l[2], " LC ");
	pl_hex(&l[2], psc_k.lc_epc, 8);

	/* 4: the last P record with cmd 0x08: ret, nwords, rx[0..8] */
	s = psc_k.last_p08;
	pl_str(&l[3], "R ");
	if (s == 0) {
		pl_str(&l[3], "NONE");
	} else {
		const struct psc_sc *p = &psc_mem.p[(s - 1) & (PSC_P_ENTRIES - 1)];

		if (p->seq != s - 1) {
			pl_str(&l[3], "----");
		} else {
			pl_ch(&l[3], p->ret < 0 ? '-' : ' ');
			pl_dec(&l[3], p->ret < 0 ? -p->ret : p->ret, 3);
			pl_str(&l[3], " N ");
			pl_dec(&l[3], p->nwords % 10, 1);
			for (i = 0; i < 9; i++) {
				pl_ch(&l[3], ' ');
				pl_hex(&l[3], p->rx[i], 2);
			}
		}
	}

	/* 5: the last W record: tick, epc, ra, cur_pcnt */
	w = PSC_RD(psc_k.head[PSC_RING_W]);
	pl_str(&l[4], "W ");
	if (w == 0) {
		pl_str(&l[4], "NONE");
	} else {
		const struct psc_w *q = &psc_mem.w[(w - 1) & (PSC_W_ENTRIES - 1)];

		pl_hex(&l[4], q->sc.tick_in, 8);
		pl_str(&l[4], " E ");
		pl_hex(&l[4], q->ext.epc, 8);
		pl_str(&l[4], " R ");
		pl_hex(&l[4], q->ext.ra, 8);
		pl_str(&l[4], " C ");
		pl_hex(&l[4], q->ext.cur_pcnt, 2);
	}

	/* 6: Memory Stick marker, fat_panics, META */
	m = PSC_RD(psc_st.ms_ip_word);
	pl_str(&l[5], (m & PSC_MSIP_ACTIVE) ? "MS1 S" : "MS0 S");
	pl_hex(&l[5], psc_st.ms_ip_sector, 7);
	pl_str(&l[5], " P");
	pl_dec(&l[5], PSC_MSIP_PID(m) % 10000, 4);
	pl_str(&l[5], " T");
	pl_hex(&l[5], psc_st.ms_ip_tick, 5);
	pl_str(&l[5], " F");
	pl_dec(&l[5], psc_st.fat_panics > 9 ? 9 : psc_st.fat_panics, 1);
	if (PSC_RD(psc_st.meta_sector)) {
		pl_str(&l[5], " META");
		pl_hex(&l[5], psc_st.meta_sector, 7);
	}
}

static void psc_panel_account(u32 tick, u32 c0)
{
	u32 cost = read_c0_count() - c0;

	psc_st.panel_paints++;
	psc_st.panel_last_tick = tick;
	psc_st.panel_cost_last = cost;
	if (cost > psc_st.panel_cost_max)
		psc_st.panel_cost_max = cost;
	if (psc_k.t_busy_p)
		psc_k.panel_cmd_id = psc_k.t_cmd_id;	/* SC lc_flags b5 (A3 OE6) */
}

/*
 * T2d, once a second (2.3, 2.10): the panel condition, then a paint, a
 * single clearing paint when the condition ends, or nothing.
 */
void psc_panel_t2d(u32 tick)
{
	struct psc_line lines[PANEL_LINES];
	u32 seq, c0;
	int test_active, rdonly, cond;

	if (!PSC_RD(psc_st.proc_opens))		/* "once a ring file has been opened" */
		return;

	seq = PSC_RD(psc_st.panel_test_seq);
	if (seq != psc_k.panel_test_seen) {
		psc_k.panel_test_seen = seq;
		psc_k.panel_test_until = tick + PSC_HZ * PSC_RD(psc_k.panel_test_secs);
	}
	test_active = (s32)(psc_k.panel_test_until - tick) > 0;
	rdonly = psc_fat_rdonly() || psc_st.fat_panics;
	cond = (tick - PSC_RD(psc_st.durable_tick) > 750) ||
	       (tick - PSC_RD(psc_st.last_reader_tick) > 750) ||
	       test_active || rdonly;

	if (cond) {
		c0 = read_c0_count();
		psc_panel_lines(lines, tick, test_active, rdonly);
		psc_panel_fill(1);
		psc_panel_text(lines);
		pspClearDcache();
		psc_panel_account(tick, c0);
		psc_st.panel_state = PSC_PANEL_SHOWING;
		if (test_active)
			psc_st.panel_test_done++;
	} else if (psc_st.panel_state == PSC_PANEL_SHOWING) {
		c0 = read_c0_count();
		psc_panel_fill(0);
		pspClearDcache();
		psc_panel_account(tick, c0);
		psc_st.panel_state = PSC_PANEL_CLEARED;
	}
}
