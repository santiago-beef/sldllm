/*
 * volsim.c - Stage 3 VOLUME test harness for pscol (WORKFLOW.md Stage 3,
 * "Volume": simulate 15 minutes at 20 polls per second; output size against
 * the design budget, DESIGN.md 5.1, 4.3, 4.4 and the 8.5 "Volume" row).
 *
 * It compiles the real collector source, /home/ubuntu/psp/work/pscol/pscol.c,
 * unchanged, with -DPSCOL_HOST, and supplies the os_* layer of pscol.h as a
 * simulated PSP. Written for Stage 3, independently of pscol/test/sim.c (the
 * implementer's harness); only the os_* interface of pscol.h is shared.
 *
 *  kernel  the five /proc/psc rings with the reader of psc.c:976-1033 (whole
 *          records, overwritten -> oldest, skip-and-count, *ppos for read(),
 *          a local position for pread()), llseek as psc.c:1035-1058, the stats
 *          block (DESIGN 1.7) built at each read, ctl ops 1-4 as
 *          psc.c:1147-1195; records on a simulated clock: 2 P + 1 POLL per poll
 *          at a fixed period (20/s or 17.86/s), a WT record at every tick
 *          1250k, WB at boot, one boot M record, S records from the stick
 *          model; the stall panel's condition at every tick = 125 mod 250 as
 *          psc_panel.c:301-338 (a MODEL of the kernel code, not executed).
 *  vfat    sequential cluster allocation, FAT1 + mirror sectors dirtied per
 *          allocated cluster; page cache with per-buffer mapped / dirty /
 *          uptodate state; fsync in this tree's order (data pages, then the
 *          file's own directory entry, then FSINFO, FAT1, FAT2 and other dirty
 *          directory sectors: DESIGN 4.4 step 4, fs/sync.c:55-76,
 *          fs/fs-writeback.c:158-174); data pages as fs/mpage.c:464-690 writes
 *          them (all buffers mapped, dirty, uptodate: one bio segment of the
 *          mapped prefix, contiguous pages merged up to 255 sectors; otherwise
 *          "confused": block_write_full_page, one bio per dirty buffer,
 *          fs/buffer.c:1584-1736); one S record per bio segment
 *          (ms_psp.c:258-292); a failed segment ends its bio (ms_psp.c:282-287)
 *          after 10 tries of its first sector with mdelay(1) (ms_psp.c:319-335);
 *          FIBMAP, fadvise(DONTNEED) of whole pages (mm/fadvise.c:98-108), a
 *          read-back by whole page; the PSCLOG directory buffer re-read from the
 *          stick after a failed write, an inode cache by slot (aliases, DESIGN
 *          4.4 step 1).
 *  stick   bytes / speed for every segment (the DESIGN 15.6 model).
 *  faults  a stalled flush (one flush data segment blocks for N s, then
 *          completes), a whole-stick write outage window, one failed flush data
 *          segment, write() returning -1 in a window.
 *  screen  /dev/fb0 (512 x 272 x 32 bit, stride 2048): every HUD row write
 *          lands in a pixel buffer; after each tick the ten HUD lines are READ
 *          BACK FROM THE PIXELS with telem.c's font (OCR) and their colours,
 *          into the screen record; pscol's own hud[] model is compared with it.
 *
 * Host only (floating point allowed here). Model limits: README.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <strings.h>
#include <errno.h>
#include <sys/stat.h>
#include "pscol.h"
#include "telem_font.h"

typedef uint64_t u64;

#define TICK_US		4000ull			/* HZ = 250 */
#define CNT_PER_S	220912896ull		/* psp.c:38 */
#define WPID		50			/* worker */
#define SUPPID		49			/* supervisor */
#define JPPID		28			/* joypad kernel thread */
#define OSKPID		40
#define MDPID		41
#define SEG		((u32)PSC_SEG_SIZE)
#define FILE_BYTES	(SEG + 131072u)
#define FILE_SECS	(FILE_BYTES / 512u)
#define FILE_PAGES	(FILE_BYTES / 4096u)
#define MAXCL		200
#define MAXINO		256
#define NFD		128
#define FB_W		512
#define FB_H		272
#define BIO_MAX_SECT	255			/* SAFE_MAX_SECTORS, blkdev.h:798 */
#define BIO_MAX_VECS	32			/* bio_get_nr_vecs, fs/bio.c:309 */

/* ================================================================ config */
struct cfg {
	char	name[64];
	char	outdir[512];
	u32	poll_us;		/* 50,000 = 20 polls/s; 56,000 = 17.86/s */
	u32	thread_start_ms;	/* joypad thread start (15.6: 3 s) */
	u32	worker_start_ms;	/* collector start (6.2: 20-40 s) */
	u32	dur_s;			/* collection time after worker start */
	u32	speed_kbs;		/* stick speed, KB/s (1 KB = 1,024 B) */
	u32	cl_bytes;		/* cluster size 32 or 64 KB */
	u32	cpu_ms;			/* loop body besides I/O (15.6: 0.23 s tick) */
	u32	press_at_ms;		/* TRIANGLE held 2 s (BTN self-test) */
	u32	stall_at_ms, stall_ms;	/* first flush data segment at/after: blocks */
	int	stall_nonpreempt;	/* variant: the joypad thread is held too */
	u32	out_at_ms, out_ms;	/* every write segment fails in the window */
	u32	fail1_at_ms;		/* first flush data segment at/after: fails */
	u32	wfail_at_ms, wfail_ms;	/* write() on a segment file returns -1 */
	u32	run, nonce;
};
static struct cfg C;

/* ================================================================ time */
static u64 now_us;
static u32 ktick(void) { return (u32)(now_us / TICK_US); }
static u32 kcount_at(u64 t) { return (u32)(((t % TICK_US) * CNT_PER_S) / 1000000ull); }
static u32 kcount(void) { return kcount_at(now_us); }
static void advance(u64 us);
static FILE *f_screen, *f_events;
static const char *banner_text;		/* /proc/version = linux_banner */
static u32 banner_len;

/* ================================================================ violations */
static int nviol;
static char viol_txt[8192];
static void viol(const char *what, long a, long b)
{
	char l[256];
	snprintf(l, sizeof(l), "%s (%ld, %ld) at %.3f s\n", what, a, b, now_us / 1e6);
	if (nviol < 30 && strlen(viol_txt) + strlen(l) < sizeof(viol_txt))
		strcat(viol_txt, l);
	nviol++;
}

/* ================================================================ rings */
struct ring { u32 n, size, head; u8 *slots; FILE *dump; };
static struct ring R[PSC_NRINGS];
static const u32 ring_n[PSC_NRINGS] = { PSC_P_ENTRIES, PSC_POLL_ENTRIES, PSC_W_ENTRIES, PSC_S_ENTRIES, PSC_M_ENTRIES };
static const u32 ring_sz[PSC_NRINGS] = { PSC_P_SIZE, PSC_POLL_SIZE, PSC_W_SIZE, PSC_S_SIZE, PSC_M_SIZE };
static const char *const ring_nm[PSC_NRINGS] = { "P", "POLL", "W", "S", "M" };
static u32 m_dropped;

static void ring_push(int r, void *rec)
{
	struct ring *q = &R[r];
	if (r == PSC_RING_M && q->head >= q->n) {	/* fill-once M ring (3.1) */
		m_dropped++;
		return;
	}
	*(u32 *)rec = q->head;
	memcpy(q->slots + (size_t)(q->head & (q->n - 1)) * q->size, rec, q->size);
	if (q->dump)
		fwrite(rec, q->size, 1, q->dump);
	q->head++;
}

/* kernel words the stats block shows */
static u32 st_last_reader, st_proc_opens, st_head_regress, st_ring_rewinds, st_slot_bad[PSC_NRINGS];
static u32 st_jp_loop, st_wd_calls, st_wd_last, st_ms_seg_wr, st_ms_seg_rd, st_ms_err, st_led_calls;
static u32 st_ctl_writes, st_panel_paints, st_panel_last, st_panel_test_seq, st_panel_test_done, st_panel_state;
static u32 st_ms_ip_tick, st_ms_ip_sector, st_ms_ip_word;
static u32 k_durable_tick, k_durable_next[PSC_NRINGS], k_meta_sector, k_meta_tick, k_panel_secs;
static u32 k_pid_class[8];
static u64 st_total_counts;

/* psc_ring_read (psc.c:976-1033) */
static int ring_read(int r, u32 *ppos, u8 *buf, int count)
{
	struct ring *q = &R[r];
	u32 n = q->n, size = q->size, s, h, skips = 0;
	int done = 0;
	st_last_reader = ktick();			/* even for 0 bytes (2.8) */
	if (*ppos % size) { errno = EINVAL; return -1; }
	s = *ppos / size;
	for (;;) {
		const u8 *slot;
		h = q->head;
		if (s > h) { st_head_regress++; break; }
		if (s == h) break;
		if (h - s > n) s = h - n;			/* overwritten: oldest */
		if (done + (int)size > count) break;
		slot = q->slots + (size_t)(s & (n - 1)) * size;
		if (*(const u32 *)slot == s) {
			memcpy(buf + done, slot, size);
			done += (int)size;
			s++;
			continue;
		}
		h = q->head;
		if (h - s < n) st_slot_bad[r]++;
		s++;
		if (++skips > n) break;
	}
	*ppos = s * size;
	return done;
}

/* ================================================================ production */
static u64 next_poll_us, next_wd_us, next_t2d_us;
static u32 n_polls, cur_wd_k;
static u64 hold_t0, hold_t1;			/* active non-preemptible stall */
/* panel model (psc_panel.c:301-338) */
static u32 panel_test_seen, panel_test_until;
struct pep { u64 t0, t1; u32 paints, dur_first, dur_max, rdr_max; char title[12]; };
static struct pep PEP[512];
static int npep, pep_open;

static void make_p(struct psc_sc *p, u64 t, u8 cmd, u32 dur_us)
{
	u64 te = t + dur_us;
	memset(p, 0, sizeof(*p));
	p->tick_in = (u32)(t / TICK_US);
	p->c_in = kcount_at(t);
	p->c_out = kcount_at(te);
	p->dtick = (u16)((te / TICK_US) - (t / TICK_US));
	p->cmd = cmd;
	p->ctx = PSC_ORIGIN_P | PSC_CTX_IE | PSC_CTX_JP_TASK;
	p->w_head_lo = (u16)R[PSC_RING_W].head;
	p->ack_polls = 20;
	p->lc_dtick = PSC_LC_DTICK_NONE;
	memset(p->rx, 0xFF, sizeof(p->rx));
}

static void produce_poll(u64 t)
{
	struct psc_sc p;
	struct psc_poll q;
	u32 p0 = R[PSC_RING_P].head;
	int press = C.press_at_ms && t >= (u64)C.press_at_ms * 1000 && t < (u64)(C.press_at_ms + 2000) * 1000;
	/* 0x33 (AStickPower): 2-word reply; ret > 0 => rx[0] == ret (REC, 8.2) */
	make_p(&p, t, 0x33, 420);
	p.txlen = 3; p.ret = 4; p.nwords = 2;
	p.rx[0] = 4; p.rx[1] = 4; p.rx[2] = 0x33; p.rx[3] = 0x00;
	ring_push(PSC_RING_P, &p);
	/* 0x08 (GetCtrl2): 5-word reply, rx[3..6] keys active low, rx[7..8] analog */
	make_p(&p, t + 600, 0x08, 640);
	p.txlen = 2; p.ret = 10; p.nwords = 5;
	p.rx[0] = 10; p.rx[1] = 10; p.rx[2] = 0x08;
	p.rx[3] = press ? 0xEF : 0xFF;			/* TRIANGLE = rx[3] b4 (6) */
	p.rx[4] = 0xFF; p.rx[5] = 0xFF; p.rx[6] = 0xFF; p.rx[7] = 0x80; p.rx[8] = 0x7E; p.rx[9] = 0x31;
	ring_push(PSC_RING_P, &p);
	memset(&q, 0, sizeof(q));
	q.tick_start = (u32)(t / TICK_US);
	q.c_start = kcount_at(t);
	q.c_end = kcount_at(t + 1500);
	q.sc_seq_lo = (u16)p0;
	q.ri_branch = PSC_RI_R5;
	q.pi_flags = PSC_PI_F_CALLED | PSC_PI_F_DEDUPE;
	q.period = (u8)(C.poll_us / TICK_US);
	q.stage_max = PSC_STAGE_PI_ENTRY;
	q.nsc = 2;
	ring_push(PSC_RING_POLL, &q);
	st_jp_loop++;
	n_polls++;
}

