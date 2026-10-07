/*
 * test/vectors.c - DESIGN 8.5 "S-record verdicts" vectors (A4 F1(b), F4,
 * r7 A6-1 / IF7b own-entry rule) and the 8.5 HUD render test (N-2), run on
 * the pure verdict functions of pscol.c.
 */
#include <stdio.h>
#include <string.h>
#include "../pscol.h"

#define PART	8192u
#define FAT_S	32u
#define FAT_L	2048u
#define DATA_S	(FAT_S + 2 * FAT_L)
#define WPID	50
#define PDFL	5

static struct geom g;
static struct run runs[2];
static int nruns;
static struct wrec w[64];
static int n;
static int fails;

static u32 dsec(u32 fsec) { return PART + DATA_S + 64 + fsec; }	/* file in cluster 3 */
static void W(u32 sector, int nsect, int pid, int meta, int err)
{
	w[n].seq = (u32)n;
	w[n].sector = sector;
	w[n].nsect = (u8)nsect;
	w[n].pid = (u16)pid;
	w[n].flags = PSC_S_F_WRITE | (meta ? PSC_S_F_META : 0) | (err ? PSC_S_F_ERROR : 0);
	n++;
}
#define DATA(fs, ns, err)	W(dsec(fs), ns, WPID, 0, err)
#define DIRW(pid, err)		W(PART + DATA_S + 0, 1, pid, 1, err)	/* PSCLOG sector 0 */
#define DIRX(pid, err)		W(PART + DATA_S + 5, 1, pid, 1, err)	/* another dir sector */
#define FSINFO(err)		W(PART + 1, 1, WPID, 1, err)
#define FAT1(err)		W(PART + FAT_S + 0, 1, WPID, 1, err)
#define FATM(err)		W(PART + FAT_S + FAT_L, 1, WPID, 1, err)

static const char *vn(int v)
{
	switch (v) {
	case V_DURABLE: return "DURABLE";
	case V_FAILED: return "FAILED";
	case V_CONFIRMED: return "CONFIRMED";
	case V_RETRY: return "FAILED(retry in place)";
	case V_STOP: return "stopped";
	case V_ABANDON: return "abandoned";
	}
	return "?";
}

static void expect(const char *name, int got, int want)
{
	printf("  %-78s %-22s %s\n", name, vn(got), got == want ? "PASS" : "FAIL");
	if (got != want)
		fails++;
}

/* a step: FAT part first, then data part (as pscol.c step0/do_step) */
static int step(int step0, u32 off, u32 len, int alloc, int skipped)
{
	int v = judge_step_fat(w, n, skipped, &g, alloc);
	if (v != V_CONFIRMED)
		return step0 ? V_ABANDON : v;
	return judge_step_data(w, n, skipped, runs, nruns, off, len, (int)len, off + len, off + len,
			       step0, WPID, &g);
}

