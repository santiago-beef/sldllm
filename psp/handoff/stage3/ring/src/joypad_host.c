/*
 * joypad_host.c - compiles the REAL drivers/input/joypad_psp.c (unmodified;
 * sha256 checked by the Makefile) so that the POLL record, the thread
 * stages, ri_branch, pi_flags, the queue pushes and the mouse fields come from
 * the driver's own code (DESIGN 1.4, 2.5). Only accessors for its static
 * objects are added below; they are harness code.
 *
 * Host note (LP64): the driver's fop_read copies `unsigned long` elements
 * (joypad_psp.c:461-466); on the host they are 8 bytes, so callers pass a
 * buffer of size_ / 4 longs.
 */
#include "host.h"
#include JOYPAD_C_PATH

int jp_host_thread(void) { return psp_joypad_thread(NULL); }
void jp_host_terminate(void) { s_psp_joypad_thread_terminated = TRUE; }
int jp_host_init(void) { return psp_joypad_init(); }

/* psposk2's open of /dev/joypad (joypad_psp.c:300-323) */
static struct inode osk_inode;
static struct file osk_file;

int jp_host_osk_open(void)
{
	memset(&osk_inode, 0, sizeof(osk_inode));
	memset(&osk_file, 0, sizeof(osk_file));
	return psp_joypad_fop_open(&osk_inode, &osk_file);
}

int jp_host_osk_has_data(void)
{
	return osk_file.private_data &&
	       !psp_joypad_queue_empty((psp_joypad_queue_t *)osk_file.private_data);
}

int jp_host_osk_queued(void)
{
	psp_joypad_queue_t *q = osk_file.private_data;
	int n;

	if (!q || psp_joypad_queue_empty(q))
		return 0;
	n = q->head - q->tail;
	if (n <= 0)
		n += PSP_JOYPAD_MAX_QUEUE;
	return n;
}

/* psposk2's read() (joypad_psp.c:220-254): returns elements popped */
int jp_host_osk_read(unsigned long *keys, int max)
{
	ssize_t r = psp_joypad_fop_read(&osk_file, (char *)keys,
					(size_t)max * 4, &osk_file.f_pos);

	return r > 0 ? (int)(r / 4) : (int)r;
}
