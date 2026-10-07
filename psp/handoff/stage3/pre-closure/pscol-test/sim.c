/*
 * test/sim.c - host-side harness for pscol (DESIGN 8.5 host tests, Stage 2
 * self-check). It implements the os_* layer of pscol.h as a simulated
 * kernel + vfat + Memory Stick:
 *
 *  - /proc/psc: the five rings with the 3.5 reader protocol (skip and
 *    count, *ppos for read, local position for pread), stats (1.7) built at
 *    each read, ctl (2.8: durable, class, panel test, meta);
 *  - record production by simulated time: P 35.71/s, POLL 17.86/s, W at
 *    tick 1250k (WB at boot), one boot M record; S records from the stick;
 *  - vfat: 32 KB clusters, a sequential allocator, FAT1 + mirror, FSINFO
 *    on every fsync, the PSCLOG directory with a buffer that is re-read from
 *    the stick after a failed write and an inode cache keyed by slot (so a
 *    failed step-0 entry write returns an alias, 4.4 step 1 / A5-1); fsync
 *    writes data first, then the file's own entry, then FSINFO, FAT1, the
 *    mirror and other dirty directory sectors (4.4 step 4 order);
 *  - Memory Stick: modelled speed (bytes / speed, 1 KB per fsync, 15.6),
 *    fault injection: whole-stick bursts, Poisson whole-tick failures,
 *    triggered bursts, data-only failures of chosen creation steps;
 *  - checks: no alias written, no flush extends a file or crosses a missing
 *    link, no region handed to a flush written twice, holds <= 114.7 s, and
 *    at the end a decoder pass over the stick content: every record with
 *    seq < durable_next is present.
 *
 * Host only; FP is allowed here (never runs on the PSP).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include "../pscol.h"

typedef uint64_t u64;
#define TICK_US		4000ull
#define WPID		50
#define SUPPID		49

/* ---------------------------------------------------------------- config */
struct cfg {
	const char *name;
	u32	speed_kbs;
	u32	worker_start_s;
	u32	end_s;
	u32	seed;
	int	fb;
	int	nburst;
	u64	b0[64], b1[64];
	int	poisson_per_30min;	/* IF4: whole-tick failures */
	int	burst_on_step0;		/* k-th FILEHDR write starts a burst (1-based) */
	u64	burst_on_step0_us;
	int	fail_step[8];		/* writev ordinal whose fsync DATA writes fail */
	int	nfail_step;
	int	burst_at_step;		/* writev ordinal that starts a burst */
	u64	burst_at_step_us;
	int	dir_refuse_from_s;	/* persistent DIR sector refusal (IF7b), 0 = off */
	int	press_at_s;
	int	quiet;
	int	trace;
	/* G2 attempt 2 vectors */
	u32	run;			/* run number given to the worker (0 = 1) */
	u32	dir_bytes;		/* PSCLOG size for stat (0 = one 32 KB cluster) */
	int	bad_build_id;		/* stats word 2 differs from CRC(/proc/version) */
	const char *version;		/* /proc/version text (0 = the sim's) */
	u32	build_id;		/* stats word 2 when version is given */
	int	fail_flush[8];		/* flush ordinals whose DATA writes fail */
	int	nfail_flush;
	u32	stall_at_s, stall_s, stall_fail_ms;	/* one fsync stalls, the stick refuses */
	const char *const *pre;		/* PSCLOG entries before the worker starts */
};
static struct cfg C;

/* ---------------------------------------------------------------- time */
static u64 now_us;
static u32 tick_now(void) { return (u32)(now_us / TICK_US); }
static u32 count_now(void) { return (u32)((now_us % TICK_US) * 221ull); }
static void produce(void);
static void advance(u64 us) { now_us += us; produce(); }

/* ---------------------------------------------------------------- violations */
static int nviol;
static char viol_first[256];
static void viol(const char *what, u32 a, u32 b)
{
	if (!nviol)
		snprintf(viol_first, sizeof(viol_first), "%s %u %u at %.2fs", what, a, b, now_us / 1e6);
	nviol++;
}

/* ---------------------------------------------------------------- rings */
struct sring { u32 n, size; u8 *slots; u32 head; };
static struct sring R[PSC_NRINGS];
static u32 st_slot_bad[PSC_NRINGS], st_head_regress, st_ring_rewinds, st_last_reader;
static u32 st_ms_seg_wr, st_ms_seg_rd, st_ms_err, st_ctl_writes, st_jp_loop;
static u32 ctl_durable_tick, ctl_durable_next[PSC_NRINGS], ctl_meta, ctl_panel_seq;
static u32 panel_until, panel_done, panel_chk;

static void ring_push(int r, void *rec)
{
	struct sring *q = &R[r];
	*(u32 *)rec = q->head;
	memcpy(q->slots + (size_t)(q->head & (q->n - 1)) * q->size, rec, q->size);
	q->head++;
}

static int ring_read(int r, u32 *ppos, u8 *buf, int len, int is_read)
{
	struct sring *q = &R[r];
	u32 s = *ppos / q->size, out = 0, h, skips = 0;
	if (is_read)
		st_last_reader = tick_now();
	for (;;) {
		u8 *sl;
		h = q->head;
		if (s > h) { st_head_regress++; break; }
		if (s == h) break;
		if (h - s > q->n) s = h - q->n;
		if (out + q->size > (u32)len) break;
		sl = q->slots + (size_t)(s & (q->n - 1)) * q->size;
		if (*(u32 *)sl == s) {
			memcpy(buf + out, sl, q->size);
			out += q->size;
			s++;
		} else {
			st_slot_bad[r]++;
			s++;
			if (++skips > q->n) break;
		}
	}
	*ppos = s * q->size;
	return (int)out;
}

/* ---------------------------------------------------------------- production */
static u64 next_poll_us;
static u32 next_wd_tick;
static u32 nprod_p;

static void produce(void)
{
	while (next_poll_us <= now_us) {
		u64 t = next_poll_us;
		struct psc_sc p;
		struct psc_poll q;
		u32 c = (u32)((t % TICK_US) * 221ull);
		int k, press = C.press_at_s && t >= (u64)C.press_at_s * 1000000ull &&
			t < (u64)(C.press_at_s + 2) * 1000000ull;
		memset(&p, 0, sizeof(p));
		p.tick_in = (u32)(t / TICK_US);
		p.c_in = c;
		p.c_out = c + 50000;
		if (p.c_out >= PSC_CPT) { p.c_out -= PSC_CPT; p.dtick = 1; }
		p.cmd = 0x33; p.txlen = 3; p.ret = 3; p.nwords = 2;
		for (k = 0; k < 16; k++) p.rx[k] = 0xFF;
		p.rx[0] = 3; p.rx[1] = 3; p.rx[2] = 0x33; p.rx[3] = 0;
		p.ctx = PSC_ORIGIN_P | PSC_CTX_IE | PSC_CTX_JP_TASK;
		p.lc_dtick = 0xFFFF;
		ring_push(PSC_RING_P, &p);
		p.cmd = 0x08; p.txlen = 2; p.ret = 9; p.nwords = 5;
		p.rx[0] = 9; p.rx[1] = 9; p.rx[2] = 0x08;
		p.rx[3] = press ? 0xEF : 0xFF; p.rx[4] = 0xFF; p.rx[5] = 0xFF; p.rx[6] = 0xFF;
		p.rx[7] = 0x80; p.rx[8] = 0x7F;
		ring_push(PSC_RING_P, &p);
		nprod_p += 2;
		memset(&q, 0, sizeof(q));
		q.tick_start = (u32)(t / TICK_US);
		q.c_start = c;
		q.ri_branch = PSC_RI_R5;
		q.period = 14;
		q.nsc = 2;
		ring_push(PSC_RING_POLL, &q);
		st_jp_loop++;
		next_poll_us += 56000;
	}
	while ((u64)next_wd_tick * TICK_US <= now_us) {
		struct psc_w w;
		int k;
		memset(&w, 0, sizeof(w));
		w.sc.tick_in = next_wd_tick;
		w.sc.c_in = 1000;
		w.sc.c_out = 30000;
		w.sc.cmd = 0; w.sc.txlen = 2; w.sc.ret = 4; w.sc.nwords = 2;
		for (k = 0; k < 16; k++) w.sc.rx[k] = 0xFF;
		w.sc.rx[0] = 4; w.sc.rx[1] = 3; w.sc.rx[2] = 0;
		w.sc.ctx = PSC_ORIGIN_WT;
		w.ext.ext_flags = PSC_EXT_F_REGS_VALID;
		ring_push(PSC_RING_W, &w);
		next_wd_tick += PSC_WD_CYCLE;
	}
}

static void boot_records(void)
{
	struct psc_w w;
	struct psc_sc m;
	int k;
	memset(&w, 0, sizeof(w));
	w.sc.cmd = 0; w.sc.ret = 4; w.sc.nwords = 2;
	for (k = 0; k < 16; k++) w.sc.rx[k] = 0xFF;
	w.sc.rx[0] = 4;
	w.sc.ctx = PSC_ORIGIN_WB;
	ring_push(PSC_RING_W, &w);		/* W seq 0 = WB */
	memset(&m, 0, sizeof(m));
	m.cmd = 0x34; m.ret = 3; m.nwords = 2;
	for (k = 0; k < 16; k++) m.rx[k] = 0xFF;
	m.rx[0] = 3;
	m.ctx = PSC_ORIGIN_M | PSC_CTX_IE;
	ring_push(PSC_RING_M, &m);
}

/* ---------------------------------------------------------------- vfat */
#define PART		8192u
#define FAT_START	32u
#define FAT_LEN		2048u
#define FSINFO_SEC	1u
#define DATA_START	(FAT_START + 2 * FAT_LEN)
#define SPC		64u
#define CL		(SPC * 512u)
#define DIR_CLUS	2u
#define DIR_SLOTS	1024
#define DIR_SECS	(DIR_SLOTS / 16)
#define MAXCLUS		80
#define NSEC_FILE	(PSC_SEG_SIZE / 512 + 256)