static void produce_wt(u64 t)
{
	struct psc_w w;
	memset(&w, 0, sizeof(w));
	w.sc.tick_in = (u32)(t / TICK_US);		/* = 1250k exactly (1.1) */
	w.sc.c_in = 1800;
	w.sc.c_out = 1800 + 60000;
	w.sc.cmd = 0x00; w.sc.txlen = 2; w.sc.ret = 4; w.sc.nwords = 2;
	memset(w.sc.rx, 0xFF, 16);
	w.sc.rx[0] = 4; w.sc.rx[1] = 4; w.sc.rx[2] = 0x00; w.sc.rx[3] = 0x00;
	w.sc.ctx = PSC_ORIGIN_WT;			/* IE 0, in_interrupt() 0 (dossier 9.1) */
	w.sc.ack_polls = 18;
	w.sc.w_head_lo = (u16)R[PSC_RING_W].head;
	w.sc.lc_dtick = 0;
	w.ext.ext_flags = PSC_EXT_F_REGS_VALID | PSC_EXT_F_KMODE;
	w.ext.p_head = R[PSC_RING_P].head;
	w.ext.jp_loop = st_jp_loop;
	w.ext.c_pre = 883651;
	ring_push(PSC_RING_W, &w);
	st_wd_calls++;
	st_wd_last = w.sc.tick_in;
}

static void boot_records(void)
{
	struct psc_w w;
	struct psc_sc m;
	memset(&w, 0, sizeof(w));
	w.sc.cmd = 0x00; w.sc.txlen = 2; w.sc.ret = 4; w.sc.nwords = 2;
	memset(w.sc.rx, 0xFF, 16);
	w.sc.rx[0] = 4; w.sc.rx[1] = 4; w.sc.rx[2] = 0x00;
	w.sc.ctx = PSC_ORIGIN_WB;
	ring_push(PSC_RING_W, &w);			/* W seq 0 = WB (prom_init, psp.c:557) */
	st_wd_calls++;
	memset(&m, 0, sizeof(m));
	m.tick_in = 250; m.c_in = 1000; m.c_out = 90000;
	m.cmd = 0x34; m.txlen = 3; m.ret = 4; m.nwords = 2;
	memset(m.rx, 0xFF, 16);
	m.rx[0] = 4; m.rx[1] = 4; m.rx[2] = 0x34;
	m.ctx = PSC_ORIGIN_M | PSC_CTX_IE;
	m.lc_dtick = PSC_LC_DTICK_NONE;
	ring_push(PSC_RING_M, &m);			/* pspSysconCtrlHRPower, serial init */
}

static void panel_t2d(u64 t)
{
	u32 tick = (u32)(t / TICK_US);
	int test_active, cond;
	if (!st_proc_opens)
		return;
	if (st_panel_test_seq != panel_test_seen) {
		panel_test_seen = st_panel_test_seq;
		panel_test_until = tick + 250 * k_panel_secs;
	}
	test_active = (int32_t)(panel_test_until - tick) > 0;
	cond = (tick - k_durable_tick > 750) || (tick - st_last_reader > 750) || test_active;
	if (cond) {
		u32 dur = (tick - k_durable_tick) / 25, rdr = (tick - st_last_reader) / 25;
		st_panel_paints++;
		st_panel_last = tick;
		st_panel_state = PSC_PANEL_SHOWING;
		if (test_active)
			st_panel_test_done++;
		if (!pep_open && npep < 512) {
			memset(&PEP[npep], 0, sizeof(PEP[npep]));
			PEP[npep].t0 = t;
			strcpy(PEP[npep].title, test_active ? "PSC TEST" : "PSC STALL");
			PEP[npep].dur_first = dur;
			pep_open = 1;
			npep++;
			if (f_screen)
				fprintf(f_screen, "[%9.3f] PANEL(model of psc_panel.c:301-338) painted: '%s DUR %03u.%u RDR %03u.%u' (rows 176-271)\n",
					t / 1e6, PEP[npep - 1].title, dur / 10, dur % 10, rdr / 10, rdr % 10);
		}
		if (pep_open) {
			struct pep *e = &PEP[npep - 1];
			e->paints++;
			e->t1 = t;
			if (dur > e->dur_max) e->dur_max = dur;
			if (rdr > e->rdr_max) e->rdr_max = rdr;
			if (!test_active && !strcmp(e->title, "PSC TEST"))
				strcpy(e->title, "TEST+STALL");
		}
	} else if (st_panel_state == PSC_PANEL_SHOWING) {
		st_panel_paints++;
		st_panel_last = tick;
		st_panel_state = PSC_PANEL_CLEARED;
		if (pep_open) {
			struct pep *e = &PEP[npep - 1];
			e->t1 = t;
			pep_open = 0;
			if (f_screen)
				fprintf(f_screen, "[%9.3f] PANEL(model) cleared after %u paints, max DUR %u.%u s, max RDR %u.%u s\n",
					t / 1e6, e->paints, e->dur_max / 10, e->dur_max % 10, e->rdr_max / 10, e->rdr_max % 10);
		}
	}
}

static void advance(u64 us)
{
	u64 target = now_us + us;
	for (;;) {
		u64 t = next_poll_us;
		int which = 0;
		if (next_wd_us < t) { t = next_wd_us; which = 1; }
		if (next_t2d_us < t) { t = next_t2d_us; which = 2; }
		if (t > target)
			break;
		if (which == 0 && hold_t1 && t >= hold_t0 && t < hold_t1) {
			next_poll_us = hold_t1;		/* thread held: non-preemptible stall */
			continue;
		}
		st_total_counts += ((t - now_us) * CNT_PER_S) / 1000000ull;
		now_us = t;
		if (which == 0) {
			produce_poll(t);
			next_poll_us += C.poll_us;
		} else if (which == 1) {
			produce_wt(t);
			cur_wd_k++;
			next_wd_us = (u64)(cur_wd_k + 1) * PSC_WD_CYCLE * TICK_US;
		} else {
			panel_t2d(t);
			next_t2d_us += 250 * TICK_US;
		}
	}
	st_total_counts += ((target - now_us) * CNT_PER_S) / 1000000ull;
	now_us = target;
}

/* ================================================================ stick geometry */
/* ms0 [0000003f-0e86bfc1] in the recovered kmsg.txt: partition 0 starts at 63 */
static u32 G_PART = 63, G_RSVD = 32, G_FATLEN, G_DATA, G_SPC;
#define DIR_CLUS	1000u			/* PSCLOG directory cluster (made on the Mac, RUNBOOK A4) */
#define FIRST_FREE	1001u			/* allocator start: prev_free + 1 (fatent.c:455) */
static u32 next_free;
static u32 dir_slots, dir_secs;

static u32 clus_rel(u32 c) { return G_DATA + (c - 2) * G_SPC; }
static u32 fat_sec_of(u32 c) { return (c * 4) / 512; }	/* FAT32: 128 entries per sector */
static u32 dir_rel(u32 sec) { return clus_rel(DIR_CLUS) + sec; }

static void build_stats(struct psc_stats *st)
{
	int r;
	memset(st, 0, sizeof(*st));
	st->magic = PSC_STATS_MAGIC;
	st->version_size = PSC_STATS_VERSION_SIZE;
	st->build_id = psc_crc32(0, banner_text, banner_len);	/* 1.7 word 2 (17 R-4) */
	st->hz = PSC_HZ;
	st->counts_per_tick = PSC_CPT;
	st->last_reader_tick = st_last_reader;
	st->initial_jiffies = 0xFFFFFFFFu - 300u * 250u + 1u;	/* INITIAL_JIFFIES */
	st->now_tick = ktick();
	st->now_count = kcount();
	st->now_jiffies = st->initial_jiffies + ktick();
	st->total_counts_lo = (u32)st_total_counts;
	st->total_counts_hi = (u32)(st_total_counts >> 32);
	st->c_pre_max = 883700;
	for (r = 0; r < PSC_NRINGS; r++) {
		st->head[r] = R[r].head;
		st->durable_next[r] = k_durable_next[r];
		st->slot_bad[r] = st_slot_bad[r];
	}
	st->m_dropped = m_dropped;
	st->addr_syscon_cmd = 0x880ceed0u;
	st->proc_opens = st_proc_opens;
	st->p_rec_cost_last = 1100;
	st->p_rec_cost_max = 2400;
	st->w_rec_cost_max = 4200;
	st->wd_calls = st_wd_calls;
	st->wd_last_tick = st_wd_last;
	st->jp_pid = JPPID;
	st->jp_loop = st_jp_loop;
	st->jp_stage = PSC_STAGE_BEFORE_MSLEEP;
	st->jp_state = 1;
	st->console_sem_count = 1;
	st->list_sem_count = 1;
	st->led_calls = st_led_calls;
	st->ms_seg_wr = st_ms_seg_wr;
	st->ms_seg_rd = st_ms_seg_rd;
	st->ms_err = st_ms_err;
	st->ms_ip_tick = st_ms_ip_tick;
	st->ms_ip_sector = st_ms_ip_sector;
	st->ms_ip_word = st_ms_ip_word;
	st->durable_tick = k_durable_tick;
	st->ctl_writes = st_ctl_writes;
	st->panel_paints = st_panel_paints;
	st->panel_last_tick = st_panel_last;
	st->panel_test_seq = st_panel_test_seq;
	st->panel_test_done = st_panel_test_done;
	st->panel_state = st_panel_state;
	st->ring_rewinds = st_ring_rewinds;
	st->head_regress = st_head_regress;
	for (r = 0; r < 8; r++)
		st->pid_class[r] = k_pid_class[r];
	st->meta_sector = k_meta_sector;
	st->meta_tick = k_meta_tick;
	st->ms_part_start = G_PART;
	st->fat_start = G_RSVD;
	st->fat_length = G_FATLEN;
	st->fats = 2;
	st->fsinfo_sector = 1;
	st->data_start = G_DATA;
	st->sec_per_clus_bits = G_SPC | (9u << 16);
}

/* ================================================================ accounting */
enum { K_FLUSH, K_STEP0, K_STEP, K_PROBE, K_READ, K_NKIND };
static const char *const kind_nm[K_NKIND] = { "flush", "step0", "step", "probe", "readback" };
enum { X_DATA, X_DIR, X_FSINFO, X_FAT1, X_FAT2, X_READ, X_NCLS };
static const char *const cls_nm[X_NCLS] = { "DATA", "DIR", "FSINFO", "FAT1", "FAT2", "READ" };
struct acct {
	u64 s_rec[K_NKIND][X_NCLS], sectors[K_NKIND][X_NCLS], s_err[K_NKIND][X_NCLS];
	u64 bytes_handed[K_NKIND], nops[K_NKIND];
	u64 led_ops, sector_attempts, io_us;
};
static struct acct A, AT;			/* whole run, this tick */
static int io_kind;

/* faults */
static int stall_pending, fail1_pending;
static u64 stall_begin_us, stall_end_us;

static int outage_now(void)
{
	return C.out_ms && now_us >= (u64)C.out_at_ms * 1000 && now_us < (u64)(C.out_at_ms + C.out_ms) * 1000;
}

