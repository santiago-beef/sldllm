/*
 * PSP-specific functions
 * Created by Jackson Mo, Sep 2007
 */

#include <linux/linkage.h>
#include <linux/init.h>
#include <linux/interrupt.h>
#include <linux/sched.h>
#include <linux/irq.h>
#include <linux/delay.h>
#include <asm/irq.h>
#include <asm/bootinfo.h>
#include <asm/ptrace.h>
#include <asm/branch.h>
#include <asm/psp.h>
#include <asm/ipl_sdk/syscon.h>
#include <asm/ipl_sdk/cache.h>
#include <asm/psc.h>


/*-----------------------------------------------------------------------------
 * Constants
 *---------------------------------------------------------------------------*/
#define PSP_EXCEPT_RESET      0
#define PSP_EXCEPT_EBASE      1

#define PSP_IRQ_STAT0         ( *(volatile unsigned long *)( 0xbc300000 ) )
#define PSP_IRQ_CTRL0         ( *(volatile unsigned long *)( 0xbc300008 ) )
#define PSP_IRQ_STAT1         ( *(volatile unsigned long *)( 0xbc300010 ) )
#define PSP_IRQ_CTRL1         ( *(volatile unsigned long *)( 0xbc300018 ) )

#define PSP_GPIO_SET          ( *(volatile unsigned long *)( 0xbe240008 ) )
#define PSP_GPIO_CLEAR        ( *(volatile unsigned long *)( 0xbe24000c ) )
#define PSP_GPIO_WATCHDOG     (unsigned long)( 0x8 )
#define PSP_GPIO_LED_MS       (unsigned long)( 0x40 )
#define PSP_GPIO_LED_WLAN     (unsigned long)( 0x80 )

#define PSP_COUNTS_PER_SEC    220912896   /* measured by tests */
#define PSP_COUNTS_PER_TICK   (unsigned long)( PSP_COUNTS_PER_SEC / HZ )

#define PSP_WATCHDOG_CYCLE    5   /* seconds */

#define PSP_PLAT_IRQ_CPUTIMER 66  /* Platform IRQs for PSP */

#define PSP_MEM_TEST_MAGIC    0x900df00d
#define PSP_MEM_TEST_ERROR    0xdeadbeef


/*-----------------------------------------------------------------------------
 * Macros
 *---------------------------------------------------------------------------*/
#define REG32(addr)           ( * (volatile unsigned long *)(addr) )
#if 0
#define PSP_DEBUG_PRINTF      psp_uart3_printf
#else
#define PSP_DEBUG_PRINTF      printk
#endif


/*-----------------------------------------------------------------------------
 * Static data
 *---------------------------------------------------------------------------*/
extern const char psp_debug_reset_except[];
extern const char psp_debug_reset_except_end[];
extern const char psp_debug_ebase_except[];
extern const char psp_mem_test_except[];
extern const char _end[];   /* End of the kernel */
static BOOL	s_psp_shutdown = FALSE;
/* PSC (DESIGN 1.1, 2.2): psp_watchdog_tick's localTick at file scope */
unsigned long psp_local_tick;


/*-----------------------------------------------------------------------------
 * Prototypes
 *---------------------------------------------------------------------------*/
#ifdef CONFIG_SERIAL_PSP_UART3
#ifdef CONFIG_SERIAL_PSP_UART3_EARLY_PRINTK
void __init psp_early_console_setup(void);
#endif
extern void psp_uart3_txrx_tick(void);
#endif

/* External functions */
void __init arch_early_setup(void);
void __init psp_debug_except_handler(int type_, struct pt_regs * regs_);
void __init psp_mem_test_except_handler(struct pt_regs * regs_);
void psp_show_regs(struct pt_regs * regs_);
void psp_shutdown(BOOL reboot_);
void __init psp_cache_init(void);
void psp_lcd_on(void);
void psp_led_ctrl(int led_, BOOL on_);
/* void psp_debug_watch(void * addr_, int condition_) */

/* Internal functions */
static void __init psp_debug_except_init(void);
static void __init psp_install_handler(void * base_, const void * handler_, int size_);
static void psp_cputimer_handler(void);
static void psp_watchdog_tick(void);
static void psp_pacify_watchdog(void);
static void psp_gpio_set(unsigned long mask_);
static void psp_gpio_clear(unsigned long mask_);
static unsigned long __init psp_detect_mem_size(void);
static BOOL __init psp_mem_test_addr(unsigned long addr_);

