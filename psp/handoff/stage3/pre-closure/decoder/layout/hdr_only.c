#include "/work/work/linux/include/linux/psc_format.h"
unsigned int f(const void *p, unsigned long n);
unsigned int f(const void *p, unsigned long n) { return psc_crc32(0, p, n); }
