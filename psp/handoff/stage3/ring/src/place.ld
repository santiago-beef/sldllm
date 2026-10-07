/*
 * place.ld - put four host functions at the addresses the RELEASED image has
 * for them (deploy/uClinux_TRACE/BUILD/System.map), so that psc.c's own
 * (u32)(unsigned long)Syscon_cmd etc. (stats words 20-22, psc.c:1095-1097)
 * and psc_syscon_end_calc() (psc.c:97-116) give the release values:
 *   Syscon_cmd          880ceed0  (host code 1016 B < 1072 B release slot)
 *   pspSyscon_tx_noparam 880cf300 (the release Syscon_wait address: the host
 *                       Syscon_wait does not fit the 112 B slot, so the
 *                       smallest syscon.c function marks the end of
 *                       Syscon_cmd; psc_syscon_end_calc() then returns
 *                       880cf300 as on the device)
 *   _pspSysconGetCtrl2  880cf370
 *   psc_sc_exit         880d2b04
 * All four are below 4 GB, so the u32 casts of the LP64 host are exact.
 */
SECTIONS {
  .psc_at_Syscon_cmd 0x880ceed0 : { *(.text.Syscon_cmd) }
  .psc_at_tx_noparam 0x880cf300 : { *(.text.pspSyscon_tx_noparam) }
  .psc_at_GetCtrl2 0x880cf370 : { *(.text._pspSysconGetCtrl2) }
  .psc_at_psc_sc_exit 0x880d2b04 : { *(.text.psc_sc_exit) }
} INSERT AFTER .bss;
