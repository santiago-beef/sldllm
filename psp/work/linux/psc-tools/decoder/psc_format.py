"""psc_format.py - PSC record and file format for the host decoder.

Mirror of /home/ubuntu/psp/work/linux/include/linux/psc_format.h (branch
stage2-trace), which is the single C definition used by the kernel and by
pscol. Specification: handoff/design/DESIGN.md revision 6, sections 1
(records, stats), 2.8 (ctl), 3.1 (rings), 4.3-4.4 (collector constants),
10.2-10.4 (chunks, UHB, FILEHDR, struct strings).

For every structure there are two descriptions that must agree:
  *_FMT     the struct string exactly as DESIGN 10.2/10.3 prints it
  *_FIELDS  (name, code, count) in C member order, from which the offset
            table *_OFF = {name: (offset, code, count)} is computed
selftest() asserts calcsize(FMT) == design size, that FIELDS expands to the
same item sequence as FMT, and every offset DESIGN section 1 tabulates.
check_format.py cross-checks all of this against the C header.

Python 3, standard library only. Run `python3 psc_format.py` for the
self-test.
"""

import struct
import zlib

FORMAT_VERSION = 5
HZ = 250
CPT = 883651
COUNTS_PER_SEC = 220912896
WD_CYCLE = 1250

SAT_U8, SAT_U16, SAT_U32 = 0xFF, 0xFFFF, 0xFFFFFFFF
SEQ_WRITING = 0xFFFFFFFF

# ---------------------------------------------------------------- rings (3.1)
RING_P, RING_POLL, RING_W, RING_S, RING_M = 0, 1, 2, 3, 4
NRINGS = 5
RING_NAMES = ("P", "POLL", "W", "S", "M")
RING_ENTRIES = {RING_P: 4096, RING_POLL: 2048, RING_W: 256, RING_S: 4096, RING_M: 64}
RING_RECSIZE = {RING_P: 80, RING_POLL: 40, RING_W: 288, RING_S: 40, RING_M: 80}
RING_DIV4 = {RING_P: 20, RING_POLL: 10, RING_W: 72, RING_S: 10, RING_M: 20}
RINGS_TOTAL_BYTES = 652288

PROC_DIR = "/proc/psc"
PROC_RING = {RING_P: "/proc/psc/p", RING_POLL: "/proc/psc/poll", RING_W: "/proc/psc/w",
             RING_S: "/proc/psc/s", RING_M: "/proc/psc/m"}
PROC_STATS = "/proc/psc/stats"
PROC_CTL = "/proc/psc/ctl"
BOOT_PRINTK_PREFIX = "PSC5 P4096 POLL2048 W256 S4096 M64 bootnop "

# ------------------------------------------------------------ record sizes
SC_SIZE, WEXT_SIZE, W_SIZE, POLL_SIZE, S_SIZE, M_SIZE = 80, 208, 288, 40, 40, 80
STATS_SIZE, STATS_WORDS = 768, 192
CTL_SIZE, CHUNK_HDR_SIZE, BLK_HDR_SIZE = 32, 20, 8
FILEHDR_FIXED, FILEHDR_VERSION_LEN, FILEHDR_PAYLOAD = 44, 256, 1068
UHB_SIZE = 84

# ======================================================= SC record (1.2, 10.3)
SC_FMT = '<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH'
SC_FIELDS = [
    ("seq", "I", 1), ("tick_in", "I", 1), ("c_in", "I", 1), ("c_out", "I", 1),
    ("dtick", "H", 1), ("cmd", "B", 1), ("txlen", "B", 1), ("ret", "h", 1),
    ("nwords", "B", 1), ("retries", "B", 1), ("ack_polls", "I", 1),
    ("drain", "H", 1), ("drain_last", "H", 1), ("gpio_in", "H", 1),
    ("spi_st9", "H", 1), ("spi_sttx", "H", 1), ("ctx", "B", 1), ("wn", "B", 1),
    ("w_head_lo", "H", 1), ("pre_wrk", "H", 1), ("pre_cls", "B", 1),
    ("ms_delta", "B", 1), ("pre_flags", "B", 1), ("preempt_delta", "B", 1),
    ("rx", "s", 16), ("lc_epc", "I", 1), ("lc_dtick", "H", 1), ("lc_n", "B", 1),
    ("lc_flags", "B", 1), ("led_or", "I", 1), ("led_pid", "H", 1), ("pre_tot", "H", 1),
]
# DESIGN 1.2 table, byte offsets
SC_DESIGN_OFF = {
    "seq": 0, "tick_in": 4, "c_in": 8, "c_out": 12, "dtick": 16, "cmd": 18,
    "txlen": 19, "ret": 20, "nwords": 22, "retries": 23, "ack_polls": 24,
    "drain": 28, "drain_last": 30, "gpio_in": 32, "spi_st9": 34, "spi_sttx": 36,
    "ctx": 38, "wn": 39, "w_head_lo": 40, "pre_wrk": 42, "pre_cls": 44,
    "ms_delta": 45, "pre_flags": 46, "preempt_delta": 47, "rx": 48, "lc_epc": 64,
    "lc_dtick": 68, "lc_n": 70, "lc_flags": 71, "led_or": 72, "led_pid": 76,
    "pre_tot": 78,
}

