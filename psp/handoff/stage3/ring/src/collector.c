/*
 * collector.c - a minimal collector (stand-in for pscol, NOT pscol) that
 * drains the rings through the REAL /proc/psc file operations registered by
 * the real psc_init() (psc.c:1200-1247): psc_ring_open, psc_ring_read,
 * psc_ring_llseek, psc_stats_read, psc_ctl_write. It writes T<rrr><nnn>.BIN
 * files in the chunk format of DESIGN 10.2 (struct layouts and CRC from the
 * shared header include/linux/psc_format.h, as pscol does) so the dumps can
 * be fed to the decoder.
 *
 * Follows DESIGN 4.3: drain order W, P, POLL, S, M; caps P 48, POLL 24, W 2,
 * S 64, M 8 times m (m = 4 at the first drain, else min(4, max(1, ceil(dt /
 * 57.5 ticks)))); one RECS chunk per flush with one new-records block per
 * ring; UHB every flush; STATS every 8th flush; PROCS every 40th; KMSG and
 * EVENT when due; PAD to a 512-byte boundary; durable point through ctl
 * op 1 after a complete drain (4.5).
 *
 * Simplifications (harness, not under test): files are created complete
 * (FILEHDR + 2 MB of PAD sectors, EVENT "segment create"/"segment ready") in
 * one step without S records; no flush ever fails; the Memory Stick write of
 * each flush is modeled sector by sector with the real psc_ms_seg_begin/end
 * and psc_note_led hooks (S records, LED read-backs; ms_psp.c:286-326,
 * :355-379; psp.c:268-279, :410-428).
 */
#include "host.h"
#include <stdarg.h>
#include <sys/stat.h>
#include <sys/types.h>

extern struct proc_dir_entry *host_pde(const char *name);
extern int g_where[T_NTASK];
extern char g_kmsg[];
extern int g_kmsg_len;
extern unsigned long g_wrk_wake;
extern int g_wrk_started;
extern unsigned long g_mouse_pkts_wrk, g_mouse_press_wrk;
void scen_before_seg_end(void);
void col_mouse_drain(void);
enum { WH_DEFAULT, WH_RINGREAD, WH_MSIO, WH_PSC_EXIT, WH_POLL_END, WH_SEG_END, WH_SOFTIRQ };

#define SEG		PSC_SEG_SIZE
#define NRING		5
static const int ring_size[NRING] = { 80, 40, 288, 40, 80 };
static const int ring_div4[NRING] = { 20, 10, 72, 10, 20 };
static const int ring_cap[NRING] = { 48, 24, 2, 64, 8 };
static const char *const ring_name[NRING] = { "p", "poll", "w", "s", "m" };
static const int drain_order[NRING] = { PSC_RING_W, PSC_RING_P, PSC_RING_POLL, PSC_RING_S, PSC_RING_M };

struct rfile {
	struct inode ino;
	struct file f;
	const struct file_operations *fops;
	u32 next_seq;		/* next seq expected (lost accounting) */
	u64 delivered, lost;
};
static struct rfile R[NRING];
static struct inode stats_ino, ctl_ino;
static struct file stats_f, ctl_f;
static const struct file_operations *stats_fops, *ctl_fops;

struct segfile {
	u8 *buf;
	int nnn;
	u32 fseq;
	u32 seg_end;
};
static struct segfile files[64];
static int nfiles, act = -1;

u32 col_nonce = 0x1234ABCD;
int col_run = 1;
static char evq[16384];
static int evq_len;
static int nflush, kmsg_sent, complete_once, panel_tests;
static u64 bytes_synced;
static u32 last_drain_tick, durable_tick_sent;
static u32 drain_stuck;
u64 col_rec_total[NRING], col_lost_total[NRING];
static u32 last_write_ms;

/* geometry published once at mount (psc_fat_mounted, the real hook) */
#define PART_START	63u
#define DATA_START	8064u
static struct msdos_sb_info sbi = { 64, 2, 32, 4000, 8064, 1 };
static struct super_block sb = { 0, 9, &sbi };

