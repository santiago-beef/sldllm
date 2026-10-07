/*
 * PSP serial driver
 * Created by Jackson Mo, Aug 2007
 */

#include <linux/console.h>
#include <linux/serial_core.h>
#include <asm/psp.h>
#include <asm/semaphore.h>
#include <asm/ipl_sdk/syscon.h>
#include <asm/ipl_sdk/psp_uart.h>

#ifdef CONFIG_VT_CONSOLE
#include <linux/kd.h>
#include <linux/console_struct.h>
#include <linux/kbd_kern.h>
#endif

//#define DEBUG   1

#ifdef DEBUG
#define DPUTS(args)     psp_uart3_puts args       /* use it like DPUTS((...)); */
#define DPRINTF(args)   psp_uart3_printf args
#else
#define DPUTS(args)
#define DPRINTF(args)
#endif


/*-----------------------------------------------------------------------------
 * Type definitions
 *---------------------------------------------------------------------------*/
typedef struct
{
  struct semaphore sem;
  long txThreadId;
  volatile BOOL txStarted;
  volatile BOOL rxStopped;
  volatile BOOL shutdown;
} PspPortDataType;


/*-----------------------------------------------------------------------------
 * Constants
 *---------------------------------------------------------------------------*/
#define PSP_SERIAL_NAME         "ttySRC"
#define PSP_SERIAL_MAJOR        4
#define PSP_SERIAL_MINOR        200
#define PSP_SERIAL_NUM_PORTS    3

/* Port types */
#define PORT_PSP_UART3          202

/* UART3 */
#define PSP_UART3_DEFAULT_BAUD  115200
#define PSP_UART3_IOBASE        0xbe500000
#define PSP_UART3_RXBUF         ( *(volatile char *)PSP_UART3_IOBASE )
#define PSP_UART3_TXBUF         ( *(volatile char *)PSP_UART3_IOBASE )
#define PSP_UART3_STATUS        ( *(volatile unsigned long *)0xbe500018 )
#define PSP_UART3_DIV1          ( *(volatile unsigned long *)0xbe500024 )
#define PSP_UART3_DIV2          ( *(volatile unsigned long *)0xbe500028 )
#define PSP_UART3_CTRL          ( *(volatile unsigned long *)0xbe50002c )
#define PSP_UART3_MASK_RXEMPTY  ( (unsigned long)0x00000010 )
#define PSP_UART3_MASK_TXFULL   ( (unsigned long)0x00000020 )
#define PSP_UART3_MASK_SETBAUD  ( (unsigned long)0x00000060 )
#define PSP_UART3_BUF_MAX       1024
#define PSP_UART3_LINE          2
#define PSP_UART3_WAIT_OP
#define PSP_UART3_WAIT_RX()     { while ( PSP_UART3_STATUS & PSP_UART3_MASK_RXEMPTY ) PSP_UART3_WAIT_OP; }
#define PSP_UART3_WAIT_TX()     { while ( PSP_UART3_STATUS & PSP_UART3_MASK_TXFULL ) PSP_UART3_WAIT_OP; }


/*-----------------------------------------------------------------------------
 * Prototypes
 *---------------------------------------------------------------------------*/
/* Export functions */
void psp_uart3_setbaud(int baud_);
int psp_uart3_puts(const char * str_);
int psp_uart3_printf(const char * fmt_, ...);
void psp_uart3_txrx_tick(void);
#ifdef CONFIG_SERIAL_PSP_UART3_EARLY_PRINTK
void __init psp_early_console_setup(void);
#endif

/* UART3 functions */
static int __init psp_serial_console_init(void);
static int __init psp_uart3_setup(char * options_);
static int psp_uart3_write(const char * buf_, int size_);
static void psp_uart3_tx_chars(struct uart_port * port_);
static void psp_uart3_rx_chars(struct uart_port * port_);