static u32 clus_sec(u32 c) { return DATA_START + (c - 2) * SPC; }

struct reg { u32 a, b; int kind; };
#define K_FLUSH 1
#define K_STEP0 2
#define K_STEP 3
struct sinode {
	int	used;
	u32	ino;
	int	slot;
	u32	i_size;
	int	nclus;
	u32	clus[MAXCLUS];
	u8	link_missing[MAXCLUS];
	u8	*cache, *disk, *dirty;
	int	entry_dirty;
	int	dropped;
	int	nreg;
	struct reg *regs;
	int	nnn;
};
#define NINODE 2048
static struct sinode IN[NINODE];
static int ninode;
static u32 next_ino = 1000, next_clus = 3;

/* one directory slot: a short entry (kind 0, name = the 8.3 name as created,
 * lname = its long name or "") or a long-name slot (kind 1, not listed);
 * used = 0 is a free or deleted slot (fs/fat/dir.c:493-496 skip both) */
struct dslot { int used; int kind; char name[13]; char lname[40]; u32 size, start; };
static struct dslot ddisk[DIR_SLOTS], dbuf[DIR_SLOTS];
static u8 dbuf_uptodate[DIR_SECS], dbuf_dirty[DIR_SECS];
static int icache[DIR_SLOTS];
static u8 fat_dirty[FAT_LEN];
struct pfat { int ino_idx; int ci; u32 fsec; };
static struct pfat pfat[4096];
static int npfat;
static int dir_refuse_sec = -1;
static const char *sim_version(void)
{
	return C.version ? C.version : "Linux version 2.6.22 (sim) #1 PREEMPT\n";
}
static int C_getdents_max = 1 << 30;	/* smaller: forces several getdents calls */

static void dir_refresh(void)
{
	int s, k;
	for (s = 0; s < DIR_SECS; s++)
		if (!dbuf_uptodate[s]) {
			for (k = 0; k < 16; k++)
				dbuf[s * 16 + k] = ddisk[s * 16 + k];
			dbuf_uptodate[s] = 1;
			dbuf_dirty[s] = 0;
		}
}

/* Entries left by earlier boots or by the Mac, from slot 2 on (after "."
 * and ".."): "T001001.BIN" a short entry as pscol creates it; "L:<long>:<SFN>"
 * a long name (ceil(len/13) slots) and its short entry; "D" a deleted slot */
static void dir_prepopulate(const char *const *list)
{
	int slot = 2, k, nl;
	for (; *list; list++) {
		const char *e = *list;
		if (!strcmp(e, "D")) {
			ddisk[slot].used = 0;
			slot++;
			continue;
		}
		if (!strncmp(e, "L:", 2)) {
			char ln[40], sn[13];
			const char *c = strchr(e + 2, ':');
			snprintf(ln, sizeof(ln), "%.*s", (int)(c - e - 2), e + 2);
			snprintf(sn, sizeof(sn), "%s", c + 1);
			nl = ((int)strlen(ln) + 12) / 13;
			for (k = 0; k < nl; k++, slot++) {
				memset(&ddisk[slot], 0, sizeof(ddisk[slot]));
				ddisk[slot].used = 1;
				ddisk[slot].kind = 1;
			}
			memset(&ddisk[slot], 0, sizeof(ddisk[slot]));
			ddisk[slot].used = 1;
			strcpy(ddisk[slot].name, sn);
			strcpy(ddisk[slot].lname, ln);
			slot++;
			continue;
		}
		memset(&ddisk[slot], 0, sizeof(ddisk[slot]));
		ddisk[slot].used = 1;
		snprintf(ddisk[slot].name, sizeof(ddisk[slot].name), "%s", e);
		slot++;
	}
	memset(dbuf_uptodate, 0, sizeof(dbuf_uptodate));
}

/* ---------------------------------------------------------------- faults */
static u64 dyn_b0, dyn_b1;
static int nstep0_writes, nwritev, cur_fail_data, nflush_writes, stall_done;
static double *pois;
static int npois;

static int fault(int cls, u32 abs_sector)
{
	int i;
	(void)abs_sector;
	for (i = 0; i < C.nburst; i++)
		if (now_us >= C.b0[i] && now_us < C.b1[i])
			return 1;
	if (now_us >= dyn_b0 && now_us < dyn_b1)
		return 1;
	for (i = 0; i < npois; i++)
		if (now_us >= (u64)(pois[i] * 1e6) && now_us < (u64)(pois[i] * 1e6) + 230000ull)
			return 1;
	if (cur_fail_data && cls == SC_DATA)
		return 1;
	if (dir_refuse_sec >= 0 && cls == SC_DIR &&
	    abs_sector == PART + clus_sec(DIR_CLUS) + (u32)dir_refuse_sec &&
	    C.dir_refuse_from_s && now_us >= (u64)C.dir_refuse_from_s * 1000000ull)
		return 1;
	return 0;
}

static void s_record(u32 abs, int nsect, int write, int err, int meta)
{
	struct psc_s s;
	memset(&s, 0, sizeof(s));
	s.tick_on = tick_now();
	s.c_on = count_now();
	s.sector = abs;
	s.pid = WPID;
	s.nsect = (u8)nsect;
	s.flags = (write ? PSC_S_F_WRITE : 0) | (err ? PSC_S_F_ERROR : 0) | (meta ? PSC_S_F_META : 0);
	s.led_ops = (u8)(2 * nsect);
	ring_push(PSC_RING_S, &s);
	if (write) st_ms_seg_wr++; else st_ms_seg_rd++;
	if (err) st_ms_err++;
}

static void io_time(u32 bytes)
{
	advance((u64)bytes * 1000000ull / ((u64)C.speed_kbs * 1024ull));
}

static int meta_write(u32 rel, int cls)
{
	int f;
	io_time(512);
	f = fault(cls, PART + rel);
	s_record(PART + rel, 1, 1, f, 1);
	return f;
}

static int dir_write(int sec)
{
	int k, f = meta_write(clus_sec(DIR_CLUS) + (u32)sec, SC_DIR);
	if (f) {
		dbuf_uptodate[sec] = 0;		/* re-read from the stick (fs/buffer.c:1378) */
	} else {
		for (k = 0; k < 16; k++)
			ddisk[sec * 16 + k] = dbuf[sec * 16 + k];
	}
	dbuf_dirty[sec] = 0;
	return f;
}

/* ---------------------------------------------------------------- fds */
enum { FK_NONE, FK_RING, FK_STATS, FK_CTL, FK_TEXT, FK_FILE, FK_DIR, FK_PROCDIR, FK_FB, FK_MICE, FK_KMSG };
struct sfd { int kind, ring, ino, alias, done; u32 pos; char text[1024]; int tlen; };
#define NFD 64
static struct sfd FD[NFD];
static int last_err;
static int fb_writes_tick, fb_bad;
static u32 kmsg_given;

static int fd_alloc(int kind)
{
	int i;
	for (i = 3; i < NFD; i++)
		if (FD[i].kind == FK_NONE) {
			memset(&FD[i], 0, sizeof(FD[i]));
			FD[i].kind = kind;
			return i;
		}
	last_err = 24;
	return -1;
}

int os_errno(void) { return last_err; }
int os_getpid(void) { return WPID; }
int os_getppid(void) { return SUPPID; }
void os_reap(void) { }

static void text_fd(int fd, const char *t)
{
	strncpy(FD[fd].text, t, sizeof(FD[fd].text) - 1);
	FD[fd].tlen = (int)strlen(FD[fd].text);
}