/* one bio segment through psp_ms_write/psp_ms_read (ms_psp.c:340-395) */
static int transfer(u32 rel, u32 nsect, int write, int meta, int cls, int is_flush_data)
{
	struct psc_s s;
	u64 t0 = now_us, dur;
	int fail = 0;
	u32 attempts;
	if (write) {
		if (outage_now())
			fail = 1;
		if (fail1_pending && is_flush_data && now_us >= (u64)C.fail1_at_ms * 1000) {
			fail = 1;
			fail1_pending = 0;
		}
	}
	memset(&s, 0, sizeof(s));
	s.tick_on = ktick();
	s.c_on = kcount();
	s.p_head_lo = (u16)R[PSC_RING_P].head;
	st_ms_ip_tick = s.tick_on;
	st_ms_ip_sector = G_PART + rel;
	st_ms_ip_word = WPID | (nsect << 16) | PSC_MSIP_ACTIVE | (write ? PSC_MSIP_WRITE : 0);
	if (fail) {
		attempts = 10;
		dur = 10ull * (512ull * 1000000ull / ((u64)C.speed_kbs * 1024ull) + 1000ull);
	} else {
		attempts = nsect;
		dur = (u64)nsect * 512ull * 1000000ull / ((u64)C.speed_kbs * 1024ull);
	}
	if (stall_pending && is_flush_data && now_us >= (u64)C.stall_at_ms * 1000) {
		stall_pending = 0;
		stall_begin_us = now_us;
		stall_end_us = now_us + (u64)C.stall_ms * 1000 + dur;
		if (C.stall_nonpreempt) { hold_t0 = stall_begin_us; hold_t1 = stall_end_us; }
		dur += (u64)C.stall_ms * 1000;
		if (f_screen)
			fprintf(f_screen, "[%9.3f] STICK: flush data write to sector %u blocks for %u ms (fault injected)\n",
				now_us / 1e6, G_PART + rel, C.stall_ms);
	}
	advance(dur);
	if (hold_t1 && now_us >= hold_t1) hold_t0 = hold_t1 = 0;
	s.c_off = kcount();
	s.dtick = (u16)(ktick() - s.tick_on);
	s.sector = G_PART + rel;
	s.pid = WPID;
	s.nsect = (u8)nsect;
	s.flags = (u8)((write ? PSC_S_F_WRITE : 0) | (fail ? PSC_S_F_ERROR : 0) | (meta ? PSC_S_F_META : 0));
	s.led_ops = (u8)(2 * attempts > 255 ? 255 : 2 * attempts);
	s.rd_set_or = 0x00000040u;
	s.rd_clr_or = 0x00000040u;
	ring_push(PSC_RING_S, &s);
	st_ms_ip_word &= ~PSC_MSIP_ACTIVE;
	if (write) st_ms_seg_wr++; else st_ms_seg_rd++;
	if (fail) st_ms_err++;
	st_led_calls += 2 * attempts;
	A.led_ops += 2 * attempts; AT.led_ops += 2 * attempts;
	A.sector_attempts += attempts; AT.sector_attempts += attempts;
	A.s_rec[io_kind][cls]++; AT.s_rec[io_kind][cls]++;
	A.sectors[io_kind][cls] += nsect; AT.sectors[io_kind][cls] += nsect;
	if (fail) { A.s_err[io_kind][cls]++; AT.s_err[io_kind][cls]++; }
	A.io_us += now_us - t0; AT.io_us += now_us - t0;
	return fail;
}

/* ================================================================ vfat: directory */
struct dent { int used; char name[13]; u32 start, size; };
static struct dent *ddisk, *dbuf;
static u8 *dsec_uptodate, *dsec_dirty;
static int *icache;				/* slot -> inode index (fat_iget by i_pos) */

static void dir_refresh(u32 sec)
{
	u32 k;
	if (dsec_uptodate[sec])
		return;
	for (k = 0; k < 16; k++)
		dbuf[sec * 16 + k] = ddisk[sec * 16 + k];	/* re-read (fs/buffer.c:1378-1384) */
	dsec_uptodate[sec] = 1;
	dsec_dirty[sec] = 0;
}
static void dir_refresh_all(void) { u32 s; for (s = 0; s < dir_secs; s++) dir_refresh(s); }

static int dir_write(u32 sec)
{
	u32 k;
	int f = transfer(dir_rel(sec), 1, 1, 1, X_DIR, 0);
	if (f) {
		dsec_uptodate[sec] = 0;			/* fs/buffer.c:449-451 */
	} else {
		for (k = 0; k < 16; k++)
			ddisk[sec * 16 + k] = dbuf[sec * 16 + k];
	}
	dsec_dirty[sec] = 0;
	return f;
}

/* ================================================================ vfat: inodes, page cache */
#define SF_UPTODATE	1
#define SF_DIRTY	2
#define SF_MAPPED	4
#define SF_ONDISK	8
struct inode {
	int	used, slot;
	u32	ino;
	char	name[13];
	u32	i_size, mmu_private;
	u32	nclus, clus[MAXCL];
	u8	*cache, *disk, *sec;
	int	inode_dirty;
	u64	flush_bytes, step_bytes;
	u32	nflush, nstep;
	int	alias_opens;
};
static struct inode IN[MAXINO];
static int ninode;
static u32 next_ino = 7001;
static u8 *fat_dirty, *fat_failed;
static int fsinfo_dirty;
static u32 fat_stale_alloc;			/* allocations in a FAT sector whose last write failed */
static double fat_stale_first = -1;

static void inode_alloc_to(struct inode *I, u32 end)
{
	/* fat_get_block: one cluster at each cluster start (fs/fat/inode.c:80-88) */
	while ((u64)I->nclus * C.cl_bytes < end) {
		u32 c = next_free++;
		if (I->nclus >= MAXCL) { viol("too many clusters", I->nclus, 0); return; }
		if (fat_failed[fat_sec_of(c)]) {
			/* not a pscol fault: the buffer is re-read from the stick (fs/buffer.c:1378-1384)
			 * and the stopped file's last link stays lost there (DESIGN 4.6, R11) */
			fat_stale_alloc++;
			if (fat_stale_first < 0) fat_stale_first = now_us / 1e6;
		}
		I->clus[I->nclus] = c;
		fat_dirty[fat_sec_of(c)] = 1;			/* new entry: EOF */
		if (I->nclus > 0)
			fat_dirty[fat_sec_of(I->clus[I->nclus - 1])] = 1;	/* link */
		I->nclus++;
	}
	if (end > I->mmu_private)
		I->mmu_private = end;
}

static u32 file_rel(const struct inode *I, u32 fs)
{
	return clus_rel(I->clus[(fs * 512u) / C.cl_bytes]) + fs % G_SPC;
}

/* ================================================================ file descriptors */
enum { FK_NONE, FK_RING, FK_STATS, FK_CTL, FK_TEXT, FK_KMSG, FK_FILE, FK_LOGDIR, FK_PROCDIR, FK_FB, FK_MICE };
struct fdesc { int kind, ring, ino, alias, done; u32 pos; char text[2048]; int tlen; };
static struct fdesc FD[NFD];
static int ring_fd[PSC_NRINGS] = { -1, -1, -1, -1, -1 };
static int last_errno;

static int fd_new(int kind)
{
	int i;
	for (i = 3; i < NFD; i++)
		if (FD[i].kind == FK_NONE) {
			memset(&FD[i], 0, sizeof(FD[i]));
			FD[i].kind = kind;
			return i;
		}
	last_errno = 24;
	return -1;
}
static int bad_fd(int fd) { return fd < 0 || fd >= NFD || FD[fd].kind == FK_NONE; }

/* write(): buffered through cont_prepare_write (fs/fat/inode.c:143-148) */
static int file_write_bytes(int fd, const u8 *buf, u32 len, int kind)
{
	struct inode *I = &IN[FD[fd].ino];
	u32 a = FD[fd].pos, b = a + len, s;
	if (FD[fd].alias)
		viol("write through an alias inode", (long)I->ino, (long)a);
	if (b > FILE_BYTES) { last_errno = 27; return -1; }
	if (kind == K_FLUSH && b > I->i_size)
		viol("flush extends the file", (long)a, (long)b);
	if (kind == K_FLUSH && b > I->mmu_private)
		viol("flush beyond mmu_private (would allocate)", (long)a, (long)b);
	if (a % 512 || len % 512)
		viol("unaligned write", (long)a, (long)len);
	inode_alloc_to(I, b);
	memcpy(I->cache + a, buf, len);
	for (s = a / 512; s < b / 512; s++)
		I->sec[s] |= SF_UPTODATE | SF_DIRTY | SF_MAPPED;
	if (b > I->i_size)
		I->i_size = b;
	I->inode_dirty = 1;				/* file_update_time (mm/filemap.c:2276) */
	FD[fd].pos = b;
	if (kind == K_FLUSH) { I->flush_bytes += len; I->nflush++; }
	else { I->step_bytes += len; I->nstep++; }
	A.bytes_handed[kind] += len; AT.bytes_handed[kind] += len;
	A.nops[kind]++; AT.nops[kind]++;
	return (int)len;
}

/* one bio: its segments in order; a failed segment ends it (ms_psp.c:282-287) */
struct seg { u32 fs, n; };
static int submit_bio(struct inode *I, const struct seg *sg, int nseg, int is_flush)
{
	int i, err = 0;
	u32 k;
	for (i = 0; i < nseg; i++) {
		int f = transfer(file_rel(I, sg[i].fs), sg[i].n, 1, 0, X_DATA, is_flush);
		if (!f) {
			memcpy(I->disk + (size_t)sg[i].fs * 512, I->cache + (size_t)sg[i].fs * 512, (size_t)sg[i].n * 512);
			for (k = 0; k < sg[i].n; k++)
				I->sec[sg[i].fs + k] |= SF_ONDISK;
		} else {
			err = 1;
			for (; i < nseg; i++)			/* the whole bio ends in error */
				for (k = 0; k < sg[i].n; k++)
					I->sec[sg[i].fs + k] &= ~SF_UPTODATE;
			break;
		}
	}
	return err;
}

/* write_cache_pages -> __mpage_writepage (fs/mpage.c:464-690) */
static int write_data_pages(struct inode *I, int is_flush)
{
	u32 npages = (I->i_size + 4095) / 4096, p, k;
	struct seg bio[BIO_MAX_VECS];
	int nb = 0, err = 0;
	u32 bsect = 0, last_rel = 0;
	for (p = 0; p < npages; p++) {
		u32 fs0 = p * 8, fu = 8, ndirty = 0;
		int confused = 0;
		u8 st[8];
		for (k = 0; k < 8; k++) {
			st[k] = I->sec[fs0 + k];
			if (st[k] & SF_DIRTY) ndirty++;
		}
		if (!ndirty)
			continue;
		for (k = 0; k < 8; k++) {
			if (!(st[k] & SF_MAPPED)) {
				if (st[k] & SF_DIRTY) { confused = 1; break; }
				if (fu == 8) fu = k;
				continue;
			}
			if (fu != 8) { confused = 1; break; }		/* hole -> non-hole */
			if (!(st[k] & SF_DIRTY) || !(st[k] & SF_UPTODATE)) { confused = 1; break; }
			if (k && file_rel(I, fs0 + k) != file_rel(I, fs0 + k - 1) + 1) { confused = 1; break; }
		}
		if (!confused && fu == 0)
			confused = 1;
		for (k = 0; k < 8; k++)
			I->sec[fs0 + k] &= ~SF_DIRTY;		/* cleaned when submitted */
		if (!confused) {
			u32 rel0 = file_rel(I, fs0);
			if (nb > 0 && (last_rel + 1 != rel0 || nb == BIO_MAX_VECS || bsect + fu > BIO_MAX_SECT)) {
				err |= submit_bio(I, bio, nb, is_flush);
				nb = 0; bsect = 0;
			}
			bio[nb].fs = fs0; bio[nb].n = fu; nb++;
			bsect += fu;
			last_rel = rel0 + fu - 1;
			if (fu != 8) {				/* fs/mpage.c:640-648 */
				err |= submit_bio(I, bio, nb, is_flush);
				nb = 0; bsect = 0;
			}
		} else {
			if (nb > 0) { err |= submit_bio(I, bio, nb, is_flush); nb = 0; bsect = 0; }
			for (k = 0; k < 8; k++)
				if (st[k] & SF_DIRTY) {		/* one bio per dirty buffer */
					struct seg one;
					one.fs = fs0 + k; one.n = 1;
					err |= submit_bio(I, &one, 1, is_flush);
				}
		}
	}
	if (nb > 0)
		err |= submit_bio(I, bio, nb, is_flush);
	return err;
}