void col_mount(void)
{
	/* ms_psp.c:202-203 (psp_ms_init end): partition start (stats 153) */
	psc_st.ms_part_start = PART_START;
	/* fs/fat/inode.c:1418-1420 -> real psc_fat_mounted (psc.c:912) */
	psc_fat_mounted(&sb);
}

static void evq_add(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void evq_add(const char *fmt, ...)
{
	va_list ap;
	int n;

	if (evq_len > (int)sizeof(evq) - 256)
		return;
	n = sprintf(evq + evq_len, "%lu ", psp_local_tick);
	evq_len += n;
	va_start(ap, fmt);
	evq_len += vsprintf(evq + evq_len, fmt, ap);
	va_end(ap);
	evq[evq_len++] = '\n';
	evq[evq_len] = 0;
}

static void ctl(u32 op, u32 a0, u32 a1, u32 a2, u32 a3, u32 a4, u32 a5)
{
	struct psc_ctl c;
	loff_t pos = 0;
	ssize_t r;

	memset(&c, 0, sizeof(c));
	c.op = op;
	c.arg[0] = a0; c.arg[1] = a1; c.arg[2] = a2;
	c.arg[3] = a3; c.arg[4] = a4; c.arg[5] = a5;
	r = ctl_fops->write(&ctl_f, (const char *)&c, sizeof(c), &pos);
	ev("CTL %u %u %u %u %u %u %u %ld %lu\n", op, a0, a1, a2, a3, a4, a5, (long)r, psp_local_tick);
}

static void read_stats(struct psc_stats *st)
{
	loff_t pos = 0;
	ssize_t r;
	r = stats_fops->read(&stats_f, (char *)st, sizeof(*st), &pos);
	if (r != (ssize_t)sizeof(*st))
		fprintf(stderr, "collector: stats read %ld\n", (long)r);
}

/* ------------------------------------------------------------- chunks */
static u32 put_chunk(u8 *dst, u16 type, const void *payload, u32 len, u32 fseq, u32 seed)
{
	struct psc_chunk_hdr h;
	u32 tot = PSC_CHUNK_TOTAL(len);

	memcpy(h.magic, PSC_CHUNK_MAGIC, 4);
	h.type = type;
	h.hver = PSC_FORMAT_VERSION;
	h.len = len;
	h.fseq = fseq;
	h.crc = psc_crc32(seed, payload, len);
	memcpy(dst, &h, sizeof(h));
	if (len)
		memcpy(dst + sizeof(h), payload, len);
	memset(dst + sizeof(h) + len, 0, PSC_CHUNK_PAD4(len) - len);
	return tot;
}

static void file_create(void)
{
	struct segfile *f = &files[nfiles];
	struct psc_filehdr_payload fh;
	u8 zero[PSC_PAD_SECTOR_LEN];
	u32 off, padlen;
	u8 pad[512];
	char name[32];

	memset(f, 0, sizeof(*f));
	f->nnn = nfiles + 1;
	f->buf = calloc(1, SEG);
	memset(zero, 0, sizeof(zero));
	/* preallocation PAD sectors (4.4 step 3): len 492, fseq 0xFFFFFFFF */
	for (off = 0; off < SEG; off += 512)
		put_chunk(f->buf + off, PSC_CHUNK_PAD, zero, PSC_PAD_SECTOR_LEN,
			  PSC_FSEQ_PREALLOC, col_nonce);
	memset(&fh, 0, sizeof(fh));
	memcpy(fh.hdr.magic, PSC_FILEHDR_MAGIC, 8);
	fh.hdr.fmt = PSC_FORMAT_VERSION;
	fh.hdr.run = col_run;
	fh.hdr.seg = f->nnn;
	fh.hdr.inst = PSC_INST_WORKER;
	fh.hdr.writer_pid = 77;
	fh.hdr.sup_pid = 76;
	read_stats(&fh.stats);
	fh.hdr.now_tick = fh.stats.now_tick;
	fh.hdr.now_jiffies = fh.stats.now_jiffies;
	fh.hdr.nonce = col_nonce;
	strncpy((char *)fh.version, linux_banner, sizeof(fh.version));
	off = put_chunk(f->buf, PSC_CHUNK_FILEHDR, &fh, sizeof(fh), 0, 0);
	padlen = PSC_PAD_LEN_AT(off);
	memset(pad, 0, sizeof(pad));
	off += put_chunk(f->buf + off, PSC_CHUNK_PAD, pad, padlen, 1, col_nonce);
	if (off != PSC_FILEHDR_AREA)
		fprintf(stderr, "collector: FILEHDR area %u\n", off);
	f->fseq = 2;
	f->seg_end = PSC_FILEHDR_AREA;
	snprintf(name, sizeof(name), PSC_SEG_NAME_FMT, (unsigned)col_run, (unsigned)f->nnn);
	evq_add("segment create %s", name);
	evq_add("segment ready %s", name);
	ev("FILE %d\n", f->nnn);
	nfiles++;
}

void col_start(void)
{
	int i;
	struct proc_dir_entry *e;

	for (i = 0; i < NRING; i++) {
		e = host_pde(ring_name[i]);
		memset(&R[i], 0, sizeof(R[i]));
		R[i].ino.host_pde = e;
		R[i].fops = e->proc_fops;
		R[i].fops->open(&R[i].ino, &R[i].f);	/* psc_ring_open */
		ev("OPEN %d %lu\n", i, psp_local_tick);
	}
	e = host_pde("stats");
	stats_ino.host_pde = e;
	stats_fops = e->proc_fops;
	e = host_pde("ctl");
	ctl_ino.host_pde = e;
	ctl_fops = e->proc_fops;
	/* pid classes (2.11, ctl op 2): worker 1, supervisor 2, psposk2 3,
	 * pspmd 4, pdflush 5 */
	ctl(2, 0, 77, 1, 0, 0, 0);
	ctl(2, 1, 76, 2, 0, 0, 0);
	ctl(2, 2, 30, 3, 0, 0, 0);
	ctl(2, 3, 31, 4, 0, 0, 0);
	ctl(2, 4, 9, 5, 0, 0, 0);
	file_create();
	act = 0;
	evq_add("worker start inst 1 run %d", col_run);
	evq_add("conlevel 0 0");
}

/* --------------------------------------------- Memory Stick write model */
int g_ms_active;
#define SECTOR_COST	25000u

static void led_op(int set)
{
	u32 v;

	/* psp_led_ctrl(PSP_LED_MEMSTICK, on) -> psp_gpio_set/clear (psp.c:268-279,
	 * :410-428): one load, one store of v | 0x40, barrier, psc_note_led */
	dev_led_rmw(set, 0x40, &v);
	__asm__ __volatile__("" : : : "memory");	/* psp.c:415 barrier() */
	psc_note_led(set, v);				/* real (psc.c:625) */
	ev("LED %d %u %d %lu %u\n", set, v, current->pid, psp_local_tick, g_count);
}

void ms_write_seg(u32 sector, u32 nsect, int meta)
{
	u32 i;
	int w = g_where[g_cur];

	/* __bio_kmap_atomic raises the preempt count (ms_psp.c:254,
	 * highmem.h:49-52); down(s_psp_ms_rw_sem) (ms_psp.c:360) */
	psc_host_preempt_count++;
	g_where[g_cur] = WH_MSIO;
	g_ms_active = 1;
	ev("MSB %u %u 1 %d %lu %u\n", sector, nsect, current->pid, psp_local_tick, g_count);
	psc_ms_seg_begin(sector, nsect, 1);		/* ms_psp.c:364 (real hook) */
	for (i = 0; i < nsect; i++) {
		led_op(1);				/* ms_psp.c:313 */
		sim_advance(SECTOR_COST);		/* pspMsWriteSector */
		led_op(0);				/* ms_psp.c:315 */
	}
	g_where[g_cur] = WH_SEG_END;
	if (!meta)
		scen_before_seg_end();
	psc_ms_seg_end(sector, nsect, 1, 0, meta);	/* ms_psp.c:378 (real hook) */
	g_where[g_cur] = WH_MSIO;
	g_ms_active = 0;
	ev("MSE %u %u 1 0 %d %lu %u\n", sector, nsect, meta, psp_local_tick, g_count);
	g_where[g_cur] = w;
	psc_host_preempt_count--;
}

/* ------------------------------------------------------------- one tick */
static u8 flushbuf[65536];
static u8 recs[40960];
static u8 rbuf[48 * 4 * 288];

static u32 drain_ring(int ring, int m, u8 *out, u32 *outlen, u32 *lost_out, int *full)
{
	struct rfile *r = &R[ring];
	u32 want = (u32)ring_cap[ring] * (u32)m;
	loff_t pos = r->f.f_pos;
	ssize_t got;
	u32 n, i, lost = 0;
	int w = g_where[g_cur];

	g_where[g_cur] = WH_RINGREAD;
	got = r->fops->read(&r->f, (char *)rbuf, want * ring_size[ring], &pos);
	r->f.f_pos = pos;				/* sys_read: file_pos_write */
	g_where[g_cur] = w;
	ev("RR %d %lu %ld %lld\n", ring, psp_local_tick, (long)got, (long long)pos);
	if (got < 0) {
		fprintf(stderr, "collector: read ring %d: %ld\n", ring, (long)got);
		got = 0;
	}
	n = (u32)got / ring_size[ring];
	*full = (n == want);
	for (i = 0; i < n; i++) {
		u32 seq;

		memcpy(&seq, rbuf + i * ring_size[ring], 4);
		if (seq != r->next_seq) {
			if (seq > r->next_seq)
				lost += seq - r->next_seq;
			else
				ev("SEQ-BACK %d %u %u\n", ring, seq, r->next_seq);
		}
		r->next_seq = seq + 1;
	}
	memcpy(out, rbuf, n * ring_size[ring]);
	*outlen = n * ring_size[ring];
	*lost_out = lost;
	r->delivered += n;
	r->lost += lost;
	col_rec_total[ring] += n;
	col_lost_total[ring] += lost;
	return n;
}

static int col_m(void)
{
	u32 dt;

	if (!nflush)
		return 4;				/* P-14: Δt from worker start */
	dt = (u32)psp_local_tick - last_drain_tick;
	dt = (dt * 10 + 574) / 575;			/* ceil(dt / 57.5 ticks) */
	if (dt < 1)
		dt = 1;
	if (dt > 4)
		dt = 4;
	return (int)dt;
}

extern int g_selftest_tick;
extern unsigned long g_mouse_pkts_wrk;

void col_burst(void)
{
	struct psc_stats st;
	u32 recs_len = 0, pos[NRING], heads[NRING], i, off, flen, padlen, start;
	int m, complete = 1, catchup = 0, ri;
	struct segfile *f;
	struct psc_uhb u;
	u8 pad[512];
	char procs[1024];

	unsigned long sj = jiffies;

	start = (u32)psp_local_tick;
	sim_advance(30000);				/* wake-up, syscalls */
	read_stats(&st);
	for (i = 0; i < NRING; i++)
		heads[i] = st.head[i];
	m = col_m();
	/* RECS: one new-records block per ring (10.2) */
	for (ri = 0; ri < NRING; ri++) {
		int ring = drain_order[ri], full;
		u32 n, len, lost;
		struct psc_block_hdr bh;

		n = drain_ring(ring, m, recs + recs_len + sizeof(bh), &len, &lost, &full);
		bh.ring = (u8)ring;
		bh.recsize_div4 = (u8)ring_div4[ring];
		bh.count = (u16)n;
		bh.lost = lost;
		memcpy(recs + recs_len, &bh, sizeof(bh));
		recs_len += sizeof(bh) + len;
		pos[ring] = (u32)(R[ring].f.f_pos / ring_size[ring]);
		if (pos[ring] < heads[ring])
			complete = 0;
		if (full)
			catchup = 1;
		if (!full && pos[ring] < heads[ring]) {
			drain_stuck++;
			evq_add("drain stuck %s %u %u", ring_name[ring], pos[ring], heads[ring]);
		}
	}
	last_drain_tick = (u32)psp_local_tick;
	col_mouse_drain();
	sim_advance(20000 + recs_len / 4);

	/* the active file, switching when the next flush would not fit */
	f = &files[act];
	if (f->seg_end + PSC_FLUSH_MAX > SEG) {
		char a[32], b[32];

		snprintf(a, sizeof(a), PSC_SEG_NAME_FMT, (unsigned)col_run, (unsigned)f->nnn);
		file_create();
		act = nfiles - 1;
		f = &files[act];
		snprintf(b, sizeof(b), PSC_SEG_NAME_FMT, (unsigned)col_run, (unsigned)f->nnn);
		evq_add("switch %s %s full", a, b);
	}
	/* UHB (10.2) */
	memset(&u, 0, sizeof(u));
	u.tickno = (u32)nflush;
	u.stats_now_tick = st.now_tick;
	u.gtod_sec = 1700000000u + st.now_tick / 250;
	u.gtod_usec = (st.now_tick % 250) * 4000;
	u.uptime_cs = st.now_tick * 2 / 5;
	u.memfree_kb = 20800;
	u.mouse_pkts_total = (u32)g_mouse_pkts_wrk;
	u.mouse_press_total = (u32)g_mouse_press_wrk;
	u.bytes_synced_total = (u32)bytes_synced;
	u.last_write_ms = last_write_ms;
	u.last_fsync_ms = 3;
	u.max_fsync_ms_60s = 5;
	u.max_tick_ms_60s = 240;
	u.flags = PSC_UHB_F_SUP_ALIVE | (complete ? PSC_UHB_F_DRAIN_COMPLETE : 0) |
		  (catchup ? PSC_UHB_F_CATCHUP : 0);
	if ((int)st.now_tick >= g_selftest_tick)
		u.flags |= 0x1FEu;			/* b1-b8 self-test checks */
	u.durable_tick = durable_tick_sent;
	u.lag_max = 60;
	u.seg = PSC_UHB_SEG_MAKE(f->nnn, 0, 0, 0, 0);
	u.drain_stuck = drain_stuck;
	u.nonce = col_nonce;
	/* the flush */
	off = 0;
	off += put_chunk(flushbuf + off, PSC_CHUNK_RECS, recs, recs_len, f->fseq++, col_nonce);
	off += put_chunk(flushbuf + off, PSC_CHUNK_UHB, &u, sizeof(u), f->fseq++, col_nonce);
	if (nflush % 8 == 0)
		off += put_chunk(flushbuf + off, PSC_CHUNK_STATS, &st, sizeof(st), f->fseq++, col_nonce);
	if (nflush % 40 == 0) {
		int n = snprintf(procs, sizeof(procs),
			"JP 25 25 (kjoypad) %c 1 1 1\nOSK 30 30 (psposk2) S 1 1 1\nMD 31 31 (pspmd) S 1 1 1\n"
			"WRK 77 77 (pscol) R 1 1 1\n"
			"JPSTATUS State: %s SigPnd: 0000000000000000 ShdPnd: 0000000000000000\n"
			"MEM MemFree: 20800 kB\n",
			g_task[T_JP]->state == TASK_RUNNING ? 'R' : 'D',
			g_task[T_JP]->state == TASK_RUNNING ? "R (running)" : "D (disk sleep)");
		off += put_chunk(flushbuf + off, PSC_CHUNK_PROCS, procs, (u32)n, f->fseq++, col_nonce);
	}
	if (!kmsg_sent && g_kmsg_len) {
		off += put_chunk(flushbuf + off, PSC_CHUNK_KMSG, g_kmsg, (u32)g_kmsg_len, f->fseq++, col_nonce);
		kmsg_sent = 1;
	}
	if (evq_len && off + PSC_CHUNK_TOTAL((u32)evq_len) + 512 <= PSC_FLUSH_MAX) {
		off += put_chunk(flushbuf + off, PSC_CHUNK_EVENT, evq, (u32)evq_len, f->fseq++, col_nonce);
		evq_len = 0;
	}
	padlen = PSC_PAD_LEN_AT(f->seg_end + off);
	memset(pad, 0, sizeof(pad));
	off += put_chunk(flushbuf + off, PSC_CHUNK_PAD, pad, padlen, f->fseq++, col_nonce);
	flen = off;
	if (flen % 512 || flen > PSC_FLUSH_MAX || f->seg_end + flen > SEG)
		fprintf(stderr, "collector: bad flush %u at %u\n", flen, f->seg_end);
	memcpy(f->buf + f->seg_end, flushbuf, flen);
	ev("FLUSH %d %u %u %d %d\n", f->nnn, f->seg_end, flen, complete, m);
	/* the Memory Stick write of the flush: data sectors in segments of
	 * <= 8, then the directory entry and FSINFO (5.1) */
	{
		u32 s0 = PART_START + DATA_START + (u32)(f->nnn - 1) * 4096u + f->seg_end / 512u;
		u32 ns = flen / 512u, k;

		for (k = 0; k < ns; k += 8)
			ms_write_seg(s0 + k, ns - k > 8 ? 8 : ns - k, 0);
		ms_write_seg(PART_START + DATA_START + 4, 1, 1);	/* PSCLOG directory sector */
		ms_write_seg(PART_START + 1, 1, 1);			/* FSINFO */
	}
	f->seg_end += flen;
	bytes_synced += flen;
	last_write_ms = 1;
	nflush++;
	/* durable point (4.5, ctl op 1) after a complete drain */
	if (complete) {
		durable_tick_sent = st.now_tick;
		ctl(1, st.now_tick, pos[0], pos[1], pos[2], pos[3], pos[4]);
		if (!complete_once) {
			complete_once = 1;
			ctl(3, 5, 0, 0, 0, 0, 0);		/* PANEL test (8.2) */
			panel_tests++;
		}
	}
	if (panel_tests == 1 && (int)st.now_tick >= g_selftest_tick) {
		ctl(3, 5, 0, 0, 0, 0, 0);			/* second PSC TEST (8.2) */
		panel_tests++;
	}
	sim_advance(350000);				/* HUD blit, /proc reads */
	g_wrk_wake = sj + ((nflush % 2) ? 57 : 58);
	(void)start;
}

/* write the files out (after the pull) */
int col_write(const char *dir)
{
	char p[1024];
	int i;

	snprintf(p, sizeof(p), "%s/PSCLOG", dir);
	mkdir(dir, 0755);
	mkdir(p, 0755);
	for (i = 0; i < nfiles; i++) {
		FILE *fo;

		snprintf(p, sizeof(p), "%s/PSCLOG/" PSC_SEG_NAME_FMT, dir,
			 (unsigned)col_run, (unsigned)files[i].nnn);
		fo = fopen(p, "wb");
		if (!fo) {
			perror(p);
			return -1;
		}
		fwrite(files[i].buf, 1, SEG, fo);
		fclose(fo);
	}
	return nfiles;
}

void col_report(FILE *o)
{
	int i;

	for (i = 0; i < NRING; i++)
		fprintf(o, "ring %-4s delivered %llu lost %llu next_seq %u\n", ring_name[i],
			(unsigned long long)R[i].delivered, (unsigned long long)R[i].lost,
			R[i].next_seq);
	fprintf(o, "flushes %d files %d bytes %llu drain_stuck %u\n", nflush, nfiles,
		(unsigned long long)bytes_synced, drain_stuck);
}

/* direct reads for the unit tests */
const struct file_operations *col_ring_fops(int ring) { return R[ring].fops; }
struct file *col_ring_file(int ring) { return &R[ring].f; }
void col_read_stats(struct psc_stats *st) { read_stats(st); }
void col_ctl(u32 op, u32 a0, u32 a1, u32 a2, u32 a3, u32 a4, u32 a5) { ctl(op, a0, a1, a2, a3, a4, a5); }