/* Port driver functions */
static unsigned int psp_uart3_tx_empty(struct uart_port * port_);
static void psp_uart3_set_mctrl(struct uart_port * port_, unsigned int mctrl_);
static unsigned int  psp_uart3_get_mctrl(struct uart_port * port_);
static void psp_uart3_start_tx(struct uart_port * port_);
static void psp_uart3_stop_tx(struct uart_port * port_);
static void psp_uart3_send_xchar(struct uart_port * port_, char ch_);
static void psp_uart3_stop_rx(struct uart_port * port_);
static void psp_uart3_enable_ms(struct uart_port * port_);
static void psp_uart3_break_ctl(struct uart_port * port_, int ctl_);
static int psp_uart3_startup(struct uart_port * port_);
static void psp_uart3_shutdown(struct uart_port * port_);
static void psp_uart3_set_termios(struct uart_port * port_, struct ktermios * new_, struct ktermios * old_);
static void psp_uart3_pm(struct uart_port * port_, unsigned int state_, unsigned int oldstate_);
static int psp_uart3_set_wake(struct uart_port * port_, unsigned int state_);
static const char * psp_uart3_type(struct uart_port * port_);
static void psp_uart3_release_port(struct uart_port * port_);
static int psp_uart3_request_port(struct uart_port * port_);
static void psp_uart3_config_port(struct uart_port * port_, int flags_);
static int psp_uart3_verify_port(struct uart_port * port_, struct serial_struct * ser_);
static int psp_uart3_ioctl(struct uart_port * port_, unsigned int req_, unsigned long arg_);

/* TX thread */
static int psp_port_txrx_thread(struct uart_port * port_);

/* Serial console functions */
static void psp_serial_console_write
(
  struct console * console_,
  const char * buf_,
  unsigned int size_
);
static int psp_serial_console_setup
(
  struct console * console_,
  char * options_
);

/* Serial driver functions */
static int  __init psp_serial_modinit(void);
static void __exit psp_serial_modexit(void);


/*-----------------------------------------------------------------------------
 * Static data
 *---------------------------------------------------------------------------*/
#ifdef CONFIG_VT_CONSOLE
extern struct vc vc_cons[];
extern int fg_console;
#endif

static struct uart_driver s_psp_serial_drv;

static struct console s_psp_serial_console =
{
  .name    = PSP_SERIAL_NAME,

  .write  = psp_serial_console_write,
  .device = uart_console_device,        /* Implemented in serial_core.c */
  .setup  = psp_serial_console_setup,
  
  .flags  = CON_PRINTBUFFER,
  .index  = PSP_UART3_LINE,

  .data    = &s_psp_serial_drv
};

static struct uart_driver s_psp_serial_drv =
{
  .owner        = THIS_MODULE,
  .driver_name  = PSP_SERIAL_NAME,
  .dev_name      = "PSP Serial",
  .major        = PSP_SERIAL_MAJOR,
  .minor        = PSP_SERIAL_MINOR,
  .nr            = PSP_SERIAL_NUM_PORTS,
  .cons          = &s_psp_serial_console
};

static struct uart_ops s_psp_uart3_ops =
{
  .tx_empty      = psp_uart3_tx_empty,
  .set_mctrl    = psp_uart3_set_mctrl,
  .get_mctrl    = psp_uart3_get_mctrl,
  .stop_tx      = psp_uart3_stop_tx,
  .start_tx      = psp_uart3_start_tx,
  .send_xchar    = psp_uart3_send_xchar,
  .stop_rx      = psp_uart3_stop_rx,
  .enable_ms    = psp_uart3_enable_ms,
  .break_ctl    = psp_uart3_break_ctl,
  .startup      = psp_uart3_startup,
  .shutdown      = psp_uart3_shutdown,
  .set_termios  = psp_uart3_set_termios,
  .pm            = psp_uart3_pm,
  .set_wake      = psp_uart3_set_wake,
  .type          = psp_uart3_type,
  .release_port = psp_uart3_release_port,
  .request_port = psp_uart3_request_port,
  .config_port  = psp_uart3_config_port,
  .verify_port  = psp_uart3_verify_port,
  .ioctl        = psp_uart3_ioctl
};

