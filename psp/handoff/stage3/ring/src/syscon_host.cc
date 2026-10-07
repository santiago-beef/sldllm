/*
 * syscon_host.cc - compiles the REAL arch/mips/psp/ipl_sdk/syscon.c on the
 * host (Stage 3 ring test). The file is #included unmodified (the Makefile
 * checks its sha256 against stage2-trace 48dcc1b9). Two stubs, both at the
 * preprocessor level, neither touching the transaction's C statements:
 *
 *  1. MMIO. syscon.c:15 defines REG32(ADDR) as (*(vu32*)(ADDR)). This TU is
 *     C++, and the host psptypes.h makes vu32 a register proxy class, so each
 *     REG32 read or write in Syscon_cmd calls the harness's SPI/GPIO model
 *     (mmio.c) with the address. Locals of type vu32 (spin, spin_ack) stay
 *     plain words. C and C++ give the same integer semantics for every
 *     statement of this file (u8/u16 truncations, int promotions, the
 *     checksum); the language change is only the vehicle for the proxy.
 *
 *  2. The exit hand-off. syscon.c:31-61 PSC_XFER_OUT is MIPS asm that copies
 *     the six capture slots and the registers $8 (t0, the receive loop's
 *     i + 2) and $24 (t8, retry_cnt) to psc_xfer_out(). Here `__asm__` is
 *     empty and `__volatile__(...)` becomes a call that passes the same six
 *     slots (read at the `out:` label, syscon.c:309-310) and retry_cnt; the
 *     harness adds t0 from its model of the compiled receive loop
 *     (IMPLEMENTATION 9.2.5: k words -> t0 = 2k + 2, capped at 16) and calls
 *     the real psc_xfer_out(). See mmio.c psc_host_xfer_out().
 */
#include <stddef.h>
#include "psptypes.h"

extern "C" void psc_host_xfer_out(unsigned gin, unsigned spin, unsigned spin_ack,
				  unsigned dlast, unsigned st9, unsigned sttx,
				  unsigned retry_cnt);
extern "C" {
#define __asm__
#define __volatile__(...) psc_host_xfer_out((unsigned)dmy, (unsigned)spin, \
	(unsigned)spin_ack, (unsigned)dlast, (unsigned)st9, (unsigned)sttx, \
	(unsigned)retry_cnt)
#include SYSCON_C_PATH
#undef __volatile__
#undef __asm__
}
