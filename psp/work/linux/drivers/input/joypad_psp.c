/*
 * Joypad & Mouse Emulation driver for PSP
 * Created by Jackson Mo, Oct 2007
 */

#include <linux/module.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/list.h>
#include <linux/wait.h>
#include <linux/sched.h>
#include <linux/delay.h>
#include <linux/input.h>

#include <asm/errno.h>
#include <asm/semaphore.h>
#include <asm/psp.h>
#include <asm/ipl_sdk/syscon.h>
#include <asm/psc.h>

#if 1
#define DEBUG   1
#endif

#ifdef DEBUG
#define DBG(args)   printk args
#else
#define DBG(args)
#endif


/*-----------------------------------------------------------------------------
 * Constants
 *---------------------------------------------------------------------------*/
/* Key definitions from the IPL SDK */
#define PSP_JOYPAD_KEY_ALLOW_UP       0x00000001
#define PSP_JOYPAD_KEY_ALLOW_RT       0x00000002
#define PSP_JOYPAD_KEY_ALLOW_DN       0x00000004
#define PSP_JOYPAD_KEY_ALLOW_LT       0x00000008
#define PSP_JOYPAD_KEY_TRIANGLE       0x00000010
#define PSP_JOYPAD_KEY_CIRCLE         0x00000020
#define PSP_JOYPAD_KEY_CROSS          0x00000040
#define PSP_JOYPAD_KEY_RECTANGLE      0x00000080
#define PSP_JOYPAD_KEY_SELECT         0x00000100
#define PSP_JOYPAD_KEY_LTRG           0x00000200
#define PSP_JOYPAD_KEY_RTRG           0x00000400
#define PSP_JOYPAD_KEY_START          0x00000800
#define PSP_JOYPAD_KEY_HOME           0x00001000
#define PSP_JOYPAD_KEY_HOLD           0x00002000
#define PSP_JOYPAD_KEY_WLAN           0x00004000
#define PSP_JOYPAD_KEY_HR_EJ          0x00008000
#define PSP_JOYPAD_KEY_VOL_UP         0x00010000
#define PSP_JOYPAD_KEY_VOL_DN         0x00020000
#define PSP_JOYPAD_KEY_LCD            0x00040000
#define PSP_JOYPAD_KEY_NOTE           0x00080000
#define PSP_JOYPAD_KEY_UMD_EJCT       0x00100000
#define PSP_JOYPAD_KEY_UNKNOWN        0x00200000
#define PSP_JOYPAD_KEY_MOUSE_MODE     0x00800000
                                        
#define PSP_JOYPAD_NAME               "PSP Joypad"
#define PSP_JOYPAD_MAJOR              39
#define PSP_JOYPAD_MINOR              200
#define PSP_JOYPAD_MAX_QUEUE          16
#define PSP_JOYPAD_SAMPLE_RATE        20      /* samples per second */

#define PSP_JOYPAD_IOCTL_FLUSH        1
#define PSP_JOYPAD_IOCTL_POLL         2

#define PSP_MOUSE_NAME                "PSP Emulate Mouse"
#define PSP_MOUSE_PHYS                "pspmouse/input0"

#define LIST_TO_QUEUE(p)    list_entry( (p), psp_joypad_queue_t, list )


/*-----------------------------------------------------------------------------
 * Type definitions
 *---------------------------------------------------------------------------*/
typedef struct
{
  struct semaphore sem;
  struct list_head list;
  int head;
  int tail;
  BOOL empty;
  unsigned long element[ PSP_JOYPAD_MAX_QUEUE ];
} psp_joypad_queue_t;


/*-----------------------------------------------------------------------------
 * Prototypes
 *---------------------------------------------------------------------------*/
static int __init psp_joypad_init(void);
static void __exit psp_joypad_exit(void);

static ssize_t psp_joypad_fop_read(struct file * file_, char __user * buf_,
                                   size_t size_, loff_t * pos_);
static int psp_joypad_fop_ioctl(struct inode * inode_, struct file * file_,
                                unsigned int cmd_, unsigned long arg_);
static int psp_joypad_fop_open(struct inode * inode_, struct file * file_);
static int psp_joypad_fop_release(struct inode * inode_, struct file * file_);