int os_open(const char *path, int flags)
{
	int fd, r;
	static const char *rp[PSC_NRINGS] = { PSC_PROC_P, PSC_PROC_POLL, PSC_PROC_W, PSC_PROC_S, PSC_PROC_M };
	for (r = 0; r < PSC_NRINGS; r++)
		if (!strcmp(path, rp[r])) {
			fd = fd_alloc(FK_RING);
			if (fd >= 0) FD[fd].ring = r;
			return fd;
		}
	if (!strcmp(path, PSC_PROC_STATS)) return fd_alloc(FK_STATS);
	if (!strcmp(path, PSC_PROC_CTL)) return fd_alloc(FK_CTL);
	if (!strcmp(path, "/proc/kmsg")) return fd_alloc(FK_KMSG);
	if (!strcmp(path, "/proc")) return fd_alloc(FK_PROCDIR);
	if (!strcmp(path, PSC_LOG_DIR)) return fd_alloc(FK_DIR);
	if (!strncmp(path, "/proc/", 6)) {
		char b[512];
		fd = fd_alloc(FK_TEXT);
		if (fd < 0) return -1;
		if (!strcmp(path, "/proc/uptime"))
			snprintf(b, sizeof(b), "%u.%02u 1.00\n", (unsigned)(now_us / 1000000), (unsigned)(now_us / 10000 % 100));
		else if (!strcmp(path, "/proc/meminfo"))
			snprintf(b, sizeof(b), "MemTotal:        24000 kB\nMemFree:         20800 kB\n");
		else if (!strcmp(path, "/proc/mounts"))
			snprintf(b, sizeof(b), "rootfs / rootfs rw 0 0\nproc /proc proc rw 0 0\n/dev/ms0 /ms0 vfat rw,fmask=0022,dmask=0022 0 0\n");
		else if (!strcmp(path, "/proc/version"))
			snprintf(b, sizeof(b), "%s", sim_version());
		else if (!strcmp(path, "/proc/30/stat"))
			snprintf(b, sizeof(b), "30 (swapper) S 1 1 1 0 -1 0\n");
		else if (!strcmp(path, "/proc/30/status"))
			snprintf(b, sizeof(b), "Name:\tswapper\nState:\tS (sleeping)\nSigPnd:\t00000000\nShdPnd:\t00000000\n");
		else if (!strcmp(path, "/proc/40/stat"))
			snprintf(b, sizeof(b), "40 (psposk2) S 1 1 1 0 -1 0\n");
		else if (!strcmp(path, "/proc/41/stat"))
			snprintf(b, sizeof(b), "41 (pspmd) S 1 1 1 0 -1 0\n");
		else if (!strcmp(path, "/proc/5/stat"))
			snprintf(b, sizeof(b), "5 (pdflush) S 2 0 0 0 -1 0\n");
		else if (!strcmp(path, "/proc/50/stat"))
			snprintf(b, sizeof(b), "50 (pscol) S 49 1 1 0 -1 0\n");
		else if (!strcmp(path, "/proc/49/stat"))
			snprintf(b, sizeof(b), "49 (pscol) S 1 1 1 0 -1 0\n");
		else if (!strcmp(path, "/proc/1/stat"))
			snprintf(b, sizeof(b), "1 (init) S 0 1 1 0 -1 0\n");
		else {
			FD[fd].kind = FK_NONE;
			last_err = OS_ENOENT;
			return -1;
		}
		text_fd(fd, b);
		return fd;
	}
	if (!strncmp(path, PSC_LOG_DIR "/", sizeof(PSC_LOG_DIR))) {
		const char *nm = path + sizeof(PSC_LOG_DIR);
		int slot, i, ii;
		if (!(flags & OS_O_CREAT_EXCL)) { last_err = OS_ENOENT; return -1; }
		dir_refresh();
		for (i = 0; i < DIR_SLOTS; i++)	/* vfat lookups ignore case */
			if (dbuf[i].used && dbuf[i].kind == 0 &&
			    (!strcasecmp(dbuf[i].name, nm) || (dbuf[i].lname[0] && !strcasecmp(dbuf[i].lname, nm)))) {
				last_err = OS_EEXIST;
				return -1;
			}
		for (slot = 0; slot < DIR_SLOTS; slot++)
			if (!dbuf[slot].used)
				break;
		if (slot == DIR_SLOTS) { last_err = 28; return -1; }
		memset(&dbuf[slot], 0, sizeof(dbuf[slot]));
		dbuf[slot].used = 1;
		strncpy(dbuf[slot].name, nm, 12);	/* upper-case 8.3: one short entry */
		dbuf_dirty[slot / 16] = 1;
		fd = fd_alloc(FK_FILE);
		if (fd < 0) return -1;
		ii = icache[slot];
		if (ii >= 0) {
			FD[fd].ino = ii;
			FD[fd].alias = 1;		/* fat_iget returned the cached inode */
			return fd;
		}
		if (ninode >= NINODE) { last_err = 12; return -1; }
		ii = ninode++;
		memset(&IN[ii], 0, sizeof(IN[ii]));
		IN[ii].used = 1;
		IN[ii].ino = next_ino++;
		IN[ii].slot = slot;
		IN[ii].nnn = atoi(nm + 4);
		IN[ii].cache = calloc(NSEC_FILE, 512);
		IN[ii].disk = calloc(NSEC_FILE, 512);
		IN[ii].dirty = calloc(NSEC_FILE, 1);
		IN[ii].regs = calloc(8192, sizeof(struct reg));
		icache[slot] = ii;
		FD[fd].ino = ii;
		return fd;
	}
	last_err = OS_ENOENT;
	return -1;
}

int os_close(int fd) { if (fd >= 0 && fd < NFD) FD[fd].kind = FK_NONE; return 0; }

static void build_stats(struct psc_stats *st)
{
	u32 t = tick_now(), lim, r;
	memset(st, 0, sizeof(*st));
	st->magic = PSC_STATS_MAGIC;
	st->version_size = PSC_STATS_VERSION_SIZE;
	/* word 2 (R-4): the kernel's CRC-32 of linux_banner, unless a test
	 * gives the value (packaged banner) or asks for a mismatch */
	if (C.version && C.build_id)
		st->build_id = C.build_id;
	else
		st->build_id = psc_crc32(0, sim_version(), strlen(sim_version()));
	if (C.bad_build_id)
		st->build_id ^= 0x00010000u;
	st->hz = PSC_HZ;
	st->counts_per_tick = PSC_CPT;
	st->last_reader_tick = st_last_reader;
	st->now_tick = t;
	st->now_count = count_now();
	st->now_jiffies = t + 1000;
	st->total_counts_lo = (u32)(now_us * 221ull);
	for (r = 0; r < PSC_NRINGS; r++) {
		st->head[r] = R[r].head;
		st->durable_next[r] = ctl_durable_next[r];
		st->slot_bad[r] = st_slot_bad[r];
	}
	st->jp_pid = 30;
	st->jp_loop = st_jp_loop;
	st->p_rec_cost_last = 180;
	st->ms_seg_wr = st_ms_seg_wr;
	st->ms_seg_rd = st_ms_seg_rd;
	st->ms_err = st_ms_err;
	st->durable_tick = ctl_durable_tick;
	st->ctl_writes = st_ctl_writes;
	st->head_regress = st_head_regress;
	st->ring_rewinds = st_ring_rewinds;
	st->meta_sector = ctl_meta;
	/* panel test: one paint per second at ticks = 125 mod 250 (2.10) */
	lim = t < panel_until ? t : panel_until;
	while (panel_chk < lim) {
		panel_chk++;
		if (panel_chk % 250 == 125)
			panel_done++;
	}
	if (panel_chk < t && t >= panel_until) panel_chk = t;
	st->panel_test_seq = ctl_panel_seq;
	st->panel_test_done = panel_done;
	st->ms_part_start = PART;
	st->fat_start = FAT_START;
	st->fat_length = FAT_LEN;
	st->fats = 2;
	st->fsinfo_sector = FSINFO_SEC;
	st->data_start = DATA_START;
	st->sec_per_clus_bits = SPC | (9u << 16);
}

static void file_alloc_to(struct sinode *I, int ii, u32 end)
{
	while ((u32)I->nclus * CL < end && I->nclus < MAXCLUS) {
		u32 c = next_clus++, fs = c / 128;
		int k;
		for (k = 0; k < I->nclus; k++)
			if (I->link_missing[k])
				viol("extend after failed allocating step", I->ino, (u32)k);
		I->clus[I->nclus] = c;
		I->link_missing[I->nclus] = 0;
		fat_dirty[fs] = 1;
		if (npfat < 4096) { pfat[npfat].ino_idx = ii; pfat[npfat].ci = I->nclus; pfat[npfat].fsec = fs; npfat++; }
		if (I->nclus > 0) {
			u32 ps = I->clus[I->nclus - 1] / 128;
			fat_dirty[ps] = 1;
		}
		I->nclus++;
	}
}

static void region_check(struct sinode *I, u32 a, u32 b, int kind)
{
	int i;
	for (i = 0; i < I->nreg; i++) {
		struct reg *g = &I->regs[i];
		int ov = a < g->b && g->a < b;
		if (!ov)
			continue;
		if (kind == K_FLUSH && (g->kind == K_FLUSH || g->kind == K_STEP0))
			viol("flush region written twice", a, g->a);
		if (kind == K_STEP && g->kind == K_FLUSH)
			viol("step over a flush region", a, g->a);
	}
	if (kind == K_FLUSH && (a % 512 || b - a > PSC_FLUSH_MAX || (b - a) % 512))
		viol("flush not sector aligned or over 40,960 B", a, b - a);
	if (I->nreg < 8192) {
		I->regs[I->nreg].a = a;
		I->regs[I->nreg].b = b;
		I->regs[I->nreg].kind = kind;
		I->nreg++;
	}
}

static int file_write(int fd, const void *buf, u32 len, int kind)
{
	struct sinode *I = &IN[FD[fd].ino];
	u32 a = FD[fd].pos, b = a + len, s;
	int k;
	if (FD[fd].alias)
		viol("alias written", I->ino, a);
	if (kind != K_STEP && a == 0 && len == PSC_FILEHDR_AREA)
		kind = K_STEP0;
	if (kind == K_FLUSH) {
		nflush_writes++;
		for (k = 0; k < C.nfail_flush; k++)
			if (C.fail_flush[k] == nflush_writes)
				cur_fail_data = 1;	/* this flush's DATA writes fail */
	}
	if (kind == K_FLUSH && b > I->i_size)
		viol("flush extends the file", a, b);
	if (kind == K_FLUSH)
		for (k = (int)(a / CL); k <= (int)((b - 1) / CL) && k < I->nclus; k++)
			if (I->link_missing[k])
				viol("flush over a missing link", a, (u32)k);
	if (b > (u32)NSEC_FILE * 512) { last_err = 27; return -1; }
	region_check(I, a, b, kind);
	if (kind == K_STEP0) {
		nstep0_writes++;
		if (C.burst_on_step0 && nstep0_writes == C.burst_on_step0) {
			dyn_b0 = now_us;
			dyn_b1 = now_us + C.burst_on_step0_us;
		}
	}
	file_alloc_to(I, FD[fd].ino, b);
	memcpy(I->cache + a, buf, len);
	for (s = a / 512; s < (b + 511) / 512; s++)
		I->dirty[s] = 1;
	if (b > I->i_size)
		I->i_size = b;
	I->entry_dirty = 1;
	FD[fd].pos = b;
	return (int)len;
}

int os_write(int fd, const void *buf, int len)
{
	if (fd < 0 || fd >= NFD) { last_err = 9; return -1; }
	if (FD[fd].kind == FK_FB) {
		if (FD[fd].pos / 2048 >= 176 || FD[fd].pos % 2048)
			fb_bad++;
		fb_writes_tick++;
		return len;
	}
	if (FD[fd].kind == FK_FILE)
		return file_write(fd, buf, (u32)len, K_FLUSH);
	last_err = 9;
	return -1;
}