#if 1
static void psp_flush_cache_all(void);
static void __psp_flush_cache_all(void);
static void psp_flush_cache_mm(struct mm_struct *mm);
static void psp_flush_cache_range(struct vm_area_struct *vma, unsigned long start,
                                  unsigned long end);
static void psp_flush_cache_page(struct vm_area_struct *vma, unsigned long page,
                                 unsigned long pfn);
static void psp_flush_icache_range(unsigned long start, unsigned long end);
static void psp_flush_cache_sigtramp(unsigned long addr);
static void psp_local_flush_data_cache_page(void * addr);
static void psp_flush_data_cache_page(unsigned long addr);
static void psp_flush_icache_all(void);
#endif

/* System required functions */
void __init prom_init(void);
void __init plat_mem_setup(void);
void __init arch_init_irq(void);
void __init plat_timer_setup(struct irqaction * irq_);
asmlinkage void plat_irq_dispatch(void);
void __init prom_free_prom_memory(void);

/* Stub functions ... */


/*-----------------------------------------------------------------------------
 * External functions
 *---------------------------------------------------------------------------*/
void __init arch_early_setup(void)
{
  /* syscon init */
  pspSyscon_init();

  /* early printk support */
#ifdef CONFIG_SERIAL_PSP_UART3_EARLY_PRINTK
  psp_early_console_setup();
#endif

  /* early exception handling, for debugging purpose mostly */
  psp_debug_except_init();
}
/*---------------------------------------------------------------------------*/
void __init psp_debug_except_handler(int type_, struct pt_regs * regs_)
{
  PSP_DEBUG_PRINTF( "Exception (%s) occurred!\n",
                    ( type_ == PSP_EXCEPT_RESET ) ? "RESET" : "EBASE" );
  psp_show_regs( regs_ );
  psp_led_ctrl( PSP_LED_MEMSTICK | PSP_LED_WLAN, TRUE );
}
/*---------------------------------------------------------------------------*/
void __init psp_mem_test_except_handler(struct pt_regs * regs_)
{
  //psp_show_regs( regs_ );
  compute_return_epc( regs_ );
}
/*---------------------------------------------------------------------------*/
void psp_show_regs(struct pt_regs * regs_)
{
  PSP_DEBUG_PRINTF(
      "GPRs:\n"
      "  at=%08x v0=%08x v1=%08x\n"
      "  a0=%08x a1=%08x a2=%08x a3=%08x\n"
      "  t0=%08x t1=%08x t2=%08x t3=%08x\n"
      "  t4=%08x t5=%08x t6=%08x t7=%08x\n"
      "  s0=%08x s1=%08x s2=%08x s3=%08x\n"
      "  s4=%08x s5=%08x s6=%08x s7=%08x\n"
      "  t8=%08x t9=%08x\n"
      "  gp=%08x sp=%08x fp=%08x ra=%08x\n"
      "CP0 Regs:\n"
      "  status=%08x\n"
      "  hi=%08x lo=%08x\n"
      "  badvaddr=%08x\n"
      "  cause=%08x(%d)\n"
      "  epc=%08x\n"
      "\n",
      (unsigned int)regs_->regs[1],  (unsigned int)regs_->regs[2],
      (unsigned int)regs_->regs[3],  (unsigned int)regs_->regs[4],
      (unsigned int)regs_->regs[5],  (unsigned int)regs_->regs[6],
      (unsigned int)regs_->regs[7],  (unsigned int)regs_->regs[8],
      (unsigned int)regs_->regs[9],  (unsigned int)regs_->regs[10],
      (unsigned int)regs_->regs[11], (unsigned int)regs_->regs[12],
      (unsigned int)regs_->regs[13], (unsigned int)regs_->regs[14],
      (unsigned int)regs_->regs[15], (unsigned int)regs_->regs[16],
      (unsigned int)regs_->regs[17], (unsigned int)regs_->regs[18],
      (unsigned int)regs_->regs[19], (unsigned int)regs_->regs[20],
      (unsigned int)regs_->regs[21], (unsigned int)regs_->regs[22],
      (unsigned int)regs_->regs[23], (unsigned int)regs_->regs[24],
      (unsigned int)regs_->regs[25], (unsigned int)regs_->regs[28],
      (unsigned int)regs_->regs[29], (unsigned int)regs_->regs[30],
      (unsigned int)regs_->regs[31],

      (unsigned int)regs_->cp0_status,
      (unsigned int)regs_->hi,
      (unsigned int)regs_->lo,
      (unsigned int)regs_->cp0_badvaddr,
      (unsigned int)regs_->cp0_cause,
      (unsigned int)( ( regs_->cp0_cause & 0x7c ) >> 2 ),
      (unsigned int)regs_->cp0_epc );
}
/*---------------------------------------------------------------------------*/
void psp_shutdown(BOOL reboot_)
{
	s_psp_shutdown = TRUE;

#if 1
  /*
  if ( reboot_ )
  {
    (void)pspSysconResetDevice( 0 );  // It just doesn't work :(
  }
  */

  for (;;)
  {
    pspSysconPowerStandby();
  }
#else
  printk( "PSP will be shutdown in about 15 seconds\n" );
#endif
}
/*---------------------------------------------------------------------------*/
void __init psp_cache_init(void)
{
#if 1
  extern void (*flush_cache_all)(void);
  extern void (*__flush_cache_all)(void);
  extern void (*flush_cache_mm)(struct mm_struct *mm);
  extern void (*flush_cache_range)(struct vm_area_struct *vma, unsigned long start,
                                   unsigned long end);
  extern void (*flush_cache_page)(struct vm_area_struct *vma, unsigned long page,
                                  unsigned long pfn);
  extern void (*flush_icache_range)(unsigned long start, unsigned long end);
  extern void (*flush_cache_sigtramp)(unsigned long addr);
  extern void (*local_flush_data_cache_page)(void * addr);
  extern void (*flush_data_cache_page)(unsigned long addr);
  extern void (*flush_icache_all)(void);

  flush_cache_all             = psp_flush_cache_all;
  __flush_cache_all           = __psp_flush_cache_all;
  flush_cache_mm              = psp_flush_cache_mm;
  flush_cache_range           = psp_flush_cache_range;
  flush_cache_page            = psp_flush_cache_page;
  flush_icache_range          = psp_flush_icache_range;
  flush_cache_sigtramp        = psp_flush_cache_sigtramp;
  local_flush_data_cache_page = psp_local_flush_data_cache_page;
  flush_data_cache_page       = psp_flush_data_cache_page;
  flush_icache_all            = psp_flush_icache_all;
#endif
}
/*---------------------------------------------------------------------------*/
void psp_lcd_on(void)
{
  extern int console_blanked;
  extern void do_unblank_screen(int leaving_gfx);

  if ( console_blanked )
  {
    do_unblank_screen( 0 );
  }
}
/*---------------------------------------------------------------------------*/
void psp_led_ctrl(int led_, BOOL on_)
{
  unsigned long leds = 0;

  if ( led_ & PSP_LED_MEMSTICK )
    leds |= PSP_GPIO_LED_MS;

  if ( led_ & PSP_LED_WLAN )
    leds |= PSP_GPIO_LED_WLAN;

  if ( on_ )
    psp_gpio_set( leds );
  else
    psp_gpio_clear( leds );
}
/*---------------------------------------------------------------------------*/
/*
void psp_debug_watch(void * addr_, int condition_)
{
  unsigned long watchLo = 0;

  if ( addr_ )
  {
    if ( (unsigned long)addr_ & 0x7 )
    {
      printk( "WARNING: Watch address %08x is not aligned to 8\n",
                        addr_ );
    }

    watchLo = ( ( (unsigned long)addr_ & 0xfffffff8 ) | condition_ );
  }

  __asm__ __volatile__ (
    "mtc0 %0, $18\n"
    "mtc0 $0, $19\n"
    : : "r"( watchLo )
  );
}
*/