CTX_ORIGIN_MASK = 0x03
ORIGIN_P, ORIGIN_M, ORIGIN_WB, ORIGIN_WT = 0, 1, 2, 3
ORIGIN_NAMES = ("P", "M", "WB", "WT")
CTX_IE, CTX_IN_INTERRUPT, CTX_JP_TASK, CTX_PREEMPT_CNT, CTX_SIGPENDING = 0x04, 0x08, 0x10, 0x20, 0x40
WDCTX_NONE, WDCTX_BOOT, WDCTX_TIMER = 0, 1, 2   # kernel-internal psc_wd_ctx (1.8), not origin codes
RET_BADFRAME, RET_DRAIN_TIMEOUT, RET_ACK_TIMEOUT, RET_BUSY = -2, -3, -4, -5
RETRIES_E5 = 16
SYSCON_SPIN_MAX = 1000000
ACK_POLLS_TIMEOUT = 1000001
ACK_POLLS_NOT_REACHED = 0xFFFFFFFF
DRAIN_E3 = 0xFFFF
PRE_F_VALID, PRE_F_MULTI, PRE_F_SAT, PRE_F_OTHER_HOLDER, PRE_F_CLS345 = 0x01, 0x02, 0x04, 0x08, 0x10
LC_DTICK_NONE, LC_N_SAT = 0xFFFF, 0xFF
LC_F_VALID, LC_F_BD, LC_F_IN_SYSCON, LC_F_WD_TICK, LC_F_NESTED_SEEN, LC_F_PANEL = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20


def pre_cls_first(b): return b & 0x0F
def pre_cls_last(b): return (b >> 4) & 0x0F


# ===================================================== W extension (1.3, 10.3)
WEXT_FMT = '<5I16I5IBBBB4I4I16IHH'
WEXT_FIELDS = [
    ("epc", "I", 1), ("cause", "I", 1), ("status", "I", 1), ("ra", "I", 1), ("sp", "I", 1),
    ("r", "I", 16),
    ("pid", "I", 1), ("p_head", "I", 1), ("jp_loop", "I", 1), ("t_entry_tick", "I", 1),
    ("t_entry_c", "I", 1),
    ("t_busy", "B", 1), ("jp_stage", "B", 1), ("ext_flags", "B", 1), ("cur_pcnt", "B", 1),
    ("c_pre", "I", 1), ("lc_tick", "I", 1), ("lc_c_pre", "I", 1), ("lc_cmd_id", "I", 1),
    ("lc_epc", "I", 1), ("lc_cause", "I", 1), ("lc_ra", "I", 1), ("lc_sp", "I", 1),
    ("lc_r", "I", 16), ("lc_n", "H", 1), ("rsv", "H", 1),
]
# DESIGN 1.3 table, byte offsets within the W record (WEXT starts at 80)
WEXT_DESIGN_OFF_IN_W = {
    "epc": 80, "cause": 84, "status": 88, "ra": 92, "sp": 96, "r": 100, "pid": 164,
    "p_head": 168, "jp_loop": 172, "t_entry_tick": 176, "t_entry_c": 180,
    "t_busy": 184, "jp_stage": 185, "ext_flags": 186, "cur_pcnt": 187, "c_pre": 188,
    "lc_tick": 192, "lc_c_pre": 196, "lc_cmd_id": 200, "lc_epc": 204, "lc_cause": 208,
    "lc_ra": 212, "lc_sp": 216, "lc_r": 220, "lc_n": 284, "rsv": 286,
}
# W = SC followed by WEXT; flat names are "sc.<f>" and "ext.<f>" (C: w.sc.f, w.ext.f)
W_FMT = '<' + SC_FMT[1:] + WEXT_FMT[1:]
W_FIELDS = [("sc." + n, c, k) for (n, c, k) in SC_FIELDS] + \
           [("ext." + n, c, k) for (n, c, k) in WEXT_FIELDS]