int os_writev_rep(int fd, const void *buf, int unit, u32 total)
{
	static u8 tmp[65536 + 4096];
	u32 o = 0;
	if (FD[fd].kind != FK_FILE || total > sizeof(tmp)) { last_err = 22; return -1; }
	while (o < total) {
		u32 l = total - o < (u32)unit ? total - o : (u32)unit;
		memcpy(tmp + o, buf, l);
		o += l;
	}
	nwritev++;
	cur_fail_data = 0;
	{
		int i;
		for (i = 0; i < C.nfail_step; i++)
			if (C.fail_step[i] == nwritev)
				cur_fail_data = 1;
	}
	if (C.burst_at_step && nwritev == C.burst_at_step) {
		dyn_b0 = now_us;
		dyn_b1 = now_us + C.burst_at_step_us;
	}
	return file_write(fd, tmp, total, K_STEP);
}

int os_ctl_write(int fd, const struct psc_ctl *c)
{
	int r;
	(void)fd;
	st_ctl_writes++;
	switch (c->op) {
	case PSC_CTL_OP_DURABLE:
		ctl_durable_tick = c->arg[0];
		for (r = 0; r < PSC_NRINGS; r++)
			ctl_durable_next[r] = c->arg[1 + r];
		return 32;
	case PSC_CTL_OP_CLASS:
		return 32;
	case PSC_CTL_OP_PANEL_TEST:
		ctl_panel_seq++;
		if (panel_chk < tick_now()) panel_chk = tick_now();
		panel_until = tick_now() + 250 * c->arg[0];
		return 32;
	case PSC_CTL_OP_META:
		ctl_meta = c->arg[0];
		return 32;
	}
	last_err = 22;
	return -1;
}

int os_read(int fd, void *buf, int len)
{
	struct sfd *f;
	int n;
	if (fd < 0 || fd >= NFD) { last_err = 9; return -1; }
	f = &FD[fd];
	switch (f->kind) {
	case FK_RING:
		return ring_read(f->ring, &f->pos, buf, len, 1);
	case FK_TEXT:
		n = f->tlen - (int)f->pos;
		if (n > len) n = len;
		if (n < 0) n = 0;
		memcpy(buf, f->text + f->pos, (size_t)n);
		f->pos += (u32)n;
		return n;
	case FK_KMSG:
		if (!kmsg_given) {
			const char *m = "<4>PSC5 P4096 POLL2048 W256 S4096 M64 bootnop ret=4 nw=2 rx2=00\n";
			kmsg_given = 1;
			n = (int)strlen(m);
			if (n > len) n = len;
			memcpy(buf, m, (size_t)n);
			return n;
		}
		last_err = OS_EAGAIN;
		return -1;
	case FK_MICE:
		last_err = OS_EAGAIN;
		return -1;
	}
	last_err = 9;
	return -1;
}

int os_pread(int fd, void *buf, int len, u32 off)
{
	struct sfd *f;
	if (fd < 0 || fd >= NFD) { last_err = 9; return -1; }
	f = &FD[fd];
	if (f->kind == FK_RING) {
		u32 p = off;
		return ring_read(f->ring, &p, buf, len, 1);
	}
	if (f->kind == FK_STATS) {
		struct psc_stats st;
		build_stats(&st);
		if (off != 0 || len < (int)sizeof(st)) { last_err = 22; return -1; }
		memcpy(buf, &st, sizeof(st));
		return (int)sizeof(st);
	}
	if (f->kind == FK_FILE) {
		struct sinode *I = &IN[f->ino];
		if (off + (u32)len > I->i_size) len = (int)(I->i_size - off);
		if (I->dropped) {		/* page dropped by fadvise: read from the stick */
			u32 rel = clus_sec(I->clus[off / CL]) + (off % CL) / 512;
			io_time(512);
			s_record(PART + rel, 1, 0, 0, 0);
			memcpy(buf, I->disk + off, (size_t)len);
			I->dropped = 0;
		} else {
			memcpy(buf, I->cache + off, (size_t)len);
		}
		return len;
	}
	last_err = 9;
	return -1;
}

s32 os_lseek(int fd, s32 off, int whence)
{
	struct sfd *f;
	if (fd < 0 || fd >= NFD) { last_err = 9; return -1; }
	f = &FD[fd];
	if (whence == 1)
		return (s32)(f->pos + (u32)off);
	if (f->kind == FK_RING) {
		if ((u32)off % R[f->ring].size) { last_err = 22; return -1; }
		if ((u32)off < f->pos)
			st_ring_rewinds++;
	}
	f->pos = (u32)off;
	return off;
}

int os_fsync(int fd)
{
	struct sinode *I;
	u32 s, nsec;
	int err = 0, k, sec;
	if (fd < 0 || fd >= NFD || FD[fd].kind != FK_FILE) { last_err = 9; return -1; }
	I = &IN[FD[fd].ino];
	if (C.stall_s && !stall_done && now_us >= (u64)C.stall_at_s * 1000000ull) {
		stall_done = 1;			/* one fsync stalls; the stick refuses meanwhile */
		dyn_b0 = now_us;
		advance((u64)C.stall_s * 1000000ull);
		dyn_b1 = now_us + (u64)C.stall_fail_ms * 1000ull;
	}
	io_time(1024);					/* 1 KB per fsync (15.6 model) */
	/* data: page runs of <= 8 sectors (fs/mpage.c) */
	nsec = (I->i_size + 511) / 512;
	for (s = 0; s < nsec; ) {
		u32 n = 0, rel;
		int f;
		if (!I->dirty[s]) { s++; continue; }
		while (s + n < nsec && I->dirty[s + n] && n < 8 && (s + n) / 8 == s / 8)
			n++;
		rel = clus_sec(I->clus[(s * 512) / CL]) + (s % SPC);
		io_time(512 * n);
		f = fault(SC_DATA, PART + rel);
		s_record(PART + rel, (int)n, 1, f, 0);
		if (f) err = 1;
		else memcpy(I->disk + (size_t)s * 512, I->cache + (size_t)s * 512, (size_t)n * 512);
		for (k = 0; k < (int)n; k++) I->dirty[s + k] = 0;
		s += n;
	}
	/* the file's own entry, written at once (fat_write_inode, sync) */
	if (I->entry_dirty && !FD[fd].alias) {
		int slot = I->slot;
		dir_refresh();
		dbuf[slot].size = I->i_size;
		dbuf[slot].start = I->nclus ? I->clus[0] : 0;
		if (dir_write(slot / 16)) err = 1;
		I->entry_dirty = 0;
	}
	/* FSINFO on every fsync, then sync_blockdev: FAT1, mirror, other dirs */
	if (meta_write(FSINFO_SEC, SC_FSINFO)) err = 1;
	for (k = 0; k < (int)FAT_LEN; k++)
		if (fat_dirty[k]) {
			int i, f1 = meta_write(FAT_START + (u32)k, SC_FAT1);
			if (f1) {
				err = 1;
				for (i = 0; i < npfat; i++)
					if (pfat[i].fsec == (u32)k && pfat[i].ino_idx >= 0)
						IN[pfat[i].ino_idx].link_missing[pfat[i].ci] = 1;
			}
			for (i = 0; i < npfat; i++)
				if (pfat[i].fsec == (u32)k)
					pfat[i].ino_idx = -1;
			if (meta_write(FAT_START + FAT_LEN + (u32)k, SC_FATM)) err = 1;
			fat_dirty[k] = 0;
		}
	for (sec = 0; sec < DIR_SECS; sec++)
		if (dbuf_dirty[sec] && dbuf_uptodate[sec])
			if (dir_write(sec)) err = 1;
	{
		int j = 0, i;
		for (i = 0; i < npfat; i++)
			if (pfat[i].ino_idx >= 0) pfat[j++] = pfat[i];
		npfat = j;
	}
	cur_fail_data = 0;
	if (err) { last_err = OS_EIO; return -1; }
	return 0;
}

int os_fstat(int fd, u32 *size, u32 *ino, u32 *blksize)
{
	if (fd < 0 || fd >= NFD || FD[fd].kind != FK_FILE) { last_err = 9; return -1; }
	*size = IN[FD[fd].ino].i_size;
	*ino = IN[FD[fd].ino].ino;
	*blksize = CL;
	return 0;
}

int os_stat(const char *path, u32 *size, int *isdir)
{
	if (!strcmp(path, PSC_LOG_DIR)) { *size = C.dir_bytes ? C.dir_bytes : CL; *isdir = 1; return 0; }
	last_err = OS_ENOENT;
	return -1;
}
int os_mkdir(const char *path) { (void)path; return 0; }

int os_fibmap(int fd, u32 *blk)
{
	struct sinode *I;
	if (fd < 0 || fd >= NFD || FD[fd].kind != FK_FILE) { last_err = 9; return -1; }
	I = &IN[FD[fd].ino];
	if (*blk * 512 >= (u32)I->nclus * CL) { *blk = 0; return 0; }
	*blk = clus_sec(I->clus[*blk / SPC]) + *blk % SPC;
	return 0;
}

int os_fadvise_dontneed(int fd, u32 off, u32 len)
{
	(void)off; (void)len;
	if (fd < 0 || fd >= NFD || FD[fd].kind != FK_FILE) { last_err = 9; return -1; }
	IN[FD[fd].ino].dropped = 1;
	return 0;
}

static int put_dirent(char *b, int off, int len, u32 ino, const char *nm)
{
	int n = (int)strlen(nm), rl = (10 + n + 1 + 3) & ~3;
	if (off + rl > len) return -1;
	*(u32 *)(b + off) = ino;
	*(u32 *)(b + off + 4) = 0;
	*(u16 *)(b + off + 8) = (u16)rl;
	memcpy(b + off + 10, nm, (size_t)n + 1);
	return off + rl;
}

/* vfat readdir of PSCLOG under shortname=lower (fs/fat/dir.c:434-640 with
 * fs/readdir.c:136-212): a short entry with no long name is shown in lower
 * case, one with a long name by the long name; each dirent's d_off is the
 * first slot of the next entry (lpos), the last one's the directory position
 * where the scan stopped; the scan resumes there on the next call */
