/*
 * PSP-specific functions
 * Created by Jackson Mo, Sep 2007
 */

#include <asm/regdef.h>
#include <asm/mipsregs.h>
#include <asm/stackframe.h>


/*-----------------------------------------------------------------------------
 * Constants
 *---------------------------------------------------------------------------*/
#define PSP_MEM_TEST_ERROR    0xdeadbeef


/*-----------------------------------------------------------------------------
 * Reset, Soft Reset, and NMI exceptions
 *---------------------------------------------------------------------------*/
  .globl psp_debug_reset_except
  .align 4
psp_debug_reset_except:
  SAVE_ALL
  move  a0, zero    /* RESET */
  move  a1, sp
  jal   psp_debug_except_handler
  b     .

  .globl psp_debug_reset_except_end
psp_debug_reset_except_end:

  
/*-----------------------------------------------------------------------------
 * Other exceptions
 *---------------------------------------------------------------------------*/
  .globl psp_debug_ebase_except
  .align 4
psp_debug_ebase_except:
  SAVE_ALL
  li    a0, 0x1   /* EBASE */
  move  a1, sp
  jal   psp_debug_except_handler
  b     .


/*-----------------------------------------------------------------------------
 * For memory testing
 *---------------------------------------------------------------------------*/
  .globl psp_mem_test_except
  .align 4
psp_mem_test_except:
  SAVE_ALL
  move  a0, sp
  jal   psp_mem_test_except_handler
  RESTORE_ALL
  li    k0, PSP_MEM_TEST_ERROR
  eret


/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