REGS_ORDER = tuple(range(2, 16)) + (24, 25)   # r[16], lc_r[16]

TBUSY_P, TBUSY_M = 0x01, 0x02
EXT_F_REGS_VALID, EXT_F_KMODE, EXT_F_IN_SYSCON, EXT_F_JP_TASK = 0x01, 0x04, 0x08, 0x10
EXT_F_LC_VALID, EXT_F_MS_ACTIVE, EXT_F_NESTED = 0x20, 0x40, 0x80

(STAGE_NOT_STARTED, STAGE_LOOP_TOP, STAGE_ASTICKPOWER, STAGE_GETCTRL2, STAGE_RI_RETURNED,
 STAGE_PI_ENTRY, STAGE_DEDUPE_RET, STAGE_BEFORE_LCD_ON, STAGE_AFTER_LCD_ON, STAGE_BEFORE_LISTSEM,
 STAGE_LISTSEM_HELD, STAGE_BEFORE_QSEM, STAGE_PUSHING, STAGE_AFTER_UP_LIST, STAGE_AFTER_WAKEUP,
 STAGE_MOUSE_ENTRY, STAGE_BEFORE_SYNC, STAGE_BEFORE_MSLEEP) = range(18)   # 2.5
STAGES = {
    0: "not started", 1: "loop top", 2: "AStickPower", 3: "GetCtrl2",
    4: "read_input returned", 5: "process_input entry", 6: "dedupe return",
    7: "before psp_lcd_on", 8: "after psp_lcd_on", 9: "before down(list_sem)",
    10: "list_sem held", 11: "before down(Q->sem)", 12: "pushing",
    13: "after up(list_sem)", 14: "after wake_up", 15: "mouse entry",
    16: "before input_sync", 17: "before msleep",
}

# ======================================================== POLL record (1.4)
POLL_FMT = '<IIIIH7B2b5BHHBBBB'
POLL_FIELDS = [
    ("seq", "I", 1), ("tick_start", "I", 1), ("c_start", "I", 1), ("c_end", "I", 1),
    ("sc_seq_lo", "H", 1), ("body_ticks", "B", 1), ("ri_branch", "B", 1),
    ("pi_flags", "B", 1), ("nqueues", "B", 1), ("push_ok", "B", 1), ("push_fail", "B", 1),
    ("mouse_flags", "B", 1), ("dx", "b", 1), ("dy", "b", 1), ("sig", "B", 1),
    ("period", "B", 1), ("preempt_delta", "B", 1), ("stage_max", "B", 1), ("nsc", "B", 1),
    ("wk_delay", "H", 1), ("wk_wrk", "H", 1), ("wk_cls0", "B", 1), ("wk_cls1", "B", 1),
    ("wk_nsw", "B", 1), ("rsv", "B", 1),
]
POLL_DESIGN_OFF = {
    "seq": 0, "tick_start": 4, "c_start": 8, "c_end": 12, "sc_seq_lo": 16,
    "body_ticks": 18, "ri_branch": 19, "pi_flags": 20, "nqueues": 21, "push_ok": 22,
    "push_fail": 23, "mouse_flags": 24, "dx": 25, "dy": 26, "sig": 27, "period": 28,
    "preempt_delta": 29, "stage_max": 30, "nsc": 31, "wk_delay": 32, "wk_wrk": 34,
    "wk_cls0": 36, "wk_cls1": 37, "wk_nsw": 38, "rsv": 39,
}
RI_R1, RI_R3, RI_R4, RI_R5 = 1, 3, 4, 5
PI_F_CALLED, PI_F_DEDUPE, PI_F_BLANKED, PI_F_SELECT_TOGGLE = 0x01, 0x02, 0x04, 0x08
PI_F_MOUSEMODE, PI_F_LISTSEM, PI_F_LISTSEM_FAIL, PI_F_WAKE = 0x10, 0x20, 0x40, 0x80
MOUSE_F_CALLED, MOUSE_F_NODEV, MOUSE_F_NOOP, MOUSE_F_REPORTED = 0x01, 0x02, 0x04, 0x08
MOUSE_F_LEFT, MOUSE_F_MIDDLE, MOUSE_F_RIGHT = 0x10, 0x20, 0x40
SIG_PENDING = 0x01


