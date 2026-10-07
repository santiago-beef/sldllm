/*
 * host_kernel.h - host stand-ins for the Linux 2.6.22 kernel interfaces that
 * the real PSC sources use (Stage 3 ring-logic test, handoff/stage3/ring).
 *
 * Compiled under test, unmodified, from /home/ubuntu/psp/work/linux
 * (stage2-trace, identical to 48dcc1b9 for these paths):
 *   arch/mips/psp/psc.c, arch/mips/psp/psc_panel.c,
 *   arch/mips/psp/ipl_sdk/syscon.c (as C++, see syscon_host.cc),
 *   drivers/input/joypad_psp.c,
 *   include/asm-mips/psc.h, include/linux/psc_format.h, include/asm-mips/psp.h,
 *   include/asm-mips/ipl_sdk/{syscon,kprintf,sysreg,cache}.h.
 *
 * This header only declares interfaces (types, macros, prototypes). Every
 * behaviour behind them (CP0 Count, current, preempt_count, the timer tick,
 * the scheduler, copy_to_user, /proc registration, the syscon device) lives
 * in the harness (sim.c, mmio.c) and is documented there. Nothing here
 * contains PSC logic. No floating point.
 *
 * Host: aarch64 Linux, LP64, little-endian like the target (mipsel); the
 * PSC formats are little-endian only (psc_format.h:35-37 #error on BE).
 */
#ifndef PSC_HOST_KERNEL_H
#define PSC_HOST_KERNEL_H

#include <stddef.h>
#include <string.h>
#include <sys/types.h>
#include <errno.h>

#ifndef __KERNEL__
#define __KERNEL__
#endif

/* ---- linux/types.h, asm/types.h ---------------------------------------- */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;
typedef signed long long s64;
typedef u8 __u8;
typedef u16 __u16;
typedef u32 __u32;
typedef u64 __u64;
typedef s8 __s8;
typedef s16 __s16;
typedef s32 __s32;
typedef s64 __s64;
typedef unsigned int gfp_t;
typedef unsigned short umode_t;
#ifndef S_IRUSR
#define S_IRUSR 0400
#define S_IWUSR 0200
#define S_IRGRP 0040
#define S_IROTH 0004
#endif

/* ---- linux/compiler.h, linux/kernel.h ---------------------------------- */
#define __user
#define __iomem
#define __init
#define __exit
#define __initdata
#define __devinit
#define asmlinkage
#define likely(x)	__builtin_expect(!!(x), 1)
#define unlikely(x)	__builtin_expect(!!(x), 0)
/*
 * barrier(): in the kernel a compiler barrier (linux/compiler-gcc.h). Here a
 * call to an external function, which is also a full compiler barrier for
 * memory, and which the harness uses as an interrupt-injection point
 * (DESIGN 3.4 ordering points). It changes no PSC logic.
 */
void psc_host_barrier(void);
#define barrier()	psc_host_barrier()
#define ARRAY_SIZE(a)	(sizeof(a) / sizeof((a)[0]))
#define container_of(ptr, type, member) \
	((type *)((char *)(ptr) - offsetof(type, member)))
#define KERN_EMERG	"<0>"
#define KERN_ERR	"<3>"
#define KERN_WARNING	"<4>"
#define KERN_INFO	"<6>"
#define KERN_DEBUG	"<7>"
int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
extern const char linux_banner[];
#define BITS_PER_LONG	(8 * (int)sizeof(long))

/* ---- linux/jiffies.h --------------------------------------------------- */
#define HZ		250
extern volatile unsigned long jiffies;
#define INITIAL_JIFFIES	((unsigned long)(unsigned int)(-300 * HZ))
#define MSEC_PER_SEC	1000L

/* ---- linux/hardirq.h (values of work/linux/include/linux/hardirq.h:23-53) */
#define PREEMPT_BITS	8
#define SOFTIRQ_BITS	8
#define HARDIRQ_BITS	12
#define PREEMPT_SHIFT	0
#define SOFTIRQ_SHIFT	(PREEMPT_SHIFT + PREEMPT_BITS)
#define HARDIRQ_SHIFT	(SOFTIRQ_SHIFT + SOFTIRQ_BITS)
#define __IRQ_MASK(x)	((1UL << (x)) - 1)
#define PREEMPT_MASK	(__IRQ_MASK(PREEMPT_BITS) << PREEMPT_SHIFT)
#define SOFTIRQ_MASK	(__IRQ_MASK(SOFTIRQ_BITS) << SOFTIRQ_SHIFT)
#define HARDIRQ_MASK	(__IRQ_MASK(HARDIRQ_BITS) << HARDIRQ_SHIFT)
#define PREEMPT_OFFSET	(1UL << PREEMPT_SHIFT)
#define SOFTIRQ_OFFSET	(1UL << SOFTIRQ_SHIFT)
#define HARDIRQ_OFFSET	(1UL << HARDIRQ_SHIFT)
#define PREEMPT_ACTIVE	0x10000000
extern int psc_host_preempt_count;
#define preempt_count()	(psc_host_preempt_count)
#define in_interrupt()	(preempt_count() & (HARDIRQ_MASK | SOFTIRQ_MASK))
#define in_irq()	(preempt_count() & HARDIRQ_MASK)