static int sim_readdir(struct sfd *f, char *buf, int len)
{
	int off = 0, prev = -1, i, k, n;
	u32 p = f->pos / 32;
	dir_refresh();
	while (p < DIR_SLOTS) {
		char disp[48];
		u32 st = p;
		if (!dbuf[p].used) { p++; f->pos = p * 32; continue; }
		while (p < DIR_SLOTS && dbuf[p].used && dbuf[p].kind == 1)
			p++;			/* long-name slots before the short entry */
		if (p >= DIR_SLOTS) break;
		if (dbuf[p].lname[0]) {
			strcpy(disp, dbuf[p].lname);
		} else {
			for (k = 0; dbuf[p].name[k]; k++) {
				char c = dbuf[p].name[k];
				disp[k] = (c >= 'A' && c <= 'Z') ? (char)(c + 32) : c;
			}
			disp[k] = 0;
		}
		n = put_dirent(buf, off, len, 200 + p, disp);
		if (n < 0)
			break;			/* f_pos stays at st: the next call starts here */
		if (prev >= 0)
			*(u32 *)(buf + prev + 4) = st * 32;
		prev = off;
		off = n;
		p++;
		f->pos = p * 32;
	}
	if (prev >= 0)
		*(u32 *)(buf + prev + 4) = f->pos;	/* fs/readdir.c:206 */
	(void)i;
	return off;
}

int os_getdents(int fd, void *buf, int len)
{
	struct sfd *f;
	int off = 0, i, n;
	if (fd < 0 || fd >= NFD) { last_err = 9; return -1; }
	f = &FD[fd];
	if (f->kind == FK_DIR)
		return sim_readdir(f, buf, len < C_getdents_max ? len : C_getdents_max);
	if (f->done)
		return 0;
	f->done = 1;
	if (f->kind == FK_PROCDIR) {
		static const char *p[] = { "1", "5", "30", "40", "41", "49", "50", "self", "uptime", "meminfo" };
		for (i = 0; i < (int)(sizeof(p) / sizeof(p[0])); i++)
			if ((n = put_dirent(buf, off, len, 100 + (u32)i, p[i])) > 0) off = n;
		return off;
	}
	last_err = 20;
	return -1;
}

int os_syslog(int type, char *buf, int len)
{
	(void)buf; (void)len;
	return type == 3 ? 1606 : 0;
}

void os_gettimeofday(u32 *sec, u32 *usec)
{
	*sec = (u32)(1700000000ull + now_us / 1000000ull);
	*usec = (u32)(now_us % 1000000ull);
}

void os_sleep_ms(int ms) { advance((u64)ms * 1000ull); }
int os_fb_stride(int fd) { (void)fd; return 2048; }
int os_open_fb(void) { return C.fb ? fd_alloc(FK_FB) : -1; }
int os_open_mice(void) { return fd_alloc(FK_MICE); }

/* every EVENT line the worker emits (pscol.c ev()) */
static char evlog[1 << 20];
static int evlog_len;
#define NEVT 8192
static u64 evt_us[NEVT];
static u32 evt_tick[NEVT], sim_tickno;
static int evt_off[NEVT], nevt;
void pscol_ev_hook(const char *s, int len)
{
	if (nevt < NEVT && evlog_len + len + 2 < (int)sizeof(evlog)) {
		evt_us[nevt] = now_us;
		evt_tick[nevt] = sim_tickno;
		evt_off[nevt] = evlog_len;
		nevt++;
	}
	if (evlog_len + len + 2 < (int)sizeof(evlog)) {
		memcpy(evlog + evlog_len, s, (size_t)len);
		evlog_len += len;
		evlog[evlog_len++] = '\n';
		evlog[evlog_len] = 0;
	}
	if (!C.quiet)
		printf("    [%8.2fs] EVENT %.*s\n", now_us / 1e6, len, s);
}
static int ev_count(const char *prefix)
{
	int n = 0;
	const char *p = evlog;
	size_t l = strlen(prefix);
	while (p && *p) {
		if (!strncmp(p, prefix, l)) n++;
		p = strchr(p, '\n');
		if (p) p++;
	}
	return n;
}

/* ---------------------------------------------------------------- reset */
static void sim_reset(void)
{
	int r, i;
	static const u32 n[PSC_NRINGS] = { PSC_P_ENTRIES, PSC_POLL_ENTRIES, PSC_W_ENTRIES, PSC_S_ENTRIES, PSC_M_ENTRIES };
	static const u32 sz[PSC_NRINGS] = { PSC_P_SIZE, PSC_POLL_SIZE, PSC_W_SIZE, PSC_S_SIZE, PSC_M_SIZE };
	for (i = 0; i < ninode; i++) {
		free(IN[i].cache); free(IN[i].disk); free(IN[i].dirty); free(IN[i].regs);
	}
	memset(IN, 0, sizeof(IN));
	ninode = 0;
	next_ino = 1000;
	next_clus = 3;
	for (r = 0; r < PSC_NRINGS; r++) {
		free(R[r].slots);
		R[r].n = n[r];
		R[r].size = sz[r];
		R[r].slots = calloc(n[r], sz[r]);
		for (i = 0; i < (int)n[r]; i++)
			*(u32 *)(R[r].slots + (size_t)i * sz[r]) = 0xFFFFFFFFu;	/* never written */
		R[r].head = 0;
		st_slot_bad[r] = 0;
		ctl_durable_next[r] = 0;
	}
	st_head_regress = st_ring_rewinds = st_last_reader = 0;
	st_ms_seg_wr = st_ms_seg_rd = st_ms_err = st_ctl_writes = st_jp_loop = 0;
	ctl_durable_tick = ctl_meta = ctl_panel_seq = 0;
	panel_until = panel_done = panel_chk = 0;
	memset(ddisk, 0, sizeof(ddisk));
	ddisk[0].used = 1; strcpy(ddisk[0].name, ".");
	ddisk[1].used = 1; strcpy(ddisk[1].name, "..");
	memset(dbuf_uptodate, 0, sizeof(dbuf_uptodate));
	memset(dbuf_dirty, 0, sizeof(dbuf_dirty));
	for (i = 0; i < DIR_SLOTS; i++) icache[i] = -1;
	memset(fat_dirty, 0, sizeof(fat_dirty));
	npfat = 0;
	memset(FD, 0, sizeof(FD));
	now_us = 0;
	next_poll_us = 3000000ull;		/* thread starts at 3 s (15.6) */
	next_wd_tick = PSC_WD_CYCLE;
	nprod_p = 0;
	dyn_b0 = dyn_b1 = 0;
	nstep0_writes = nwritev = cur_fail_data = nflush_writes = stall_done = 0;
	C_getdents_max = 1 << 30;
	nviol = 0;
	viol_first[0] = 0;
	evlog_len = 0;
	evlog[0] = 0;
	nevt = 0;
	sim_tickno = 0;
	kmsg_given = 0;
	fb_bad = 0;
	free(pois);
	pois = 0;
	npois = 0;
	dir_refuse_sec = -1;
}

/* ---------------------------------------------------------------- end check */
struct result {
	int	missing[PSC_NRINGS];
	u32	dn[PSC_NRINGS], head[PSC_NRINGS];
	int	viol, boot_ok;
	u32	max_hold_ms, dur_age_end_ms, worker_lost;
	int	files_with_recs, chunks_ok, chunks_bad, ntype[PSC_CHUNK_NTYPES];
	u32	recs_max, flush_max;
	u32	write_errs, st_pass, st_bits;
	int	ev_flushfail, ev_abandon, ev_alias, ev_stop, ev_resend_lost;
	u32	recov_ms;			/* burst end -> next fresh file CONFIRMED */
	int	same_file_hold;
};

static void decode_check(struct result *res, u32 nonce)
{
	static u8 *seen[PSC_NRINGS];
	int r, i;
	for (r = 0; r < PSC_NRINGS; r++) {
		free(seen[r]);
		seen[r] = calloc(R[r].head + 1, 1);
	}
	for (i = 0; i < ninode; i++) {
		struct sinode *I = &IN[i];
		u32 off = 0;
		int recs = 0;
		while (off + 20 <= I->i_size) {
			const struct psc_chunk_hdr *h = (const struct psc_chunk_hdr *)(I->disk + off);
			u32 tot, crc;
			if (memcmp(h->magic, "PSCK", 4) || h->type >= PSC_CHUNK_NTYPES || h->len > 65536) { off += 4; continue; }
			tot = 20 + ((h->len + 3) & ~3u);
			if (off + tot > I->i_size) { off += 4; continue; }
			crc = psc_crc32(h->type == PSC_CHUNK_FILEHDR ? 0 : nonce, I->disk + off + 20, h->len);
			if (crc != h->crc) { res->chunks_bad++; off += 4; continue; }
			res->chunks_ok++;
			res->ntype[h->type]++;
			if (h->type == PSC_CHUNK_RECS && h->len + 20 > res->recs_max)
				res->recs_max = h->len + 20;
			if (h->type == PSC_CHUNK_RECS) {
				u32 p = off + 20, end = off + 20 + h->len;
				recs = 1;
				while (p + 8 <= end) {
					const struct psc_block_hdr *b = (const struct psc_block_hdr *)(I->disk + p);
					u32 rr = b->ring & PSC_BLK_RING_MASK, sz = (u32)b->recsize_div4 * 4, k;
					p += 8;
					for (k = 0; k < b->count && p + sz <= end; k++, p += sz) {
						u32 sq = *(const u32 *)(I->disk + p);
						if (rr < PSC_NRINGS && sq < R[rr].head)
							seen[rr][sq] = 1;
					}
				}
			}
			off += tot;
		}
		res->files_with_recs += recs;
	}
	for (r = 0; r < PSC_NRINGS; r++) {
		u32 s;
		res->dn[r] = ctl_durable_next[r];
		res->head[r] = R[r].head;
		res->missing[r] = 0;
		for (s = 0; s < ctl_durable_next[r] && s < R[r].head; s++)
			if (!seen[r][s])
				res->missing[r]++;
	}
	res->boot_ok = R[PSC_RING_W].head > 0 && seen[PSC_RING_W][0] && seen[PSC_RING_P][0] &&
		seen[PSC_RING_M][0];
}

