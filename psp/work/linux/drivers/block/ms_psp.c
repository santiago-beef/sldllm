/*
 * PSP Memory Stick driver
 * Created by Jackson Mo, Nov 2007
 */

#include <linux/module.h>
#include <linux/blkdev.h>
#include <linux/fs.h>
#include <linux/list.h>
#include <linux/genhd.h>
#include <linux/delay.h>
#include <asm/semaphore.h>
#include <asm/psp.h>
#include <asm/ipl_sdk/memstk.h>
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
#define PSP_MS_NAME                     "PSP MemStick"
#define PSP_MS_MAJOR                    31
#define PSP_MS_MINOR                    200
#define PSP_MS_PARTITION_NAME           "ms%d"
#define PSP_MS_NUM_OF_PARTITIONS        4
#define PSP_MS_SECTOR_SIZE              512     /* in bytes */
#define PSP_MS_PARTITION_TABLE_OFFSET   0x1be
#define PSP_MS_MAX_RETRIES              10


/*-----------------------------------------------------------------------------
 * Type definitions
 *---------------------------------------------------------------------------*/
typedef struct
{
  struct gendisk * disk;
  struct request_queue * queue;
  unsigned long startSector;
  unsigned long numSectors;
} psp_ms_partition_t;

typedef struct
{
  unsigned char unused[ 8 ];
  unsigned long startSector;
  unsigned long numSectors;
} psp_ms_partition_info_t;


/*-----------------------------------------------------------------------------
 * Prototypes
 *---------------------------------------------------------------------------*/
static int __init psp_ms_init(void);
static void __exit psp_ms_exit(void);
static int psp_ms_make_request(request_queue_t * queue_, struct bio * bio_);
static int psp_ms_transfer_bio(psp_ms_partition_t * partition_, struct bio * bio_);

static int psp_ms_read_sector(void * buf_, int sector_);
static int psp_ms_write_sector(const void * buf_, int sector_);
static int psp_ms_read(void * buf_, int sector_, int numSectors_, int meta_);
static int psp_ms_write(const void * buf_, int sector_, int numSectors_, int meta_);

static int psp_ms_fop_open(struct inode * inode_, struct file * file_);
static int psp_ms_fop_release(struct inode * inode_, struct file * file_);
static int psp_ms_fop_ioctl(struct inode * inode_, struct file * file_,
                            unsigned cmd_, unsigned long arg_);


/*-----------------------------------------------------------------------------
 * Static Data
 *---------------------------------------------------------------------------*/
static psp_ms_partition_t s_psp_ms_partitions[ PSP_MS_NUM_OF_PARTITIONS ];

static struct block_device_operations s_psp_ms_fops =
{
  .open     = psp_ms_fop_open,
  .release  = psp_ms_fop_release,
  .ioctl    = psp_ms_fop_ioctl,
  .owner    = THIS_MODULE,
};

static DECLARE_MUTEX( s_psp_ms_rw_sem );


/*-----------------------------------------------------------------------------
 * Implementations
 *---------------------------------------------------------------------------*/
