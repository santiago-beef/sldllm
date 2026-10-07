/*
 * tests.c - unit tests of the ring and record code (Stage 3 ring logic).
 * The code under test is the real psc.c / syscon.c / joypad_psp.c; this file
 * drives it and checks the results. Every check counts as PASS or FAIL and
 * every observation that is not a pass/fail property is printed as NOTE.
 *
 *   ringtest all | nwords | wrap | overflow | reader | inject | single | tsread | mring | ctl
 */
#define _GNU_SOURCE
#include "host.h"
#include <signal.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/uio.h>
#include <elf.h>
#include <ucontext.h>
#include <stdarg.h>
#include <sys/user.h>

/* harness entry points */
void vram_map(void);
void syms_init(void);
void tasks_init(void);
void col_start(void);
void col_mount(void);
int jp_host_init(void);
void sim_align_wd(void);
void sim_idle_tick(void);
void ms_write_seg(u32 sector, u32 nsect, int meta);
const struct file_operations *col_ring_fops(int ring);
struct file *col_ring_file(int ring);
void col_read_stats(struct psc_stats *st);
void col_ctl(u32 op, u32 a0, u32 a1, u32 a2, u32 a3, u32 a4, u32 a5);
void dev_force_reply(const u16 *w, int n);
void dev_force_noack(int on);
void dev_force_busy(int times);
void dev_force_rx_stuck(int on);
void dev_flush(void);
const char *host_fn_of(unsigned long ra, unsigned long *off);
extern int (*psc_host_late_initcall_psc_init)(void);
extern int g_in_boot_nop, g_in_nop, g_log_reads, g_irq_depth;
extern void (*g_binj_reader)(void);
extern void (*g_xfer_hook)(char origin, int cmd);
extern void (*g_copy_hook)(void);
extern int psc_sc_exit(struct psc_scratch *sc);	/* psc.c:427 (not in a header) */

static int n_pass, n_fail, n_note;
#define CHECK(cond, ...) do { if (cond) n_pass++; else { n_fail++; printf("FAIL %s:%d: ", __func__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)
#define NOTE(...) do { n_note++; printf("NOTE "); printf(__VA_ARGS__); printf("\n"); } while (0)

static const int RSZ[5] = { 80, 40, 288, 40, 80 };


/* ------------------------------------------------------------- set-up */
static void boot(void)
{
	vram_map();
	syms_init();
	tasks_init();
	dev_init(7);
	g_ev = NULL;
	g_log_reads = 0;
	g_ie = 0;
	g_count = 2000;
	psc_k.wd_ctx = PSC_WDCTX_BOOT;
	g_in_boot_nop = 1;
	pspSysconNop();
	g_in_boot_nop = 0;
	psc_k.wd_ctx = PSC_WDCTX_NONE;
	g_ie = 1;
	do_switch(T_IDLE, T_INIT);
	pspSysconCtrlHRPower(1);
	jp_host_init();
	psc_host_late_initcall_psc_init();
	do_switch(T_INIT, T_JP);
	psc_jp_thread_start();
	do_switch(T_JP, T_WRK);
	col_mount();
	col_start();
	do_switch(T_WRK, T_IDLE);
}

static void as(int t) { if (g_cur != t) do_switch(g_cur, t); }

static int cmd08(void)
{
	u32 keys;
	u8 x, y;

	as(T_JP);
	return _pspSysconGetCtrl2(&keys, &x, &y);
}

static ssize_t rd(int ring, void *buf, size_t n)
{
	struct file *f = col_ring_file(ring);
	loff_t pos = f->f_pos;
	ssize_t r = col_ring_fops(ring)->read(f, buf, n, &pos);

	f->f_pos = pos;			/* sys_read writes the position back */
	return r;
}

static ssize_t prd(int ring, void *buf, size_t n, loff_t off, loff_t *after)
{
	loff_t pos = off;		/* pread: a local position (read_write.c:404) */
	ssize_t r = col_ring_fops(ring)->read(col_ring_file(ring), buf, n, &pos);

	if (after)
		*after = pos;
	return r;
}

#define BIGSZ (5200 * 288)
static u8 *big;		/* heap: the bss must stay below 0x880ceed0 (place.ld) */

/* read everything pending on a ring; returns records, checks seq order */
static int drain_all(int ring, u32 *first, u32 *lost, u32 *expect_next)
{
	int n = 0, i;
	ssize_t r;

	*lost = 0;
	*first = 0xFFFFFFFF;
	as(T_WRK);
	while ((r = rd(ring, big, BIGSZ / RSZ[ring] * RSZ[ring])) > 0) {
		for (i = 0; i < r / RSZ[ring]; i++) {
			u32 seq;

			memcpy(&seq, big + i * RSZ[ring], 4);
			if (*first == 0xFFFFFFFF)
				*first = seq;
			if (seq != *expect_next) {
				if (seq > *expect_next)
					*lost += seq - *expect_next;
			}
			*expect_next = seq + 1;
			n++;
		}
	}
	return n;
}

/* ============================================ T1: nwords table (R-1, 18.3) */
static void mk_frame(u16 *w, int k, int last_ffff)
{
	u8 b[16];
	int i, nb = 2 * k;
	u8 sum = 0;

	memset(b, 0, sizeof(b));
	b[0] = 0x22;
	b[1] = (u8)(nb - 1);		/* checksum at the last byte */
	b[2] = 0x08;
	for (i = 3; i < nb - 1; i++)
		b[i] = (u8)(0x10 + i);
	if (k == 8 && last_ffff) {
		/* rx[14] = 0xff and checksum rx[15] = 0xff: sum(rx[0..14]) = 0 */
		b[14] = 0xff;
		for (i = 0; i < 14; i++)
			sum += b[i];
		sum += b[14];
		b[13] = (u8)(b[13] - sum);	/* make sum(rx[0..14]) == 0 */
		b[15] = 0xff;
	} else if (k == 8) {
		b[14] = 0x33;
		for (i = 0; i < 15; i++)
			sum += b[i];
		b[15] = (u8)~sum;
		if (b[15] != 0x33) {
			b[13] = (u8)(b[13] + (u8)(b[15] - 0x33));
			sum = 0;
			for (i = 0; i < 15; i++)
				sum += b[i];
			b[15] = (u8)~sum;
		}
	} else if (nb >= 4) {
		for (i = 0; i < nb - 1; i++)
			sum += b[i];
		b[nb - 1] = (u8)~sum;
	}
	for (i = 0; i < k; i++)
		w[i] = (u16)((b[2 * i] << 8) | b[2 * i + 1]);
}

static struct psc_sc *last_p(void)
{
	return &psc_mem.p[(psc_k.head[PSC_RING_P] - 1) & (PSC_P_ENTRIES - 1)];
}

