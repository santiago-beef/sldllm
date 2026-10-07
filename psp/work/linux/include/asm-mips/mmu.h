#ifndef __ASM_MMU_H
#define __ASM_MMU_H

#include <linux/autoconf.h>

#ifdef CONFIG_MMU

typedef unsigned long mm_context_t[NR_CPUS];
#define MM_CONTEXT( mm )    ( (mm)->context )

#else

typedef struct
{
  unsigned long           context;
	struct vm_list_struct	* vmlist;
	unsigned long		        end_brk;
} mm_context_t[NR_CPUS];

#define MM_CONTEXT( mm )    ( (mm)->context[ smp_processor_id() ] )

#endif

#endif /* __ASM_MMU_H */