static void poisson_init(u32 seed, int per30, double t0, double t1)
{
	double t = t0, rate = per30 / 1800.0;
	srand48(seed);
	pois = malloc(sizeof(double) * 4096);
	npois = 0;
	for (;;) {
		t += -log(1.0 - drand48()) / rate;
		if (t >= t1 || npois >= 4096) break;
		pois[npois++] = t;
	}
}

/* run one scenario; returns 0 on pass */
static int run(struct cfg *c, struct result *res, u32 *burst_end_us)
{
	struct pscol_tinfo ti;
	u64 hold_start = 0, end_us;
	u32 nonce = 0x5EED0000u ^ c->seed;
	int was_hold = 0, hold_nnn = -1, had_active = 0, hold_counts = 0;
	memset(res, 0, sizeof(*res));
	res->same_file_hold = 1;
	C = *c;
	sim_reset();
	boot_records();
	if (c->poisson_per_30min)
		poisson_init(c->seed, c->poisson_per_30min, c->worker_start_s + 1.0, c->end_s);
	if (c->dir_refuse_from_s)
		dir_refuse_sec = 0;
	advance((u64)c->worker_start_s * 1000000ull);
	if (c->pre)
		dir_prepopulate(c->pre);
	worker_init(PSC_INST_WORKER, c->run ? c->run : 1, nonce, 0, 0);
	end_us = (u64)c->end_s * 1000000ull;
	while (now_us < end_us) {
		fb_writes_tick = 0;
		sim_tickno++;
		worker_tick();
		if (C.fb && fb_writes_tick != 272)
			viol("fb writes per tick != 272", (u32)fb_writes_tick, 0);
		pscol_tinfo(&ti);
		if (ti.holding && !was_hold) { hold_start = now_us; hold_nnn = ti.active_nnn; hold_counts = had_active; }
		if (ti.holding && ti.active_nnn != hold_nnn && hold_nnn >= 0 && ti.active_nnn >= 0)
			res->same_file_hold = 0;
		if (ti.active_nnn >= 0 && !had_active) had_active = 1;
		if (!ti.holding && was_hold && hold_counts) {
			u32 ms = (u32)((now_us - hold_start) / 1000);
			if (ms > res->max_hold_ms) res->max_hold_ms = ms;
		}
		if (ti.holding && now_us - hold_start > 114700000ull && hold_start)
			viol("hold over 114.7 s", (u32)((now_us - hold_start) / 1000), 0);
		was_hold = ti.holding;
		if (C.trace && now_us < (u64)(c->worker_start_s + C.trace) * 1000000ull)
			printf("    [%8.2fs] tick hold=%d active=%d creating=%d seg_end=%u usable=%u errs=%u\n",
			       now_us / 1e6, ti.holding, ti.active_nnn, ti.creating_nnn, ti.active_seg_end,
			       ti.active_conf, ti.write_errs);
		advance(30000);			/* loop body (15.6: 0.23 s tick) */
		os_sleep_ms(TICK_SLEEP_MS);
	}
	pscol_tinfo(&ti);
	decode_check(res, nonce);
	res->viol = nviol;
	res->dur_age_end_ms = (u32)(((u64)tick_now() - ctl_durable_tick) * 4);
	res->worker_lost = ti.lost_total;
	res->write_errs = ti.write_errs;
	res->st_pass = (u32)ti.st_pass;
	res->st_bits = ti.st_bits;
	res->ev_flushfail = ev_count("flush fail");
	res->ev_abandon = ev_count("abandon");
	res->ev_alias = ev_count("inode reused");
	res->ev_stop = ev_count("stop");
	if (burst_end_us) *burst_end_us = (u32)(dyn_b1 / 1000);
	{
		int r, miss = 0;
		for (r = 0; r < PSC_NRINGS; r++) miss += res->missing[r];
		/* the durable point must also keep up: at most 5 s behind at the end */
		return (miss || nviol || !res->boot_ok || res->worker_lost || res->dur_age_end_ms > 5000) ? 1 : 0;
	}
}

static void print_res(const char *name, const struct result *res, int fail)
{
	printf("  %-44s %s  missing P/POLL/W/S/M=%d/%d/%d/%d/%d  durable_next P=%u/head %u  "
	       "viol=%d%s%s boot=%s lost=%u errs=%u flushfail=%d abandon=%d alias=%d stop=%d "
	       "maxhold=%.1fs dur_age_end=%.1fs selftest=%s(%03x)\n",
	       name, fail ? "FAIL" : "PASS",
	       res->missing[0], res->missing[1], res->missing[2], res->missing[3], res->missing[4],
	       res->dn[0], res->head[0], res->viol, res->viol ? " first=" : "", res->viol ? viol_first : "",
	       res->boot_ok ? "ok" : "BAD", res->worker_lost, res->write_errs, res->ev_flushfail,
	       res->ev_abandon, res->ev_alias, res->ev_stop, res->max_hold_ms / 1000.0,
	       res->dur_age_end_ms / 1000.0, res->st_pass ? "PASS" : "no", res->st_bits);
}

/* the first "segment create" after t0 whose file is not abandoned later:
 * returns its time (us) or 0 */
static u64 fresh_create_after(u64 t0)
{
	int i, j;
	for (i = 0; i < nevt; i++) {
		const char *l = evlog + evt_off[i], *nm;
		if (evt_us[i] < t0 || strncmp(l, "segment create ", 15))
			continue;
		nm = l + 15;
		for (j = i + 1; j < nevt; j++) {
			const char *m = evlog + evt_off[j];
			if (!strncmp(m, "abandon ", 8) && !strncmp(m + 8, nm, 11))
				break;
		}
		if (j == nevt)
			return evt_us[i];
	}
	return 0;
}

int vectors_main(void);
int hud_test_main(void);

static int test_burst_step0(void)
{
	struct cfg c;
	struct result res;
	int fails = 0, which, sp;
	static const u32 speeds[] = { 25, 52, 100, 300 };
	printf("TEST burst3s_step0: a 3 s whole-stick write-error burst starting at the FILEHDR write of a creation "
	       "(4.4 steps 0-1, 6; A5-1): #1 = the first file at start-up, #3 = a later file mid-run\n");
	for (which = 1; which <= 3; which += 2) {
		for (sp = 0; sp < 4; sp++) {
			u32 bend = 0;
			u64 fresh;
			char nm[80];
			int f;
			memset(&c, 0, sizeof(c));
			c.speed_kbs = speeds[sp];
			c.worker_start_s = 30;
			c.end_s = 30 + 900;
			c.seed = 7;
			c.quiet = 1;
			c.burst_on_step0 = which;
			c.burst_on_step0_us = 3000000ull;
			c.press_at_s = 120;
			f = run(&c, &res, &bend);
			fresh = fresh_create_after(dyn_b0 + 1);
			if (res.ev_abandon < 1) {
				printf("    expected an abandon EVENT for the burst-hit step 0, saw none\n");
				f = 1;
			}
			if (!fresh || fresh > dyn_b1 + 10000000ull + 300000ull) {
				printf("    next fresh file not created within 10 s + 1 tick of recovery (%.2f s after)\n",
				       fresh ? (fresh - dyn_b1) / 1e6 : -1.0);
				f = 1;
			}
			snprintf(nm, sizeof(nm), "step0 #%d burst, %u KB/s (fresh +%.1fs)", which, speeds[sp],
				 fresh ? ((double)fresh - (double)dyn_b1) / 1e6 : -1.0);
			print_res(nm, &res, f);
			fails += f;
		}
	}
	return fails;
}

static int test_if4(int nseeds)
{
	struct cfg c;
	struct result res;
	static const u32 speeds[] = { 25, 52, 100, 300 };
	int sp, s, fails = 0;
	printf("TEST if4_sporadic: Poisson whole-tick write failures, 98 per 30 min, 30 min runs (A4/A5 IF4, 15.6), %d seeds per speed\n", nseeds);
	for (sp = 0; sp < 4; sp++) {
		int pf = 0, tot_missing = 0, tot_viol = 0, tot_errs = 0, pass_st = 0;
		u32 maxhold = 0;
		for (s = 0; s < nseeds; s++) {
			int f, r;
			memset(&c, 0, sizeof(c));
			c.speed_kbs = speeds[sp];
			c.worker_start_s = 40;
			c.end_s = 40 + 1800;
			c.seed = 1000u + (u32)s;
			c.quiet = 1;
			c.poisson_per_30min = 98;
			c.press_at_s = 150;
			f = run(&c, &res, 0);
			for (r = 0; r < PSC_NRINGS; r++) tot_missing += res.missing[r];
			tot_viol += res.viol;
			tot_errs += (int)res.write_errs;
			if (res.max_hold_ms > maxhold) maxhold = res.max_hold_ms;
			pass_st += res.st_pass ? 1 : 0;
			if (f) {
				char nm[80];
				snprintf(nm, sizeof(nm), "IF4 %u KB/s seed %d", speeds[sp], 1000 + s);
				print_res(nm, &res, f);
			}
			pf += f;
		}
		printf("  IF4 %3u KB/s: %d/%d runs PASS, records missing below durable_next %d, violations %d, "
		       "FAILED verdicts %d (avg %.1f/run), longest hold after start %.1f s, SELFTEST PASS in %d/%d\n",
		       speeds[sp], nseeds - pf, nseeds, tot_missing, tot_viol, tot_errs, (double)tot_errs / nseeds,
		       maxhold / 1000.0, pass_st, nseeds);
		fails += pf;
	}
	return fails;
}

