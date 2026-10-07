/*
 * Another uClinux port for Sony PlayStation Portable 
 * Created by Jackson Mo, Aug 30, 2007
 */
#ifndef PSP_H
#define PSP_H
/*---------------------------------------------------------------------------*/
#include <linux/kernel.h>


/*-----------------------------------------------------------------------------
 * Constants
 *---------------------------------------------------------------------------*/
#ifndef BOOL
#define BOOL    int
#endif
#ifndef TRUE
#define TRUE    1
#endif
#ifndef FALSE
#define FALSE   0
#endif

#define SZ_1K                   0x00000400
#define SZ_1M                   ( SZ_1K * SZ_1K )
#define PSP_RAM_BASE            (unsigned long)( 0x08000000 + CONFIG_PSP_ADDRESS_BASE )
#define PSP_RESET_VEC_BASE      (unsigned long)( 0xbfc00000 )
#define PSP_RAMFS_SIZE          (unsigned long)( 2 * SZ_1M )
#define PSP_SCR_WIDTH           480
#define PSP_SCR_HEIGHT          272
#define PSP_SCR_VIRTUAL_WIDTH   512
#define PSP_SCR_VIRTUAL_HEIGHT  272
#define PSP_SCR_PIXEL_SIZE      sizeof( unsigned long )
#define PSP_DEFAULT_FONT_WIDTH  6
#define PSP_DEFAULT_FONT_HEIGHT 8
#define PSP_VRAM_BASE           (unsigned long *)( 0x04000000 + CONFIG_PSP_ADDRESS_BASE )
#define PSP_VRAM_SIZE           ( PSP_SCR_VIRTUAL_WIDTH * PSP_SCR_VIRTUAL_HEIGHT * PSP_SCR_PIXEL_SIZE )

/* LED */
#define PSP_LED_MEMSTICK        1
#define PSP_LED_WLAN            2

/*
#define PSP_WATCH_READ      0x2
#define PSP_WATCH_WRITE     0x1
*/


/*-----------------------------------------------------------------------------
 * Type definitions
 *---------------------------------------------------------------------------*/


/*-----------------------------------------------------------------------------
 * Extern data
 *---------------------------------------------------------------------------*/
extern struct boot_mem_map boot_mem_map;


/*-----------------------------------------------------------------------------
 * Extern functions
 *---------------------------------------------------------------------------*/
/* serial_pspuart3.c */
extern void psp_uart3_setbaud(int baud_);
extern int psp_uart3_puts(const char * str_);
extern int psp_uart3_printf(const char * fmt_, ...);

/* psp.c */
extern void __init arch_early_setup(void);
extern void psp_show_regs(struct pt_regs * regs_);
extern void psp_shutdown(BOOL reboot_);
extern void __init psp_cache_init(void);
extern void psp_lcd_on(void);
extern void psp_led_ctrl(int led_, BOOL on_);
/* extern void psp_debug_watch(void * addr_, int condition_); */


/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
#endif