static void psp_joypad_queue_init(psp_joypad_queue_t * queue_);
static void psp_joypad_queue_free(psp_joypad_queue_t * queue_);
static void psp_joypad_queue_reset(psp_joypad_queue_t * queue_);
static inline BOOL psp_joypad_queue_empty(psp_joypad_queue_t * queue_);
static inline BOOL psp_joypad_queue_full(psp_joypad_queue_t * queue_);
static BOOL psp_joypad_queue_push(psp_joypad_queue_t * queue_, unsigned long val_);
static BOOL psp_joypad_queue_pop(psp_joypad_queue_t * queue_,
                                 unsigned long * buf_,
                                 int * pcount_);

static int psp_joypad_thread(void * unused_);
static BOOL psp_joypad_read_input(unsigned long * pkeys_, unsigned char * px_, unsigned char * py_);
static void psp_joypad_process_input(unsigned long keys_, unsigned char x_, unsigned char y_);

/* Mouse Emulation */
static int __init psp_mouse_init(void);
static void __exit psp_mouse_exit(void);
static void psp_mouse_process_input(unsigned long keys_, unsigned char x_, unsigned char y_);
static int psp_mouse_convert_to_rel(unsigned char v_);


/*-----------------------------------------------------------------------------
 * Static data
 *---------------------------------------------------------------------------*/
static struct file_operations s_psp_joypad_fops;

static struct cdev s_psp_joypad_cdev =
{
  .kobj   = { .name = PSP_JOYPAD_NAME },
  .owner  = THIS_MODULE,
  .ops    = &s_psp_joypad_fops,
  //.list
  .dev    = MKDEV( PSP_JOYPAD_MAJOR, PSP_JOYPAD_MINOR ),
  .count  = 1,
};

static struct file_operations s_psp_joypad_fops =
{
  .owner    = THIS_MODULE,
  .read     = psp_joypad_fop_read,
  .ioctl    = psp_joypad_fop_ioctl,
  .open     = psp_joypad_fop_open,
  .release  = psp_joypad_fop_release,
};

static struct list_head s_psp_joypad_queue_list;
static DECLARE_MUTEX( s_psp_joypad_queue_list_sem );
static DECLARE_WAIT_QUEUE_HEAD( s_psp_joypad_wait_queue );
static int s_psp_joypad_thread_id = -1;
static volatile BOOL s_psp_joypad_thread_terminated = FALSE;
static struct input_dev * s_psp_mouse_dev = NULL;
static unsigned long s_psp_joypad_keys = 0;


/*-----------------------------------------------------------------------------
 * Implementations
 *---------------------------------------------------------------------------*/