static int test_te10(void)
{
	struct cfg c;
	struct result res;
	int fails = 0, v, sp;
	static const u32 speeds[] = { 25, 52, 100 };
	printf("TEST te10_hold_resume: worker starts with a 100 s backlog (catch-up, the active file still in creation); "
	       "(a) two failed creation steps, (b) a 3 s burst at a creation step (r7 TE10)\n");
	for (v = 0; v < 2; v++)
		for (sp = 0; sp < 3; sp++) {
			char nm[96];
			int f;
			memset(&c, 0, sizeof(c));
			c.speed_kbs = speeds[sp];
			c.worker_start_s = 100;
			c.end_s = 100 + 300;
			c.seed = 3;
			c.quiet = 1;
			if (v == 0) {
				c.nfail_step = 2;
				c.fail_step[0] = 2;
				c.fail_step[1] = 3;	/* the step and its first retry in place */
			} else {
				c.burst_at_step = 3;
				c.burst_at_step_us = 3000000ull;
			}
			f = run(&c, &res, 0);
			if (!res.same_file_hold) {
				printf("    hold switched files while the active file was in creation\n");
				f = 1;
			}
			snprintf(nm, sizeof(nm), "TE10 %s, %u KB/s", v == 0 ? "two failed steps" : "3 s burst", speeds[sp]);
			print_res(nm, &res, f);
			fails += f;
		}
	return fails;
}

static int test_if7b(void)
{
	struct cfg c;
	struct result res;
	int f;
	printf("TEST if7b_dir_sector: the first PSCLOG directory sector refuses every write from 60 s (IF7b, A6-1), 25 min run at 52 KB/s\n");
	memset(&c, 0, sizeof(c));
	c.speed_kbs = 52;
	c.worker_start_s = 30;
	c.end_s = 30 + 1500;
	c.seed = 11;
	c.quiet = 1;
	c.dir_refuse_from_s = 60;
	f = run(&c, &res, 0);
	{
		struct pscol_tinfo ti;
		int i, first = -1, nm_first = 0, nm = 0, creations = 0, maxper = 0, cur = 0;
		u64 t_first = 0, t_ok = 0;
		u32 k_first = 0, k_ok = 0;
		pscol_tinfo(&ti);
		/* names: every "segment create" and "inode reused" consumed one */
		for (i = 0; i < nevt; i++) {
			const char *l = evlog + evt_off[i];
			int isname = !strncmp(l, "segment create", 14) || !strncmp(l, "inode reused", 12);
			if (evt_us[i] < 60000000ull)
				continue;
			if (isname) { nm++; cur++; }
			if (first < 0 && isname) { first = i; t_first = evt_us[i]; k_first = evt_tick[i]; }
			if (!strncmp(l, "segment create", 14) && fresh_create_after(evt_us[i]) == evt_us[i]) {
				creations++;
				if (!t_ok) { t_ok = evt_us[i]; k_ok = evt_tick[i]; nm_first = nm; }
				else if (cur > maxper) maxper = cur;
				cur = 0;
			}
		}
		printf("    META EVENTs %d, alias rejections %d, abandons %d, names used in run %u of budget %u\n",
		       ev_count("meta err"), res.ev_alias, res.ev_abandon, ti.names_used, ti.names_budget);
		printf("    first creation attempt after onset at %.2f s; first file not abandoned created at %.2f s "
		       "(%u collector ticks later), %d names up to it (design: <= 20 ticks, <= 153 names); "
		       "%d later creations, at most %d names each (design: <= 17)\n",
		       t_first / 1e6, t_ok / 1e6, k_ok - k_first, nm_first,
		       creations - 1, maxper);
		if (!t_ok || nm_first > 153 || maxper > 17 || k_ok - k_first > 20) f = 1;
	}
	print_res("IF7b persistent DIR sector", &res, f);
	return f;
}

static int test_selftest_hud(void)
{
	struct cfg c;
	struct result res;
	int f;
	printf("TEST nominal_hud: 5 min at 52 KB/s with HUD rendering, TRIANGLE press at 120 s: SELFTEST PASS, 272 fb writes per tick, rows < 176\n");
	memset(&c, 0, sizeof(c));
	c.speed_kbs = 52;
	c.worker_start_s = 30;
	c.end_s = 330;
	c.seed = 1;
	c.quiet = 1;
	c.fb = 1;
	c.press_at_s = 120;
	f = run(&c, &res, 0);
	if (fb_bad) { printf("    fb writes outside rows 0-175: %d\n", fb_bad); f = 1; }
	if (!res.st_pass) { printf("    SELFTEST did not pass (bits %03x)\n", res.st_bits); f = 1; }
	print_res("nominal 52 KB/s with HUD", &res, f);
	printf("    chunks OK %d (bad CRC %d): PAD %d FILEHDR %d RECS %d STATS %d KMSG %d PROCS %d UHB %d EVENT %d; "
	       "largest RECS chunk %u B\n", res.chunks_ok, res.chunks_bad, res.ntype[0], res.ntype[1], res.ntype[2],
	       res.ntype[3], res.ntype[4], res.ntype[5], res.ntype[6], res.ntype[7], res.recs_max);
	if (!res.ntype[1] || !res.ntype[2] || !res.ntype[3] || !res.ntype[4] || !res.ntype[5] || !res.ntype[6] || !res.ntype[7])
		f = 1;
	{
		int i;
		printf("    final HUD:\n");
		for (i = 0; i < HUD_LINES; i++)
			printf("      %2d |%-35s| %d\n", i + 1, hud[i].t, hud[i].n);
	}
	return f;
}

/* ---------------------------------------------------------------- G2 attempt 2 vectors */
static int first_create(char *out, int outlen)	/* name of the first "segment create" */
{
	const char *p = strstr(evlog, "segment create ");
	if (!p) return 0;
	snprintf(out, (size_t)outlen, "%.11s", p + 15);
	return 1;
}

/* F2: run number, nnn and the names budget against what vfat's readdir really
 * returns (shortname=lower: our short entries come back as t001001.bin) */
static int test_names(void)
{
	static const char *const pre_a[] = { "T001001.BIN", "T001002.BIN", "T001003.BIN", "T001004.BIN",
					     "T001005.BIN", 0 };
	static const char *const pre_b[] = { "T001001.BIN", "T003002.BIN", "L:Mac Notes.txt:MACNOT~1.TXT", 0 };
	static const char *const pre_c[] = { "T002001.BIN", "T002002.BIN", "T001007.BIN", 0 };
	static const char *const pre_d[] = { "L:readme.txt:README.TXT", "T001001.BIN", "D", "T001002.BIN",
					     "T001003.BIN", 0 };
	struct {
		const char *name;
		const char *const *pre;
		u32 run;		/* 0: the supervisor's scan picks it */
		int gd_max;
		u32 want_run, want_nnn, want_used;
		const char *want_first;
	} v[] = {
		{ "A earlier boot, lower-case names: rrr advances, nnn restarts, 1 slot per file",
		  pre_a, 0, 0, 2, 1, 2 + 5, "T002001.BIN" },
		{ "B runs 1 and 3 present and a Mac long name: rrr = 4", pre_b, 0, 0, 4, 1, 2 + 1 + 1 + 2,
		  "T004001.BIN" },
		{ "C takeover in run 2: nnn continues after this run's largest", pre_c, 2, 0, 2, 3, 2 + 3,
		  "T002003.BIN" },
		{ "C' same directory, run 1: nnn after 007", pre_c, 1, 0, 1, 8, 2 + 3, "T001008.BIN" },
		{ "D lower-case long name, deleted slot, 64-byte getdents buffer", pre_d, 0, 64, 2, 1,
		  2 + 2 + 2 + 1 + 1, "T002001.BIN" },
		{ "E empty PSCLOG", 0, 0, 0, 1, 1, 2, "T001001.BIN" },
	};
	int i, fails = 0;
	printf("TEST names (G2 attempt 1 F2): PSCLOG read back as vfat shortname=lower returns it; "
	       "PSCLOG = 512 slots (16 KB), budget = min(999, slots - used - 16)\n");
	for (i = 0; i < (int)(sizeof(v) / sizeof(v[0])); i++) {
		struct cfg c;
		struct result res;
		struct pscol_tinfo ti;
		char first[16] = "";
		u32 srun, budget;
		int f = 0;
		memset(&c, 0, sizeof(c));
		c.speed_kbs = 52;
		c.worker_start_s = 30;
		c.end_s = 45;
		c.seed = 21;
		c.quiet = 1;
		c.dir_bytes = 16384;
		c.pre = v[i].pre;
		/* the supervisor's scan (main.c) on the same directory */
		C = c;
		sim_reset();
		if (c.pre)
			dir_prepopulate(c.pre);
		if (v[i].gd_max)
			C_getdents_max = v[i].gd_max;
		srun = pscol_run_scan();
		c.run = v[i].run ? v[i].run : srun;
		run(&c, &res, 0);
		(void)res;
		pscol_tinfo(&ti);
		budget = 512 - v[i].want_used - 16;
		first_create(first, sizeof(first));
		if (!v[i].run && srun != v[i].want_run) f = 1;
		if (ti.run != (v[i].run ? v[i].run : v[i].want_run)) f = 1;
		if (strcmp(first, v[i].want_first)) f = 1;
		if (ti.names_slots_used != v[i].want_used || ti.names_budget != budget) f = 1;
		printf("  %-78s %s  scan rrr %u (want %u), first file %s (want %s), slots used %u (want %u), "
		       "budget %u (want %u)\n", v[i].name, f ? "FAIL" : "PASS", srun, v[i].want_run, first,
		       v[i].want_first, ti.names_slots_used, v[i].want_used, ti.names_budget, budget);
		fails += f;
	}
	{	/* the name parser itself */
		static const struct { const char *n; int ok; u32 r, k; } t[] = {
			{ "t001001.bin", 1, 1, 1 }, { "T999998.BIN", 1, 999, 998 }, { "t012345.Bin", 1, 12, 345 },
			{ "T0010010.BIN", 0, 0, 0 }, { "T00100.BIN", 0, 0, 0 }, { "t001001.bix", 0, 0, 0 },
			{ "x001001.bin", 0, 0, 0 }, { "t00a001.bin", 0, 0, 0 }, { "t001001_bin", 0, 0, 0 },
			{ "t001001.binx", 0, 0, 0 }, { "", 0, 0, 0 },
		};
		int k, f = 0;
		for (k = 0; k < (int)(sizeof(t) / sizeof(t[0])); k++) {
			u32 r = 0, n = 0;
			int ok = pscol_tname(t[k].n, &r, &n);
			if (ok != t[k].ok || (ok && (r != t[k].r || n != t[k].k))) {
				printf("    pscol_tname(\"%s\") = %d %u %u\n", t[k].n, ok, r, n);
				f = 1;
			}
		}
		printf("  %-78s %s  (%d names)\n", "T<rrr><nnn>.BIN parser: 11 characters, dot at 7, any case", f ? "FAIL" : "PASS",
		       (int)(sizeof(t) / sizeof(t[0])));
		fails += f;
	}
	return fails;
}