/* sync_blockdev: dirty metadata buffers in block order (FSINFO, FAT1, FAT2, DIR) */
static int sync_blockdev(void)
{
	u32 k;
	int err = 0;
	if (fsinfo_dirty) {
		if (transfer(1, 1, 1, 1, X_FSINFO, 0)) err = 1;
		fsinfo_dirty = 0;
	}
	for (k = 0; k < G_FATLEN; k++)
		if (fat_dirty[k]) {
			int f1 = transfer(G_RSVD + k, 1, 1, 1, X_FAT1, 0);
			fat_failed[k] = (u8)f1;
			if (f1) err = 1;
		}
	for (k = 0; k < G_FATLEN; k++)
		if (fat_dirty[k]) {				/* the mirror (fat_mirror_bhs) */
			if (transfer(G_RSVD + G_FATLEN + k, 1, 1, 1, X_FAT2, 0)) err = 1;
			fat_dirty[k] = 0;
		}
	for (k = 0; k < dir_secs; k++)
		if (dsec_dirty[k] && dsec_uptodate[k])
			if (dir_write(k)) err = 1;
	return err;
}

static int fsync_fd(int fd)
{
	struct inode *I = &IN[FD[fd].ino];
	int err = 0;
	if (!FD[fd].alias)
		err |= write_data_pages(I, io_kind == K_FLUSH);	/* do_fsync: data first */
	if (I->inode_dirty && !FD[fd].alias) {			/* fat_write_inode(inode, 1) */
		u32 sec = (u32)I->slot / 16;
		dir_refresh(sec);
		dbuf[I->slot].size = I->i_size;			/* size, start, times; not the name */
		dbuf[I->slot].start = I->nclus ? I->clus[0] : 0;
		if (dir_write(sec)) err = 1;
		I->inode_dirty = 0;
	}
	fsinfo_dirty = 1;					/* write_super, every fsync (5.2) */
	err |= sync_blockdev();
	if (err) { last_errno = OS_EIO; return -1; }
	return 0;
}

/* ================================================================ /proc text */
static const char *kmsg_text;
static int kmsg_given;

/* /proc/<pid>/stat in the exact format of this tree (fs/proc/array.c:413-461,
 * do_task_stat); values plausible for this system, growing with time */
static int stat_line(char *b, int sz, int pid)
{
	const char *comm = "?";
	char state = 'S';
	int ppid = 1, pgid = 0, sid = 0, prio = 15, user = 0;
	unsigned long ut = (unsigned long)(now_us / 10000ull), utime = 0, stime = 0, vsize = 0, rss = 0;
	unsigned long scode = 0, ecode = 0, sstack = 0, minflt = 0, wchan = 0;
	unsigned int flags = 0x00008040u;
	switch (pid) {
	case 1: comm = "init"; ppid = 0; pgid = 1; sid = 1; utime = 12; stime = 40; user = 1; vsize = 1167360; rss = 76; break;
	case 2: comm = "ksoftirqd/0"; stime = ut / 400; break;
	case 3: comm = "events/0"; stime = ut / 300; break;
	case 4: comm = "khelper"; break;
	case 5: comm = "pdflush"; ppid = 4; stime = ut / 900; break;
	case 6: comm = "pdflush"; ppid = 4; stime = ut / 2000; break;
	case 7: comm = "kswapd0"; break;
	case JPPID: comm = "kthread"; stime = ut / 40; break;
	case OSKPID: comm = "psposk2"; pgid = 39; sid = 39; user = 1; utime = ut / 25; stime = ut / 30; vsize = 1855488; rss = 233; break;
	case MDPID: comm = "pspmd"; pgid = 39; sid = 39; user = 1; utime = ut / 60; stime = ut / 50; vsize = 286720; rss = 52; break;
	case SUPPID: comm = "pscol"; pgid = SUPPID; sid = SUPPID; user = 1; utime = ut / 3000; stime = ut / 2000; vsize = 262144; rss = 64; break;
	case WPID: comm = "pscol"; ppid = SUPPID; pgid = SUPPID; sid = SUPPID; user = 1; utime = ut / 12; stime = ut / 8; vsize = 262144; rss = 64; state = 'R'; break;
	default: return -1;
	}
	if (user) {
		prio = 20; flags = 0x00400100u; minflt = 40 + ut / 900;
		scode = 2282749952ul + (unsigned long)pid * 524288ul; ecode = scode + 52768;
		sstack = scode + vsize - 64; wchan = state == 'R' ? 0 : 2281856096ul;
	} else {
		wchan = 2281771232ul + (unsigned long)pid * 64ul;
	}
	return snprintf(b, (size_t)sz,
		"%d (%s) %c %d %d %d %d %d %u %lu %lu %lu %lu %lu %lu %ld %ld %ld %ld %d 0 %llu %lu %ld %lu %lu %lu %lu %lu "
		"%lu %lu %lu %lu %lu %lu %lu %lu %d %d %u %u %llu\n",
		pid, comm, state, ppid, pgid, sid, 0, -1, flags, minflt, 0ul, user ? 3ul : 0ul, 0ul,
		utime, stime, 0l, 0l, (long)prio, 0l, 1, (unsigned long long)(pid < 40 ? pid * 3 : 900 + pid * 7),
		vsize, (long)rss, user ? 4294967295ul : 4294967295ul, scode, ecode, sstack,
		user ? sstack - 312 : 2281701376ul + (unsigned long)pid * 8192ul + 7992ul,
		user ? scode + 9124 : 2281787700ul, 0ul, 0ul, user ? 4096ul : 2147483647ul, user ? 81920ul : 0ul,
		wchan, 0ul, 0ul, user ? 17 : 0, 0, 0u, 0u, 0ull);
}

static int status_text(char *b, int sz, int pid)
{
	return snprintf(b, (size_t)sz,
		"Name:\tkthread\nState:\tS (sleeping)\nSleepAVG:\t98%%\nTgid:\t%d\nPid:\t%d\nPPid:\t1\nTracerPid:\t0\n"
		"Uid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\nFDSize:\t32\nGroups:\t\nThreads:\t1\n"
		"SigQ:\t0/256\nSigPnd:\t0000000000000000\nShdPnd:\t0000000000000000\nSigBlk:\t0000000000000000\n"
		"SigIgn:\tffffffffffffffff\nSigCgt:\t0000000000000000\nCapInh:\t0000000000000000\n"
		"CapPrm:\t00000000fffffeff\nCapEff:\t00000000fffffeff\nvoluntary_ctxt_switches:\t%lu\n"
		"nonvoluntary_ctxt_switches:\t%lu\n", pid, pid,
		(unsigned long)(now_us / 56000ull), (unsigned long)(now_us / 3000000ull));
}

static void text_for(char *b, int sz, const char *path, int *ok)
{
	int pid;
	char leaf[32];
	*ok = 1;
	if (!strcmp(path, "/proc/uptime")) {
		u64 cs = now_us / 10000ull;
		snprintf(b, (size_t)sz, "%lu.%02lu %lu.%02lu\n", (unsigned long)(cs / 100), (unsigned long)(cs % 100),
			 (unsigned long)(cs * 7 / 1000), (unsigned long)(cs * 7 / 10 % 100));
		return;
	}
	if (!strcmp(path, "/proc/meminfo")) {
		snprintf(b, (size_t)sz,
			 "MemTotal:        30628 kB\nMemFree:         %u kB\nBuffers:           %u kB\nCached:           %u kB\n"
			 "SwapCached:          0 kB\nActive:           2944 kB\nInactive:         %u kB\nSwapTotal:           0 kB\n"
			 "SwapFree:            0 kB\nDirty:               0 kB\nWriteback:           0 kB\nAnonPages:         996 kB\n"
			 "Mapped:              0 kB\nSlab:             1612 kB\nSReclaimable:      328 kB\nSUnreclaim:       1284 kB\n"
			 "PageTables:          0 kB\nNFS_Unstable:        0 kB\nBounce:              0 kB\nCommitLimit:     15312 kB\n"
			 "Committed_AS:     2020 kB\nVmallocTotal:  1048404 kB\nVmallocUsed:         0 kB\nVmallocChunk:  1048404 kB\n",
			 20120u - (u32)(now_us / 1000000ull) * 2u, 80u + (u32)(now_us / 30000000ull),
			 900u + (u32)(now_us / 500000ull), 600u + (u32)(now_us / 500000ull));
		return;
	}
	if (!strcmp(path, "/proc/mounts")) {
		snprintf(b, (size_t)sz, "rootfs / rootfs rw 0 0\nproc /proc proc rw 0 0\n"
			 "/dev/ms0 /ms0 vfat rw,fmask=0022,dmask=0022,codepage=cp437,iocharset=iso8859-1 0 0\n");
		return;
	}
	if (sscanf(path, "/proc/%d/%31s", &pid, leaf) == 2) {
		if (!strcmp(leaf, "stat") && stat_line(b, sz, pid) > 0)
			return;
		if (!strcmp(leaf, "status") && pid == JPPID && status_text(b, sz, pid) > 0)
			return;
	}
	*ok = 0;
}

/* ================================================================ framebuffer and OCR */
static u32 *fb;
static u32 fb_writes_tick, fb_band_writes, fb_bad_writes;
static u64 fb_writes_total;
struct scr { char t[10][36]; char c[10][36]; };
static struct scr SCR;
static u32 ocr_unknown, ocr_dup_bad, ocr_mismatch_ticks;
static char ocr_mismatch_first[512];

static int lit(u32 v) { return (int)((v & 0xff) + ((v >> 8) & 0xff) + ((v >> 16) & 0xff)) > 150; }
static char colc(u32 v)
{
	u32 r = v & 0xff, g = (v >> 8) & 0xff, b = (v >> 16) & 0xff;
	if (r > 200 && g < 120 && b < 120) return 'R';
	if (g > 200 && r < 120) return 'G';
	if (r > 180 && g > 180 && b > 180) return 'W';
	return 'o';
}

static void ocr_screen(void)
{
	int li, j, gr, col, ch;
	memset(&SCR, 0, sizeof(SCR));
	for (li = 0; li < 10; li++) {
		int last = -1;
		for (j = 0; j < 35; j++) {
			int y0 = 8 + 16 * li, x0 = 8 + 12 * j, found = -1;
			unsigned char bm[7];
			char cc = ' ';
			for (gr = 0; gr < 7; gr++) {
				bm[gr] = 0;
				for (col = 0; col < 5; col++) {
					u32 p00 = fb[(y0 + 2 * gr) * FB_W + x0 + 2 * col];
					u32 p11 = fb[(y0 + 2 * gr + 1) * FB_W + x0 + 2 * col + 1];
					if (p00 != p11) ocr_dup_bad++;
					if (lit(p00)) {
						bm[gr] |= (unsigned char)(0x10 >> col);
						if (cc == ' ') cc = colc(p00);
					}
				}
			}
			for (ch = 0; ch < 59 && found < 0; ch++)
				if (!memcmp(bm, TELEM_FONT[ch], 7))
					found = ch;
			if (found < 0) { ocr_unknown++; SCR.t[li][j] = '#'; }
			else SCR.t[li][j] = (char)(32 + found);
			if (SCR.t[li][j] != ' ') last = j;
			SCR.c[li][j] = SCR.t[li][j] == ' ' ? ' ' : cc;
		}
		SCR.t[li][last + 1] = 0;
		SCR.c[li][last + 1] = 0;
	}
	/* cross-check with pscol's own line model hud[] (pscol.h) */
	{
		int bad = 0;
		char why[256] = "";
		for (li = 0; li < 10; li++) {
			char want[36], wc[36];
			int n = hud[li].n, k;
			for (k = 0; k < n; k++) {
				char c = hud[li].t[k];
				want[k] = (c >= 'a' && c <= 'z') ? (char)(c - 32) : c;
				wc[k] = hud[li].c[k] == COL_RED ? 'R' : hud[li].c[k] == COL_GREEN ? 'G' : 'W';
			}
			while (n > 0 && want[n - 1] == ' ') n--;
			want[n] = 0;
			for (k = 0; k < n; k++) if (want[k] == ' ') wc[k] = ' ';
			wc[n] = 0;
			if (strcmp(want, SCR.t[li]) || strcmp(wc, SCR.c[li])) {
				if (!bad) snprintf(why, sizeof(why), "line %d: hud[] '%s' screen '%s'", li + 1, want, SCR.t[li]);
				bad = 1;
			}
		}
		if (bad) {
			ocr_mismatch_ticks++;
			if (!ocr_mismatch_first[0]) snprintf(ocr_mismatch_first, sizeof(ocr_mismatch_first), "%.3f s %s", now_us / 1e6, why);
		}
	}
}