static void t_nwords(void)
{
	int k;
	u16 w[8];

	printf("== T1 nwords table (DESIGN 1.2 offset 22, 17 R-1, 18.3; IMPLEMENTATION 9.2.5)\n");
	for (k = 0; k <= 8; k++) {
		int variants = (k == 8) ? 2 : 1, v;

		for (v = 0; v < variants; v++) {
			struct psc_sc *r;
			int flagged, expect_nw;

			mk_frame(w, k ? k : 1, v);
			dev_force_reply(w, k);
			cmd08();
			r = last_p();
			flagged = r->nwords == 7 && r->rx[14] == 0xff && r->rx[15] == 0xff;
			expect_nw = (k == 8 && v) ? 7 : k;
			CHECK(r->nwords == expect_nw, "k=%d ffff=%d: nwords %u, want %d", k, v, r->nwords, expect_nw);
			CHECK(flagged == (expect_nw == 7), "k=%d ffff=%d: nw7or8 flag %d", k, v, flagged);
			CHECK(r->retries == 0 && r->drain == 0, "k=%d retries %u drain %u", k, r->retries, r->drain);
			if (k >= 2)
				CHECK(r->ret == 0x22, "k=%d valid frame ret %d", k, r->ret);
			else if (k == 1)
				CHECK(r->ret == -2, "k=1 ret %d (rx[1] < 3)", r->ret);
			else
				CHECK(r->ret == 0 && !memcmp(r->rx, "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff", 16),
				      "k=0 ret %d", r->ret);
			printf("  k=%d%s: ret %d nwords %u nw7or8 %d ack_polls %u rx %02x%02x..%02x%02x\n",
			       k, (k == 8) ? (v ? " (8th 0xFFFF)" : " (8th 0x3333)") : "", r->ret, r->nwords,
			       flagged, r->ack_polls, r->rx[0], r->rx[1], r->rx[14], r->rx[15]);
		}
	}
	/* -4 */
	{
		struct psc_sc *r;

		dev_force_noack(1);
		cmd08();
		dev_force_noack(0);
		r = last_p();
		CHECK(r->ret == -4 && r->nwords == 0 && r->ack_polls == 1000001u && r->drain == 0,
		      "-4: ret %d nwords %u ack_polls %u drain %u", r->ret, r->nwords, r->ack_polls, r->drain);
		CHECK(r->lc_n >= 12 && (r->lc_flags & PSC_LC_F_VALID) && (r->lc_flags & PSC_LC_F_IN_SYSCON) &&
		      r->lc_epc == 0x880cf0a0, "-4: lc_n %u lc_flags %02x lc_epc %08x", r->lc_n, r->lc_flags, r->lc_epc);
		printf("  -4: ret %d nwords %u ack_polls %u dtick %u lc_n %u lc_epc %08x lc_dtick %u\n", r->ret,
		       r->nwords, r->ack_polls, r->dtick, r->lc_n, r->lc_epc, r->lc_dtick);
		dev_flush();
	}
	/* -3 */
	{
		struct psc_sc *r;

		dev_force_rx_stuck(1);
		cmd08();
		dev_force_rx_stuck(0);
		r = last_p();
		CHECK(r->ret == -3 && r->nwords == 0 && r->ack_polls == 0xFFFFFFFFu && r->drain == 0xFFFF &&
		      r->drain_last == 0x1234 && r->spi_st9 == 0 && r->spi_sttx == 0,
		      "-3: ret %d nwords %u ack %08x drain %04x dlast %04x st9 %u sttx %u", r->ret, r->nwords,
		      r->ack_polls, r->drain, r->drain_last, r->spi_st9, r->spi_sttx);
		printf("  -3: ret %d nwords %u ack_polls %08x drain %04x drain_last %04x\n", r->ret, r->nwords,
		       r->ack_polls, r->drain, r->drain_last);
		dev_flush();
	}
	/* -5 */
	{
		struct psc_sc *r;

		dev_force_busy(16);
		cmd08();
		r = last_p();
		CHECK(r->ret == -5 && r->retries == 16 && r->nwords == 2 && r->rx[2] == 0x80,
		      "-5: ret %d retries %u nwords %u rx2 %02x", r->ret, r->retries, r->nwords, r->rx[2]);
		printf("  -5: ret %d retries %u nwords %u rx[2] %02x\n", r->ret, r->retries, r->nwords, r->rx[2]);
	}
	/* one BUSY, then success */
	{
		struct psc_sc *r;

		dev_force_busy(1);
		cmd08();
		r = last_p();
		CHECK(r->ret == 0x22 && r->retries == 1 && r->nwords == 5 && r->rx[2] == 0x08,
		      "retry: ret %d retries %u nwords %u", r->ret, r->retries, r->nwords);
		printf("  BUSY once: ret %d retries %u nwords %u\n", r->ret, r->retries, r->nwords);
	}
}

/* ========================================== T3: wrap-around on every ring */
static u8 *shadow;

static void t_wrap(void)
{
	u32 first, lost, next, i, total, got = 0, base;
	int n, bad = 0, ring;

	printf("== T3 wrap-around (3 laps of P, POLL, S; 2.5 laps of W)\n");
	/* P: drain pending, then 3 laps + 7, reading every 1000 */
	as(T_WRK);
	next = col_ring_file(PSC_RING_P)->f_pos / 80;
	drain_all(PSC_RING_P, &first, &lost, &next);
	base = psc_k.head[PSC_RING_P];
	total = 3 * PSC_P_ENTRIES + 7;
	for (i = 0; i < total; i++) {
		u32 s;

		cmd08();
		s = psc_k.head[PSC_RING_P] - 1;
		memcpy(shadow + (size_t)(s - base) * 80, &psc_mem.p[s & 4095], 80);
		if ((i + 1) % 1000 == 0 || i + 1 == total) {
			ssize_t r;
			int j;

			as(T_WRK);
			while ((r = rd(PSC_RING_P, big, BIGSZ / 80 * 80)) > 0) {
				for (j = 0; j < r / 80; j++) {
					u32 seq;

					memcpy(&seq, big + j * 80, 4);
					if (seq != next)
						bad++;
					if (seq >= base && memcmp(big + j * 80, shadow + (size_t)(seq - base) * 80, 80))
						bad++;
					next = seq + 1;
					got++;
				}
			}
		}
	}
	CHECK(got == total && bad == 0, "P wrap: delivered %u of %u, %d seq/content errors", got, total, bad);
	printf("  P: %u records over %u laps of %d, delivered %u, seq/content errors %d, head %u\n", total,
	       total / PSC_P_ENTRIES, PSC_P_ENTRIES, got, bad, psc_k.head[PSC_RING_P]);

	/* POLL: the real psc_poll_begin/psc_poll_end as the thread */
	as(T_WRK);
	next = col_ring_file(PSC_RING_POLL)->f_pos / 40;
	drain_all(PSC_RING_POLL, &first, &lost, &next);
	total = 3 * PSC_POLL_ENTRIES + 5;
	got = 0; bad = 0;
	for (i = 0; i < total; i++) {
		as(T_JP);
		psc_poll_begin();
		g_count += 100;
		psc_poll_end();
		if ((i + 1) % 500 == 0 || i + 1 == total) {
			n = drain_all(PSC_RING_POLL, &first, &lost, &next);
			got += n;
			bad += (int)lost;
		}
	}
	CHECK(got == total && bad == 0, "POLL wrap: %u of %u, lost %d", got, total, bad);
	printf("  POLL: %u records, delivered %u, lost %d, head %u\n", total, got, bad, psc_k.head[PSC_RING_POLL]);

	/* S: the collector's Memory Stick model (real psc_ms_seg_begin/end) */
	as(T_WRK);
	next = col_ring_file(PSC_RING_S)->f_pos / 40;
	drain_all(PSC_RING_S, &first, &lost, &next);
	total = 3 * PSC_S_ENTRIES + 3;
	got = 0; bad = 0;
	for (i = 0; i < total; i++) {
		as(T_WRK);
		ms_write_seg(100000 + i, 1 + (i % 8), i % 5 == 0);
		if ((i + 1) % 1000 == 0 || i + 1 == total) {
			n = drain_all(PSC_RING_S, &first, &lost, &next);
			got += n;
			bad += (int)lost;
		}
	}
	CHECK(got == total && bad == 0, "S wrap: %u of %u, lost %d", got, total, bad);
	printf("  S: %u records, delivered %u, lost %d, head %u\n", total, got, bad, psc_k.head[PSC_RING_S]);

	/* W: 640 Nops (real timer path), drained every 100 */
	as(T_IDLE);
	next = col_ring_file(PSC_RING_W)->f_pos / 288;
	drain_all(PSC_RING_W, &first, &lost, &next);
	total = 640;
	got = 0; bad = 0;
	for (i = 0; i < total; i++) {
		as(T_IDLE);
		sim_align_wd();
		sim_idle_tick();
		if ((i + 1) % 100 == 0 || i + 1 == total) {
			n = drain_all(PSC_RING_W, &first, &lost, &next);
			got += n;
			bad += (int)lost;
		}
	}
	CHECK(got == total && bad == 0, "W wrap: %u of %u, lost %d", got, total, bad);
	printf("  W: %u Nops, delivered %u, lost %d, head %u (ring %d)\n", total, got, bad,
	       psc_k.head[PSC_RING_W], PSC_W_ENTRIES);
	for (ring = 0; ring < 5; ring++)
		CHECK(psc_st.slot_bad[ring] == 0, "slot_bad[%d] = %u", ring, psc_st.slot_bad[ring]);
}