def push_fail_full(b): return b & 0x0F
def push_fail_eintr(b): return (b >> 4) & 0x0F


# =========================================================== S record (1.5)
S_FMT = '<IIIIIHHBBHBBHII'
S_FIELDS = [
    ("seq", "I", 1), ("tick_on", "I", 1), ("c_on", "I", 1), ("c_off", "I", 1),
    ("sector", "I", 1), ("dtick", "H", 1), ("pid", "H", 1), ("nsect", "B", 1),
    ("flags", "B", 1), ("p_head_lo", "H", 1), ("led_ops", "B", 1), ("rsv29", "B", 1),
    ("rsv30", "H", 1), ("rd_set_or", "I", 1), ("rd_clr_or", "I", 1),
]
S_DESIGN_OFF = {
    "seq": 0, "tick_on": 4, "c_on": 8, "c_off": 12, "sector": 16, "dtick": 20,
    "pid": 22, "nsect": 24, "flags": 25, "p_head_lo": 26, "led_ops": 28,
    "rsv29": 29, "rsv30": 30, "rd_set_or": 32, "rd_clr_or": 36,
}
S_F_WRITE, S_F_ERROR, S_F_SET_B3, S_F_CLR_B3 = 0x01, 0x02, 0x04, 0x08
S_F_P_ENTRY, S_F_P_EXIT, S_F_M, S_F_META = 0x10, 0x20, 0x40, 0x80

# M record = SC (1.6)
M_FMT, M_FIELDS = SC_FMT, SC_FIELDS

