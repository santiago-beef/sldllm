#ifndef __PSPTYPES_H__
#define __PSPTYPES_H__
/*
 * Host psptypes.h for the Stage 3 ring test. Same scalar typedefs as the
 * build's shim (/home/ubuntu/psp/build/pspsdk/include/psptypes.h). One
 * difference, the MMIO stub: when compiled as C++ (only syscon_host.cc does),
 * vu32 is a register proxy, so that syscon.c's own unmodified
 *     #define REG32(ADDR) (*(vu32*)(ADDR))          (syscon.c:15)
 * reaches the harness's SPI/GPIO model (mmio.c) on every access, as a read or
 * a write. A vu32 object that is not at a register address (syscon.c's
 * locals `vu32 spin`, `vu32 spin_ack`, Syscon_wait's `vu32 dmy`) behaves as a
 * plain volatile word. In C, vu32 is the shim's `volatile unsigned int`.
 */
typedef unsigned char       u8;
typedef unsigned short      u16;
typedef unsigned int        u32;
typedef unsigned long long  u64;
typedef signed char         s8;
typedef signed short        s16;
typedef signed int          s32;
typedef signed long long    s64;
typedef volatile unsigned char       vu8;
typedef volatile unsigned short      vu16;
typedef volatile unsigned long long  vu64;
typedef volatile signed char         vs8;
typedef volatile signed short        vs16;
typedef volatile signed int          vs32;
typedef volatile signed long long    vs64;

#ifdef __cplusplus
extern "C" unsigned int psc_host_mmio_rd(unsigned long addr);
extern "C" void psc_host_mmio_wr(unsigned long addr, unsigned int val);
extern "C" int psc_host_is_mmio(unsigned long addr);

struct psc_host_reg32 {
	volatile unsigned int v;	/* storage when not a register */
	psc_host_reg32() {}
	psc_host_reg32(unsigned int x) : v(x) {}
	__attribute__((noinline)) unsigned int rd() const
	{
		unsigned long a = (unsigned long)this;
		if (psc_host_is_mmio(a))
			return psc_host_mmio_rd(a);
		return v;
	}
	__attribute__((noinline)) void wr(unsigned int x)
	{
		unsigned long a = (unsigned long)this;
		if (psc_host_is_mmio(a))
			psc_host_mmio_wr(a, x);
		else
			v = x;
	}
	operator unsigned int() const { return rd(); }
	psc_host_reg32 &operator=(unsigned int x) { wr(x); return *this; }
	psc_host_reg32 &operator|=(unsigned int x) { wr(rd() | x); return *this; }
	psc_host_reg32 &operator&=(unsigned int x) { wr(rd() & x); return *this; }
	psc_host_reg32 &operator^=(unsigned int x) { wr(rd() ^ x); return *this; }
	unsigned int operator--(int) { unsigned int o = rd(); wr(o - 1u); return o; }
};
typedef psc_host_reg32 vu32;
#else
typedef volatile unsigned int        vu32;
#endif

typedef float  f32;
typedef double f64;
#endif /* __PSPTYPES_H__ */