int vectors_main(void)
{
	struct psc_stats st;
	int local, v;
	memset(&st, 0, sizeof(st));
	st.ms_part_start = PART;
	st.fat_start = FAT_S;
	st.fat_length = FAT_L;
	st.fats = 2;
	st.fsinfo_sector = 1;
	st.data_start = DATA_S;
	st.sec_per_clus_bits = 64 | (9u << 16);
	geom_from_stats(&g, &st);
	runs[0].fsec = 0; runs[0].dsec = dsec(0); runs[0].n = 64;
	runs[1].fsec = 64; runs[1].dsec = dsec(64); runs[1].n = 64;
	nruns = 2;
	printf("TEST verdict_vectors (DESIGN 8.5 'S-record verdicts', 4.4 step 4, 4.8)\n");

	/* flushes: [1536, 1536 + 2048) = file sectors 3..6 */
	n = 0; DATA(3, 4, 0); DIRW(WPID, 0); FSINFO(1);
	expect("flush: data sectors all good, fsync failed (FSINFO refused)",
	       judge_flush(w, n, 0, runs, nruns, 1536, 2048, 2048, &g, &local), V_DURABLE);
	n = 0; DATA(3, 2, 0); DATA(5, 1, 1); DATA(6, 1, 0); DIRW(WPID, 0); FSINFO(0);
	v = judge_flush(w, n, 0, runs, nruns, 1536, 2048, 2048, &g, &local);
	expect("flush: one data sector failed", v, V_FAILED);
	expect("  ... and it counts as a local data error for the bad-region rule (4.6)",
	       local ? V_FAILED : V_DURABLE, V_FAILED);
	n = 0; DATA(3, 4, 0); DIRW(WPID, 0); FSINFO(0);
	expect("flush: a skipped seq in the window",
	       judge_flush(w, n, 1, runs, nruns, 1536, 2048, 2048, &g, &local), V_FAILED);
	n = 0; DATA(3, 4, 0);
	expect("flush: short write() (returned less than len)",
	       judge_flush(w, n, 0, runs, nruns, 1536, 2048, 1024, &g, &local), V_FAILED);
	n = 0; DATA(3, 4, 1); FSINFO(1); DIRW(WPID, 1);
	judge_flush(w, n, 0, runs, nruns, 1536, 2048, 2048, &g, &local);
	expect("flush: whole-stick failure is not a local data error (no bad-region count)",
	       local ? V_FAILED : V_DURABLE, V_DURABLE);

	/* later steps (8 KB at conf = 9728 -> sectors 19..34), not allocating */
	n = 0; DATA(19, 8, 0); DATA(27, 8, 0); DIRW(WPID, 0); FSINFO(0); FAT1(1);
	expect("step 5: FAT1 write failed", step(0, 9728, 8192, 0, 0), V_STOP);
	n = 0; DATA(19, 8, 0); DATA(27, 8, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0); FATM(1);
	expect("step 5: FAT mirror failed (allocating)", step(0, 9728, 8192, 1, 0), V_CONFIRMED);
	n = 0; DATA(19, 8, 0); DATA(27, 8, 0); DIRW(WPID, 1); FSINFO(0);
	expect("step 5: directory failed", step(0, 9728, 8192, 0, 0), V_CONFIRMED);
	n = 0; DATA(19, 8, 0); DATA(27, 8, 1); DIRW(WPID, 0); FSINFO(0);
	expect("step 5: a data sector failed", step(0, 9728, 8192, 0, 0), V_RETRY);
	n = 0; DATA(19, 8, 0); DATA(27, 8, 0); DIRW(WPID, 0); FSINFO(0);
	expect("step 5: allocating step with no FAT1 record (never extend, conservative)",
	       step(0, 9728, 8192, 1, 0), V_STOP);
	n = 0; DATA(19, 8, 0); DATA(27, 8, 0); FAT1(0);
	expect("step 5: allocating step, skipped seq in the window", step(0, 9728, 8192, 1, 1), V_STOP);
	n = 0; DATA(19, 8, 0); DATA(27, 8, 0); FAT1(0);
	expect("step 5: non-allocating step, skipped seq in the window", step(0, 9728, 8192, 0, 1), V_RETRY);

	/* step 0: [0, 1536) = file sectors 0..2, always allocating */
	n = 0; DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0); FATM(0);
	expect("step 0: nominal", step(1, 0, 1536, 1, 0), V_CONFIRMED);
	n = 0; DATA(0, 3, 0); DIRW(WPID, 1); FSINFO(0); FAT1(0);
	expect("step 0: directory (own entry) failed", step(1, 0, 1536, 1, 0), V_ABANDON);
	n = 0; DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0); DIRX(WPID, 1);
	expect("step 0: own entry OK, another directory sector failing later (IF7b)",
	       step(1, 0, 1536, 1, 0), V_CONFIRMED);
	n = 0; DATA(0, 3, 0); DIRW(WPID, 1); FSINFO(0); FAT1(0); DIRX(WPID, 0);
	expect("step 0: own entry failed, another directory sector OK",
	       step(1, 0, 1536, 1, 0), V_ABANDON);
	n = 0; DATA(0, 3, 0); FSINFO(0); FAT1(0);
	expect("step 0: no worker DIR record after its DATA records", step(1, 0, 1536, 1, 0), V_ABANDON);
	n = 0; DATA(0, 3, 0); DIRW(PDFL, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0);
	expect("step 0: a pdflush DIR record before the worker's first", step(1, 0, 1536, 1, 0), V_ABANDON);
	n = 0; DIRW(PDFL, 0); DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0);
	expect("step 0: a pdflush DIR record before the DATA records is ignored", step(1, 0, 1536, 1, 0), V_CONFIRMED);
	n = 0; DIRW(WPID, 0); DATA(0, 3, 0); FSINFO(0); FAT1(0);
	expect("step 0: worker DIR record only before its DATA records", step(1, 0, 1536, 1, 0), V_ABANDON);
	n = 0; DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(1); FAT1(0); FATM(1);
	expect("step 0: FSINFO and FAT mirror failed, own entry and FAT1 OK", step(1, 0, 1536, 1, 0), V_CONFIRMED);
	n = 0; DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(0); FAT1(1);
	expect("step 0: FAT1 failed", step(1, 0, 1536, 1, 0), V_ABANDON);
	n = 0; DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0);
	expect("step 0: skipped seq", step(1, 0, 1536, 1, 1), V_ABANDON);

	/* geometry self-check (4.8): wrong partition offset */
	n = 0; DATA(0, 3, 0); DIRW(WPID, 0); FSINFO(0); FAT1(0);
	expect("geometry self-check, right offset",
	       geometry_selfcheck(w, n, runs, nruns, 0, 1536, &g) ? V_CONFIRMED : V_FAILED, V_CONFIRMED);
	{
		struct run bad[1];
		bad[0] = runs[0];
		bad[0].dsec += 63;			/* partition start off by 63 sectors */
		expect("geometry self-check, wrong partition offset (STICK red)",
		       geometry_selfcheck(w, n, bad, 1, 0, 1536, &g) ? V_CONFIRMED : V_FAILED, V_FAILED);
	}
	n = 0; DATA(0, 3, 0); W(dsec(100), 8, PDFL, 0, 0); DIRW(WPID, 0);
	expect("geometry self-check, an extra DATA write outside the step's sectors",
	       geometry_selfcheck(w, n, runs, nruns, 0, 1536, &g) ? V_CONFIRMED : V_FAILED, V_FAILED);
	/* sector classes */
	{
		struct wrec r;
		int okc = 1;
		r.flags = PSC_S_F_WRITE | PSC_S_F_META;
		r.sector = PART + FAT_S; okc &= sector_class(&g, &r) == SC_FAT1;
		r.sector = PART + FAT_S + FAT_L - 1; okc &= sector_class(&g, &r) == SC_FAT1;
		r.sector = PART + FAT_S + FAT_L; okc &= sector_class(&g, &r) == SC_FATM;
		r.sector = PART + 1; okc &= sector_class(&g, &r) == SC_FSINFO;
		r.sector = PART + DATA_S; okc &= sector_class(&g, &r) == SC_DIR;
		r.sector = PART + 0; okc &= sector_class(&g, &r) == SC_OTHER;
		r.flags = PSC_S_F_WRITE; okc &= sector_class(&g, &r) == SC_DATA;
		expect("sector classes FAT1/FATM/FSINFO/DIR/OTHER/DATA from the geometry",
		       okc ? V_CONFIRMED : V_FAILED, V_CONFIRMED);
	}
	printf("  verdict vectors: %s (%d failing)\n", fails ? "FAIL" : "PASS", fails);
	return fails;
}