/* line signature: digits masked, colours kept (for change-based logging) */
static void signature(const struct scr *s, char *out, int sz)
{
	int li, k, o = 0;
	for (li = 0; li < 10 && o < sz - 80; li++) {
		for (k = 0; s->t[li][k] && o < sz - 2; k++)
			out[o++] = (s->t[li][k] >= '0' && s->t[li][k] <= '9') ? 'n' : s->t[li][k];
		out[o++] = '|';
		for (k = 0; s->c[li][k] && o < sz - 2; k++)
			out[o++] = s->c[li][k];
		out[o++] = '/';
	}
	out[o] = 0;
}

static void screen_dump(const char *why, u32 tickno)
{
	int li;
	if (!f_screen) return;
	fprintf(f_screen, "[%9.3f] tick %u screen (%s): HUD read back from framebuffer pixels\n", now_us / 1e6, tickno, why);
	for (li = 0; li < 10; li++) {
		fprintf(f_screen, "   L%-2d %s\n", li + 1, SCR.t[li]);
		if (strspn(SCR.c[li], "W ") != strlen(SCR.c[li]))
			fprintf(f_screen, "       %s\n", SCR.c[li]);
	}
}

/* ================================================================ os_* (pscol.h) */
int os_errno(void) { return last_errno; }
int os_getpid(void) { return WPID; }
int os_getppid(void) { return SUPPID; }
void os_reap(void) { }
int os_mkdir(const char *path) { (void)path; last_errno = 17; return -1; }

int os_open(const char *path, int flags)
{
	static const char *const rp[PSC_NRINGS] = { PSC_PROC_P, PSC_PROC_POLL, PSC_PROC_W, PSC_PROC_S, PSC_PROC_M };
	int fd, r, ok;
	for (r = 0; r < PSC_NRINGS; r++)
		if (!strcmp(path, rp[r])) {
			fd = fd_new(FK_RING);
			if (fd < 0) return -1;
			FD[fd].ring = r;
			st_proc_opens++;			/* psc_ring_open */
			if (ring_fd[r] < 0) ring_fd[r] = fd;
			return fd;
		}
	if (!strcmp(path, PSC_PROC_STATS)) return fd_new(FK_STATS);
	if (!strcmp(path, PSC_PROC_CTL)) return fd_new(FK_CTL);
	if (!strcmp(path, "/proc/kmsg")) return fd_new(FK_KMSG);
	if (!strcmp(path, "/proc")) return fd_new(FK_PROCDIR);
	if (!strcmp(path, PSC_LOG_DIR)) return fd_new(FK_LOGDIR);
	if (!strcmp(path, "/proc/version")) {		/* = linux_banner of the packaged build */
		fd = fd_new(FK_TEXT);
		if (fd < 0) return -1;
		memcpy(FD[fd].text, banner_text, banner_len);
		FD[fd].tlen = (int)banner_len;
		return fd;
	}
	if (!strncmp(path, "/proc/", 6)) {
		fd = fd_new(FK_TEXT);
		if (fd < 0) return -1;
		text_for(FD[fd].text, sizeof(FD[fd].text), path, &ok);
		if (!ok) { FD[fd].kind = FK_NONE; last_errno = OS_ENOENT; return -1; }
		FD[fd].tlen = (int)strlen(FD[fd].text);
		return fd;
	}
	if (!strncmp(path, PSC_LOG_DIR "/", sizeof(PSC_LOG_DIR))) {
		const char *nm = path + sizeof(PSC_LOG_DIR);
		u32 slot, i;
		struct inode *I;
		if (!(flags & OS_O_CREAT_EXCL)) { last_errno = OS_ENOENT; return -1; }
		dir_refresh_all();
		for (i = 0; i < dir_slots; i++)		/* vfat lookups ignore case */
			if (dbuf[i].used && !strcasecmp(dbuf[i].name, nm)) { last_errno = OS_EEXIST; return -1; }
		for (slot = 0; slot < dir_slots; slot++)
			if (!dbuf[slot].used) break;
		if (slot == dir_slots) { last_errno = 28; return -1; }
		memset(&dbuf[slot], 0, sizeof(dbuf[slot]));	/* fat_add_entries: name, start 0, size 0 */
		dbuf[slot].used = 1;
		snprintf(dbuf[slot].name, sizeof(dbuf[slot].name), "%s", nm);
		dsec_dirty[slot / 16] = 1;
		fd = fd_new(FK_FILE);
		if (fd < 0) return -1;
		if (icache[slot] >= 0) {			/* fat_iget: cached inode of this i_pos */
			FD[fd].ino = icache[slot];
			FD[fd].alias = 1;
			IN[icache[slot]].alias_opens++;
			return fd;
		}
		if (ninode >= MAXINO) { FD[fd].kind = FK_NONE; last_errno = 12; return -1; }
		I = &IN[ninode];
		memset(I, 0, sizeof(*I));
		I->used = 1;
		I->ino = next_ino++;
		I->slot = (int)slot;
		snprintf(I->name, sizeof(I->name), "%s", nm);
		I->cache = calloc(FILE_BYTES, 1);
		I->disk = calloc(FILE_BYTES, 1);
		I->sec = calloc(FILE_SECS, 1);
		icache[slot] = ninode;
		FD[fd].ino = ninode;
		ninode++;
		return fd;
	}
	last_errno = OS_ENOENT;
	return -1;
}

int os_close(int fd) { if (!bad_fd(fd)) FD[fd].kind = FK_NONE; return 0; }

int os_read(int fd, void *buf, int len)
{
	struct fdesc *f;
	int n;
	if (bad_fd(fd)) { last_errno = 9; return -1; }
	f = &FD[fd];
	switch (f->kind) {
	case FK_RING:
		return ring_read(f->ring, &f->pos, buf, len);
	case FK_TEXT:
		n = f->tlen - (int)f->pos;
		if (n > len) n = len;
		if (n < 0) n = 0;
		memcpy(buf, f->text + f->pos, (size_t)n);
		f->pos += (u32)n;
		return n;
	case FK_KMSG:
		if (!kmsg_given) {
			n = (int)strlen(kmsg_text);
			if (n > len) n = len;
			memcpy(buf, kmsg_text, (size_t)n);
			kmsg_given = 1;
			return n;
		}
		last_errno = OS_EAGAIN;
		return -1;
	case FK_MICE:
		last_errno = OS_EAGAIN;			/* mouse mode off (dossier 9.8) */
		return -1;
	}
	last_errno = 9;
	return -1;
}

int os_pread(int fd, void *buf, int len, u32 off)
{
	struct fdesc *f;
	if (bad_fd(fd)) { last_errno = 9; return -1; }
	f = &FD[fd];
	if (f->kind == FK_RING) {
		u32 p = off;
		return ring_read(f->ring, &p, buf, len);
	}
	if (f->kind == FK_STATS) {
		struct psc_stats st;
		if (off != 0 || len < (int)sizeof(st)) { last_errno = 22; return -1; }
		build_stats(&st);
		memcpy(buf, &st, sizeof(st));
		return (int)sizeof(st);
	}
	if (f->kind == FK_FILE) {
		struct inode *I = &IN[f->ino];
		u32 s, p;
		if (off >= I->i_size) return 0;
		if (off + (u32)len > I->i_size) len = (int)(I->i_size - off);
		for (p = off / 4096; p <= (off + (u32)len - 1) / 4096; p++) {
			int miss = 0;
			for (s = p * 8; s < p * 8 + 8; s++)
				if (!(I->sec[s] & SF_UPTODATE)) miss = 1;
			if (miss) {				/* mpage_readpage: the whole page */
				int sv = io_kind;
				io_kind = K_READ;
				transfer(file_rel(I, p * 8), 8, 0, 0, X_READ, 0);
				io_kind = sv;
				memcpy(I->cache + (size_t)p * 4096, I->disk + (size_t)p * 4096, 4096);
				for (s = p * 8; s < p * 8 + 8; s++)
					I->sec[s] |= SF_UPTODATE | SF_MAPPED;
			}
		}
		memcpy(buf, I->cache + off, (size_t)len);
		return len;
	}
	last_errno = 9;
	return -1;
}

int os_write(int fd, const void *buf, int len)
{
	if (bad_fd(fd)) { last_errno = 9; return -1; }
	if (FD[fd].kind == FK_FB) {
		u32 y = FD[fd].pos / 2048u;
		fb_writes_tick++;
		fb_writes_total++;
		if (FD[fd].pos % 2048u || len != ROW_BYTES || y >= FB_H) { fb_bad_writes++; return -1; }
		if (y >= 176) fb_band_writes++;		/* the kernel's band (2.10): never */
		memcpy(fb + (size_t)y * FB_W, buf, (size_t)len);
		FD[fd].pos += (u32)len;
		return len;
	}
	if (FD[fd].kind == FK_FILE) {
		if (C.wfail_ms && now_us >= (u64)C.wfail_at_ms * 1000 && now_us < (u64)(C.wfail_at_ms + C.wfail_ms) * 1000) {
			last_errno = OS_EIO;			/* injected: write() itself fails */
			A.nops[K_FLUSH]++; AT.nops[K_FLUSH]++;
			return -1;
		}
		io_kind = (FD[fd].pos == 0 && len == PSC_FILEHDR_AREA) ? K_STEP0 : K_FLUSH;
		return file_write_bytes(fd, buf, (u32)len, io_kind);
	}
	last_errno = 9;
	return -1;
}

int os_writev_rep(int fd, const void *buf, int unit, u32 total)
{
	static u8 tmp[65536 + 4096];
	u32 o = 0;
	if (bad_fd(fd) || FD[fd].kind != FK_FILE || total > sizeof(tmp)) { last_errno = 22; return -1; }
	while (o < total) {
		u32 l = total - o < (u32)unit ? total - o : (u32)unit;
		memcpy(tmp + o, buf, l);
		o += l;
	}
	io_kind = K_STEP;
	return file_write_bytes(fd, tmp, total, K_STEP);
}

s32 os_lseek(int fd, s32 off, int whence)
{
	struct fdesc *f;
	if (bad_fd(fd)) { last_errno = 9; return -1; }
	f = &FD[fd];
	if (whence == 1) {
		if (f->kind == FK_RING && off != 0) { last_errno = 22; return -1; }
		return (s32)(f->pos + (u32)off);
	}
	if (off < 0) { last_errno = 22; return -1; }
	if (f->kind == FK_RING) {
		if ((u32)off % R[f->ring].size) { last_errno = 22; return -1; }
		if ((u32)off < f->pos) st_ring_rewinds++;
	}
	f->pos = (u32)off;
	return off;
}

int os_fsync(int fd)
{
	if (bad_fd(fd) || FD[fd].kind != FK_FILE) { last_errno = 9; return -1; }
	if (FD[fd].alias) io_kind = K_PROBE;
	return fsync_fd(fd);
}

int os_fstat(int fd, u32 *size, u32 *ino, u32 *blksize)
{
	if (bad_fd(fd) || FD[fd].kind != FK_FILE) { last_errno = 9; return -1; }
	*size = IN[FD[fd].ino].i_size;
	*ino = IN[FD[fd].ino].ino;
	*blksize = C.cl_bytes;				/* fs/fat/file.c:310 cluster_size */
	return 0;
}

int os_stat(const char *path, u32 *size, int *isdir)
{
	if (!strcmp(path, PSC_LOG_DIR)) { *size = C.cl_bytes; *isdir = 1; return 0; }
	last_errno = OS_ENOENT;
	return -1;
}

int os_fibmap(int fd, u32 *blk)
{
	struct inode *I;
	if (bad_fd(fd) || FD[fd].kind != FK_FILE) { last_errno = 9; return -1; }
	I = &IN[FD[fd].ino];
	if ((u64)*blk * 512 >= (u64)I->nclus * C.cl_bytes) { *blk = 0; return 0; }
	*blk = file_rel(I, *blk);			/* partition-relative block (512 B) */
	return 0;
}