# ======================================================= stats block (1.7)
STATS_MAGIC = 0x54535350
STATS_VERSION_SIZE = (768 << 16) | 5
STATS_FMT = '<192I'          # as printed in 10.3/10.4; words 62, 63 are signed
OC_NAMES = ("pos", "zero_words", "zero_nowords", "e2", "e3", "e4", "e5")
OC_POS, OC_ZERO_WORDS, OC_ZERO_NOWORDS, OC_E2, OC_E3, OC_E4, OC_E5 = range(7)
STATS_FIELDS = [
    ("magic", "I", 1), ("version_size", "I", 1), ("build_id", "I", 1), ("hz", "I", 1),
    ("counts_per_tick", "I", 1),
    ("last_reader_tick", "I", 1), ("initial_jiffies", "I", 1), ("now_tick", "I", 1),
    ("now_count", "I", 1), ("now_jiffies", "I", 1),
    ("total_counts_lo", "I", 1), ("total_counts_hi", "I", 1), ("c_pre_max", "I", 1),
    ("long_ticks", "I", 1),
    ("head", "I", 5), ("m_dropped", "I", 1), ("addr_syscon_cmd", "I", 1),
    ("addr_psc_sc_exit", "I", 1), ("addr_getctrl2", "I", 1), ("proc_opens", "I", 1),
    ("p_rec_cost_last", "I", 1), ("p_rec_cost_max", "I", 1), ("w_rec_cost_max", "I", 1),
    ("wd_calls", "I", 1), ("wd_last_tick", "I", 1), ("p_nested", "I", 1), ("p_ticked", "I", 1),
    ("oc_p08", "I", 7), ("oc_p33", "I", 7), ("oc_w", "I", 7),
    ("jp_pid", "I", 1), ("jp_loop", "I", 1), ("jp_stage", "I", 1), ("jp_stage_arg", "I", 1),
    ("jp_state", "I", 1), ("jp_sigpending", "I", 1), ("jp_sigword", "I", 1), ("jp_nivcsw", "I", 1),
    ("jp_keys", "I", 1), ("console_blanked", "I", 1), ("console_sem_count", "i", 1),
    ("list_sem_count", "i", 1),
    ("t_busy", "I", 1), ("t_cmd", "I", 1), ("t_entry_tick", "I", 1), ("t_entry_c", "I", 1),
    ("jp_r3", "I", 1), ("jp_r4", "I", 1), ("jp_r5", "I", 1), ("jp_proc_calls", "I", 1),
    ("jp_dedupe", "I", 1), ("jp_changed", "I", 1), ("jp_lcd_unblank", "I", 1),
    ("jp_mode_toggles", "I", 1),
    ("jp_listsem_fail", "I", 1), ("jp_push_ok", "I", 1), ("jp_push_full", "I", 1),
    ("jp_push_eintr", "I", 1), ("jp_wake", "I", 1), ("jp_mouse_calls", "I", 1),
    ("jp_mouse_noop", "I", 1), ("jp_mouse_reports", "I", 1),
    ("fop_open", "I", 1), ("fop_release", "I", 1), ("fop_read_enter", "I", 1),
    ("fop_read_ret", "I", 1), ("fop_read_eintr", "I", 1), ("fop_ioctl", "I", 1),
    ("qfree_stage", "I", 1), ("qfree_queue", "I", 1), ("qfree_pid", "I", 1),
    ("vcs_putchar", "I", 1), ("vcs_changecon", "I", 1), ("vcs_updscr", "I", 1),
    ("vcs_getsize", "I", 1),
    ("md_event_syn", "I", 1), ("md_notify_calls", "I", 1), ("md_read_ret", "I", 1),
    ("led_calls", "I", 1), ("led_calls_t_busy", "I", 1), ("led_or_set_run", "I", 1),
    ("led_or_clr_run", "I", 1),
    ("ms_seg_wr", "I", 1), ("ms_seg_rd", "I", 1), ("ms_err", "I", 1), ("ms_ip_tick", "I", 1),
    ("ms_ip_sector", "I", 1), ("ms_ip_word", "I", 1), ("kupd_count", "I", 1),
    ("kupd_last_tick", "I", 1),
    ("durable_tick", "I", 1), ("durable_next", "I", 5),
    ("ctl_writes", "I", 1), ("panel_paints", "I", 1), ("panel_last_tick", "I", 1),
    ("panel_test_seq", "I", 1), ("panel_test_done", "I", 1), ("panel_cost_max", "I", 1),
    ("lc_nested", "I", 1),
    ("kguard_bad", "I", 1), ("ring_rewinds", "I", 1), ("head_regress", "I", 1),
    ("slot_bad", "I", 5),
    ("fat_panics", "I", 1), ("fat_panic_tick", "I", 1), ("ms_rdonly", "I", 1),
    ("wk_count", "I", 1), ("wk_max", "I", 1), ("jp_exit_tick", "I", 1),
    ("kguard_first_tick", "I", 1),
    ("pid_class", "I", 8),
    ("panel_cost_last", "I", 1), ("panel_state", "I", 1),
    ("meta_sector", "I", 1), ("meta_tick", "I", 1), ("pre_count", "I", 1),
    ("ms_part_start", "I", 1), ("fat_start", "I", 1), ("fat_length", "I", 1),
    ("fats", "I", 1), ("fsinfo_sector", "I", 1), ("data_start", "I", 1),
    ("sec_per_clus_bits", "I", 1),
    ("reserved", "I", 32),
]
# DESIGN 1.7 row starts: word index of the first field of each table row
STATS_DESIGN_ROWS = {
    0: "magic", 5: "last_reader_tick", 10: "total_counts_lo", 14: "head",
    24: "p_rec_cost_last", 31: "oc_p08", 38: "oc_p33", 45: "oc_w", 52: "jp_pid",
    56: "jp_state", 60: "jp_keys", 64: "t_busy", 68: "jp_r3", 76: "jp_listsem_fail",
    84: "fop_open", 90: "qfree_stage", 93: "vcs_putchar", 97: "md_event_syn",
    100: "led_calls", 104: "ms_seg_wr", 112: "durable_tick", 113: "durable_next",
    118: "ctl_writes", 125: "kguard_bad", 128: "slot_bad", 133: "fat_panics",
    136: "wk_count", 140: "pid_class", 148: "panel_cost_last", 150: "meta_sector",
    153: "ms_part_start", 160: "reserved",
}
# words named individually in the design text that are checked by index
STATS_DESIGN_WORDS = {
    2: "build_id", 3: "hz", 4: "counts_per_tick", 19: "m_dropped",
    20: "addr_syscon_cmd", 21: "addr_psc_sc_exit", 22: "addr_getctrl2", 23: "proc_opens",
    62: "console_sem_count", 63: "list_sem_count", 109: "ms_ip_word",
    121: "panel_test_seq", 122: "panel_test_done", 149: "panel_state",
    154: "fat_start", 159: "sec_per_clus_bits",
}
MSIP_ACTIVE, MSIP_WRITE = 1 << 24, 1 << 25
PANEL_NEVER, PANEL_CLEARED, PANEL_SHOWING = 0, 1, 2
QFREE_ENTRY, QFREE_AFTER_348, QFREE_AFTER_353, QFREE_AFTER_LISTDEL, QFREE_BEFORE_KFREE = 1, 2, 3, 4, 5
CLASS_NONE, CLASS_WRK, CLASS_SUP, CLASS_OSK, CLASS_MD, CLASS_PDFLUSH, CLASS_KTHREAD, CLASS_OTHER = range(8)
CLASS_NAMES = ("-", "WRK", "SUP", "OSK", "MD", "PDFLUSH", "KTHREAD", "OTHER")