static int __init psp_ms_init(void)
{
  static BOOL s_initialized = FALSE;
  int rt, i;
  char buf[ PSP_MS_SECTOR_SIZE ];
  char * entryPtr;
  psp_ms_partition_info_t partitionInfo;

  if ( s_initialized )
  {
    /* The driver has already been initialized */
    return 0;
  }

  printk( "PSP Memory Stick block device (NEW)\n" );
  memset( &s_psp_ms_partitions, 0, sizeof( s_psp_ms_partitions ) );

  /* Initialize the device */
  //pspSysconMsOn();
	//pspSysconCtrlMsPower( 1 );
  //pspMsInit();
  psp_led_ctrl( PSP_LED_MEMSTICK, FALSE );

  /* Register the device major ID */
  rt = register_blkdev( PSP_MS_MAJOR, PSP_MS_NAME );
  if ( rt != 0 )
  {
    DBG(( "%s: Failed to register MS major ID, err=%d\n",
          PSP_MS_NAME, rt ));
    return rt;
  }

  /* Read MBR */
  rt = psp_ms_read( buf, 0, 1, 0 );	/* PSC 2.4: meta tag 0 */
  if ( rt < 0 )
  {
    DBG(( "%s: Failed to read MBR, err=%d\n",
          PSP_MS_NAME, rt ));
    return rt;
  }

  for ( i = 0, entryPtr = buf + PSP_MS_PARTITION_TABLE_OFFSET;
        i < PSP_MS_NUM_OF_PARTITIONS;
        i++, entryPtr += sizeof( psp_ms_partition_info_t ) )
  {
    memcpy( &partitionInfo, entryPtr, sizeof( partitionInfo ) );

    if ( partitionInfo.numSectors == 0 )
    {
      continue;
    }

    printk( "  Adding disk " PSP_MS_PARTITION_NAME " %dM [%08x-%08x]\n",
            i,
            (int)( partitionInfo.numSectors >> 11 ),
            (unsigned int)partitionInfo.startSector,
            (unsigned int)partitionInfo.numSectors );

    /* Allocate the disk struct */
    s_psp_ms_partitions[ i ].disk = alloc_disk( 1 );
    if ( s_psp_ms_partitions[ i ].disk == NULL )
    {
      DBG(( "%s: Failed to allocate disk[%d]\n", PSP_MS_NAME, i ));
      psp_ms_exit();
      return -ENOMEM;
    }

    /* Allocate the request queue */
    s_psp_ms_partitions[ i ].queue = blk_alloc_queue( GFP_KERNEL );
    if ( s_psp_ms_partitions[ i ].queue == NULL )
    {
      DBG(( "%s: Failed to allocate request queue[%d]\n", PSP_MS_NAME, i ));
      psp_ms_exit();
      return -ENOMEM;
    }

    /* Config the disk */
    s_psp_ms_partitions[ i ].startSector = partitionInfo.startSector;
    s_psp_ms_partitions[ i ].numSectors = partitionInfo.numSectors;

    s_psp_ms_partitions[ i ].disk->major = PSP_MS_MAJOR;
    s_psp_ms_partitions[ i ].disk->first_minor = PSP_MS_MINOR + i;
    s_psp_ms_partitions[ i ].disk->minors = 1;
    s_psp_ms_partitions[ i ].disk->fops = &s_psp_ms_fops;
    s_psp_ms_partitions[ i ].disk->queue = s_psp_ms_partitions[ i ].queue;
    //s_psp_ms_partitions[ i ].disk->flags = ...
    sprintf( s_psp_ms_partitions[ i ].disk->disk_name, PSP_MS_PARTITION_NAME, i );

    s_psp_ms_partitions[ i ].disk->private_data = &( s_psp_ms_partitions[ i ] );
    s_psp_ms_partitions[ i ].queue->queuedata = &( s_psp_ms_partitions[ i ] );

    /* Bind the handler to the queue */
    blk_queue_make_request( s_psp_ms_partitions[ i ].queue,
                            psp_ms_make_request );

    /* Set capacity (num of sectors) */
    set_capacity( s_psp_ms_partitions[ i ].disk,
                  s_psp_ms_partitions[ i ].numSectors );

    /* Activate the disk */
    add_disk( s_psp_ms_partitions[ i ].disk );
  }

  /* PSC (DESIGN 2.4, 4.8): start sector of partition 0 = /dev/ms0 (stats 153) */
  psc_st.ms_part_start = s_psp_ms_partitions[ 0 ].startSector;

  s_initialized = TRUE;
  return 0;
}
/*---------------------------------------------------------------------------*/
static void __exit psp_ms_exit(void)
{
  int i;

  for ( i = 0; i < PSP_MS_NUM_OF_PARTITIONS; i++ )
  {
    if ( s_psp_ms_partitions[ i ].disk != NULL )
    {
      put_disk( s_psp_ms_partitions[ i ].disk );
      del_gendisk( s_psp_ms_partitions[ i ].disk );
      s_psp_ms_partitions[ i ].disk = NULL;
    }

    if ( s_psp_ms_partitions[ i ].queue != NULL )
    {
      blk_cleanup_queue( s_psp_ms_partitions[ i ].queue );
      s_psp_ms_partitions[ i ].queue = NULL;
    }
  }

  (void)unregister_blkdev( PSP_MS_MAJOR, PSP_MS_NAME );
}
/*---------------------------------------------------------------------------*/
static int psp_ms_make_request(request_queue_t * queue_, struct bio * bio_)
{
  bio_endio( bio_,
             bio_->bi_size,
             psp_ms_transfer_bio( (psp_ms_partition_t *)queue_->queuedata,
                                  bio_ )
    );
  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_transfer_bio
(
  psp_ms_partition_t * partition_,
  struct bio * bio_
)
{
  struct bio_vec * bvec;
  int i, rt;
  void * buf;
  sector_t sector, numSectors;
  struct address_space * mapping;
  int meta;

  /* Calculate the start sector */
  sector = bio_->bi_sector + partition_->startSector;

  bio_for_each_segment( bvec, bio_, i )
  {
    buf = __bio_kmap_atomic( bio_, i, KM_USER0 );
    //numSectors = bio_cur_sectors( bio_ );
    numSectors = bvec->bv_len >> 9;

    /* PSC (DESIGN 2.4, r4): the page belongs to a block device's page cache
     * (FAT, FSINFO, directory sectors read through sb_bread), else file data */
    mapping = bvec->bv_page->mapping;
    meta = mapping && !( (unsigned long)mapping & PAGE_MAPPING_ANON ) &&
           S_ISBLK( mapping->host->i_mode );

    if ( bio_data_dir( bio_ ) == READ )
    {
      rt = psp_ms_read( buf, sector, numSectors, meta );
    }
    else
    {
      rt = psp_ms_write( buf, sector, numSectors, meta );
    }

    /* always call unmap regardless of the operation succeeded or not */
    __bio_kunmap_atomic( bio_, KM_USER0 );

    if ( rt < 0 )
    {
      DBG(( "Failed to %s MS (%d,%d) with error of %d\n",
            ( bio_data_dir( bio_ ) == READ ) ? "read" : "write",
            (int)sector, (int)numSectors, rt ));
      return -EIO;
    }

    sector += numSectors;
  }

  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_read_sector(void * buf_, int sector_)
{
  int rt, i;

  for ( i = 0; i < PSP_MS_MAX_RETRIES; i++ )
  {
    psp_led_ctrl( PSP_LED_MEMSTICK, TRUE );
    rt = pspMsReadSector( sector_, buf_ );
    psp_led_ctrl( PSP_LED_MEMSTICK, FALSE );

    if ( rt >= 0 )
    {
      return 0;
    }

    /* delay for a while after a failed attempt */
    mdelay( 1 );
  }

  return rt;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_write_sector(const void * buf_, int sector_)
{
  int rt, i;

  for ( i = 0; i < PSP_MS_MAX_RETRIES; i++ )
  {
    psp_led_ctrl( PSP_LED_MEMSTICK, TRUE );
    rt = pspMsWriteSector( sector_, (void *)buf_ );
    psp_led_ctrl( PSP_LED_MEMSTICK, FALSE );
    
    if ( rt >= 0 )
    {
      return 0;
    }

    /* delay for a while after a failed attempt */
    mdelay( 1 );
  }

  return rt;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_read(void * buf_, int sector_, int numSectors_, int meta_)
{
  int i, rt = -EBUSY;
  char * readBuf;

  if ( down_interruptible( &s_psp_ms_rw_sem ) != 0 )
  {
    return rt;
  }
  psc_ms_seg_begin( sector_, numSectors_, 0 );	/* PSC 2.4 */

  for ( readBuf = (char *)buf_, i = 0; i < numSectors_; i++ )
  {
    rt = psp_ms_read_sector( readBuf, sector_ + i );
    if ( rt < 0 )
    {
      DBG(( "%s: Failed to read sector %d, err=%d\n",
            PSP_MS_NAME, sector_ + i, rt ));
      break;
    }

    readBuf += PSP_MS_SECTOR_SIZE;
  }

  psc_ms_seg_end( sector_, numSectors_, 0, rt, meta_ );	/* PSC 2.4: S record */
  up( &s_psp_ms_rw_sem );
  return rt;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_write(const void * buf_, int sector_, int numSectors_, int meta_)
{
  int i, rt = -EBUSY;
  const char * writeBuf;

  if ( down_interruptible( &s_psp_ms_rw_sem ) != 0 )
  {
    return rt;
  }
  psc_ms_seg_begin( sector_, numSectors_, 1 );	/* PSC 2.4 */

  for ( writeBuf = (const char *)buf_, i = 0; i < numSectors_; i++ )
  {
    rt = psp_ms_write_sector( writeBuf, sector_ + i );
    if ( rt < 0 )
    {
      DBG(( "%s: Failed to write sector %d, err=%d\n",
            PSP_MS_NAME, sector_ + i, rt ));
      break;
    }

    writeBuf += PSP_MS_SECTOR_SIZE;
  }

  psc_ms_seg_end( sector_, numSectors_, 1, rt, meta_ );	/* PSC 2.4: S record */
  up( &s_psp_ms_rw_sem );
  return rt;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_fop_open(struct inode * inode_, struct file * file_)
{
  /* Always succeess */
  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_fop_release(struct inode * inode_, struct file * file_)
{
  /* Always success */
  return 0;
}
/*---------------------------------------------------------------------------*/
static int psp_ms_fop_ioctl(struct inode * inode_, struct file * file_,
                            unsigned cmd_, unsigned long arg_)
{
  /* No command is supported yet */
  return -ENOSYS;
}
/*---------------------------------------------------------------------------*/
module_init( psp_ms_init );
module_exit( psp_ms_exit );
MODULE_LICENSE( "GPL" );


/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
/*---------------------------------------------------------------------------*/