int pscol_hud_force(int v);
int hud_test_main(void)
{
	static u32 row[480];
	int v, i, y, x, bad = 0, maxlen = 0;
	u32 bg, hb0, hb1;
	printf("TEST hud_render (8.2, 8.5 N-2): every forced state, every line <= 35 chars, "
	       "no text pixel at x >= 428 in rows 8-39, none in rows >= 168\n");
	for (v = 0; pscol_hud_force(v); v++) {
		hud_build_lines();
		for (i = 0; i < HUD_LINES; i++) {
			if (hud[i].n > maxlen) maxlen = hud[i].n;
			if (hud[i].n > HUD_COLS || (int)strlen(hud[i].t) != hud[i].n) bad++;
			printf("    v%-2d L%-2d |%-35s| %2d\n", v, i + 1, hud[i].t, hud[i].n);
		}
		for (y = 0; y < 176; y++) {
			hud_render_row(y, row);
			bg = row[5 + 0 * 0];
			(void)bg;
			for (x = 4; x < 476; x++) {
				u32 p = row[x];
				int text = p != 0x00100A08u && p != 0x005ADC00u && p != 0x001E4600u &&
					   p != 0x0028D2FFu && p != 0x000A323Cu;
				hb0 = 0; hb1 = 0; (void)hb0; (void)hb1;
				if (!text) continue;
				if ((y >= 8 && y <= 39 && x >= 428) || y >= 168 || y < 8) {
					bad++;
					if (bad < 5) printf("    text pixel at x=%d y=%d (v%d)\n", x, y, v);
				}
			}
		}
	}
	printf("  hud render: %s (longest line %d chars, %d problems)\n", bad ? "FAIL" : "PASS", maxlen, bad);
	return bad ? 1 : 0;
}