/* =================================== T4: overflow and `lost` accounting */
static void t_overflow(void)
{
	u32 first, lost, next, h0, i, slot_bad0 = psc_st.slot_bad[PSC_RING_P];
	int n, k;
	static const u32 extra[] = { 0, 1, 1000, 4096, 9000 };

	printf("== T4 overflow: the reader falls behind by N + x records (3.5 step 2)\n");
	for (k = 0; k < 5; k++) {
		as(T_WRK);
		next = col_ring_file(PSC_RING_P)->f_pos / 80;
		drain_all(PSC_RING_P, &first, &lost, &next);
		h0 = psc_k.head[PSC_RING_P];
		for (i = 0; i < PSC_P_ENTRIES + extra[k]; i++)
			cmd08();
		n = drain_all(PSC_RING_P, &first, &lost, &next);
		CHECK((u32)n == PSC_P_ENTRIES && lost == extra[k] && first == h0 + extra[k],
		      "x=%u: delivered %d (want %d), lost %u (want %u), first %u (want %u)", extra[k], n,
		      PSC_P_ENTRIES, lost, extra[k], first, h0 + extra[k]);
		printf("  behind by N + %u: delivered %d, lost %u, first seq %u = head0 + %u\n", extra[k], n, lost,
		       first, first - h0);
	}
	CHECK(psc_st.slot_bad[PSC_RING_P] == slot_bad0 && psc_st.head_regress == 0,
	      "slot_bad %u head_regress %u", psc_st.slot_bad[PSC_RING_P], psc_st.head_regress);
	/* POLL and W rings: the same rule */
	{
		u32 hw;

		as(T_WRK);
		next = col_ring_file(PSC_RING_W)->f_pos / 288;
		drain_all(PSC_RING_W, &first, &lost, &next);
		hw = psc_k.head[PSC_RING_W];
		for (i = 0; i < PSC_W_ENTRIES + 37; i++) {
			as(T_IDLE);
			sim_align_wd();
			sim_idle_tick();
		}
		n = drain_all(PSC_RING_W, &first, &lost, &next);
		CHECK((u32)n == PSC_W_ENTRIES && lost == 37 && first == hw + 37, "W overflow: n %d lost %u first %u",
		      n, lost, first);
		printf("  W behind by N + 37: delivered %d, lost %u\n", n, lost);
	}
}

/* ====================================== T5: reader protocol corner cases */
static void t_reader(void)
{
	u32 first, lost, next, h, sb0, hr0, rw0, i;
	ssize_t r;
	loff_t pos, after;
	u8 one[300];
	int n;

	printf("== T5 reader protocol (3.5, 2.8, 8.5 reader row)\n");
	as(T_WRK);
	next = col_ring_file(PSC_RING_P)->f_pos / 80;
	drain_all(PSC_RING_P, &first, &lost, &next);
	for (i = 0; i < 20; i++)
		cmd08();
	as(T_WRK);
	/* partial counts: < 1 record, 1.5 records */
	r = rd(PSC_RING_P, one, 79);
	CHECK(r == 0, "count 79 -> %ld", (long)r);
	r = rd(PSC_RING_P, one, 120);
	CHECK(r == 80, "count 120 -> %ld (one whole record)", (long)r);
	/* offset not a record multiple, negative offset */
	pos = 81;
	r = col_ring_fops(PSC_RING_P)->read(col_ring_file(PSC_RING_P), (char *)one, 80, &pos);
	CHECK(r == -EINVAL, "offset 81 -> %ld", (long)r);
	pos = -80;
	r = col_ring_fops(PSC_RING_P)->read(col_ring_file(PSC_RING_P), (char *)one, 80, &pos);
	CHECK(r == -EINVAL, "offset -80 -> %ld", (long)r);
	/* pread windows do not move the drain position (A6-4) */
	{
		loff_t before = col_ring_file(PSC_RING_P)->f_pos;
		u32 s0 = (u32)(before / 80), seq;

		r = prd(PSC_RING_P, one, 80, (loff_t)(s0 + 3) * 80, &after);
		memcpy(&seq, one, 4);
		CHECK(r == 80 && seq == s0 + 3 && col_ring_file(PSC_RING_P)->f_pos == before,
		      "pread: r %ld seq %u f_pos moved %lld", (long)r, seq, (long long)(col_ring_file(PSC_RING_P)->f_pos - before));
		r = rd(PSC_RING_P, one, 80);
		memcpy(&seq, one, 4);
		CHECK(r == 80 && seq == s0, "read after pread: seq %u want %u", seq, s0);
		next = seq + 1;
	}
	/* llseek: SEEK_SET multiple / not, rewinds counted, SEEK_CUR 0 */
	rw0 = psc_st.ring_rewinds;
	pos = col_ring_file(PSC_RING_P)->f_pos;
	CHECK(col_ring_fops(PSC_RING_P)->llseek(col_ring_file(PSC_RING_P), 0, SEEK_CUR) == pos, "SEEK_CUR 0");
	CHECK(col_ring_fops(PSC_RING_P)->llseek(col_ring_file(PSC_RING_P), 8, SEEK_CUR) == -EINVAL, "SEEK_CUR 8");
	CHECK(col_ring_fops(PSC_RING_P)->llseek(col_ring_file(PSC_RING_P), 0, SEEK_END) == -EINVAL, "SEEK_END");
	CHECK(col_ring_fops(PSC_RING_P)->llseek(col_ring_file(PSC_RING_P), pos - 160 + 1, SEEK_SET) == -EINVAL, "SEEK_SET odd");
	CHECK(col_ring_fops(PSC_RING_P)->llseek(col_ring_file(PSC_RING_P), pos - 160, SEEK_SET) == pos - 160 &&
	      psc_st.ring_rewinds == rw0 + 1, "SEEK_SET back 2: rewinds %u", psc_st.ring_rewinds);
	n = drain_all(PSC_RING_P, &first, &lost, &next);
	CHECK(first == (u32)(pos / 80) - 2, "re-read starts at the rewound seq %u", first);

	/* (a) a corrupt mid-ring seq: skipped and counted once */
	for (i = 0; i < 10; i++)
		cmd08();
	as(T_WRK);
	sb0 = psc_st.slot_bad[PSC_RING_P];
	h = psc_k.head[PSC_RING_P];
	psc_mem.p[(h - 5) & 4095].seq = 0xDEADBEEF;
	n = drain_all(PSC_RING_P, &first, &lost, &next);
	CHECK(n == 9 && lost == 1 && psc_st.slot_bad[PSC_RING_P] == sb0 + 1,
	      "corrupt seq: delivered %d lost %u slot_bad +%u", n, lost, psc_st.slot_bad[PSC_RING_P] - sb0);
	printf("  corrupt seq: delivered %d of 10, the collector sees lost %u, slot_bad +%u\n", n, lost,
	       psc_st.slot_bad[PSC_RING_P] - sb0);
	/* (b) a slot left at 0xFFFFFFFF (being written) below the head */
	for (i = 0; i < 10; i++)
		cmd08();
	as(T_WRK);
	sb0 = psc_st.slot_bad[PSC_RING_P];
	h = psc_k.head[PSC_RING_P];
	psc_mem.p[(h - 3) & 4095].seq = PSC_SEQ_WRITING;
	n = drain_all(PSC_RING_P, &first, &lost, &next);
	CHECK(n == 9 && lost == 1 && psc_st.slot_bad[PSC_RING_P] == sb0 + 1,
	      "WRITING below head: delivered %d lost %u slot_bad +%u", n, lost, psc_st.slot_bad[PSC_RING_P] - sb0);
	/* (c) a forward head jump of 100 (no records written) */
	sb0 = psc_st.slot_bad[PSC_RING_P];
	psc_k.head[PSC_RING_P] += 100;
	n = drain_all(PSC_RING_P, &first, &lost, &next);
	CHECK(n == 0 && psc_st.slot_bad[PSC_RING_P] == sb0 + 100 &&
	      col_ring_file(PSC_RING_P)->f_pos / 80 == psc_k.head[PSC_RING_P],
	      "forward jump: delivered %d slot_bad +%u pos %lld head %u", n, psc_st.slot_bad[PSC_RING_P] - sb0,
	      (long long)(col_ring_file(PSC_RING_P)->f_pos / 80), psc_k.head[PSC_RING_P]);
	printf("  head +100: 0 delivered, slot_bad +%u, reader now at the head\n", psc_st.slot_bad[PSC_RING_P] - sb0);
	next = psc_k.head[PSC_RING_P];
	for (i = 0; i < 5; i++)
		cmd08();
	n = drain_all(PSC_RING_P, &first, &lost, &next);
	CHECK(n == 5 && lost == 0, "after the jump: %d new records lost %u", n, lost);
	/* (d) a backward head jump: head_regress, nothing delivered, f_pos kept */
	hr0 = psc_st.head_regress;
	pos = col_ring_file(PSC_RING_P)->f_pos;
	psc_k.head[PSC_RING_P] -= 50;
	as(T_WRK);
	r = rd(PSC_RING_P, big, 80 * 10);
	CHECK(r == 0 && psc_st.head_regress == hr0 + 1 && col_ring_file(PSC_RING_P)->f_pos == pos,
	      "backward jump: r %ld head_regress +%u", (long)r, psc_st.head_regress - hr0);
	psc_k.head[PSC_RING_P] += 50;
	/* (e) the skip budget: a whole ring of bad slots costs <= N skips per call */
	{
		u32 j, s0;

		for (i = 0; i < 10; i++)
			cmd08();
		as(T_WRK);
		s0 = (u32)(col_ring_file(PSC_RING_P)->f_pos / 80);
		h = psc_k.head[PSC_RING_P];
		/* claim a full ring of new records whose slots are all garbage */
		for (j = 0; j < PSC_P_ENTRIES; j++)
			psc_mem.p[j].seq = 0xA5A5A5A5;
		psc_k.head[PSC_RING_P] = s0 + PSC_P_ENTRIES;
		sb0 = psc_st.slot_bad[PSC_RING_P];
		r = rd(PSC_RING_P, big, BIGSZ);
		CHECK(r == 0 && psc_st.slot_bad[PSC_RING_P] - sb0 <= (u32)PSC_P_ENTRIES + 1 &&
		      col_ring_file(PSC_RING_P)->f_pos / 80 >= s0 + PSC_P_ENTRIES,
		      "full-ring garbage: r %ld slot_bad +%u pos +%lld", (long)r, psc_st.slot_bad[PSC_RING_P] - sb0,
		      (long long)(col_ring_file(PSC_RING_P)->f_pos / 80 - s0));
		printf("  a ring of %d garbage slots: 0 delivered, slot_bad +%u, reader at the head after one call\n",
		       PSC_P_ENTRIES, psc_st.slot_bad[PSC_RING_P] - sb0);
		(void)h;
	}
	/* (f) last_reader_tick on every ring read, even of 0 bytes (2.8) */
	{
		u32 t0 = (u32)psp_local_tick;

		as(T_IDLE);
		sim_idle_tick();
		as(T_WRK);
		rd(PSC_RING_M, one, 0);
		CHECK(psc_st.last_reader_tick == (u32)psp_local_tick && (u32)psp_local_tick != t0,
		      "last_reader_tick %u now %lu", psc_st.last_reader_tick, psp_local_tick);
	}
}