static PspPortDataType s_psp_uart3_port_data =
{
  //.sem
  .txThreadId = -1,
  .txStarted  = FALSE,
  .rxStopped  = FALSE,
  .shutdown    = TRUE   /* to prevent the tick function from running at the beginning */
};

struct uart_port s_psp_serial_ports[ PSP_SERIAL_NUM_PORTS ] =
{
  /* UART3 */
  [ PSP_UART3_LINE ] = {
    .lock          = __SPIN_LOCK_UNLOCKED( s_psp_serial_ports[ 2 ].lock ),
    .iobase        = PSP_UART3_IOBASE,
    .membase      = (char *)( PSP_UART3_IOBASE ),
    .irq          = 0,
    .uartclk      = 0,
    .fifosize      = 16,
    .iotype        = UPIO_MEM,
    .cons          = &s_psp_serial_console,
    .flags        = UPF_BOOT_AUTOCONF,
    /* type must be set in the config function */
    /* .type        = PORT_PSP_UART3, */
    .ops          = &s_psp_uart3_ops,
    .line          = PSP_UART3_LINE,
    .mapbase      = PSP_UART3_IOBASE,
    .private_data = &s_psp_uart3_port_data
  }
};


/*-----------------------------------------------------------------------------
 * Export functions
 *---------------------------------------------------------------------------*/
void psp_uart3_setbaud(int baud_)
{
  int div1, div2;

  //div1 = 96000000 / baud_; 
  switch ( baud_ )
  {
    case 115200:
      div1 = 96000000 / 115200;
      break;
    
    case 9600:
    default:
      div1 = 96000000 / 9600;
      break;
  }

  div2 = div1 & 0x3F;
  div1 >>= 6;

  PSP_UART3_DIV1 = div1;
  PSP_UART3_DIV2 = div2;
  PSP_UART3_CTRL = PSP_UART3_MASK_SETBAUD;
}
/*---------------------------------------------------------------------------*/
int psp_uart3_puts(const char * str_)
{
  int len = 0;

  if ( str_ == NULL )
  {
    return 0;
  }

  while ( str_[ len ] != 0 )
  {
    ++len;
  }

  return psp_uart3_write( str_, len );
}
/*---------------------------------------------------------------------------*/
int psp_uart3_printf(const char * fmt_, ...)
{
  char buf[ PSP_UART3_BUF_MAX ];
  int len;
  va_list args;

  va_start( args, fmt_ );
  len = vsnprintf( buf, PSP_UART3_BUF_MAX, fmt_, args );
  va_end( args );

  return psp_uart3_write( buf, len );
}
/*---------------------------------------------------------------------------*/
void psp_uart3_txrx_tick(void)
{
  if ( !s_psp_uart3_port_data.shutdown &&
       ( s_psp_uart3_port_data.txStarted ||
         ( !s_psp_uart3_port_data.rxStopped &&
           !( PSP_UART3_STATUS & PSP_UART3_MASK_RXEMPTY ) ) ) )
  {
    up( &s_psp_uart3_port_data.sem );
  }
}
/*---------------------------------------------------------------------------*/
#ifdef CONFIG_SERIAL_PSP_UART3_EARLY_PRINTK
void __init psp_early_console_setup(void)
{
  s_psp_serial_console.flags |= CON_ENABLED;
  (void)psp_serial_console_init();
}
#endif


/*-----------------------------------------------------------------------------
 * UART3 functions
 *---------------------------------------------------------------------------*/