# ================================================== ctl command (2.8, 10.3)
CTL_FMT = '<I7I'
CTL_FIELDS = [("op", "I", 1), ("arg", "I", 7)]
CTL_OP_DURABLE, CTL_OP_CLASS, CTL_OP_PANEL_TEST, CTL_OP_META = 1, 2, 3, 4

# ======================================================= chunks (10.2)
SECTOR = 512
CHUNK_MAGIC = b'PSCK'
CHUNK_HDR_FMT = '<4sHHIII'
CHUNK_HDR_FIELDS = [("magic", "s", 4), ("type", "H", 1), ("hver", "H", 1), ("len", "I", 1),
                    ("fseq", "I", 1), ("crc", "I", 1)]
CHUNK_LEN_MAX = 65536
FSEQ_PREALLOC = 0xFFFFFFFF
PAD_SECTOR_LEN = 492
CHUNK_PAD, CHUNK_FILEHDR, CHUNK_RECS, CHUNK_STATS, CHUNK_KMSG, CHUNK_PROCS, CHUNK_UHB, CHUNK_EVENT = range(8)
CHUNK_NAMES = ("PAD", "FILEHDR", "RECS", "STATS", "KMSG", "PROCS", "UHB", "EVENT")

BLK_HDR_FMT = '<BBHI'
BLK_HDR_FIELDS = [("ring", "B", 1), ("recsize_div4", "B", 1), ("count", "H", 1), ("lost", "I", 1)]
BLK_RESEND, BLK_RING_MASK = 0x80, 0x7F

FILEHDR_MAGIC = b'PSCLOG5\0'
FILEHDR_FMT = '<8sIIIIIIIII'
FILEHDR_FIELDS = [("magic", "s", 8), ("fmt", "I", 1), ("run", "I", 1), ("seg", "I", 1),
                  ("inst", "I", 1), ("writer_pid", "I", 1), ("sup_pid", "I", 1),
                  ("now_tick", "I", 1), ("now_jiffies", "I", 1), ("nonce", "I", 1)]
INST_WORKER, INST_SUPERVISOR = 1, 2

UHB_FMT = '<21I'
UHB_FIELDS = [(n, "I", 1) for n in (
    "tickno", "stats_now_tick", "gtod_sec", "gtod_usec", "uptime_cs", "memfree_kb",
    "mouse_pkts_total", "mouse_press_total", "bytes_synced_total", "last_write_ms",
    "last_fsync_ms", "max_fsync_ms_60s", "max_tick_ms_60s", "write_errs", "last_errno",
    "flags", "durable_tick", "lag_max", "seg", "drain_stuck", "nonce")]
UHB_FLAG_NAMES = (
    "holding", "st_krn", "st_wdog", "st_stick", "st_rec", "st_panel", "st_sup", "st_poll",
    "st_btn", "sup_alive", "no_stick", "drain_complete", "catchup", "file_ahead", "takeover",
    "resend_pend", "guard", "abandoned", "creating", "switched", "ms_red", "rdonly",
    "rec_alarm", "meta", "growth_stop", "prefix", "abandon_wait", "retired", "alias",
    "speed_ok", "fsync_err")      # bit 0 .. bit 30

FLUSH_MAX, KMSG_MAX, EVENT_MAX, PROCS_MAX = 40960, 4096, 1024, 2400
RECS_RECORD_BYTES_MAX = 34304
CAP = {RING_P: 48, RING_POLL: 24, RING_W: 2, RING_S: 64, RING_M: 8}
CAP_M_MAX = 4