/* seq 32-bit wrap: run in a child so the main state is not touched */
static void t_seqwrap(void)
{
	ssize_t r;
	u32 i, hr0;
	pid_t pid;
	int st;

	printf("== T11 seq 32-bit wrap (observation; needs 2^32 records = 3.8 years at 35.7/s)\n");
	fflush(stdout);
	pid = fork();
	if (pid == 0) {
		u32 s;
		int delivered = 0, writing = 0, calls;

		as(T_WRK);
		psc_k.head[PSC_RING_POLL] = 0xFFFFFFFDu;
		col_ring_file(PSC_RING_POLL)->f_pos = (loff_t)0xFFFFFFFDu * 40;
		hr0 = psc_st.head_regress;
		for (i = 0; i < 6; i++) {
			as(T_JP);
			psc_poll_begin();
			psc_poll_end();
		}
		as(T_WRK);
		for (calls = 0; calls < 3; calls++) {
			r = rd(PSC_RING_POLL, big, 400);
			for (s = 0; r > 0 && s < r / 40; s++) {
				u32 seq;

				memcpy(&seq, big + s * 40, 4);
				if (seq == PSC_SEQ_WRITING)
					writing++;
				delivered++;
			}
			printf("  read %d after the wrap: %ld bytes, f_pos %lld, head %u, head_regress +%u\n", calls,
			       (long)r, (long long)col_ring_file(PSC_RING_POLL)->f_pos, psc_k.head[PSC_RING_POLL],
			       psc_st.head_regress - hr0);
		}
		printf("NOTE seq wrap: records 0xFFFFFFFD..0x2; delivered %d (%d with seq 0xFFFFFFFF = the WRITING "
		       "sentinel, which the decoder drops, 10.3); after the wrap the reader's position stays above "
		       "2^32 records, every read returns 0 and counts head_regress (psc.c:992-995); the collector's "
		       "head_regress resync (4.3 step 2) would be needed. Not reachable in a run.\n", delivered, writing);
		fflush(stdout);
		_exit(0);
	}
	waitpid(pid, &st, 0);
	n_note++;
}

/* ========================================== T9: the fill-once M ring */
static void t_mring(void)
{
	u32 h0 = psc_k.head[PSC_RING_M], d0 = psc_st.m_dropped, i, first, lost, next;
	int n, want;

	printf("== T9 M ring: fill-once, m_dropped (1.6, 3.1)\n");
	for (i = 0; i < 80; i++) {
		as(T_INIT);
		pspSysconCtrlHRPower(1);
	}
	want = PSC_M_ENTRIES - (int)h0;
	CHECK(psc_k.head[PSC_RING_M] == PSC_M_ENTRIES && psc_st.m_dropped == d0 + 80 - (u32)want,
	      "M head %u dropped %u", psc_k.head[PSC_RING_M], psc_st.m_dropped);
	as(T_WRK);
	next = col_ring_file(PSC_RING_M)->f_pos / 80;
	n = drain_all(PSC_RING_M, &first, &lost, &next);
	CHECK(next == PSC_M_ENTRIES && lost == 0, "M drained to %u lost %u", next, lost);
	printf("  80 M commands after %u: head %u, m_dropped %u, drained %d more (seq up to %u)\n", h0,
	       psc_k.head[PSC_RING_M], psc_st.m_dropped, n, next - 1);
}

/* ========================================== T10: ctl and stats file ops */
static void t_ctl(void)
{
	struct psc_stats st;
	struct psc_ctl c;
	loff_t pos;
	ssize_t r;
	const struct file_operations *cf;
	struct file f;
	extern struct proc_dir_entry *host_pde(const char *name);
	u8 part[800];

	printf("== T10 ctl (2.8) and stats (1.7)\n");
	cf = host_pde("ctl")->proc_fops;
	memset(&f, 0, sizeof(f));
	as(T_WRK);
	memset(&c, 0, sizeof(c));
	c.op = 1; c.arg[0] = 777; c.arg[1] = 11; c.arg[2] = 12; c.arg[3] = 13; c.arg[4] = 14; c.arg[5] = 15;
	pos = 0;
	r = cf->write(&f, (const char *)&c, 32, &pos);
	col_read_stats(&st);
	CHECK(r == 32 && st.durable_tick == 777 && st.durable_next[0] == 11 && st.durable_next[4] == 15, "op 1");
	r = cf->write(&f, (const char *)&c, 31, &pos);
	CHECK(r == -EINVAL, "partial command -> %ld", (long)r);
	c.op = 9;
	r = cf->write(&f, (const char *)&c, 32, &pos);
	CHECK(r == -EINVAL, "op 9 -> %ld", (long)r);
	c.op = 2; c.arg[0] = 8;
	r = cf->write(&f, (const char *)&c, 32, &pos);
	CHECK(r == -EINVAL, "class slot 8 -> %ld", (long)r);
	c.op = 3; c.arg[0] = 11;
	r = cf->write(&f, (const char *)&c, 32, &pos);
	CHECK(r == -EINVAL, "panel 11 s -> %ld", (long)r);
	/* stats: magic, version/size, build_id, release addresses */
	CHECK(st.magic == PSC_STATS_MAGIC && st.version_size == ((768u << 16) | 5u) && st.hz == 250 &&
	      st.counts_per_tick == 883651u, "stats header");
	CHECK(st.build_id == 0x045b27d9u, "build_id %08x (want the packaged 0x045b27d9)", st.build_id);
	CHECK(st.addr_syscon_cmd == 0x880ceed0u && st.addr_psc_sc_exit == 0x880d2b04u &&
	      st.addr_getctrl2 == 0x880cf370u, "addresses %08x %08x %08x", st.addr_syscon_cmd,
	      st.addr_psc_sc_exit, st.addr_getctrl2);
	printf("  stats: build_id %08x, words 20-22 %08x %08x %08x\n", st.build_id, st.addr_syscon_cmd,
	       st.addr_psc_sc_exit, st.addr_getctrl2);
	/* partial stats reads at offsets */
	{
		const struct file_operations *sf = host_pde("stats")->proc_fops;
		u8 whole[768];

		pos = 0;
		r = sf->read(&f, (char *)whole, 768, &pos);
		pos = 100;
		r = sf->read(&f, (char *)part, 50, &pos);
		CHECK(r == 50 && pos == 150 && !memcmp(part, whole + 100, 4), "stats partial");
		pos = 768;
		r = sf->read(&f, (char *)part, 50, &pos);
		CHECK(r == 0, "stats at 768 -> %ld", (long)r);
		pos = 700;
		r = sf->read(&f, (char *)part, 800, &pos);
		CHECK(r == 68, "stats tail -> %ld", (long)r);
	}
}