int os_fadvise_dontneed(int fd, u32 off, u32 len)
{
	struct inode *I;
	u32 p, p0, p1, s;
	if (bad_fd(fd) || FD[fd].kind != FK_FILE) { last_errno = 9; return -1; }
	I = &IN[FD[fd].ino];
	if (len == 0) return 0;
	p0 = (off + 4095) / 4096;			/* start_index: first FULL page */
	p1 = (off + len - 1) / 4096;			/* end_index = endbyte >> PAGE_SHIFT */
	for (p = p0; p <= p1 && p < FILE_PAGES; p++) {	/* (mm/fadvise.c:102-108) */
		int dirty = 0;
		for (s = p * 8; s < p * 8 + 8; s++) if (I->sec[s] & SF_DIRTY) dirty = 1;
		if (dirty) continue;
		for (s = p * 8; s < p * 8 + 8; s++) I->sec[s] &= ~(SF_UPTODATE | SF_MAPPED);
	}
	return 0;
}

static int put_dirent(char *b, int off, int len, u32 ino, u32 doff, const char *nm)
{
	int n = (int)strlen(nm), rl = (10 + n + 2 + 3) & ~3;
	if (off + rl > len) return -1;
	memset(b + off, 0, (size_t)rl);
	*(u32 *)(b + off) = ino;
	*(u32 *)(b + off + 4) = doff;
	*(u16 *)(b + off + 8) = (u16)rl;
	memcpy(b + off + 10, nm, (size_t)n + 1);
	return off + rl;
}

int os_getdents(int fd, void *buf, int len)
{
	struct fdesc *f;
	int off = 0, n, i;
	if (bad_fd(fd)) { last_errno = 9; return -1; }
	f = &FD[fd];
	if (f->done) return 0;
	f->done = 1;
	if (f->kind == FK_PROCDIR) {
		static const char *const p[] = { "1", "2", "3", "4", "5", "6", "7", "28", "40", "41", "49", "50",
						 "self", "uptime", "meminfo", "version", "mounts", "kmsg", "psc" };
		for (i = 0; i < (int)(sizeof(p) / sizeof(p[0])); i++)
			if ((n = put_dirent(buf, off, len, 100 + (u32)i, (u32)i + 1, p[i])) > 0) off = n;
		return off;
	}
	if (f->kind == FK_LOGDIR) {
		/* vfat readdir under shortname=lower: d_off = the next entry's first slot */
		int prev = -1;
		u32 s;
		dir_refresh_all();
		for (s = 0; s < dir_slots; s++) {
			char disp[16];
			int k;
			if (!dbuf[s].used) continue;
			for (k = 0; dbuf[s].name[k] && k < 15; k++) {
				char c = dbuf[s].name[k];
				disp[k] = (c >= 'A' && c <= 'Z') ? (char)(c + 32) : c;
			}
			disp[k] = 0;
			if (prev >= 0) *(u32 *)((char *)buf + prev + 4) = s * 32;
			n = put_dirent(buf, off, len, 9000 + s, 0, disp);
			if (n < 0) break;
			prev = off;
			off = n;
		}
		if (prev >= 0) *(u32 *)((char *)buf + prev + 4) = dir_slots * 32;
		return off;
	}
	last_errno = 20;
	return -1;
}

int os_syslog(int type, char *buf, int len)
{
	(void)buf;
	if (type == 3) { int n = (int)strlen(kmsg_text); return n < len ? n : len; }
	return 0;
}

void os_gettimeofday(u32 *sec, u32 *usec)
{
	*sec = (u32)(1791371000ull + now_us / 1000000ull);
	*usec = (u32)(now_us % 1000000ull);
}

void os_sleep_ms(int ms) { advance((u64)ms * 1000ull); }
int os_fb_stride(int fd) { (void)fd; return 2048; }
int os_open_fb(void) { return fd_new(FK_FB); }
int os_open_mice(void) { return fd_new(FK_MICE); }

int os_ctl_write(int fd, const struct psc_ctl *c)
{
	int r;
	(void)fd;
	switch (c->op) {
	case PSC_CTL_OP_DURABLE:
		for (r = 0; r < PSC_NRINGS; r++) k_durable_next[r] = c->arg[1 + r];
		k_durable_tick = c->arg[0];
		break;
	case PSC_CTL_OP_CLASS:
		if (c->arg[0] >= 8) { last_errno = 22; return -1; }
		k_pid_class[c->arg[0]] = PSC_PIDCLASS_MAKE(c->arg[1], c->arg[2]);
		break;
	case PSC_CTL_OP_PANEL_TEST:
		if (c->arg[0] < 1 || c->arg[0] > 10) { last_errno = 22; return -1; }
		k_panel_secs = c->arg[0];
		st_panel_test_seq++;
		break;
	case PSC_CTL_OP_META:
		k_meta_tick = c->arg[1];
		k_meta_sector = c->arg[0];
		break;
	default:
		last_errno = 22;
		return -1;
	}
	st_ctl_writes++;
	return PSC_CTL_SIZE;
}

/* EVENT lines (pscol.c ev()) */
static u32 cur_tickno;
static u32 n_events;
void pscol_ev_hook(const char *s, int len)
{
	n_events++;
	if (f_events)
		fprintf(f_events, "[%9.3f] tick %5u  %.*s\n", now_us / 1e6, cur_tickno, len, s);
}

/* ================================================================ driver */
static char *slurp(const char *path, u32 *len)
{
	FILE *f = fopen(path, "rb");
	char *b;
	long n;
	if (!f) { fprintf(stderr, "cannot read %s\n", path); exit(2); }
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	fseek(f, 0, SEEK_SET);
	b = calloc((size_t)n + 256, 1);
	if (fread(b, 1, (size_t)n, f) != (size_t)n) { fprintf(stderr, "short read %s\n", path); exit(2); }
	fclose(f);
	*len = (u32)n;
	return b;
}

static void mkdirs(const char *d)
{
	char b[600], *p;
	snprintf(b, sizeof(b), "%s", d);
	for (p = b + 1; *p; p++)
		if (*p == '/') { *p = 0; mkdir(b, 0755); *p = '/'; }
	mkdir(b, 0755);
}

static u32 arg_u(const char *s) { return (u32)strtoul(s, 0, 0); }

static char big[512];

static void usage(void)
{
	fprintf(stderr, "usage: volsim name=N out=DIR big=DIR [polls=20|17.86] [speed=KBs] [cl=32|64] [start=s] [dur=s]\n"
		"       [cpu=ms] [press=ms] [stall_at=ms stall_ms=ms [stall_np=1]] [out_at=ms out_ms=ms]\n"
		"       [fail1_at=ms] [wfail_at=ms wfail_ms=ms] [run=n] [nonce=x]\n");
	exit(2);
}

static void csv_str(FILE *f, const char *s)
{
	fputc('"', f);
	for (; *s; s++) { if (*s == '"') fputc('"', f); fputc(*s, f); }
	fputc('"', f);
}