/* ---- asm/mipsregs.h: CP0 Count and Status (the harness models them) --- */
unsigned int psc_host_read_c0_count(void);
unsigned int psc_host_read_c0_status(void);
#define read_c0_count()		psc_host_read_c0_count()
#define read_c0_status()	psc_host_read_c0_status()
#define ST0_CU0		0x10000000

/* ---- asm/ptrace.h (2.6.22 MIPS o32 field names) ------------------------ */
struct pt_regs {
	unsigned long pad0[6];
	unsigned long regs[32];
	unsigned long cp0_status;
	unsigned long hi;
	unsigned long lo;
	unsigned long cp0_badvaddr;
	unsigned long cp0_cause;
	unsigned long cp0_epc;
};

/* ---- linux/sched.h, asm/thread_info.h ---------------------------------- */
#define THREAD_SIZE	8192
struct task_struct;
struct thread_info {
	struct task_struct *task;
	unsigned long flags;
	int preempt_count;
	struct pt_regs *regs;		/* set by handle_int (genex.S:166-167) */
};
struct psc_host_sigpending {
	struct { unsigned long sig[2]; } signal;
};
struct task_struct {
	volatile long state;
	struct thread_info *thread_info;
	pid_t pid;
	unsigned long nvcsw, nivcsw;
	void *mm;
	struct psc_host_sigpending pending;
	/* host bookkeeping, not kernel fields */
	int host_sigpending;
	const char *host_name;
};
#define TASK_RUNNING		0
#define TASK_INTERRUPTIBLE	1
#define TASK_UNINTERRUPTIBLE	2
#define TIF_SIGPENDING		1
extern struct task_struct *psc_host_current;
#define current			psc_host_current
#define current_thread_info()	(psc_host_current->thread_info)
static inline int signal_pending(struct task_struct *p)
{
	return p->host_sigpending;
}
static inline int test_tsk_thread_flag(struct task_struct *t, int flag)
{
	return flag == TIF_SIGPENDING ? t->host_sigpending : 0;
}
#define CLONE_FS	0x00000200
#define CLONE_SIGHAND	0x00000800
int psc_host_kernel_thread(int (*fn)(void *), void *arg, unsigned long flags);
#define kernel_thread(fn, arg, flags)	psc_host_kernel_thread((fn), (arg), (flags))

/* ---- linux/delay.h ----------------------------------------------------- */
void psc_host_msleep(unsigned int msecs);
#define msleep(ms)	psc_host_msleep(ms)
#define mdelay(ms)	do { } while (0)

/* ---- linux/fs.h, linux/proc_fs.h --------------------------------------- */
struct proc_dir_entry;
struct inode {
	struct proc_dir_entry *host_pde;
	umode_t i_mode;
};
struct file {
	loff_t f_pos;
	void *private_data;
};
struct file_operations {
	void *owner;
	loff_t (*llseek)(struct file *, loff_t, int);
	ssize_t (*read)(struct file *, char __user *, size_t, loff_t *);
	ssize_t (*write)(struct file *, const char __user *, size_t, loff_t *);
	int (*ioctl)(struct inode *, struct file *, unsigned int, unsigned long);
	int (*open)(struct inode *, struct file *);
	int (*release)(struct inode *, struct file *);
};
struct proc_dir_entry {
	const char *name;
	mode_t mode;
	void *data;
	const struct file_operations *proc_fops;
	loff_t size;
	struct proc_dir_entry *parent;
};
#define PDE(inode)	((inode)->host_pde)
struct proc_dir_entry *proc_mkdir(const char *name, struct proc_dir_entry *parent);
struct proc_dir_entry *create_proc_entry(const char *name, mode_t mode,
					 struct proc_dir_entry *parent);
#ifndef SEEK_SET
#define SEEK_SET	0
#define SEEK_CUR	1
#define SEEK_END	2
#endif
struct super_block {
	unsigned long s_flags;
	unsigned char s_blocksize_bits;
	void *s_fs_info;
};
#define MS_RDONLY	1
#define ERESTARTSYS	512

/* ---- linux/msdos_fs.h (the fields psc_fat_mounted reads) --------------- */
struct msdos_sb_info {
	unsigned short sec_per_clus;
	unsigned char fats;
	unsigned short fat_start;
	unsigned long fat_length;
	unsigned long data_start;
	unsigned long fsinfo_sector;
};
static inline struct msdos_sb_info *MSDOS_SB(struct super_block *sb)
{
	return (struct msdos_sb_info *)sb->s_fs_info;
}

/* ---- asm/uaccess.h ----------------------------------------------------- */
unsigned long psc_host_copy_to_user(void *to, const void *from, unsigned long n);
unsigned long psc_host_copy_from_user(void *to, const void *from, unsigned long n);
#define copy_to_user(to, from, n)	psc_host_copy_to_user((to), (from), (n))
#define copy_from_user(to, from, n)	psc_host_copy_from_user((to), (from), (n))
#define VERIFY_READ	0
#define VERIFY_WRITE	1
#define access_ok(type, addr, size)	1