/* R-4 / G2 F4: KRN compares stats word 2 with the CRC-32 of /proc/version */
static int test_krn(const char *banner_path, const char *want_hex)
{
	struct cfg c;
	struct result res;
	struct pscol_tinfo ti;
	int f, fails = 0, k;
	static char ban[512];
	printf("TEST krn_build_id (section 17 R-4): stats word 2 = CRC-32 (zlib, initial 0) of /proc/version\n");
	for (k = 0; k < 2; k++) {
		memset(&c, 0, sizeof(c));
		c.speed_kbs = 52; c.worker_start_s = 30; c.end_s = 60; c.seed = 5; c.quiet = 1;
		c.bad_build_id = k;
		run(&c, &res, 0);
		pscol_tinfo(&ti);
		f = k ? (ti.krn_id_ok != 0) : (ti.krn_id_ok != 1 || !ti.build_ok);
		printf("  %-60s %s  build_ok %d krn_id_ok %d expect 0x%08x\n",
		       k ? "word 2 differs (one bit): KRN red" : "word 2 = CRC of the sim banner: KRN green",
		       f ? "FAIL" : "PASS", ti.build_ok, ti.krn_id_ok, ti.build_expect);
		fails += f;
	}
	if (banner_path) {
		FILE *fp = fopen(banner_path, "rb");
		size_t n;
		u32 want = (u32)strtoul(want_hex, 0, 0);
		if (!fp) { perror(banner_path); return fails + 1; }
		n = fread(ban, 1, sizeof(ban) - 1, fp);
		fclose(fp);
		ban[n] = 0;
		for (k = 0; k < 2; k++) {
			memset(&c, 0, sizeof(c));
			c.speed_kbs = 52; c.worker_start_s = 30; c.end_s = 40; c.seed = 5; c.quiet = 1;
			c.version = ban;
			c.build_id = want;
			if (k) ban[8] ^= 1;	/* one byte of the banner changed */
			run(&c, &res, 0);
			pscol_tinfo(&ti);
			if (k) ban[8] ^= 1;
			f = k ? (ti.krn_id_ok != 0) : (ti.krn_id_ok != 1 || ti.build_expect != want);
			printf("  %-60s %s  CRC %08x, word 2 %08x (build_id.txt)\n",
			       k ? "packaged banner with one byte changed: KRN red" :
			       "packaged banner.txt bytes against build_id.txt: KRN green",
			       f ? "FAIL" : "PASS", ti.build_expect, want);
			fails += f;
		}
	}
	return fails;
}

/* F6: a FAILED flush whose block had lost records is re-sent without counting
 * them twice. Invariant: lost_total = records below durable_next missing on
 * the stick (none else is lost in these runs) */
static int test_resend_lost(void)
{
	struct cfg c;
	struct result res;
	int v, fails = 0;
	printf("TEST resend_lost (G2 attempt 1 F6): lost counted once when a flush with lost records fails "
	       "and is re-sent; lost_total must equal the records missing below durable_next\n");
	for (v = 0; v < 3; v++) {
		struct pscol_tinfo ti;
		int r, miss = 0, f;
		memset(&c, 0, sizeof(c));
		c.speed_kbs = 52; c.seed = 9; c.quiet = 1;
		if (v == 0) {		/* rings lapped before the worker's first drain; first flush fails */
			c.worker_start_s = 130; c.end_s = 400;
			c.nfail_flush = 1; c.fail_flush[0] = 1;
		} else if (v == 1) {	/* the same, two failing flushes in a row */
			c.worker_start_s = 130; c.end_s = 400;
			c.nfail_flush = 2; c.fail_flush[0] = 1; c.fail_flush[1] = 2;
		} else {		/* a 130 s stall inside an fsync mid-run; the stick refuses 1.5 s */
			c.worker_start_s = 30; c.end_s = 500;
			c.stall_at_s = 200; c.stall_s = 130; c.stall_fail_ms = 1500;
		}
		run(&c, &res, 0);
		pscol_tinfo(&ti);
		for (r = 0; r < PSC_NRINGS; r++) miss += res.missing[r];
		f = !(ti.lost_total > 0 && ti.lost_total == (u32)miss && !res.viol && ti.nrq == 0);
		printf("  %-58s %s  lost_total %u, missing below durable_next %d (P %d POLL %d W %d S %d M %d), "
		       "queue %d, viol %d, flushfail %d\n",
		       v == 0 ? "startup lap, first flush FAILED" : v == 1 ? "startup lap, two flushes FAILED" :
		       "130 s stall with failing writes", f ? "FAIL" : "PASS", ti.lost_total, miss,
		       res.missing[0], res.missing[1], res.missing[2], res.missing[3], res.missing[4], ti.nrq,
		       res.viol, res.ev_flushfail);
		fails += f;
	}
	return fails;
}

int main(int argc, char **argv)
{
	int fails = 0, nseeds = argc > 2 ? atoi(argv[2]) : 20;
	const char *w = argc > 1 ? argv[1] : "all";
	setvbuf(stdout, 0, _IOLBF, 0);
	if (!strcmp(w, "all") || !strcmp(w, "vectors")) fails += vectors_main();
	if (!strcmp(w, "all") || !strcmp(w, "hud")) fails += hud_test_main();
	if (!strcmp(w, "all") || !strcmp(w, "nominal")) fails += test_selftest_hud();
	if (!strcmp(w, "all") || !strcmp(w, "burst")) fails += test_burst_step0();
	if (!strcmp(w, "all") || !strcmp(w, "te10")) fails += test_te10();
	if (!strcmp(w, "all") || !strcmp(w, "if7b")) fails += test_if7b();
	if (!strcmp(w, "all") || !strcmp(w, "if4")) fails += test_if4(nseeds);
	if (!strcmp(w, "all") || !strcmp(w, "names")) fails += test_names();
	if (!strcmp(w, "all") || !strcmp(w, "krn"))
		fails += test_krn(argc > 3 && !strcmp(w, "krn") ? argv[2] : 0, argc > 3 ? argv[3] : 0);
	if (!strcmp(w, "all") || !strcmp(w, "resend")) fails += test_resend_lost();
	if (!strcmp(w, "dump")) {		/* dump <dir> <scenario>: files for the decoder cross-check */
		struct cfg c;
		struct result res;
		const char *dir = argc > 2 ? argv[2] : "dump";
		int sc = argc > 3 ? atoi(argv[3]) : 0, i, r;
		char path[256];
		FILE *fp;
		memset(&c, 0, sizeof(c));
		c.speed_kbs = 52; c.worker_start_s = 30; c.end_s = 330; c.seed = 1; c.quiet = 1; c.press_at_s = 120;
		if (sc == 1) { c.burst_on_step0 = 3; c.burst_on_step0_us = 3000000ull; c.end_s = 930; }
		if (sc == 2) { c.poisson_per_30min = 98; c.end_s = 1840; c.seed = 1001; c.speed_kbs = 25; }
		fails += run(&c, &res, 0);
		for (i = 0; i < ninode; i++) {
			if (!IN[i].i_size) continue;
			snprintf(path, sizeof(path), "%s/T%03u%03d.BIN", dir, c.run ? c.run : 1u, IN[i].nnn);
			fp = fopen(path, "wb");
			if (!fp) { perror(path); return 2; }
			fwrite(IN[i].disk, 1, IN[i].i_size, fp);
			fclose(fp);
		}
		snprintf(path, sizeof(path), "%s/truth.txt", dir);
		fp = fopen(path, "w");
		fprintf(fp, "nonce %u\n", 0x5EED0000u ^ c.seed);
		for (r = 0; r < PSC_NRINGS; r++)
			fprintf(fp, "ring %d head %u durable_next %u missing %d\n", r, R[r].head, ctl_durable_next[r], res.missing[r]);
		fclose(fp);
		print_res("dump", &res, 0);
	}
	if (!strcmp(w, "if7bv")) {
		struct cfg c;
		struct result res;
		memset(&c, 0, sizeof(c));
		c.speed_kbs = 52; c.worker_start_s = 30; c.end_s = argc > 2 ? (u32)atoi(argv[2]) : 170; c.seed = 11; c.dir_refuse_from_s = 60;
		fails += run(&c, &res, 0);
	}
	if (!strcmp(w, "te10v")) {
		struct cfg c;
		struct result res;
		memset(&c, 0, sizeof(c));
		c.speed_kbs = 52; c.worker_start_s = 100; c.end_s = 160; c.seed = 3;
		c.nfail_step = 2; c.fail_step[0] = 2; c.fail_step[1] = 3; c.trace = 12;
		fails += run(&c, &res, 0);
		print_res("te10 verbose", &res, 0);
	}
	if (!strcmp(w, "verbose")) {
		struct cfg c;
		struct result res;
		memset(&c, 0, sizeof(c));
		c.speed_kbs = argc > 2 ? (u32)atoi(argv[2]) : 52;
		c.worker_start_s = 30;
		c.end_s = argc > 3 ? (u32)atoi(argv[3]) : 120;
		c.press_at_s = 60;
		c.burst_on_step0 = argc > 4 ? atoi(argv[4]) : 0;
		c.burst_on_step0_us = 3000000ull;
		fails += run(&c, &res, 0);
		print_res("verbose", &res, 0);
	}
	printf("RESULT %s (%d failing cases)\n", fails ? "FAIL" : "PASS", fails);
	return fails ? 1 : 0;
}