/*-----------------------------------------------------------------------------
 * Internal functions
 *---------------------------------------------------------------------------*/
static void __init psp_debug_except_init(void)
{
  /* Install reset handler */
  psp_install_handler( (void *)PSP_RESET_VEC_BASE,
                       psp_debug_reset_except,
                       psp_debug_reset_except_end - psp_debug_reset_except );

  /* Install ebase handler */
  __asm__ __volatile__ (
    "mtc0 %0, $25\n"
    :
    : "r"( psp_debug_ebase_except )
  );
}
/*---------------------------------------------------------------------------*/
static void __init psp_install_handler
(
  void * base_,
  const void * handler_,
  int size_
)
{
  char * w;
  const char * r;

  if ( unlikely( base_ == NULL || handler_ == NULL || size_ <= 0 ) )
  {
    return;
  }

  w = (char *)base_;
  r = (const char *)handler_;
  while ( size_ > 0 )
  {
    *w++ = *r++;
    --size_;
  }
}
/*---------------------------------------------------------------------------*/
static void psp_cputimer_handler(void)
{
  unsigned long c_pre;

  /* PSC (DESIGN 2.3 T1): Count before the reset = length of the tick that ended */
  __asm__ __volatile__ ( "mfc0 %0, $9\n" : "=r"( c_pre ) );

  /* Reset timer */
  __asm__ __volatile__ (
    "mtc0 $0, $9\n"   /* Reset the counter */
    "mfc0 $2, $11\n"  /* Reset the compare register to clear the timer interrupt */
    "mtc0 $2, $11\n"
    : : : "$2"
  );
  psc_k.c_pre_cur = c_pre;	/* PSC 2.3 T1: for the W extension (1.3) */
  
  /* Pacify the watchdog here */
  psp_watchdog_tick();

  /* PSC (DESIGN 2.3 T2): accounting, lc words, once-a-second panel and guards */
  psc_tick_hook( c_pre );

#ifdef CONFIG_SERIAL_PSP_UART3
  /* Activate the UART3 TX thread */
  psp_uart3_txrx_tick();
#endif

  /* Invoke the system IRQ handling */
  do_IRQ( PSP_PLAT_IRQ_CPUTIMER );
}
/*---------------------------------------------------------------------------*/
static void psp_watchdog_tick(void)
{
  static unsigned long lastTick = 0;

  psp_local_tick++;
  if ( psp_local_tick - lastTick >= ( PSP_WATCHDOG_CYCLE * HZ ) )
  {
    lastTick = psp_local_tick;
    psc_k.wd_ctx = PSC_WDCTX_TIMER;	/* PSC (DESIGN 1.8, 2.2) */
    psp_pacify_watchdog();
    psc_k.wd_ctx = PSC_WDCTX_NONE;
  }
}
/*---------------------------------------------------------------------------*/
void psp_pacify_watchdog(void)
{
	if ( s_psp_shutdown )
	{
		printk( "Stop pacifying watchdog\n" );
		return;
	}	

#if 1
  pspSysconNop();
#else
  psp_gpio_clear( PSP_GPIO_WATCHDOG );
  psp_gpio_set( PSP_GPIO_WATCHDOG );
#endif
}
/*---------------------------------------------------------------------------*/
static void psp_gpio_set(unsigned long mask_)
{
  /* PSC (DESIGN 2.4): the same single load and store, then the read-back */
  unsigned long v = PSP_GPIO_SET;
  PSP_GPIO_SET = v | mask_;
  barrier();
  psc_note_led( 1, v );
}
/*---------------------------------------------------------------------------*/
static void psp_gpio_clear(unsigned long mask_)
{
  /* PSC (DESIGN 2.4): the same single load and store, then the read-back */
  unsigned long v = PSP_GPIO_CLEAR;
  PSP_GPIO_CLEAR = v | mask_;
  barrier();
  psc_note_led( 0, v );
}
/*---------------------------------------------------------------------------*/
static unsigned long __init psp_detect_mem_size(void)
{
  unsigned long savedEBase;
  unsigned long blockStart;
  unsigned long blockEnd;
  unsigned long memSize;

  //local_irq_disable();

  /* Save and modify EBase register */
  __asm__ __volatile__ (
    "mfc0 $2, $25\n"
    "sw   $2, %0\n"
    "la   $2, %1\n"
    "mtc0 $2, $25\n"
    : "=m"( savedEBase )
    : "i"( psp_mem_test_except )
    : "$2"
  );

  for ( blockStart = ( (unsigned long)_end & ~( SZ_1M - 1 ) ) + SZ_1M;
        ;
        blockStart += SZ_1M )
  {
    /* Test the start of the 1M block */
    if ( !psp_mem_test_addr( blockStart ) )
      break;

    /* Test the end of the block */
    blockEnd = blockStart + SZ_1M - sizeof( unsigned long );
    if ( !psp_mem_test_addr( blockEnd ) )
      break;
  }

  /* Restore Status and EBase register */
  __asm__ __volatile__ (
    "lw   $2, %0\n"
    "mtc0 $2, $25\n"
    :
    : "m"( savedEBase )
    : "$2"
  );

  //local_irq_enable();

  memSize = blockStart - PSP_RAM_BASE;

  return memSize;
}
/*---------------------------------------------------------------------------*/
static BOOL __init psp_mem_test_addr(unsigned long addr_)
{
  unsigned long k0;
  unsigned long temp;

  /* Test reading from the address */
  __asm__ __volatile__ ( "move $26, $0\n" );  /* k0 = 0 */
  temp = REG32( addr_ );
  __asm__ __volatile__ ( "move %0, $26\n" : "=r"( k0 ) );

  if ( PSP_MEM_TEST_ERROR == k0 )
  {
    return FALSE;
  }

  /* Test writing to the address */
  __asm__ __volatile__ ( "move $26, $0\n" );  /* k0 = 0 */
  REG32( addr_ ) = PSP_MEM_TEST_MAGIC;
  __asm__ __volatile__ ( "move %0, $26\n" : "=r"( k0 ) );
  if ( PSP_MEM_TEST_ERROR == k0 ||
       PSP_MEM_TEST_MAGIC != REG32( addr_ ) )
  {
    return FALSE;
  }

  REG32( addr_ ) = temp;
  return TRUE;
}
/*---------------------------------------------------------------------------*/
#if 1
static void psp_flush_cache_all(void)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void __psp_flush_cache_all(void)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_cache_mm(struct mm_struct *mm)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_cache_range(struct vm_area_struct *vma, unsigned long start,
                                  unsigned long end)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_cache_page(struct vm_area_struct *vma, unsigned long page,
                                 unsigned long pfn)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_icache_range(unsigned long start, unsigned long end)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_cache_sigtramp(unsigned long addr)
{
  pspClearDcache();
  pspClearIcache();
}
/*---------------------------------------------------------------------------*/
static void psp_local_flush_data_cache_page(void * addr)
{
  pspClearDcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_data_cache_page(unsigned long addr)
{
  pspClearDcache();
}
/*---------------------------------------------------------------------------*/
static void psp_flush_icache_all(void)
{
  pspClearDcache();
  pspClearIcache();
}
#endif


/*-----------------------------------------------------------------------------
 * start_kernel -> setup_arch -> prom_init
 *---------------------------------------------------------------------------*/
void __init prom_init(void)
{
  /* Pacify watchdog the first time here */
  psc_k.wd_ctx = PSC_WDCTX_BOOT;	/* PSC (DESIGN 1.8, 2.2): origin WB */
  psp_pacify_watchdog();
  psc_k.wd_ctx = PSC_WDCTX_NONE;

  /* Nullify Epc and ErrEpc */
  __asm__ __volatile__ (
    "mtc0 $0, $14\n"
    "mtc0 $0, $30\n"
  );

  /* Disable all memory accessing protection */
  REG32( 0xbc000000 ) = 0xffffffff;   /* 0x08000000 -> 0x081ffffff */
  REG32( 0xbc000004 ) = 0xffffffff;   /* 0x08200000 -> 0x083ffffff */
  REG32( 0xbc000008 ) = 0xffffffff;   /* 0x08400000 -> 0x085ffffff */
  REG32( 0xbc00000c ) = 0xffffffff;   /* 0x08600000 -> 0x087ffffff */

  /* Setup arcs_cmdline */
  if ( fw_arg2 != 0 )
  {
    strlcpy( arcs_cmdline, (const char *)fw_arg2, CL_SIZE );
  }
}
/*-----------------------------------------------------------------------------
 * start_kernel -> setup_arch -> arch_mem_init -> plat_mem_setup
 *---------------------------------------------------------------------------*/
void __init plat_mem_setup(void)
{ 
  /* Set up boot_mem_map */
  boot_mem_map.nr_map = 1;
  boot_mem_map.map[ 0 ].addr = PSP_RAM_BASE;
  boot_mem_map.map[ 0 ].size = psp_detect_mem_size();
  boot_mem_map.map[ 0 ].type = BOOT_MEM_RAM;
}
/*-----------------------------------------------------------------------------
 * start_kernel -> init_IRQ -> arch_init_irq
 *---------------------------------------------------------------------------*/
void __init arch_init_irq(void)
{
  /* Disable all cascade IRQ from IP2 */
  PSP_IRQ_CTRL0 = 0x0;
  PSP_IRQ_CTRL1 = 0x0;
}
/*-----------------------------------------------------------------------------
 * start_kernel -> time_init -> plat_timer_setup
 *---------------------------------------------------------------------------*/
void __init plat_timer_setup(struct irqaction * irq_)
{
  int ret;

  if ( unlikely( irq_ == NULL ) )
  {
    panic( "Invalid IRQ action in plat_timer_setup" );
    return;
  }

  /* Initialize timer */
  __asm__ __volatile__ (
    "mtc0 $0, $9\n"
    "li   $2, %0\n"
    "mtc0 $2, $11\n"
    :
    : "i"( PSP_COUNTS_PER_TICK )
    : "$2"
  );

  ret = set_irq_chip( PSP_PLAT_IRQ_CPUTIMER, &dummy_irq_chip );
  if ( ret < 0 )
  {
    printk( "Failed to setup cputimer chip, err=%d\n", ret );
    return;
  }

  ret = setup_irq( PSP_PLAT_IRQ_CPUTIMER, irq_ );
  if ( ret < 0 )
  {
    printk( "Failed to setup cputimer IRQ, err=%d\n", ret );
    return;
  }
}
/*-----------------------------------------------------------------------------
 * handle_int(genex.S) -> plat_irq_dispatch
 *---------------------------------------------------------------------------*/
asmlinkage void plat_irq_dispatch(void)
{
	unsigned int pending = read_c0_status() & read_c0_cause() & ST0_IM;

  if ( pending & CAUSEF_IP7 )   /* timer */
  {
    psp_cputimer_handler();
    pending &= ~CAUSEF_IP7;
  }

  if ( pending )
  {
    printk( "Unknown IRQ: pend=%08x st0=%08x st1=%08x\n",
            pending,
            (unsigned int)PSP_IRQ_STAT0,
            (unsigned int)PSP_IRQ_STAT1 );
  }
}
/*-----------------------------------------------------------------------------
 * kernel_init -> init_post -> free_initmem -> prom_free_prom_memory
 *---------------------------------------------------------------------------*/
void __init prom_free_prom_memory(void)
{
}
/*-----------------------------------------------------------------------------
 * show_cpuinfo -> get_system_type
 *---------------------------------------------------------------------------*/
const char *get_system_type(void)
{
	return "Jackson\'s PSP";
}


/*-----------------------------------------------------------------------------
 * Stub functions
 *---------------------------------------------------------------------------*/
/*struct vm_struct *get_vm_area(unsigned long size, unsigned long flags)*/
void * get_vm_area(unsigned long size, unsigned long flags)
{
  printk( "*** calling get_vm_area\n" );
  return NULL;
}
/*---------------------------------------------------------------------------*/
/* struct vm_struct * remove_vm_area(void *addr) */
void * remove_vm_area(void * addr)
{
  printk( "*** calling remove_vm_area\n" );
  return NULL;
}
/*---------------------------------------------------------------------------*/
/* typedef unsigned long   pgd_t; */
typedef unsigned long   pud_t;
typedef unsigned long   pmd_t;
/*---------------------------------------------------------------------------*/
pud_t * pud_alloc(struct mm_struct *mm, pgd_t * pgd, unsigned long address)
{
  printk( "*** calling pud_alloc\n" );
  return NULL;
}
/*---------------------------------------------------------------------------*/
pmd_t * pmd_alloc(struct mm_struct *mm, pud_t * pud, unsigned long address)
{
  printk( "*** calling pmd_alloc\n" );
  return NULL;
}
/*---------------------------------------------------------------------------*/
int __pte_alloc_kernel(pmd_t *pmd, unsigned long address)
{
  printk( "*** calling __pte_alloc_kernel\n" );
  return 0;
}


/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