int main(int argc, char **argv)
{
	int i, r;
	u64 end_us, last_dump_us = 0;
	u32 banner_n, kmsg_n;
	char *kb, sig[2048], sig_prev[2048] = "", path[700];
	FILE *f_ticks, *f_sum;
	struct pscol_tinfo ti;
	u64 prev_t0 = 0;
	/* run-wide per-tick statistics */
	u64 n_ticks = 0, n_hold = 0, n_catch = 0, n_create = 0, n_red = 0;
	u64 per_sum_us = 0, per_max_us = 0, per_min_us = ~0ull;
	u64 cr_ticks_us = 0, nc_ticks_us = 0, cr_flushS = 0, nc_flushS = 0, cr_dataS = 0, nc_dataS = 0;
	u64 st8_n = 0, st8_S = 0, st8_maxS = 0, st64_n = 0, st64_S = 0, st64_maxS = 0, stx_n = 0, stx_S = 0;
	u32 bl_max[PSC_NRINGS] = { 0 }, bl_max_t[PSC_NRINGS] = { 0 };
	u64 flush_hist[90] = { 0 };
	u32 flush_max = 0;
	u32 first_red_tick = 0, last_red_tick = 0, err_shown_max = 0;
	double first_red_t = -1, last_red_t = -1;
	char first_red_l6[64] = "", worst_l6[64] = "";
	u32 dur_shown_max_tenths = 0;
	u64 st_pass_t = 0;

	memset(&C, 0, sizeof(C));
	snprintf(C.name, sizeof(C.name), "run");
	C.poll_us = 50000; C.thread_start_ms = 3000; C.worker_start_ms = 30000; C.dur_s = 900;
	C.speed_kbs = 52; C.cl_bytes = 32768; C.cpu_ms = 30; C.press_at_ms = 100000;
	C.run = 1; C.nonce = 0x6A1D2C4Bu;
	for (i = 1; i < argc; i++) {
		char *v = strchr(argv[i], '=');
		if (!v) usage();
		*v++ = 0;
		if (!strcmp(argv[i], "name")) snprintf(C.name, sizeof(C.name), "%s", v);
		else if (!strcmp(argv[i], "out")) snprintf(C.outdir, sizeof(C.outdir), "%s", v);
		else if (!strcmp(argv[i], "big")) snprintf(big, sizeof(big), "%s", v);
		else if (!strcmp(argv[i], "polls")) C.poll_us = !strcmp(v, "17.86") ? 56000 : (u32)(1000000.0 / atof(v) + 0.5);
		else if (!strcmp(argv[i], "speed")) C.speed_kbs = arg_u(v);
		else if (!strcmp(argv[i], "cl")) C.cl_bytes = arg_u(v) * 1024;
		else if (!strcmp(argv[i], "start")) C.worker_start_ms = arg_u(v) * 1000;
		else if (!strcmp(argv[i], "dur")) C.dur_s = arg_u(v);
		else if (!strcmp(argv[i], "cpu")) C.cpu_ms = arg_u(v);
		else if (!strcmp(argv[i], "press")) C.press_at_ms = arg_u(v);
		else if (!strcmp(argv[i], "stall_at")) C.stall_at_ms = arg_u(v);
		else if (!strcmp(argv[i], "stall_ms")) C.stall_ms = arg_u(v);
		else if (!strcmp(argv[i], "stall_np")) C.stall_nonpreempt = (int)arg_u(v);
		else if (!strcmp(argv[i], "out_at")) C.out_at_ms = arg_u(v);
		else if (!strcmp(argv[i], "out_ms")) C.out_ms = arg_u(v);
		else if (!strcmp(argv[i], "fail1_at")) C.fail1_at_ms = arg_u(v);
		else if (!strcmp(argv[i], "wfail_at")) C.wfail_at_ms = arg_u(v);
		else if (!strcmp(argv[i], "wfail_ms")) C.wfail_ms = arg_u(v);
		else if (!strcmp(argv[i], "run")) C.run = arg_u(v);
		else if (!strcmp(argv[i], "nonce")) C.nonce = arg_u(v);
		else usage();
	}
	if (!C.outdir[0] || !big[0] || (C.cl_bytes != 32768 && C.cl_bytes != 65536)) usage();

	/* inputs: the packaged banner (= /proc/version, build_id 0x045b27d9) and the
	 * kernel log recovered from the stick (dossier 9.5, Q9) + the PSC5 line */
	banner_text = slurp("/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD/banner.txt", &banner_n);
	banner_len = banner_n;
	kb = slurp("/home/ubuntu/psp/telem/logs-from-stick/kmsg.txt", &kmsg_n);
	strcat(kb, "<4>PSC5 P4096 POLL2048 W256 S4096 M64 bootnop ret=4 nw=2 rx2=00\n");
	kmsg_text = kb;

	/* geometry: FAT32 on the 0x0e86bfc1-sector card of kmsg.txt */
	G_SPC = C.cl_bytes / 512;
	G_FATLEN = C.cl_bytes == 32768 ? 29743 : 14875;
	G_DATA = G_RSVD + 2 * G_FATLEN;
	dir_slots = C.cl_bytes / 32;
	dir_secs = C.cl_bytes / 512;
	ddisk = calloc(dir_slots, sizeof(*ddisk));
	dbuf = calloc(dir_slots, sizeof(*dbuf));
	dsec_uptodate = calloc(dir_secs, 1);
	dsec_dirty = calloc(dir_secs, 1);
	icache = malloc(dir_slots * sizeof(int));
	for (i = 0; i < (int)dir_slots; i++) icache[i] = -1;
	ddisk[0].used = 1; strcpy(ddisk[0].name, ".");
	ddisk[1].used = 1; strcpy(ddisk[1].name, "..");
	fat_dirty = calloc(G_FATLEN, 1);
	fat_failed = calloc(G_FATLEN, 1);
	next_free = FIRST_FREE;
	fb = calloc((size_t)FB_W * FB_H, 4);

	mkdirs(C.outdir);
	snprintf(path, sizeof(path), "%s/produced", big); mkdirs(path);
	snprintf(path, sizeof(path), "%s/stick/PSCLOG", big); mkdirs(path);
	snprintf(path, sizeof(path), "%s/stick/raw", big); mkdirs(path);
	for (r = 0; r < PSC_NRINGS; r++) {
		u32 k;
		R[r].n = ring_n[r];
		R[r].size = ring_sz[r];
		R[r].slots = calloc(R[r].n, R[r].size);
		for (k = 0; k < R[r].n; k++)
			*(u32 *)(R[r].slots + (size_t)k * R[r].size) = PSC_SEQ_WRITING;	/* BSS: never valid */
		snprintf(path, sizeof(path), "%s/produced/ring%d_%s.bin", big, r, ring_nm[r]);
		R[r].dump = fopen(path, "wb");
	}
	snprintf(path, sizeof(path), "%s/screen.log", C.outdir); f_screen = fopen(path, "w");
	snprintf(path, sizeof(path), "%s/events.log", C.outdir); f_events = fopen(path, "w");
	snprintf(path, sizeof(path), "%s/ticks.csv", C.outdir); f_ticks = fopen(path, "w");
	fprintf(f_ticks, "tick,t_s,period_ms,io_ms,flush_B,step0_B,step_B,S_flush,S_flush_data,S_step0,S_step,S_probe,"
		"S_read,S_err,sect_written,bl_P,bl_POLL,bl_W,bl_S,bl_M,lost,write_errs,holding,catchup,active,creating,"
		"ahead,k_durable_age_s,panel_state,L1,L6,L6col,L7,L8,L8col\n");
	fprintf(f_screen, "# screen record, run %s: HUD rows 0-175 read back from the simulated framebuffer pixels\n"
		"# (OCR with telem.c's font); colour mask under a line: G green, R red, W white. A screen is\n"
		"# printed when any line changes other than in its digits, and every 60 s. PANEL lines are the\n"
		"# kernel stall panel's condition evaluated by the harness (a model of psc_panel.c:301-338).\n", C.name);

	next_poll_us = (u64)C.thread_start_ms * 1000;
	next_wd_us = (u64)PSC_WD_CYCLE * TICK_US;
	next_t2d_us = 125ull * TICK_US;
	stall_pending = C.stall_ms > 0;
	fail1_pending = C.fail1_at_ms > 0;
	boot_records();
	advance((u64)C.worker_start_ms * 1000);

	worker_init(PSC_INST_WORKER, C.run, C.nonce, 0, 0);	/* = worker_main (pscol.c:2966-2976) */
	end_us = (u64)(C.worker_start_ms + C.dur_s * 1000) * 1000;
	while (now_us < end_us) {
		u64 t0 = now_us, period;
		u32 bl[PSC_NRINGS];
		int red6 = 0, red8 = 0, creation_tick;
		u64 sflush, sstep, sdata_flush;
		cur_tickno++;
		memset(&AT, 0, sizeof(AT));
		fb_writes_tick = 0;
		for (r = 0; r < PSC_NRINGS; r++) {
			bl[r] = ring_fd[r] >= 0 ? R[r].head - FD[ring_fd[r]].pos / R[r].size : R[r].head;
			if (bl[r] > bl_max[r]) { bl_max[r] = bl[r]; bl_max_t[r] = (u32)(now_us / 1000); }
		}
		worker_tick();
		pscol_tinfo(&ti);
		ocr_screen();
		if (fb_writes_tick != 272)
			viol("framebuffer writes per tick != 272", (long)fb_writes_tick, 0);
		signature(&SCR, sig, sizeof(sig));
		if (strcmp(sig, sig_prev) || now_us - last_dump_us >= 60000000ull) {
			screen_dump(strcmp(sig, sig_prev) ? "changed" : "periodic", cur_tickno);
			strcpy(sig_prev, sig);
			last_dump_us = now_us;
		}
		red6 = strchr(SCR.c[5], 'R') != 0;
		red8 = strchr(SCR.c[7], 'R') != 0;
		if (ti.st_pass && !st_pass_t) st_pass_t = now_us;
		if (red6) {
			n_red++;
			if (first_red_t < 0) { first_red_t = now_us / 1e6; first_red_tick = cur_tickno; snprintf(first_red_l6, sizeof(first_red_l6), "%s", SCR.t[5]); }
			last_red_t = now_us / 1e6; last_red_tick = cur_tickno;
		}
		{	/* largest DUR and ERR shown on line 6 */
			const char *d = strstr(SCR.t[5], "DUR "), *e = strstr(SCR.t[5], "ERR ");
			if (d && st_pass_t) {
				u32 a = 0, b = 0;
				if (sscanf(d + 4, "%u.%u", &a, &b) == 2 && a * 10 + b > dur_shown_max_tenths) {
					dur_shown_max_tenths = a * 10 + b;
					snprintf(worst_l6, sizeof(worst_l6), "%s", SCR.t[5]);
				}
			}
			if (e) { u32 x = (u32)atoi(e + 4); if (x > err_shown_max) err_shown_max = x; }
		}
		/* tick accounting */
		creation_tick = AT.nops[K_STEP] + AT.nops[K_STEP0] > 0;
		sflush = 0; sstep = 0;
		for (i = 0; i < X_NCLS; i++) { sflush += AT.s_rec[K_FLUSH][i]; sstep += AT.s_rec[K_STEP][i] + AT.s_rec[K_STEP0][i]; }
		sdata_flush = AT.s_rec[K_FLUSH][X_DATA];
		if (AT.bytes_handed[K_FLUSH]) {
			u32 fb_ = (u32)AT.bytes_handed[K_FLUSH];
			flush_hist[fb_ / 512 < 89 ? fb_ / 512 : 89]++;
			if (fb_ > flush_max) flush_max = fb_;
		}
		if (AT.nops[K_STEP]) {
			u64 k = AT.bytes_handed[K_STEP], s = 0;
			for (i = 0; i < X_NCLS; i++) s += AT.s_rec[K_STEP][i];
			if (k == 8192) { st8_n++; st8_S += s; if (s > st8_maxS) st8_maxS = s; }
			else if (k == 65536) { st64_n++; st64_S += s; if (s > st64_maxS) st64_maxS = s; }
			else { stx_n++; stx_S += s; }
		}
		{
			FILE *t = f_ticks;
			u64 sall = 0, serr = 0, swr = 0;
			int c, k;
			for (k = 0; k < K_NKIND; k++)
				for (c = 0; c < X_NCLS; c++) {
					sall += AT.s_rec[k][c];
					serr += AT.s_err[k][c];
					if (c != X_READ) swr += AT.sectors[k][c];
				}
			(void)sall;
			fprintf(t, "%u,%.3f,%.1f,%.1f,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%u,%u,%u,%u,%u,%u,%u,%d,%d,%d,%d,%d,%.1f,%u,",
				cur_tickno, t0 / 1e6, prev_t0 ? (t0 - prev_t0) / 1000.0 : 0.0, AT.io_us / 1000.0,
				(unsigned long)AT.bytes_handed[K_FLUSH], (unsigned long)AT.bytes_handed[K_STEP0],
				(unsigned long)AT.bytes_handed[K_STEP], (unsigned long)sflush, (unsigned long)sdata_flush,
				(unsigned long)(AT.s_rec[K_STEP0][X_DATA] + AT.s_rec[K_STEP0][X_DIR] + AT.s_rec[K_STEP0][X_FSINFO] + AT.s_rec[K_STEP0][X_FAT1] + AT.s_rec[K_STEP0][X_FAT2]),
				(unsigned long)(AT.s_rec[K_STEP][X_DATA] + AT.s_rec[K_STEP][X_DIR] + AT.s_rec[K_STEP][X_FSINFO] + AT.s_rec[K_STEP][X_FAT1] + AT.s_rec[K_STEP][X_FAT2]),
				(unsigned long)(AT.s_rec[K_PROBE][X_DIR] + AT.s_rec[K_PROBE][X_FSINFO]),
				(unsigned long)AT.s_rec[K_READ][X_READ], (unsigned long)serr, (unsigned long)swr,
				bl[0], bl[1], bl[2], bl[3], bl[4], ti.lost_total, ti.write_errs, ti.holding, ti.catchup,
				ti.active_nnn, ti.creating_nnn, ti.complete_ahead,
				k_durable_tick ? (ktick() - k_durable_tick) / 250.0 : -1.0, st_panel_state);
			csv_str(t, SCR.t[0]); fputc(',', t);
			csv_str(t, SCR.t[5]); fputc(',', t); fputs(red6 ? "R" : "W", t); fputc(',', t);
			csv_str(t, SCR.t[6]); fputc(',', t);
			csv_str(t, SCR.t[7]); fputc(',', t); fputs(red8 ? "R" : "W", t); fputc('\n', t);
		}
		if (prev_t0) {
			period = t0 - prev_t0;
			per_sum_us += period;
			if (period > per_max_us) per_max_us = period;
			if (period < per_min_us) per_min_us = period;
		}
		prev_t0 = t0;
		n_ticks++;
		if (ti.holding) n_hold++;
		if (ti.catchup) n_catch++;
		if (creation_tick) n_create++;
		advance((u64)C.cpu_ms * 1000);		/* loop body besides I/O (15.6) */
		os_sleep_ms(TICK_SLEEP_MS);		/* nanosleep(200 ms) (4.3 step 10) */
		/* creation/non-creation tick split of the flush S rate (8.5 Volume row) */
		if (creation_tick) { cr_ticks_us += now_us - t0; cr_flushS += sflush; cr_dataS += sdata_flush; }
		else { nc_ticks_us += now_us - t0; nc_flushS += sflush; nc_dataS += sdata_flush; }
		(void)sstep;
	}
	pscol_tinfo(&ti);

	/* ---- stick content: the Mac copy (entry size on the stick) and every inode raw */
	{
		FILE *fl;
		snprintf(path, sizeof(path), "%s/files.txt", C.outdir);
		fl = fopen(path, "w");
		fprintf(fl, "# name slot ino clusters(first-last) i_size mmu_private ondisk_entry_size flush_bytes nflush step_bytes nstep alias_opens\n");
		for (i = 0; i < ninode; i++) {
			struct inode *I = &IN[i];
			struct dent *d = &ddisk[I->slot];
			int entry = d->used && !strcasecmp(d->name, I->name);
			FILE *o;
			fprintf(fl, "%s %d %u %u-%u %u %u %s %lu %u %lu %u %d\n", I->name, I->slot, I->ino,
				I->nclus ? I->clus[0] : 0, I->nclus ? I->clus[I->nclus - 1] : 0, I->i_size, I->mmu_private,
				entry ? (snprintf(path, 32, "%u", d->size), path) : "none", (unsigned long)I->flush_bytes,
				I->nflush, (unsigned long)I->step_bytes, I->nstep, I->alias_opens);
			if (entry) {
				char p2[700];
				snprintf(p2, sizeof(p2), "%s/stick/PSCLOG/%s", big, I->name);
				o = fopen(p2, "wb");
				fwrite(I->disk, 1, d->size, o);
				fclose(o);
			}
			{
				char p2[700];
				snprintf(p2, sizeof(p2), "%s/stick/raw/ino%u_%s", big, I->ino, I->name);
				o = fopen(p2, "wb");
				fwrite(I->disk, 1, I->nclus * C.cl_bytes < FILE_BYTES ? I->nclus * C.cl_bytes : FILE_BYTES, o);
				fclose(o);
			}
		}
		fclose(fl);
	}
	for (r = 0; r < PSC_NRINGS; r++)
		fclose(R[r].dump);

	/* ---- summary.json */
	snprintf(path, sizeof(path), "%s/summary.json", C.outdir);
	f_sum = fopen(path, "w");
	fprintf(f_sum, "{\n \"name\": \"%s\",\n", C.name);
	fprintf(f_sum, " \"config\": {\"poll_us\": %u, \"polls_per_s\": %.4f, \"thread_start_s\": %.1f, \"worker_start_s\": %.1f, "
		"\"dur_s\": %u, \"speed_kbs\": %u, \"cluster_bytes\": %u, \"cpu_ms\": %u, \"sleep_ms\": %d, \"press_at_s\": %.1f, "
		"\"stall_at_s\": %.3f, \"stall_ms\": %u, \"stall_nonpreempt\": %d, \"outage_at_s\": %.3f, \"outage_ms\": %u, "
		"\"fail1_at_s\": %.3f, \"wfail_at_s\": %.3f, \"wfail_ms\": %u, \"run\": %u, \"nonce\": %u,\n"
		"   \"geometry\": {\"part_start\": %u, \"fat_start\": %u, \"fat_length\": %u, \"fats\": 2, \"fsinfo\": 1, "
		"\"data_start\": %u, \"sec_per_clus\": %u, \"psclog_dir_cluster\": %u, \"first_free_cluster\": %u, \"dir_slots\": %u}},\n",
		C.poll_us, 1e6 / C.poll_us, C.thread_start_ms / 1e3, C.worker_start_ms / 1e3, C.dur_s, C.speed_kbs, C.cl_bytes,
		C.cpu_ms, TICK_SLEEP_MS, C.press_at_ms / 1e3, C.stall_at_ms / 1e3, C.stall_ms, C.stall_nonpreempt,
		C.out_at_ms / 1e3, C.out_ms, C.fail1_at_ms / 1e3, C.wfail_at_ms / 1e3, C.wfail_ms, C.run, C.nonce,
		G_PART, G_RSVD, G_FATLEN, G_DATA, G_SPC, DIR_CLUS, FIRST_FREE, dir_slots);
	fprintf(f_sum, " \"end_s\": %.3f, \"worker_ticks\": %lu, \"polls\": %u,\n", now_us / 1e6, (unsigned long)n_ticks, n_polls);
	fprintf(f_sum, " \"tick_period_ms\": {\"mean\": %.2f, \"min\": %.1f, \"max\": %.1f},\n",
		n_ticks > 1 ? per_sum_us / 1000.0 / (n_ticks - 1) : 0.0, per_min_us / 1000.0, per_max_us / 1000.0);
	fprintf(f_sum, " \"ticks\": {\"holding\": %lu, \"catchup\": %lu, \"creation\": %lu, \"line6_red\": %lu},\n",
		(unsigned long)n_hold, (unsigned long)n_catch, (unsigned long)n_create, (unsigned long)n_red);
	fprintf(f_sum, " \"heads\": [%u, %u, %u, %u, %u], \"m_dropped\": %u,\n", R[0].head, R[1].head, R[2].head, R[3].head, R[4].head, m_dropped);
	fprintf(f_sum, " \"kernel_durable_tick\": %u, \"kernel_durable_next\": [%u, %u, %u, %u, %u], \"end_tick\": %u,\n",
		k_durable_tick, k_durable_next[0], k_durable_next[1], k_durable_next[2], k_durable_next[3], k_durable_next[4], ktick());
	fprintf(f_sum, " \"backlog_max\": [%u, %u, %u, %u, %u], \"backlog_max_at_ms\": [%u, %u, %u, %u, %u], \"ring_entries\": [%u, %u, %u, %u, %u],\n",
		bl_max[0], bl_max[1], bl_max[2], bl_max[3], bl_max[4], bl_max_t[0], bl_max_t[1], bl_max_t[2], bl_max_t[3], bl_max_t[4],
		ring_n[0], ring_n[1], ring_n[2], ring_n[3], ring_n[4]);
	fprintf(f_sum, " \"pscol\": {\"lost_total\": %u, \"slot_bad\": %u, \"drain_stuck\": %u, \"write_errs\": %u, \"durable_tick\": %u, "
		"\"st_pass\": %d, \"st_bits\": %u, \"st_pass_at_s\": %.3f, \"names_used\": %u, \"names_budget\": %u, \"conf_total\": %u, "
		"\"nrq\": %d, \"evq_len\": %u, \"rec_alarm\": %d, \"holding\": %d, \"active_nnn\": %d, \"creating_nnn\": %d, "
		"\"complete_ahead\": %d, \"flags_sticky\": %u, \"speed_kbs\": %u, \"geom_ok\": %d, \"stick_ok\": %d, \"krn_id_ok\": %d},\n",
		ti.lost_total, ti.slot_bad, ti.drain_stuck, ti.write_errs, ti.durable_tick, ti.st_pass, ti.st_bits, st_pass_t / 1e6,
		ti.names_used, ti.names_budget, ti.conf_total, ti.nrq, ti.evq_len, ti.rec_alarm, ti.holding, ti.active_nnn,
		ti.creating_nnn, ti.complete_ahead, ti.flags_sticky, ti.speed_kbs, ti.geom_ok, ti.stick_ok, ti.krn_id_ok);
	fprintf(f_sum, " \"bytes_handed\": {");
	for (i = 0; i < K_NKIND; i++) fprintf(f_sum, "%s\"%s\": %lu", i ? ", " : "", kind_nm[i], (unsigned long)A.bytes_handed[i]);
	fprintf(f_sum, "},\n \"ops\": {");
	for (i = 0; i < K_NKIND; i++) fprintf(f_sum, "%s\"%s\": %lu", i ? ", " : "", kind_nm[i], (unsigned long)A.nops[i]);
	fprintf(f_sum, "},\n \"s_records\": {");
	for (i = 0; i < K_NKIND; i++) {
		int c;
		fprintf(f_sum, "%s\"%s\": {", i ? ", " : "", kind_nm[i]);
		for (c = 0; c < X_NCLS; c++) fprintf(f_sum, "%s\"%s\": %lu", c ? ", " : "", cls_nm[c], (unsigned long)A.s_rec[i][c]);
		fprintf(f_sum, "}");
	}
	fprintf(f_sum, "},\n \"sectors\": {");
	for (i = 0; i < K_NKIND; i++) {
		int c;
		fprintf(f_sum, "%s\"%s\": {", i ? ", " : "", kind_nm[i]);
		for (c = 0; c < X_NCLS; c++) fprintf(f_sum, "%s\"%s\": %lu", c ? ", " : "", cls_nm[c], (unsigned long)A.sectors[i][c]);
		fprintf(f_sum, "}");
	}
	fprintf(f_sum, "},\n \"s_errors\": {");
	for (i = 0; i < K_NKIND; i++) {
		int c;
		fprintf(f_sum, "%s\"%s\": {", i ? ", " : "", kind_nm[i]);
		for (c = 0; c < X_NCLS; c++) fprintf(f_sum, "%s\"%s\": %lu", c ? ", " : "", cls_nm[c], (unsigned long)A.s_err[i][c]);
		fprintf(f_sum, "}");
	}
	fprintf(f_sum, "},\n \"led_ops\": %lu, \"sector_attempts\": %lu, \"io_s\": %.3f, \"kernel_led_calls\": %u, \"ms_seg_wr\": %u, \"ms_seg_rd\": %u, \"ms_err\": %u,\n",
		(unsigned long)A.led_ops, (unsigned long)A.sector_attempts, A.io_us / 1e6, st_led_calls, st_ms_seg_wr, st_ms_seg_rd, st_ms_err);
	fprintf(f_sum, " \"flush_S_rate\": {\"noncreation_ticks_s\": %.3f, \"noncreation_flush_S\": %lu, \"noncreation_flush_data_S\": %lu, "
		"\"creation_ticks_s\": %.3f, \"creation_flush_S\": %lu, \"creation_flush_data_S\": %lu},\n",
		nc_ticks_us / 1e6, (unsigned long)nc_flushS, (unsigned long)nc_dataS, cr_ticks_us / 1e6, (unsigned long)cr_flushS, (unsigned long)cr_dataS);
	fprintf(f_sum, " \"step_S\": {\"step8k_n\": %lu, \"step8k_S\": %lu, \"step8k_maxS\": %lu, \"step64k_n\": %lu, \"step64k_S\": %lu, "
		"\"step64k_maxS\": %lu, \"step_other_n\": %lu, \"step_other_S\": %lu},\n",
		(unsigned long)st8_n, (unsigned long)st8_S, (unsigned long)st8_maxS, (unsigned long)st64_n, (unsigned long)st64_S,
		(unsigned long)st64_maxS, (unsigned long)stx_n, (unsigned long)stx_S);
	fprintf(f_sum, " \"flush_size_hist_sectors\": {");
	{
		int first = 1;
		for (i = 0; i < 90; i++) if (flush_hist[i]) { fprintf(f_sum, "%s\"%d\": %lu", first ? "" : ", ", i, (unsigned long)flush_hist[i]); first = 0; }
	}
	fprintf(f_sum, "}, \"flush_max_B\": %u,\n", flush_max);
	fprintf(f_sum, " \"panel_episodes\": [");
	for (i = 0; i < npep; i++)
		fprintf(f_sum, "%s{\"t0\": %.3f, \"t1\": %.3f, \"title\": \"%s\", \"paints\": %u, \"dur_first_s\": %.1f, \"dur_max_s\": %.1f, \"rdr_max_s\": %.1f}",
			i ? ", " : "", PEP[i].t0 / 1e6, PEP[i].t1 / 1e6, PEP[i].title, PEP[i].paints, PEP[i].dur_first / 10.0,
			PEP[i].dur_max / 10.0, PEP[i].rdr_max / 10.0);
	fprintf(f_sum, "],\n \"stall\": {\"begin_s\": %.3f, \"end_s\": %.3f},\n", stall_begin_us / 1e6, stall_end_us / 1e6);
	fprintf(f_sum, " \"screen\": {\"line6_red_ticks\": %lu, \"first_red_s\": %.3f, \"first_red_tick\": %u, \"first_red_line6\": \"%s\", "
		"\"last_red_s\": %.3f, \"last_red_tick\": %u, \"err_shown_max\": %u, \"dur_shown_max_s\": %.1f, \"dur_shown_max_line6\": \"%s\", "
		"\"fb_writes\": %lu, \"fb_band_writes\": %u, \"fb_bad_writes\": %u, \"ocr_unknown_glyphs\": %u, \"ocr_2x2_mismatch\": %u, "
		"\"ocr_vs_hud_mismatch_ticks\": %u, \"ocr_vs_hud_first\": \"%s\"},\n",
		(unsigned long)n_red, first_red_t, first_red_tick, first_red_l6, last_red_t, last_red_tick, err_shown_max,
		dur_shown_max_tenths / 10.0, worst_l6, (unsigned long)fb_writes_total, fb_band_writes, fb_bad_writes, ocr_unknown,
		ocr_dup_bad, ocr_mismatch_ticks, ocr_mismatch_first);
	fprintf(f_sum, " \"events\": %u, \"inodes\": %d, \"next_free_cluster\": %u, \"fat_stale_alloc\": %u, \"fat_stale_first_s\": %.3f,\n",
		n_events, ninode, next_free, fat_stale_alloc, fat_stale_first);
	fprintf(f_sum, " \"violations\": %d, \"violation_text\": \"", nviol);
	{ const char *p; for (p = viol_txt; *p; p++) { if (*p == '\n') fputs("\\n", f_sum); else if (*p == '"') fputs("\\\"", f_sum); else fputc(*p, f_sum); } }
	fprintf(f_sum, "\"\n}\n");
	fclose(f_sum);
	fclose(f_ticks);
	fclose(f_screen);
	fclose(f_events);
	printf("%s: %lu ticks, end %.1f s, lost %u, write_errs %u, files %d, viol %d, SELFTEST PASS %s at %.1f s\n",
	       C.name, (unsigned long)n_ticks, now_us / 1e6, ti.lost_total, ti.write_errs, ninode, nviol,
	       ti.st_pass ? "yes" : "NO", st_pass_t / 1e6);
	return 0;
}