/* ================================== T6: interrupt at each ordering point */
/* What a reader running at the injection point saw */
static int inj_reader_ring;
static int inj_reader_seen_s;		/* the in-progress record was delivered */
static u32 inj_reader_s;
static u8 *inj_reader_buf;
static ssize_t inj_reader_r;
static u32 inj_rnext[5];

static void inj_reader(void)
{
	int prev = g_cur, i;

	do_switch(prev, T_WRK);
	inj_reader_r = rd(inj_reader_ring, inj_reader_buf, 600 * 80 / RSZ[inj_reader_ring] *
			  RSZ[inj_reader_ring]);
	for (i = 0; i < inj_reader_r / RSZ[inj_reader_ring]; i++) {
		u32 seq;

		memcpy(&seq, inj_reader_buf + i * RSZ[inj_reader_ring], 4);
		if (seq == inj_reader_s)
			inj_reader_seen_s = 1;
		inj_rnext[inj_reader_ring] = seq + 1;
	}
	do_switch(T_WRK, prev);
}

static int xfer_target_origin;
static int xfer_target_barrier, xfer_target_action;
static void xfer_arm(char origin, int cmd)
{
	(void)cmd;
	if (origin == xfer_target_origin && !g_binj.armed) {
		binj_arm(xfer_target_barrier, xfer_target_action);
		xfer_target_origin = 0;
	}
}

struct diff { char what[96]; int n; };
static struct diff diffs[256];
static int ndiffs;

static void note_diff(const char *fmt, ...)
{
	char b[96];
	va_list ap;
	int i;

	va_start(ap, fmt);
	vsnprintf(b, sizeof(b), fmt, ap);
	va_end(ap);
	for (i = 0; i < ndiffs; i++)
		if (!strcmp(diffs[i].what, b)) { diffs[i].n++; return; }
	if (ndiffs < 256) { strcpy(diffs[ndiffs].what, b); diffs[ndiffs++].n = 1; }
}

static void sc_field_diffs(const char *tag, const struct psc_sc *a, const struct psc_sc *b)
{
#define FD(f) if (a->f != b->f) note_diff("%s %s %u->%u", tag, #f, (unsigned)a->f, (unsigned)b->f)
	FD(wn); FD(w_head_lo); FD(ms_delta); FD(preempt_delta); FD(lc_n); FD(lc_flags); FD(lc_epc);
	FD(lc_dtick); FD(pre_flags); FD(pre_cls); FD(dtick); FD(ret); FD(nwords); FD(ack_polls);
#undef FD
}

/* the P append (psc_sc_exit P path), each barrier, each action */
static void t_inject_p(void)
{
	int b, act, passes = 0;
	struct psc_sc ref, got;
	struct psc_w *w;

	printf("== T6a interrupt at every ordering point of the P append (psc_sc_exit, psc.c:427-473)\n");
	/* reference: the same command without injection (no tick) */
	cmd08();
	ref = *last_p();
	for (act = 1; act <= 3; act++) {
		for (b = 0; b < 12; b++) {
			u32 s, wh0, sb0 = psc_st.slot_bad[PSC_RING_P] + psc_st.slot_bad[PSC_RING_W];
			struct psc_sc *slot;
			u32 first, lost, nx;

			as(T_WRK);
			nx = col_ring_file(PSC_RING_P)->f_pos / 80;
			drain_all(PSC_RING_P, &first, &lost, &nx);
			inj_rnext[PSC_RING_P] = nx;
			if (act == 1)
				sim_align_wd();
			else
				psp_local_tick = psc_st.wd_last_tick + 10;	/* no Nop at the next tick */
			g_count = 1000;
			s = psc_k.head[PSC_RING_P];
			wh0 = psc_k.head[PSC_RING_W];
			inj_reader_ring = PSC_RING_P;
			inj_reader_s = s;
			inj_reader_seen_s = 0;
			inj_reader_r = -1;
			g_binj_reader = inj_reader;
			xfer_target_origin = 'P';
			xfer_target_barrier = b;
			xfer_target_action = act;
			g_xfer_hook = xfer_arm;
			cmd08();
			g_xfer_hook = NULL;
			g_binj.armed = 0;
			if (!g_binj.done) {
				if (b >= 9)
					break;		/* past the last barrier of the path */
				CHECK(0, "barrier %d not reached", b);
				continue;
			}
			slot = &psc_mem.p[s & 4095];
			got = *slot;
			/* ring-safety invariants */
			CHECK(psc_k.head[PSC_RING_P] == s + 1 && slot->seq == s,
			      "act %d b %d: head %u seq %u (s %u)", act, b, psc_k.head[PSC_RING_P], slot->seq, s);
			CHECK(!inj_reader_seen_s, "act %d b %d: the reader delivered the record being written", act, b);
			if (act == 1) {
				w = &psc_mem.w[(psc_k.head[PSC_RING_W] - 1) & 255];
				CHECK(psc_k.head[PSC_RING_W] == wh0 + 1 && w->sc.seq == wh0,
				      "act 1 b %d: W head %u", b, psc_k.head[PSC_RING_W]);
				note_diff("P-exit barrier %d (%s): W t_busy=%u p_head-s=%d ext_flags=%02x", b,
					  host_fn_of(g_binj.ra, NULL), w->ext.t_busy, (int)(w->ext.p_head - s),
					  w->ext.ext_flags);
			}
			/* the record delivered after the append equals the slot */
			{
				ssize_t r;
				u32 seq = 0;

				as(T_WRK);
				r = rd(PSC_RING_P, big, 80 * 600);
				if (r >= 80)
					memcpy(&seq, big + r - 80, 4);
				CHECK(r >= 80 && seq == s && !memcmp(big + r - 80, &got, 80),
				      "act %d b %d: delivered %ld last seq %u", act, b, (long)r, seq);
			}
			CHECK(psc_st.slot_bad[PSC_RING_P] + psc_st.slot_bad[PSC_RING_W] == sb0, "slot_bad moved");
			{
				char tag[48];

				snprintf(tag, sizeof(tag), "act %d P-exit barrier %d:", act, b);
				sc_field_diffs(tag, &ref, &got);
			}
			passes++;
		}
	}
	printf("  P append: %d injections (actions: 1 watchdog Nop, 2 plain tick, 3 the collector's reader)\n", passes);
}

/* the P entry (psc_sc_entry inlined in psc_syscon_cmd, psc.c:197-246) */
static void t_inject_entry(void)
{
	int b, act, n = 0;

	printf("== T6d interrupt at the ordering points of the P entry (psc_sc_entry, psc.c:240, :245)\n");
	for (act = 1; act <= 2; act++) {
		for (b = 0; b < 2; b++) {
			u32 s, wh0, wn, tb, ph;
			struct psc_w *w;
			struct psc_sc *slot;

			if (act == 1)
				sim_align_wd();
			else
				psp_local_tick = psc_st.wd_last_tick + 10;
			g_count = 1000;
			as(T_JP);
			/* the 0x33 first: arm at its end, count its 9 exit barriers */
			xfer_target_origin = 'P';
			xfer_target_barrier = 9 + b;
			xfer_target_action = act;
			g_xfer_hook = xfer_arm;
			_pspSysconCtrlAStickPower(1);
			g_xfer_hook = NULL;
			s = psc_k.head[PSC_RING_P];
			wh0 = psc_k.head[PSC_RING_W];
			cmd08();
			g_binj.armed = 0;
			CHECK(g_binj.done, "entry barrier %d not reached", b);
			slot = &psc_mem.p[s & 4095];
			CHECK(psc_k.head[PSC_RING_P] == s + 1 && slot->seq == s && slot->cmd == 0x08, "entry act %d b %d", act, b);
			if (act == 1) {
				w = &psc_mem.w[(psc_k.head[PSC_RING_W] - 1) & 255];
				CHECK(psc_k.head[PSC_RING_W] == wh0 + 1, "entry act 1 b %d: W head", b);
				wn = slot->wn; tb = w->ext.t_busy; ph = w->ext.p_head - s;
				note_diff("P-entry barrier %d (%s): W t_busy=%u p_head-s=%d, P.wn=%u, W.t_entry_c==P.c_in %d", b,
					  host_fn_of(g_binj.ra, NULL), tb, (int)ph, wn, w->ext.t_entry_c == slot->c_in);
			} else {
				note_diff("P-entry barrier %d plain tick: P.lc_n=%u lc_flags=%02x", b, slot->lc_n, slot->lc_flags);
			}
			n++;
		}
	}
	printf("  P entry: %d injections\n", n);
}