LOG_DIR = "/ms0/PSCLOG"
SEG_SIZE = 2097152
FILEHDR_AREA = 1536
STEP_SMALL, STEP_LARGE, ROOM_LARGE_BELOW = 8192, 65536, 81920


def uhb_seg_decode(w):
    """UHB seg word (10.2, r5 layout, r7 A6-3 decode)."""
    v = (w >> 20) & 0x1FF
    return {"active": w & 0x3FF, "creating": (w >> 10) & 0x3FF,
            "conf": SEG_SIZE if v == 256 else 8192 * v + 1536,
            "ahead": (w >> 29) & 3, "in_progress": bool(w >> 31)}


def pad4(n):
    return (n + 3) & ~3


def pad_len_at(off):
    """Payload length of the PAD chunk whose header starts at `off`."""
    return (SECTOR - ((off + CHUNK_HDR_SIZE) % SECTOR)) % SECTOR


def chunk_crc(ctype, payload, nonce):
    """10.2: plain CRC-32 for FILEHDR, seeded with the boot nonce otherwise."""
    return zlib.crc32(payload, 0 if ctype == CHUNK_FILEHDR else nonce) & 0xFFFFFFFF


# ============================================================== machinery
def _expand(fmt):
    """'<5I16s' -> ['I','I','I','I','I','16s'] (an 's' run is one item)."""
    assert fmt[0] == '<'
    out, num = [], ''
    for ch in fmt[1:]:
        if ch.isdigit():
            num += ch
            continue
        n = int(num) if num else 1
        num = ''
        if ch == 's':
            out.append('%ds' % n)
        else:
            out.extend([ch] * n)
    return out


def fields_fmt(fields):
    return '<' + ''.join(('%ds' % k) if c == 's' else (c if k == 1 else '%d%s' % (k, c))
                         for (_, c, k) in fields)


def offsets(fields):
    off, table = 0, {}
    for (n, c, k) in fields:
        table[n] = (off, c, k)
        off += struct.calcsize('<' + ('%ds' % k if c == 's' else c * k))
    return table


def unpack(fields, buf, off=0):
    """Unpack one record into a dict; arrays become tuples, 's' bytes."""
    vals = struct.unpack_from(fields_fmt(fields), buf, off)
    out, i = {}, 0
    for (n, c, k) in fields:
        if c == 's' or k == 1:
            out[n] = vals[i]
            i += 1
        else:
            out[n] = tuple(vals[i:i + k])
            i += k
    return out


RECORDS = {
    # name: (design FMT, FIELDS, design size)
    "SC": (SC_FMT, SC_FIELDS, SC_SIZE),
    "WEXT": (WEXT_FMT, WEXT_FIELDS, WEXT_SIZE),
    "W": (W_FMT, W_FIELDS, W_SIZE),
    "POLL": (POLL_FMT, POLL_FIELDS, POLL_SIZE),
    "S": (S_FMT, S_FIELDS, S_SIZE),
    "M": (M_FMT, M_FIELDS, M_SIZE),
    "STATS": (STATS_FMT, STATS_FIELDS, STATS_SIZE),
    "CTL": (CTL_FMT, CTL_FIELDS, CTL_SIZE),
    "CHUNK_HDR": (CHUNK_HDR_FMT, CHUNK_HDR_FIELDS, CHUNK_HDR_SIZE),
    "BLK_HDR": (BLK_HDR_FMT, BLK_HDR_FIELDS, BLK_HDR_SIZE),
    "FILEHDR": (FILEHDR_FMT, FILEHDR_FIELDS, FILEHDR_FIXED),
    "UHB": (UHB_FMT, UHB_FIELDS, UHB_SIZE),
}
OFF = {name: offsets(f) for name, (_, f, _) in RECORDS.items()}
RING_FIELDS = {RING_P: SC_FIELDS, RING_POLL: POLL_FIELDS, RING_W: W_FIELDS,
               RING_S: S_FIELDS, RING_M: SC_FIELDS}


def _signless(items):
    return [it.upper() if len(it) == 1 else it for it in items]