/* ---- asm/div64.h ------------------------------------------------------- */
#define do_div(n, base) ({					\
	unsigned int __base = (base);				\
	unsigned int __rem = (unsigned int)((n) % __base);	\
	(n) = (n) / __base;					\
	__rem; })

/* ---- linux/init.h, linux/module.h -------------------------------------- */
/* An initcall becomes a global pointer the harness calls in boot order. */
#define late_initcall(fn)	int (*psc_host_late_initcall_##fn)(void) = fn
#define module_init(fn)		int (*psc_host_module_init_##fn)(void) = fn
#define module_exit(fn)		void (*psc_host_module_exit_##fn)(void) = fn
#define MODULE_LICENSE(x)
#define THIS_MODULE		((void *)0)

/* ---- linux/cdev.h ------------------------------------------------------ */
struct cdev {
	struct { const char *name; } kobj;
	void *owner;
	const struct file_operations *ops;
	dev_t dev;
	unsigned int count;
};
#define MKDEV(ma, mi)	((dev_t)(((ma) << 20) | (mi)))
int register_chrdev_region(dev_t from, unsigned count, const char *name);
void unregister_chrdev_region(dev_t from, unsigned count);
void cdev_init(struct cdev *c, const struct file_operations *fops);
int cdev_add(struct cdev *c, dev_t dev, unsigned count);
void cdev_del(struct cdev *c);

/* ---- linux/slab.h ------------------------------------------------------ */
#define GFP_KERNEL	0xd0
void *psc_host_kmalloc(size_t size, gfp_t flags);
void psc_host_kfree(const void *p);
#define kmalloc(s, f)	psc_host_kmalloc((s), (f))
#define kfree(p)	psc_host_kfree(p)

/* ---- linux/list.h ------------------------------------------------------ */
struct list_head { struct list_head *next, *prev; };
#define INIT_LIST_HEAD(ptr) do { (ptr)->next = (ptr); (ptr)->prev = (ptr); } while (0)
static inline void list_add(struct list_head *n, struct list_head *head)
{
	n->next = head->next; n->prev = head;
	head->next->prev = n; head->next = n;
}
static inline void list_del(struct list_head *e)
{
	e->prev->next = e->next; e->next->prev = e->prev;
	e->next = e->prev = 0;
}
#define list_entry(ptr, type, member)	container_of(ptr, type, member)
#define list_for_each(pos, head) \
	for (pos = (head)->next; pos != (head); pos = pos->next)

/* ---- asm/atomic.h, asm/semaphore.h ------------------------------------- */
typedef struct { volatile int counter; } atomic_t;
#define atomic_read(v)	((v)->counter)
struct semaphore { atomic_t count; int sleepers; };
#define DECLARE_MUTEX(name)	struct semaphore name = { { 1 }, 0 }
#define init_MUTEX(sem)		do { (sem)->count.counter = 1; (sem)->sleepers = 0; } while (0)
int psc_host_down_interruptible(struct semaphore *sem);
void psc_host_up(struct semaphore *sem);
#define down_interruptible(s)	psc_host_down_interruptible(s)
#define up(s)			psc_host_up(s)

/* ---- linux/wait.h ------------------------------------------------------ */
typedef struct { int host_waiters; } wait_queue_head_t;
#define DECLARE_WAIT_QUEUE_HEAD(name)	wait_queue_head_t name = { 0 }
void psc_host_wake_up_interruptible(wait_queue_head_t *q);
#define wake_up_interruptible(q)	psc_host_wake_up_interruptible(q)
/* The harness only calls a reader when its condition holds (sim.c). */
int psc_host_would_block(void);
#define wait_event_interruptible(wq, condition) \
	((condition) ? 0 : psc_host_would_block())

/* ---- linux/input.h ----------------------------------------------------- */
#define EV_KEY		0x01
#define EV_REL		0x02
#define REL_X		0x00
#define REL_Y		0x01
#define BTN_LEFT	0x110
#define BTN_RIGHT	0x111
#define BTN_MIDDLE	0x112
#define BUS_I8042	0x11
#define BIT(x)		(1UL << ((x) % BITS_PER_LONG))
#define LONG(x)		((x) / BITS_PER_LONG)
struct input_dev {
	const char *name;
	const char *phys;
	struct { unsigned short bustype; } id;
	unsigned long evbit[1];
	unsigned long keybit[16];
	unsigned long relbit[1];
};
struct input_dev *input_allocate_device(void);
int input_register_device(struct input_dev *dev);
void input_unregister_device(struct input_dev *dev);
void input_free_device(struct input_dev *dev);
void psc_host_input_event(struct input_dev *dev, unsigned int type, unsigned int code, int value);
void psc_host_input_sync(struct input_dev *dev);
#define input_report_rel(dev, code, value)	psc_host_input_event((dev), EV_REL, (code), (value))
#define input_report_key(dev, code, value)	psc_host_input_event((dev), EV_KEY, (code), !!(value))
#define input_sync(dev)				psc_host_input_sync(dev)

#endif /* PSC_HOST_KERNEL_H */