/* the POLL append (psc_poll_end, psc.c:879-901), the S append
 * (psc_ms_seg_end, psc.c:676-725) and the M append */
static void t_inject_other(void)
{
	int b, act, n_poll = 0, n_s = 0, n_m = 0;

	printf("== T6b interrupt at every ordering point of the POLL, S and M appends\n");
	for (act = 1; act <= 3; act++) {
		for (b = 0; b < 4; b++) {
			u32 s, wh0;
			struct psc_poll *slot;

			if (act == 1) sim_align_wd();
			g_count = 1000;
			as(T_JP);
			psc_poll_begin();
			s = psc_k.head[PSC_RING_POLL];
			wh0 = psc_k.head[PSC_RING_W];
			inj_reader_ring = PSC_RING_POLL;
			inj_reader_s = s;
			inj_reader_seen_s = 0;
			g_binj_reader = inj_reader;
			binj_arm(b, act);
			psc_poll_end();
			g_binj.armed = 0;
			if (!g_binj.done) {
				if (b >= 3) break;
				CHECK(0, "POLL barrier %d not reached", b);
				continue;
			}
			slot = &psc_mem.poll[s & 2047];
			CHECK(psc_k.head[PSC_RING_POLL] == s + 1 && slot->seq == s && !inj_reader_seen_s,
			      "POLL act %d b %d", act, b);
			if (act == 1) {
				struct psc_w *w = &psc_mem.w[(psc_k.head[PSC_RING_W] - 1) & 255];

				CHECK(psc_k.head[PSC_RING_W] == wh0 + 1, "POLL act 1 b %d W", b);
				note_diff("POLL-end barrier %d (%s): W jp_stage=%u t_busy=%u", b,
					  host_fn_of(g_binj.ra, NULL), w->ext.jp_stage, w->ext.t_busy);
			}
			n_poll++;
		}
		for (b = 0; b < 5; b++) {
			u32 s, wh0, i, v;
			struct psc_s *slot;

			if (act == 1) sim_align_wd();
			g_count = 1000;
			as(T_WRK);
			s = psc_k.head[PSC_RING_S];
			wh0 = psc_k.head[PSC_RING_W];
			psc_host_preempt_count++;
			psc_ms_seg_begin(5000 + b, 2, 1);
			for (i = 0; i < 2; i++) {
				dev_led_rmw(1, 0x40, &v);
				psc_note_led(1, v);
				dev_led_rmw(0, 0x40, &v);
				psc_note_led(0, v);
			}
			inj_reader_ring = PSC_RING_S;
			inj_reader_s = s;
			inj_reader_seen_s = 0;
			g_binj_reader = inj_reader;
			binj_arm(b, act);
			psc_ms_seg_end(5000 + b, 2, 1, 0, 0);
			g_binj.armed = 0;
			psc_host_preempt_count--;
			if (!g_binj.done) {
				if (b >= 4) break;
				CHECK(0, "S barrier %d not reached", b);
				continue;
			}
			slot = &psc_mem.s[s & 4095];
			/* a reader may deliver the record only once its head is
			 * published (psc.c:715), and then only the complete record */
			CHECK(psc_k.head[PSC_RING_S] == s + 1 && slot->seq == s && slot->led_ops == 4 &&
			      slot->nsect == 2, "S act %d b %d", act, b);
			if (inj_reader_seen_s) {
				int i2, ok = 0;

				for (i2 = 0; i2 < inj_reader_r / 40; i2++)
					if (!memcmp(inj_reader_buf + i2 * 40, slot, 40))
						ok = 1;
				CHECK(ok && b >= 3, "S act %d b %d: delivered before publish or torn", act, b);
				note_diff("S-end barrier %d: the reader got the new record (head already published)", b);
			}
			if (act == 1) {
				struct psc_w *w = &psc_mem.w[(psc_k.head[PSC_RING_W] - 1) & 255];

				CHECK(psc_k.head[PSC_RING_W] == wh0 + 1, "S act 1 b %d W", b);
				note_diff("S-end barrier %d (%s): W ext_flags b6 (MS active)=%u cur_pcnt=%u", b,
					  host_fn_of(g_binj.ra, NULL), (w->ext.ext_flags >> 6) & 1, w->ext.cur_pcnt);
			}
			n_s++;
		}
	}
	/* the M append (psc_sc_exit M path, psc.c:474-491) */
	for (act = 1; act <= 3; act++) {
		for (b = 0; b < 6; b++) {
			u32 s = psc_k.head[PSC_RING_M], wh0 = psc_k.head[PSC_RING_W];

			if (s >= PSC_M_ENTRIES - 1)
				break;
			if (act == 1) sim_align_wd();
			g_count = 1000;
			inj_reader_ring = PSC_RING_M;
			inj_reader_s = s;
			inj_reader_seen_s = 0;
			g_binj_reader = inj_reader;
			xfer_target_origin = 'M';
			xfer_target_barrier = b;
			xfer_target_action = act;
			g_xfer_hook = xfer_arm;
			as(T_INIT);
			pspSysconCtrlHRPower(1);
			g_xfer_hook = NULL;
			g_binj.armed = 0;
			if (!g_binj.done) {
				if (b >= 5) break;
				CHECK(0, "M barrier %d not reached", b);
				continue;
			}
			CHECK(psc_k.head[PSC_RING_M] == s + 1 && psc_mem.m[s].seq == s && !inj_reader_seen_s,
			      "M act %d b %d", act, b);
			if (act == 1) {
				struct psc_w *w = &psc_mem.w[(psc_k.head[PSC_RING_W] - 1) & 255];

				CHECK(psc_k.head[PSC_RING_W] == wh0 + 1, "M act 1 b %d W", b);
				note_diff("M-exit barrier %d (%s): W t_busy=%u", b, host_fn_of(g_binj.ra, NULL), w->ext.t_busy);
			}
			n_m++;
		}
	}
	printf("  POLL append: %d injections; S append: %d injections; M append: %d injections\n", n_poll, n_s, n_m);
}

/* the reader interrupted by the Nop at each record copy (copy_to_user) */
static int copy_k, copy_target;
static void copy_inject(void)
{
	struct ipt p;

	if (copy_k++ != copy_target || g_irq_depth)
		return;
	ipt_for_current(&p);
	if (g_count < CPT)
		g_count = CPT;
	fire_tick(&p);
}

static void t_inject_reader(void)
{
	int k, ok = 0;
	u32 first, lost, nx;

	printf("== T6c the Nop interrupting the W reader at every record copy\n");
	for (k = 0; k < 3; k++) {
		u32 w0, i;
		ssize_t r;
		int n, j;

		as(T_WRK);
		nx = col_ring_file(PSC_RING_W)->f_pos / 288;
		drain_all(PSC_RING_W, &first, &lost, &nx);
		/* three pending W records */
		for (i = 0; i < 3; i++) {
			as(T_IDLE);
			sim_align_wd();
			sim_idle_tick();
		}
		w0 = (u32)(col_ring_file(PSC_RING_W)->f_pos / 288);
		as(T_WRK);
		sim_align_wd();
		g_count = 1000;
		copy_k = 0;
		copy_target = k;
		g_copy_hook = copy_inject;
		r = rd(PSC_RING_W, big, 288 * 8);
		g_copy_hook = NULL;
		n = (int)(r / 288);
		for (j = 0; j < n; j++) {
			u32 seq;

			memcpy(&seq, big + j * 288, 4);
			CHECK(seq == w0 + (u32)j && !memcmp(big + j * 288, &psc_mem.w[seq & 255], 288),
			      "copy %d: record %d seq %u", k, j, seq);
		}
		CHECK(psc_k.head[PSC_RING_W] == w0 + 4, "copy %d: W head %u", k, psc_k.head[PSC_RING_W]);
		NOTE("W read interrupted by a Nop before copy %d: delivered %d records in that call (the Nop's own "
		     "record %s)", k, n, n == 4 ? "included: the reader re-reads the head per record" : "left for the next read");
		ok++;
	}
	printf("  W reader: %d injections\n", ok);
}