static int __init psp_joypad_init()
{
  dev_t dev = MKDEV( PSP_JOYPAD_MAJOR, PSP_JOYPAD_MINOR );
  int rt;

  printk( "PSP Joypad driver (NEW)\n" );

  rt = register_chrdev_region( dev, 1, PSP_JOYPAD_NAME );
  if ( rt != 0 )
  {
    DBG(( "%s: Failed to register dev region (%d)\n",
          PSP_JOYPAD_NAME, rt ));
    return rt;
  }

  cdev_init( &s_psp_joypad_cdev, &s_psp_joypad_fops );

  rt = cdev_add( &s_psp_joypad_cdev, dev, 1 );
  if ( rt != 0 )
  {
    DBG(( "%s: Failed to add char dev (%d)\n",
          PSP_JOYPAD_NAME, rt ));
    unregister_chrdev_region( dev, 1 );
    return rt;
  }

  INIT_LIST_HEAD( &s_psp_joypad_queue_list );

  /* Initialize the emulate mouse */
  rt = psp_mouse_init();
  if ( rt < 0 )
  {
    return rt;
  }

  /* Launch the daemon thread here */
  s_psp_joypad_thread_id = kernel_thread( psp_joypad_thread,
                                          NULL,
                                          CLONE_FS | CLONE_SIGHAND );
  if ( s_psp_joypad_thread_id < 0 )
  {
    DBG(( "%s: Failed to start joypad daemon thread (%d)\n",
          PSP_JOYPAD_NAME, s_psp_joypad_thread_id ));
    psp_joypad_exit();
    return s_psp_joypad_thread_id;
  }

  return 0;
}
/*---------------------------------------------------------------------------*/
static void __exit psp_joypad_exit()
{
  s_psp_joypad_thread_terminated = TRUE;
  cdev_del( &s_psp_joypad_cdev );
  unregister_chrdev_region( MKDEV( PSP_JOYPAD_MAJOR, PSP_JOYPAD_MINOR ), 1 );

  /* Un-initialize the emulate mouse driver */
  psp_mouse_exit();
}
/*---------------------------------------------------------------------------*/
static ssize_t psp_joypad_fop_read
(
  struct file * file_,
  char __user * buf_,
  size_t size_,
  loff_t * pos_
)
{
  psp_joypad_queue_t * queue;
  unsigned long * buf;
  int count;

  psc_st.fop_read_enter++;	/* PSC 2.5 */
  if ( file_->private_data == NULL ||
       buf_ == NULL || size_ < sizeof( unsigned long ) ||
       !access_ok( VERIFY_WRITE, buf_, size_ ) )
  {
    return -EINVAL;
  }

  queue = (psp_joypad_queue_t *)file_->private_data;
  buf = (unsigned long *)buf_;
  count = ( size_ >> 2 );

  if ( wait_event_interruptible( s_psp_joypad_wait_queue,
                                 psp_joypad_queue_pop( queue, buf, &count ) ) != 0 )
  {
    /* waiting was interrupted */
    psc_st.fop_read_eintr++;	/* PSC 2.5 */
    return -ERESTARTSYS;
  }
  
  psc_st.fop_read_ret++;	/* PSC 2.5 */
  return ( count << 2 );
}
/*---------------------------------------------------------------------------*/
static int psp_joypad_fop_ioctl
(
  struct inode * inode_,
  struct file * file_,
  unsigned int cmd_,
  unsigned long arg_
)
{
  int rt = 0;

  psc_st.fop_ioctl++;	/* PSC 2.5 */
  switch ( cmd_ )
  {
    /* Flush the buffer */
    case PSP_JOYPAD_IOCTL_FLUSH:
      if ( file_->private_data == NULL )
      {
        rt = -EINVAL;
        break;
      }

      psp_joypad_queue_reset( (psp_joypad_queue_t *)file_->private_data );
      break;

    /* Get the instant status of the buttons */
    case PSP_JOYPAD_IOCTL_POLL:
      if ( arg_ == 0 ||
           !access_ok( VERIFY_WRITE, arg_, sizeof( unsigned long ) ) )
      {
        rt = -EINVAL;
        break;
      }

      *(unsigned long *)arg_ = s_psp_joypad_keys;
      break;

    default:
      rt = -ENOSYS;
      break;
  }
  
  return rt;
}
/*---------------------------------------------------------------------------*/
static int psp_joypad_fop_open(struct inode * inode_, struct file * file_)
{
  psp_joypad_queue_t * queue;

  psc_st.fop_open++;	/* PSC 2.5 */
  if ( file_->private_data != NULL )
  {
    DBG(( "%s: Invalid file data\n", PSP_JOYPAD_NAME ));
    return -EINVAL;
  }

  file_->private_data = kmalloc( sizeof( psp_joypad_queue_t ),
                                 GFP_KERNEL );
  if ( file_->private_data == NULL )
  {
    DBG(( "%s: Failed to allocate private data\n", PSP_JOYPAD_NAME ));
    return -ENOMEM;
  }

  queue = (psp_joypad_queue_t *)file_->private_data;
  psp_joypad_queue_init( queue );

  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_joypad_fop_release(struct inode * inode_, struct file * file_)
{
  psc_st.fop_release++;	/* PSC 2.5 */
  if ( file_->private_data != NULL )
  {
    psp_joypad_queue_t * queue = (psp_joypad_queue_t *)file_->private_data;
    psp_joypad_queue_free( queue );
    file_->private_data = NULL;
  }

  return 0;
}
/*---------------------------------------------------------------------------*/
static void psp_joypad_queue_init(psp_joypad_queue_t * queue_)
{
  init_MUTEX( &queue_->sem );
  INIT_LIST_HEAD( &queue_->list );
  queue_->head = 0;
  queue_->tail = 0;
  queue_->empty = TRUE;

  if ( down_interruptible( &s_psp_joypad_queue_list_sem ) == 0 )
  {
    list_add( &queue_->list, &s_psp_joypad_queue_list );
    up( &s_psp_joypad_queue_list_sem );
  }
}
/*---------------------------------------------------------------------------*/
static void psp_joypad_queue_free(psp_joypad_queue_t * queue_)
{
  /* PSC (DESIGN 2.5): qfree_stage 1..5, the direct H9 signature */
  psc_st.qfree_queue = (u32)(unsigned long)queue_;
  psc_st.qfree_pid = current->pid;
  psc_st.qfree_stage = PSC_QFREE_ENTRY;
  if ( down_interruptible( &queue_->sem ) != 0 )
  {
    return;
  }
  psc_st.qfree_stage = PSC_QFREE_AFTER_348;

  if ( down_interruptible( &s_psp_joypad_queue_list_sem ) == 0 )
  {
    psc_st.qfree_stage = PSC_QFREE_AFTER_353;
    list_del( &queue_->list );
    psc_st.qfree_stage = PSC_QFREE_AFTER_LISTDEL;
    up( &s_psp_joypad_queue_list_sem );
  }

  psc_st.qfree_stage = PSC_QFREE_BEFORE_KFREE;
  kfree( queue_ );
}
/*---------------------------------------------------------------------------*/
static void psp_joypad_queue_reset(psp_joypad_queue_t * queue_)
{
  if ( down_interruptible( &queue_->sem ) == 0 )
  {
    queue_->head = 0;
    queue_->tail = 0;
    queue_->empty = TRUE;

    up( &queue_->sem );
  }
}
/*---------------------------------------------------------------------------*/
static inline BOOL psp_joypad_queue_empty(psp_joypad_queue_t * queue_)
{
  return ( queue_->head == queue_->tail && queue_->empty );
}
/*---------------------------------------------------------------------------*/
static inline BOOL psp_joypad_queue_full(psp_joypad_queue_t * queue_)
{
  return ( queue_->head == queue_->tail && !queue_->empty );
}
/*---------------------------------------------------------------------------*/
static BOOL psp_joypad_queue_push
(
  psp_joypad_queue_t * queue_,
  unsigned long val_
)
{
  psc_jp_stage_arg( PSC_STAGE_BEFORE_QSEM, queue_ );	/* PSC 2.5 */
  if ( down_interruptible( &queue_->sem ) != 0 )
  {
    psc_st.jp_push_eintr++;	/* PSC 2.5, POLL push_fail high nibble */
    if ( PSC_PUSH_FAIL_EINTR( psc_k.poll.push_fail ) < 15 )
      psc_k.poll.push_fail += 0x10;
    return FALSE;
  }
  psc_jp_stage_arg( PSC_STAGE_PUSHING, queue_ );

  if ( psp_joypad_queue_full( queue_ ) )
  {
    up( &queue_->sem );
    psc_st.jp_push_full++;	/* PSC 2.5, POLL push_fail low nibble */
    if ( PSC_PUSH_FAIL_FULL( psc_k.poll.push_fail ) < 15 )
      psc_k.poll.push_fail++;
    return FALSE;
  }

  queue_->element[ queue_->head++ ] = val_;
  queue_->empty = FALSE;

  if ( queue_->head >= PSP_JOYPAD_MAX_QUEUE )
  {
    queue_->head = 0;
  }

  up( &queue_->sem );
  psc_st.jp_push_ok++;	/* PSC 2.5 */
  if ( psc_k.poll.push_ok < 0xFF )
    psc_k.poll.push_ok++;
  return TRUE;
}
/*---------------------------------------------------------------------------*/
static BOOL psp_joypad_queue_pop
(
  psp_joypad_queue_t * queue_,
  unsigned long * buf_,
  int * pcount_
)
{
  int count;

  if ( down_interruptible( &queue_->sem ) != 0 )
  {
    return FALSE;
  }

  for ( count = 0;
        !psp_joypad_queue_empty( queue_ ) && count < *pcount_;
        count++ )
  {
    *buf_++ = queue_->element[ queue_->tail++ ];
    if ( queue_->tail >= PSP_JOYPAD_MAX_QUEUE )
    {
      queue_->tail = 0;
    }

    if ( queue_->head == queue_->tail )
    {
      queue_->empty = TRUE;
    }
  }
  up( &queue_->sem );

  if ( count > 0 )
  {
    *pcount_ = count;
    return TRUE;
  }
  
  return FALSE;
}
/*---------------------------------------------------------------------------*/
static int psp_joypad_thread(void * unused_)
{
  unsigned long keys;
  unsigned char x, y;

  psc_jp_thread_start();	/* PSC (DESIGN 1.8, 2.5): psc_jp_task, jp_pid */
  while ( !s_psp_joypad_thread_terminated )
  {
    psc_poll_begin();	/* PSC 2.5: jp_loop, POLL start, stage 1 */
    if ( psp_joypad_read_input( &keys, &x, &y ) )
    {
      psc_jp_stage( PSC_STAGE_RI_RETURNED );	/* PSC 2.5 */
      psp_joypad_process_input( keys, x, y );

      if ( s_psp_joypad_keys & PSP_JOYPAD_KEY_MOUSE_MODE )
        psp_mouse_process_input( keys, x, y );
    } // end if
    else
      psc_jp_stage( PSC_STAGE_RI_RETURNED );	/* PSC 2.5 */
    
    psc_poll_end();	/* PSC 2.5: stage 17, POLL record */
    msleep( 1000 / PSP_JOYPAD_SAMPLE_RATE );
  } // end while

  return 0;
}
/*---------------------------------------------------------------------------*/
static BOOL psp_joypad_read_input
(
  unsigned long * pkeys_,
  unsigned char * px_,
  unsigned char * py_
)
{
  unsigned long keys;

  if ( unlikely( pkeys_ == NULL || px_ == NULL || py_ == NULL ) )
  {
    psc_k.poll.ri_branch = PSC_RI_R1;	/* PSC 2.5 */
    return FALSE;
  }

  psc_jp_stage( PSC_STAGE_ASTICKPOWER );	/* PSC 2.5 */
  (void)_pspSysconCtrlAStickPower( 1 );
  psc_jp_stage( PSC_STAGE_GETCTRL2 );	/* PSC 2.5 */
  if ( _pspSysconGetCtrl2( (u32*)&keys, px_, py_ ) < 0 )
  {
    psc_k.poll.ri_branch = PSC_RI_R3;	/* PSC 2.5 */
    psc_st.jp_r3++;
    return FALSE;
  }

  *pkeys_ = ~keys;

  if ( *pkeys_ & PSP_JOYPAD_KEY_HOLD )
  {
    psc_k.poll.ri_branch = PSC_RI_R4;	/* PSC 2.5 */
    psc_st.jp_r4++;
    return FALSE;   /* Joypad is locked */
  }

  psc_k.poll.ri_branch = PSC_RI_R5;	/* PSC 2.5 */
  psc_st.jp_r5++;
  return TRUE;
}
/*---------------------------------------------------------------------------*/
static void psp_joypad_process_input
(
  unsigned long keys_,
  unsigned char x_,
  unsigned char y_
)
{
  static unsigned long lastKeys = 0;
  static BOOL mouseMode = FALSE;
  struct list_head * pos;
  extern int console_blanked;

  psc_jp_stage( PSC_STAGE_PI_ENTRY );	/* PSC 2.5 */
  psc_k.poll.pi_flags |= PSC_PI_F_CALLED;
  psc_st.jp_proc_calls++;

  keys_ |= ( ( (unsigned long)( x_ & 0xf0 ) << 20 ) |
             ( (unsigned long)( y_ & 0xf0 ) << 24 ) );

  if ( lastKeys == keys_ )
  {
    psc_jp_stage( PSC_STAGE_DEDUPE_RET );	/* PSC 2.5 */
    psc_k.poll.pi_flags |= PSC_PI_F_DEDUPE;
    psc_st.jp_dedupe++;
    return;
  }
  psc_st.jp_changed++;	/* PSC 2.5 */

  lastKeys = keys_;

  /* Turn the LCD back on whenever a button is pressed */
  psc_jp_stage( PSC_STAGE_BEFORE_LCD_ON );	/* PSC 2.5 */
  if ( console_blanked )
  {
    psc_k.poll.pi_flags |= PSC_PI_F_BLANKED;
    psc_st.jp_lcd_unblank++;
  }
  psp_lcd_on();
  psc_jp_stage( PSC_STAGE_AFTER_LCD_ON );

  /* Switch to mouse mode if SELECT is pressed */
  if ( keys_ & PSP_JOYPAD_KEY_SELECT )
  {
    mouseMode = !mouseMode;
    psc_k.poll.pi_flags |= PSC_PI_F_SELECT_TOGGLE;	/* PSC 2.5 */
    psc_st.jp_mode_toggles++;
  }

  if ( mouseMode )
  {
    keys_ |= PSP_JOYPAD_KEY_MOUSE_MODE;
    psc_k.poll.pi_flags |= PSC_PI_F_MOUSEMODE;	/* PSC 2.5 */
  }

  s_psp_joypad_keys = keys_;
  psc_st.jp_keys = keys_;	/* PSC 2.5: the value stored at :527 */

  /* Feed the data to all registered queues */
  psc_jp_stage( PSC_STAGE_BEFORE_LISTSEM );	/* PSC 2.5 */
  if ( down_interruptible( &s_psp_joypad_queue_list_sem ) == 0 )
  {
    psc_jp_stage( PSC_STAGE_LISTSEM_HELD );	/* PSC 2.5 */
    psc_k.poll.pi_flags |= PSC_PI_F_LISTSEM;
    list_for_each( pos, &s_psp_joypad_queue_list )
    {
      if ( psc_k.poll.nqueues < 0xFF )
        psc_k.poll.nqueues++;	/* PSC 2.5 */
      (void)psp_joypad_queue_push( LIST_TO_QUEUE( pos ), keys_ );
    }
    up( &s_psp_joypad_queue_list_sem );
    psc_jp_stage( PSC_STAGE_AFTER_UP_LIST );	/* PSC 2.5 */

    wake_up_interruptible( &s_psp_joypad_wait_queue );
    psc_k.poll.pi_flags |= PSC_PI_F_WAKE;	/* PSC 2.5 */
    psc_st.jp_wake++;
    psc_jp_stage( PSC_STAGE_AFTER_WAKEUP );
  }
  else
  {
    psc_k.poll.pi_flags |= PSC_PI_F_LISTSEM_FAIL;	/* PSC 2.5 */
    psc_st.jp_listsem_fail++;
  }
}

/* PSC (DESIGN 1.7 word 63): read-only accessor for the stats reader. */
int psc_jp_list_sem_count(void)
{
  return atomic_read( &s_psp_joypad_queue_list_sem.count );
}
/*---------------------------------------------------------------------------*/
static int __init psp_mouse_init()
{
  int rt;

  if ( s_psp_mouse_dev != NULL )
  {
    /* Has already been initialized */
    return 0;
  }

  printk( "PSP Emulate Mouse driver (NEW)\n" );

  s_psp_mouse_dev = input_allocate_device();
  if ( s_psp_mouse_dev == NULL )
  {
    DBG(( "%s: Failed to allocate input device\n",
          PSP_MOUSE_NAME ));
    return -ENOMEM;
  }

	s_psp_mouse_dev->name = PSP_MOUSE_NAME;
  s_psp_mouse_dev->phys = PSP_MOUSE_PHYS;
  s_psp_mouse_dev->id.bustype = BUS_I8042;  /* Simulating a PS2 mouse */
	s_psp_mouse_dev->evbit[ 0 ] = BIT( EV_KEY ) | BIT( EV_REL );
	s_psp_mouse_dev->keybit[ LONG( BTN_LEFT ) ] = BIT( BTN_LEFT ) |
                                                BIT( BTN_MIDDLE ) |
                                                BIT( BTN_RIGHT );
	s_psp_mouse_dev->relbit[ 0 ] = BIT( REL_X ) | BIT( REL_Y );

  rt = input_register_device( s_psp_mouse_dev );
  if ( rt < 0 )
  {
    DBG(( "%s: Failed to register input device, err=%d\n",
          PSP_MOUSE_NAME, rt ));
    psp_mouse_exit();
    return rt;
  }

  return 0;
}
/*---------------------------------------------------------------------------*/
static void __exit psp_mouse_exit()
{
  if ( s_psp_mouse_dev != NULL )
  {
    input_unregister_device( s_psp_mouse_dev );
    input_free_device( s_psp_mouse_dev );
    s_psp_mouse_dev = NULL;
  }
}
/*---------------------------------------------------------------------------*/
static void psp_mouse_process_input
(
  unsigned long keys_,
  unsigned char x_,
  unsigned char y_
)
{
  static BOOL btnLeft = FALSE;
  static BOOL btnMid = FALSE;
  static BOOL btnRight = FALSE;

  int dx, dy;
  BOOL left = FALSE;
  BOOL mid = FALSE;
  BOOL right = FALSE;

  psc_jp_stage( PSC_STAGE_MOUSE_ENTRY );	/* PSC 2.5 */
  psc_k.poll.mouse_flags |= PSC_MOUSE_F_CALLED;
  psc_st.jp_mouse_calls++;
  if ( unlikely( s_psp_mouse_dev == NULL ) )
  {
    psc_k.poll.mouse_flags |= PSC_MOUSE_F_NODEV;	/* PSC 2.5: M1 */
    return;
  }

  dx = psp_mouse_convert_to_rel( x_ );
  dy = psp_mouse_convert_to_rel( y_ );

  if ( ( keys_ & PSP_JOYPAD_KEY_LTRG ) &&
       ( keys_ & PSP_JOYPAD_KEY_RTRG ) )
  {
    mid = TRUE;
  }
  else if ( keys_ & PSP_JOYPAD_KEY_LTRG )
  {
    left = TRUE;
  }
  else if ( keys_ & PSP_JOYPAD_KEY_RTRG )
  {
    right = TRUE;
  }

  /* Dpad input */
  if ( keys_ & PSP_JOYPAD_KEY_ALLOW_LT )
    dx -= 2;
  if ( keys_ & PSP_JOYPAD_KEY_ALLOW_RT )
    dx += 2;
  if ( keys_ & PSP_JOYPAD_KEY_ALLOW_UP )
    dy -= 2;
  if ( keys_ & PSP_JOYPAD_KEY_ALLOW_DN )
    dy += 2;

  if ( dx == 0 && dy == 0 &&
       btnLeft == left &&
       btnMid == mid &&
       btnRight == right )
  {
    psc_k.poll.mouse_flags |= PSC_MOUSE_F_NOOP;	/* PSC 2.5: M2 */
    psc_st.jp_mouse_noop++;
    return;
  }

  btnLeft  = left;
  btnMid   = mid;
  btnRight = right;
  
  input_report_rel( s_psp_mouse_dev, REL_X, dx );
  input_report_rel( s_psp_mouse_dev, REL_Y, -dy );

  input_report_key( s_psp_mouse_dev, BTN_LEFT, left );
  input_report_key( s_psp_mouse_dev, BTN_MIDDLE, mid );
  input_report_key( s_psp_mouse_dev, BTN_RIGHT, right );

  psc_k.poll.mouse_flags |= PSC_MOUSE_F_REPORTED |	/* PSC 2.5: M3 */
                            ( left ? PSC_MOUSE_F_LEFT : 0 ) |
                            ( mid ? PSC_MOUSE_F_MIDDLE : 0 ) |
                            ( right ? PSC_MOUSE_F_RIGHT : 0 );
  psc_k.poll.dx = (s8)dx;
  psc_k.poll.dy = (s8)dy;
  psc_st.jp_mouse_reports++;
  psc_jp_stage( PSC_STAGE_BEFORE_SYNC );
  input_sync( s_psp_mouse_dev );
}
/*---------------------------------------------------------------------------*/
static int psp_mouse_convert_to_rel(unsigned char v_)
{
  switch ( ( v_ >> 4 ) & 0xf )
  {
    case 0x0:
      return -16;
    case 0x1:
      return -4;
    case 0x2:
    case 0x3:
      return -2;
    case 0x4:
    case 0x5:
      return -1;
/*
    case 0x6:
    case 0x7:
    case 0x8:
    case 0x9:
*/
    case 0xa:
    case 0xb:
      return 1;
    case 0xc:
    case 0xd:
      return 2;
    case 0xe:
      return 4;
    case 0xf:
      return 16;

    default:
      return 0;
  }
}
/*---------------------------------------------------------------------------*/
module_init( psp_joypad_init );
module_exit( psp_joypad_exit );
MODULE_LICENSE( "GPL" );


/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