#ifdef CONFIG_SERIAL_PSP_UART3_CONSOLE
static int __init psp_serial_console_init(void)
{
  static BOOL s_initialized = FALSE;

  if ( s_initialized )
  {
    /* Console has already been initialized */
    return 0;
  }

  register_console( &s_psp_serial_console );

  s_initialized = TRUE;
  return 0;
}
console_initcall( psp_serial_console_init );
#endif
/*---------------------------------------------------------------------------*/
static int __init psp_uart3_setup(char * options_)
{
  static int baud = 0;
#ifdef CONFIG_SERIAL_PSP_UART3_CONSOLE
  int bits;      /* 8 */
  int parity;    /* 'n' */
  int flow;      /* 'n' */
#endif

  if ( baud != 0 )
  {
    /* The baudrate has already been set */
    return 0;
  }

  baud = PSP_UART3_DEFAULT_BAUD;

#ifdef CONFIG_SERIAL_PSP_UART3_CONSOLE
  if ( options_ != NULL )
  {
    uart_parse_options( options_, &baud, &parity, &bits, &flow );
  }
#endif

  /* remote control power on */
#if 1
  pspSysconCtrlHRPower( 1 );
  psp_uart_init( baud );
#else
  psp_uart3_setbaud( baud );
#endif

  printk( "PSP UART3 driver (NEW), baud=%d\n", baud );
  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_uart3_write(const char * buf_, int size_)
{
  int bytesToWrite = size_;

  if ( unlikely( buf_ == NULL || size_ <= 0 ) )
  {
    return 0;
  }

  while ( bytesToWrite-- > 0 )
  {
    if ( *buf_ == '\n' )
    {
      PSP_UART3_WAIT_TX();
      PSP_UART3_TXBUF = '\r';
    }

    PSP_UART3_WAIT_TX();
    PSP_UART3_TXBUF = *buf_++;
  }
  
  return size_;
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_tx_chars(struct uart_port * port_)
{
  struct circ_buf * xmit = &( port_->info->xmit );
  int count;

  if ( unlikely( port_ == NULL ) )
  {
    return;
  }

  if ( port_->x_char )
  {
    if ( likely( !( PSP_UART3_STATUS & PSP_UART3_MASK_TXFULL ) ) )
    {
      psp_uart3_send_xchar( port_, port_->x_char );
      port_->icount.tx++;
      port_->x_char = 0;
    }
    return;
  }

  if ( uart_circ_empty( xmit ) || uart_tx_stopped( port_ ) )
  {
    psp_uart3_stop_tx( port_ );
    return;
  }

  count = ( port_->fifosize >> 1 );
  while ( count-- > 0 && likely( !( PSP_UART3_STATUS & PSP_UART3_MASK_TXFULL ) ) )
  {
    PSP_UART3_TXBUF = xmit->buf[ xmit->tail ];

    xmit->tail = ( xmit->tail + 1 ) & ( UART_XMIT_SIZE - 1 );
    port_->icount.tx++;

    if ( uart_circ_empty( xmit ) )
    {
      psp_uart3_stop_tx( port_ );
      break;
    }
  }

  if ( uart_circ_chars_pending( xmit ) < WAKEUP_CHARS )
  {
    uart_write_wakeup( port_ );
  }
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_rx_chars(struct uart_port * port_)
{
  unsigned char ch;
#ifdef CONFIG_VT_CONSOLE
  struct tty_struct * tty;
#endif

  if ( unlikely( PSP_UART3_STATUS & PSP_UART3_MASK_RXEMPTY ) )
  {
    return;
  }

  /* take the char out of the port */
  ch = (unsigned char)PSP_UART3_RXBUF;
  //psp_uart3_printf( "(%d)=%c\n", ch, ch );

#ifdef CONFIG_SERIAL_PSP_UART3_CONSOLE
  /* send the char to serial tty */
  if ( port_ != NULL && port_->info != NULL && port_->info->tty != NULL )
  {
    struct tty_struct * tty = port_->info->tty;
    tty_insert_flip_char( tty, ch, TTY_NORMAL );
    tty_schedule_flip( tty );
  }
#endif

#ifdef CONFIG_VT_CONSOLE
  if ( vc_cons[ fg_console ].d != NULL &&
       ( tty = vc_cons[ fg_console ].d->vc_tty ) != NULL )
  {
    tty_insert_flip_char( tty, ch, TTY_NORMAL );
    //tty_schedule_flip( tty );
    con_schedule_flip( tty );
  }
#endif
}


/*-----------------------------------------------------------------------------
 * Port driver functions
 *---------------------------------------------------------------------------*/
static unsigned int psp_uart3_tx_empty(struct uart_port * port_)
{
  return !( PSP_UART3_STATUS & PSP_UART3_MASK_TXFULL );
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_set_mctrl(struct uart_port * port_, unsigned int mctrl_)
{
  /* Not supported yet */
  DPUTS(( "+++ set_mctrl\n" ));
}
/*---------------------------------------------------------------------------*/
static unsigned int psp_uart3_get_mctrl(struct uart_port * port_)
{
  /* Not supported yet */
  DPUTS(( "+++ get_mctrl\n" ));
  return 0;
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_start_tx(struct uart_port * port_)
{
  PspPortDataType * portData;

  if ( port_ != NULL && port_->private_data != NULL )
  {
    portData = (PspPortDataType *)port_->private_data;
    portData->txStarted = TRUE;
  }
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_stop_tx(struct uart_port * port_)
{
  PspPortDataType * portData;

  if ( port_ != NULL && port_->private_data != NULL )
  {
    portData = (PspPortDataType *)port_->private_data;
    portData->txStarted = FALSE;
  }
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_send_xchar(struct uart_port * port_, char ch_)
{
  PSP_UART3_TXBUF = ch_;
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_stop_rx(struct uart_port * port_)
{
  /* Not supported yet */
  DPUTS(( "+++ stop_rx\n" ));
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_enable_ms(struct uart_port * port_)
{
  /* Not supported yet */
  DPUTS(( "+++ emable_ms\n" ));
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_break_ctl(struct uart_port * port_, int ctl_)
{
  /* Not supported yet */
  DPUTS(( "+++ break_ctl\n" ));
}
/*---------------------------------------------------------------------------*/
static int psp_uart3_startup(struct uart_port * port_)
{
  /* Nothing to do here */
  DPUTS(( "+++ startup\n" ));
  return 0;
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_shutdown(struct uart_port * port_)
{
  PspPortDataType * portData;

  if ( unlikely( port_ == NULL || port_->private_data == NULL ) )
  {
    DPUTS(( "Invalid port for shutdown\n" ));
    return;
  }

  /* Stop the TXRX thread */
  portData = (PspPortDataType *)port_->private_data;
  portData->shutdown = TRUE;
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_set_termios(struct uart_port * port_, struct ktermios * new_, struct ktermios * old_)
{
  /* Not supported yet */
  DPUTS(( "+++ set_termios\n" ));
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_pm(struct uart_port * port_, unsigned int state_, unsigned int oldstate_)
{
  /* Not supported yet */
  DPUTS(( "+++ pm\n" ));
}
/*---------------------------------------------------------------------------*/
static int psp_uart3_set_wake(struct uart_port * port_, unsigned int state_)
{
  /* Not supported yet */
  DPUTS(( "+++ set_wake\n" ));
  return 0;
}
/*---------------------------------------------------------------------------*/
static const char * psp_uart3_type(struct uart_port * port_)
{
  return "UART3";
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_release_port(struct uart_port * port_)
{
  /* Not supported yet */
  DPUTS(( "+++ release_port\n" ));
}
/*---------------------------------------------------------------------------*/
static int psp_uart3_request_port(struct uart_port * port_)
{
  /* Not supported yet */
  DPUTS(( "+++ request_port\n" ));
  return 0;
}
/*---------------------------------------------------------------------------*/
static void psp_uart3_config_port(struct uart_port * port_, int flags_)
{
  if ( unlikely( port_ == NULL || port_->private_data == NULL ) )
  {
    DPUTS(( "Invalid port for config\n" ));
    return;
  }

  /* The port type must be dynamically set here */
  port_->type = PORT_PSP_UART3;


  DPRINTF(( "+++ config_port %08x, type=%d\n", port_, port_->type ));
}
/*---------------------------------------------------------------------------*/
static int psp_uart3_verify_port(struct uart_port * port_, struct serial_struct * ser_)
{
  /* Not supported yet */
  DPUTS(( "+++ verify_port\n" ));
  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_uart3_ioctl(struct uart_port * port_, unsigned int req_, unsigned long arg_)
{
  /* Not supported yet */
  DPUTS(( "+++ ioctl\n" ));
  return 0;
}


/*-----------------------------------------------------------------------------
 * TX Thread
 *---------------------------------------------------------------------------*/
static int psp_port_txrx_thread(struct uart_port * port_)
{
  PspPortDataType * portData;

  if ( unlikely( port_ == NULL || port_->private_data == NULL ) )
  {
    panic( "Invalid port passed to TX thread" );
    return -1;
  }

  portData = (PspPortDataType *)( port_->private_data );
  init_MUTEX_LOCKED( &portData->sem );
  portData->shutdown = FALSE;

  while ( !portData->shutdown )
  {
    if ( down_interruptible( &portData->sem ) != 0 )
    {
      continue;
    }

    switch ( port_->line )
    {
      case PSP_UART3_LINE:
        if ( portData->txStarted )
        {
          psp_uart3_tx_chars( port_ );
        }
        if ( !portData->rxStopped )
        {
          psp_uart3_rx_chars( port_ );
        }
        break;
    
      default:
        DPRINTF(( "Unsupported line %d\n", port_->line ));
        break;
    }
  }

  return 0;
}


/*-----------------------------------------------------------------------------
 * Serial console functions
 *---------------------------------------------------------------------------*/
static void psp_serial_console_write
(
  struct console * console_,
  const char * buf_,
  unsigned int size_
)
{
  psp_uart3_write( buf_, size_ );
}
/*---------------------------------------------------------------------------*/
static int __init psp_serial_console_setup
(
  struct console * console_,
  char * options_
)
{
  return psp_uart3_setup( options_ );
}


/*-----------------------------------------------------------------------------
 * Serial driver functions
 *---------------------------------------------------------------------------*/
static int __init psp_serial_modinit(void)
{
  int i, ret;
  PspPortDataType * portData;
  
  ret = uart_register_driver( &s_psp_serial_drv );
  if ( ret < 0 )
  {
    DPRINTF(( "Failed to register serial driver, err=%d\n", ret ));
    return -1;
  }

  /* Add ports */
  for ( i = 0; i < s_psp_serial_drv.nr; i++ )
  {
    struct uart_port * port = &( s_psp_serial_ports[ i ] );
    if ( port->ops == NULL )
    {
      continue;
    }

    if ( port->line == PSP_UART3_LINE )
    {
      psp_uart3_setup( NULL );
    }

    ret = uart_add_one_port( &s_psp_serial_drv, port );
    if ( ret < 0 )
    {
      DPRINTF(( "Failed to add serial port %d, err=%d\n", i, ret ));
      return -1;
    }

    /* Start the TXRX thread */
    portData = (PspPortDataType *)port->private_data;
    if ( portData != NULL && portData->txThreadId < 0 )
    {
      typedef int (*kernel_thread_t)(void *);
      portData->txThreadId = kernel_thread( (kernel_thread_t)psp_port_txrx_thread,
                                            port,
                                            CLONE_FS | CLONE_SIGHAND );
      if ( portData->txThreadId < 0 )
      {
        DPRINTF(( "Failed to create TX thread for serial line %d\n",
                    port->line ));
        return -1;
      }
    } // end if
  } // end for

  return 0;
}
/*---------------------------------------------------------------------------*/
static void __exit psp_serial_modexit(void)
{
  int i;

  for ( i = 0; i < s_psp_serial_drv.nr; i++ )
  {
    struct uart_port * port = &( s_psp_serial_ports[ i ] );
    if ( port->ops == NULL )
    {
      continue;
    }

    uart_remove_one_port( &s_psp_serial_drv, port );
  }
    
  uart_unregister_driver( &s_psp_serial_drv );
}
/*---------------------------------------------------------------------------*/
module_init( psp_serial_modinit );
module_exit( psp_serial_modexit );
MODULE_LICENSE( "GPL" );


/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