/* ============================== T8: torn (tick, Count) pairs in ts_read */
static int tsr_armed;
extern int g_log_reads;

static void t_tsread(void)
{
	struct psc_sc *r;
	u32 t0;

	printf("== T8 ts_read() across a tick (1.1 torn reads)\n");
	/* the timer fires INSIDE psc_ts_read(), between `t1 = psp_local_tick`
	 * and `t2 = psp_local_tick` (at its read_c0_count()): the do-while must
	 * return the new tick with the new (small) Count, never the old tick
	 * with the new Count */
	{
		extern int g_tsr_fire;

		as(T_JP);
		g_count = CPT - 5000;
		t0 = (u32)psp_local_tick;
		g_tsr_fire = 1;
		cmd08();
		r = last_p();
		CHECK(g_tsr_fire == 0, "the in-read tick was not fired");
		CHECK(r->tick_in == t0 + 1 && r->c_in < 20000 && r->dtick == 0,
		      "tick_in %u (t0 %u) c_in %u dtick %u", r->tick_in, t0, r->c_in, r->dtick);
		printf("  tick inside ts_read at entry: tick_in %u = t0 + %u, c_in %u (new tick, small Count), dtick %u\n",
		       r->tick_in, r->tick_in - t0, r->c_in, r->dtick);
	}
	/* a command that crosses a tick edge (dtick 1) */
	as(T_JP);
	g_count = CPT - 10;
	t0 = (u32)psp_local_tick;
	cmd08();
	r = last_p();
	CHECK(r->tick_in == t0 && r->dtick == 1 && r->c_in < CPT && r->c_out < 50000,
	      "tick_in %u (t0 %u) dtick %u c_in %u c_out %u", r->tick_in, t0, r->dtick, r->c_in, r->c_out);
	printf("  command straddling a tick edge: tick_in %u c_in %u, dtick %u, c_out %u\n", r->tick_in, r->c_in,
	       r->dtick, r->c_out);
	(void)tsr_armed;
}

/* ============================== T7: single-step (ptrace) injection */
static volatile int ss_hit;
static volatile unsigned long ss_pc;

static void ss_handler(int sig, siginfo_t *si, void *ucv)
{
	ucontext_t *uc = ucv;
	struct ipt p;
	extern unsigned long g_last_ra;
	extern int g_where[];

	(void)sig; (void)si;
	ss_hit = 1;
	ss_pc = uc->uc_mcontext.pc;
	if (!g_ie || g_irq_depth)
		return;
	g_last_ra = ss_pc;
	{
		int w = g_where[g_cur];

		g_where[g_cur] = 7;	/* WH_BYRA: release address of the same function */
		ipt_for_current(&p);
		g_where[g_cur] = w;
	}
	if (g_count < CPT)
		g_count = CPT;
	fire_tick(&p);
}

static unsigned long get_reg_pc(pid_t pid, unsigned long *lr)
{
	struct user_regs_struct regs;
	struct iovec io = { &regs, sizeof(regs) };

	if (ptrace(PTRACE_GETREGSET, pid, (void *)NT_PRSTATUS, &io) < 0)
		return 0;
	if (lr)
		*lr = regs.regs[30];
	return regs.pc;
}

typedef int (*ss_op)(void);		/* returns 0 if every invariant holds */
static unsigned long ss_stop;			/* calibration end PC (0: the return address) */
static char ss_cls[200];			/* the op's classification text */

/* Run op in a child stopped at bp; inject SIGUSR1 after k steps (k < 0:
 * calibrate, returns the number of steps until the function returns). */
static int ss_once(ss_op op, unsigned long bp, long k, char *res, size_t ressz)
{
	int pfd[2], st;
	pid_t pid;
	long steps = 0;
	unsigned long orig, lr = 0, pc;

	if (pipe(pfd) < 0)
		return -1;
	fflush(stdout);
	pid = fork();
	if (pid == 0) {
		struct sigaction sa;
		int rc;

		close(pfd[0]);
		ss_cls[0] = 0;
		memset(&sa, 0, sizeof(sa));
		sa.sa_sigaction = ss_handler;
		sa.sa_flags = SA_SIGINFO;
		sigaction(SIGUSR1, &sa, NULL);
		ptrace(PTRACE_TRACEME, 0, 0, 0);
		raise(SIGSTOP);
		rc = op();
		{
			char b[400];
			unsigned long off = 0;
			const char *fn = ss_hit ? (ss_pc >= 0x100000000UL ? "libc" : host_fn_of(ss_pc, &off)) : "-";
			int n = snprintf(b, sizeof(b), "%d %s+0x%lx%s", rc, fn ? fn : "?", off, ss_cls);

			if (write(pfd[1], b, n) < 0)
				_exit(9);
		}
		_exit(0);
	}
	close(pfd[1]);
	waitpid(pid, &st, 0);			/* SIGSTOP */
	errno = 0;
	orig = ptrace(PTRACE_PEEKTEXT, pid, (void *)bp, 0);
	ptrace(PTRACE_POKETEXT, pid, (void *)bp, (void *)((orig & ~0xFFFFFFFFUL) | 0xd4200000UL));
	ptrace(PTRACE_CONT, pid, 0, 0);
	waitpid(pid, &st, 0);			/* the breakpoint */
	pc = get_reg_pc(pid, &lr);
	ptrace(PTRACE_POKETEXT, pid, (void *)bp, (void *)orig);
	if (pc != bp) {
		kill(pid, SIGKILL);
		waitpid(pid, &st, 0);
		snprintf(res, ressz, "bp-miss pc %lx", pc);
		close(pfd[0]);
		return -2;
	}
	if (k < 0) {
		while (1) {
			unsigned long npc;

			ptrace(PTRACE_SINGLESTEP, pid, 0, 0);
			waitpid(pid, &st, 0);
			if (!WIFSTOPPED(st))
				break;
			steps++;
			npc = get_reg_pc(pid, NULL);
			if (npc == (ss_stop ? ss_stop : lr) || steps > 200000)
				break;
		}
		ptrace(PTRACE_CONT, pid, 0, 0);
	} else {
		for (steps = 0; steps < k; steps++) {
			ptrace(PTRACE_SINGLESTEP, pid, 0, 0);
			waitpid(pid, &st, 0);
		}
		ptrace(PTRACE_CONT, pid, 0, (void *)(long)SIGUSR1);
	}
	waitpid(pid, &st, 0);
	{
		ssize_t n = read(pfd[0], res, ressz - 1);

		res[n > 0 ? n : 0] = 0;
	}
	close(pfd[0]);
	return k < 0 ? (int)steps : 0;
}

/* the operations single-stepped, each with its invariants */
static u32 op_s0, op_w0;
static int op_p_append(void)
{
	struct psc_sc *slot;
	u32 s = psc_k.head[PSC_RING_P];
	ssize_t r;
	u32 seq = 0;

	cmd08();				/* the breakpoint is psc_sc_exit */
	slot = &psc_mem.p[s & 4095];
	if (psc_k.head[PSC_RING_P] != s + 1 || slot->seq != s)
		return 1;
	if (ss_hit && (psc_k.head[PSC_RING_W] != op_w0 + 1 || psc_mem.w[op_w0 & 255].sc.seq != op_w0))
		return 2;
	as(T_WRK);
	r = rd(PSC_RING_P, big, 80 * 4096);
	if (r < 80)
		return 3;
	memcpy(&seq, big + r - 80, 4);
	if (seq != s || memcmp(big + r - 80, slot, 80))
		return 4;
	if (psc_st.slot_bad[PSC_RING_P] || psc_st.slot_bad[PSC_RING_W])
		return 5;
	r = rd(PSC_RING_W, big, 288 * 256);
	if (ss_hit && (r < 288 || memcmp(big + r - 288, &psc_mem.w[op_w0 & 255], 288)))
		return 6;
	/* classification output: W t_busy, p_head - s, P wn, lc_n */
	{
		struct psc_w *w = &psc_mem.w[op_w0 & 255];

		snprintf(ss_cls, sizeof(ss_cls), " W.t_busy=%u W.p_head-s=%d P.wn=%u P.lc_n=%u P.lc_flags=%02x P.pre_flags=%02x",
			 ss_hit ? w->ext.t_busy : 9, ss_hit ? (int)(w->ext.p_head - s) : 99, slot->wn,
			 slot->lc_n, slot->lc_flags, slot->pre_flags);
	}
	return 0;
}