def selftest(verbose=True):
    for name, (fmt, fields, size) in RECORDS.items():
        assert struct.calcsize(fmt) == size, (name, struct.calcsize(fmt), size)
        assert struct.calcsize(fields_fmt(fields)) == size, (name, 'fields')
        a, b = _expand(fmt), _expand(fields_fmt(fields))
        if name == "STATS":   # 10.3 prints '<192I'; 10.4 says words 62, 63 signed
            assert _signless(a) == _signless(b), name
            assert [i for i, x in enumerate(b) if x == 'i'] == [62, 63]
        else:
            assert a == b, (name, a, b)
        if verbose:
            print("%-9s calcsize %4d == design %4d   %s" % (name, struct.calcsize(fmt), size, fmt))
    for n, o in SC_DESIGN_OFF.items():
        assert OFF["SC"][n][0] == o, ("SC", n)
        assert OFF["W"]["sc." + n][0] == o, ("W.sc", n)
    for n, o in WEXT_DESIGN_OFF_IN_W.items():
        assert OFF["W"]["ext." + n][0] == o, ("W.ext", n)
        assert OFF["WEXT"][n][0] == o - 80, ("WEXT", n)
    for n, o in POLL_DESIGN_OFF.items():
        assert OFF["POLL"][n][0] == o, ("POLL", n)
    for n, o in S_DESIGN_OFF.items():
        assert OFF["S"][n][0] == o, ("S", n)
    for w, n in list(STATS_DESIGN_ROWS.items()) + list(STATS_DESIGN_WORDS.items()):
        assert OFF["STATS"][n][0] == 4 * w, ("STATS", n, w)
    assert set(OFF["SC"]) == set(SC_DESIGN_OFF)
    assert set(OFF["WEXT"]) == set(WEXT_DESIGN_OFF_IN_W)
    assert set(OFF["POLL"]) == set(POLL_DESIGN_OFF)
    assert set(OFF["S"]) == set(S_DESIGN_OFF)
    assert OFF["UHB"]["seg"][0] == 72 and OFF["UHB"]["nonce"][0] == 80   # 15.6, 16
    assert OFF["FILEHDR"]["nonce"][0] == 40                               # 15.6
    for r in range(NRINGS):
        assert RING_DIV4[r] * 4 == RING_RECSIZE[r]
        assert struct.calcsize(fields_fmt(RING_FIELDS[r])) == RING_RECSIZE[r]
        assert RING_ENTRIES[r] & (RING_ENTRIES[r] - 1) == 0
    assert sum(RING_ENTRIES[r] * RING_RECSIZE[r] for r in range(NRINGS)) == RINGS_TOTAL_BYTES
    assert FILEHDR_FIXED + STATS_SIZE + FILEHDR_VERSION_LEN == FILEHDR_PAYLOAD
    assert CHUNK_HDR_SIZE + FILEHDR_PAYLOAD + CHUNK_HDR_SIZE + pad_len_at(CHUNK_HDR_SIZE + FILEHDR_PAYLOAD) == FILEHDR_AREA
    assert CHUNK_HDR_SIZE + PAD_SECTOR_LEN == SECTOR == CHUNK_HDR_SIZE + pad_len_at(0)
    assert CAP_M_MAX * sum(CAP[r] * RING_RECSIZE[r] for r in range(NRINGS)) == RECS_RECORD_BYTES_MAX
    assert len(UHB_FLAG_NAMES) == 31
    assert STATS_MAGIC.to_bytes(4, 'little') == b'PSST'
    assert struct.unpack('<I', CHUNK_MAGIC)[0] == 0x4B435350
    assert uhb_seg_decode(256 << 20)["conf"] == SEG_SIZE
    assert uhb_seg_decode(3 << 20)["conf"] == 3 * 8192 + 1536
    # CRC vectors (shared with check_format.py's C run)
    assert chunk_crc(CHUNK_FILEHDR, b'123456789', 0x12345678) == 0xCBF43926
    assert chunk_crc(CHUNK_PAD, b'', 0xDEADBEEF) == 0xDEADBEEF
    if verbose:
        print("psc_format.py selftest: OK (%d structures, all offsets of DESIGN 1.2-1.5, 1.7 rows)"
              % len(RECORDS))
    return True


CRC_VECTORS = [  # (seed, data) for the C/Python cross-check
    (0, b'123456789'), (0x12345678, b'123456789'), (0xDEADBEEF, b''),
    (1, bytes(492)), (0xA5A5A5A5, bytes(range(256)) * 3),
]

if __name__ == "__main__":
    selftest()