static int op_poll_append(void)
{
	u32 s = psc_k.head[PSC_RING_POLL];
	ssize_t r;
	u32 seq = 0;

	as(T_JP);
	psc_poll_begin();
	psc_poll_end();				/* the breakpoint */
	if (psc_k.head[PSC_RING_POLL] != s + 1 || psc_mem.poll[s & 2047].seq != s)
		return 1;
	if (ss_hit && psc_k.head[PSC_RING_W] != op_w0 + 1)
		return 2;
	as(T_WRK);
	r = rd(PSC_RING_POLL, big, 40 * 2048);
	if (r < 40)
		return 3;
	memcpy(&seq, big + r - 40, 4);
	if (seq != s || memcmp(big + r - 40, &psc_mem.poll[s & 2047], 40))
		return 4;
	if (psc_st.slot_bad[PSC_RING_POLL])
		return 5;
	return 0;
}

static int op_w_read(void)
{
	ssize_t r;
	int j;

	as(T_WRK);
	r = rd(PSC_RING_W, big, 288 * 8);	/* the breakpoint is psc_ring_read */
	for (j = 0; j < r / 288; j++) {
		u32 seq;

		memcpy(&seq, big + j * 288, 4);
		if (seq != op_s0 + (u32)j || memcmp(big + j * 288, &psc_mem.w[seq & 255], 288))
			return 1;
	}
	if (ss_hit && psc_k.head[PSC_RING_W] != op_w0 + 1)
		return 2;
	if (psc_st.slot_bad[PSC_RING_W])
		return 3;
	/* the rest (if the Nop's record was not in this call) comes next */
	{
		ssize_t r2 = rd(PSC_RING_W, big, 288 * 8);

		if ((r + (r2 > 0 ? r2 : 0)) / 288 != (ss_hit ? 4 : 3))
			return 4;
	}
	return 0;
}

static void ss_campaign(const char *name, ss_op op, unsigned long bp, void (*prep)(void))
{
	char res[256];
	long n, k;
	int fails = 0;
	struct { char cls[200]; int n; } cls[64];
	int ncls = 0, i;

	prep();
	n = ss_once(op, bp, -1, res, sizeof(res));
	if (n <= 0) {
		CHECK(0, "%s: calibration failed (%ld, %s)", name, n, res);
		return;
	}
	for (k = 0; k <= n; k++) {
		char *sp;
		int rc;

		prep();
		ss_once(op, bp, k, res, sizeof(res));
		rc = atoi(res);
		if (rc != 0) {
			fails++;
			if (fails <= 10)
				printf("  %s: step %ld: invariant %d failed (%s)\n", name, k, rc, res);
		}
		sp = strchr(res, ' ');
		sp = sp ? strchr(sp + 1, ' ') : NULL;	/* skip "rc fn+off" */
		{
			char key[200];
			char fnb[80];

			if (sscanf(res, "%*d %79[^+]", fnb) != 1)
				strcpy(fnb, "?");
			snprintf(key, sizeof(key), "%s:%s", fnb, sp ? sp : "");
			for (i = 0; i < ncls; i++)
				if (!strcmp(cls[i].cls, key)) { cls[i].n++; break; }
			if (i == ncls && ncls < 64) { snprintf(cls[ncls].cls, sizeof(cls[ncls].cls), "%s", key); cls[ncls++].n = 1; }
		}
	}
	CHECK(fails == 0, "%s: %d of %ld single-step injections broke an invariant", name, fails, n + 1);
	printf("  %s: %ld instructions from %s entry to return, %ld injections, %d invariant failures\n",
	       name, n, name, n + 1, fails);
	for (i = 0; i < ncls; i++)
		printf("    %5d x  %s\n", cls[i].n, cls[i].cls);
}

static void prep_p(void)
{
	as(T_WRK);
	{
		u32 first, lost, nx = col_ring_file(PSC_RING_P)->f_pos / 80;

		drain_all(PSC_RING_P, &first, &lost, &nx);
		nx = col_ring_file(PSC_RING_W)->f_pos / 288;
		drain_all(PSC_RING_W, &first, &lost, &nx);
		nx = col_ring_file(PSC_RING_POLL)->f_pos / 40;
		drain_all(PSC_RING_POLL, &first, &lost, &nx);
	}
	psc_st.slot_bad[0] = psc_st.slot_bad[1] = psc_st.slot_bad[2] = 0;
	sim_align_wd();
	g_count = 1000;
	op_w0 = psc_k.head[PSC_RING_W];
	as(T_JP);
}

static int op_p_entry(void)
{
	int rc = op_p_append();
	struct psc_sc *slot = &psc_mem.p[(psc_k.head[PSC_RING_P] - 1) & 4095];
	struct psc_w *w = &psc_mem.w[op_w0 & 255];
	size_t l = strlen(ss_cls);

	if (rc)
		return rc;
	if (ss_hit)
		snprintf(ss_cls + l, sizeof(ss_cls) - l, " W.t_entry_c==P.c_in=%d W.c_in>P.c_in=%d",
			 w->ext.t_entry_c == slot->c_in,
			 w->sc.tick_in > slot->tick_in || (w->sc.tick_in == slot->tick_in && w->sc.c_in > slot->c_in));
	return 0;
}

static void prep_w(void)
{
	u32 i, first, lost, nx;

	as(T_WRK);
	nx = col_ring_file(PSC_RING_W)->f_pos / 288;
	drain_all(PSC_RING_W, &first, &lost, &nx);
	op_s0 = (u32)(col_ring_file(PSC_RING_W)->f_pos / 288);
	for (i = 0; i < 3; i++) {
		as(T_IDLE);
		sim_align_wd();
		sim_idle_tick();
	}
	psc_st.slot_bad[2] = 0;
	sim_align_wd();
	g_count = 1000;
	op_w0 = psc_k.head[PSC_RING_W];
	as(T_WRK);
}

static void t_single(void)
{
	printf("== T7 interrupt at every instruction (ptrace single-step, SIGUSR1 = the timer Nop)\n");
	g_log_reads = 0;
	ss_stop = 0x880ceed0UL;			/* the entry part ends at Syscon_cmd */
	ss_campaign("psc_syscon_cmd entry (to Syscon_cmd)", op_p_entry, (unsigned long)psc_syscon_cmd, prep_p);
	ss_stop = 0;
	ss_campaign("psc_sc_exit (P append)", op_p_append, (unsigned long)psc_sc_exit, prep_p);
	ss_campaign("psc_poll_end (POLL append)", op_poll_append, (unsigned long)psc_poll_end, prep_p);
	ss_campaign("psc_ring_read (W reader)", op_w_read, (unsigned long)col_ring_fops(PSC_RING_W)->read, prep_w);
}

static void print_diffs(void)
{
	int i;

	printf("== field differences against an uninterrupted append (observations, not failures)\n");
	for (i = 0; i < ndiffs; i++)
		printf("  %4d x %s\n", diffs[i].n, diffs[i].what);
}

int main(int argc, char **argv)
{
	const char *which = argc > 1 ? argv[1] : "all";
	int all = !strcmp(which, "all");

	setvbuf(stdout, NULL, _IOLBF, 0);
	big = malloc(BIGSZ);
	shadow = malloc(4 * 4096 * 80);
	inj_reader_buf = malloc(600 * 80);
	boot();
	printf("boot: W head %u (WB seq 0), M head %u, P head %u, build_id %08x\n", psc_k.head[PSC_RING_W],
	       psc_k.head[PSC_RING_M], psc_k.head[PSC_RING_P], psc_k.build_id);
	if (all || !strcmp(which, "nwords")) t_nwords();
	if (all || !strcmp(which, "tsread")) t_tsread();
	if (all || !strcmp(which, "wrap")) t_wrap();
	if (all || !strcmp(which, "overflow")) t_overflow();
	if (all || !strcmp(which, "reader")) t_reader();
	if (all || !strcmp(which, "inject")) { t_inject_p(); t_inject_entry(); t_inject_other(); t_inject_reader(); print_diffs(); }
	if (all || !strcmp(which, "single")) t_single();
	if (all || !strcmp(which, "mring")) t_mring();
	if (all || !strcmp(which, "ctl")) t_ctl();
	if (all || !strcmp(which, "seqwrap")) t_seqwrap();
	printf("RESULT %s: %d checks passed, %d failed, %d notes\n", n_fail ? "FAIL" : "PASS", n_pass, n_fail, n_note);
	return n_fail ? 1 : 0;
}
