	.file	1 "probe.c"
	.section .mdebug.abi32
	.previous
	.text
	.align	2
	.globl	probe_seq_store
	.ent	probe_seq_store
	.type	probe_seq_store, @function
probe_seq_store:
	.frame	$sp,0,$31		# vars= 0, regs= 0/0, args= 0, gp= 0
	.mask	0x00000000,0
	.fmask	0x00000000,0
	li	$2,-1			# 0xffffffffffffffff
	sw	$2,0($4)
	.set	noreorder
	.set	nomacro
	j	$31
	sw	$5,0($4)
	.set	macro
	.set	reorder

	.end	probe_seq_store
	.align	2
	.globl	probe_seq_load
	.ent	probe_seq_load
	.type	probe_seq_load, @function
probe_seq_load:
	.frame	$sp,0,$31		# vars= 0, regs= 0/0, args= 0, gp= 0
	.mask	0x00000000,0
	.fmask	0x00000000,0
	.set	noreorder
	.set	nomacro
	
	lw	$2,0($4)
	j	$31
	nop

	.set	macro
	.set	reorder
	.end	probe_seq_load
	.align	2
	.globl	probe_u16_store
	.ent	probe_u16_store
	.type	probe_u16_store, @function
probe_u16_store:
	.frame	$sp,0,$31		# vars= 0, regs= 0/0, args= 0, gp= 0
	.mask	0x00000000,0
	.fmask	0x00000000,0
	.set	noreorder
	.set	nomacro
	
	j	$31
	sh	$5,16($4)

	.set	macro
	.set	reorder
	.end	probe_u16_store
	.align	2
	.globl	probe_u32_store
	.ent	probe_u32_store
	.type	probe_u32_store, @function
probe_u32_store:
	.frame	$sp,0,$31		# vars= 0, regs= 0/0, args= 0, gp= 0
	.mask	0x00000000,0
	.fmask	0x00000000,0
	.set	noreorder
	.set	nomacro
	
	sw	$5,24($4)
	j	$31
	sw	$5,80($4)

	.set	macro
	.set	reorder
	.end	probe_u32_store
	.globl	PROBE__psc_sc__SIZE
	.rdata
	.align	2
	.type	PROBE__psc_sc__SIZE, @object
	.size	PROBE__psc_sc__SIZE, 4
PROBE__psc_sc__SIZE:
	.word	80
	.globl	PROBE__psc_sc__seq__OFF
	.align	2
	.type	PROBE__psc_sc__seq__OFF, @object
	.size	PROBE__psc_sc__seq__OFF, 4
PROBE__psc_sc__seq__OFF:
	.space	4
	.globl	PROBE__psc_sc__seq__ESZ
	.align	2
	.type	PROBE__psc_sc__seq__ESZ, @object
	.size	PROBE__psc_sc__seq__ESZ, 4
PROBE__psc_sc__seq__ESZ:
	.word	4
	.globl	PROBE__psc_sc__seq__TSZ
	.align	2
	.type	PROBE__psc_sc__seq__TSZ, @object
	.size	PROBE__psc_sc__seq__TSZ, 4
PROBE__psc_sc__seq__TSZ:
	.word	4
	.globl	PROBE__psc_sc__seq__SGN
	.align	2
	.type	PROBE__psc_sc__seq__SGN, @object
	.size	PROBE__psc_sc__seq__SGN, 4
PROBE__psc_sc__seq__SGN:
	.space	4
	.globl	PROBE__psc_sc__tick_in__OFF
	.align	2
	.type	PROBE__psc_sc__tick_in__OFF, @object
	.size	PROBE__psc_sc__tick_in__OFF, 4
PROBE__psc_sc__tick_in__OFF:
	.word	4
	.globl	PROBE__psc_sc__tick_in__ESZ
	.align	2
	.type	PROBE__psc_sc__tick_in__ESZ, @object
	.size	PROBE__psc_sc__tick_in__ESZ, 4
PROBE__psc_sc__tick_in__ESZ:
	.word	4
	.globl	PROBE__psc_sc__tick_in__TSZ
	.align	2
	.type	PROBE__psc_sc__tick_in__TSZ, @object
	.size	PROBE__psc_sc__tick_in__TSZ, 4
PROBE__psc_sc__tick_in__TSZ:
	.word	4
	.globl	PROBE__psc_sc__tick_in__SGN
	.align	2
	.type	PROBE__psc_sc__tick_in__SGN, @object
	.size	PROBE__psc_sc__tick_in__SGN, 4
PROBE__psc_sc__tick_in__SGN:
	.space	4
	.globl	PROBE__psc_sc__c_in__OFF
	.align	2
	.type	PROBE__psc_sc__c_in__OFF, @object
	.size	PROBE__psc_sc__c_in__OFF, 4
PROBE__psc_sc__c_in__OFF:
	.word	8
	.globl	PROBE__psc_sc__c_in__ESZ
	.align	2
	.type	PROBE__psc_sc__c_in__ESZ, @object
	.size	PROBE__psc_sc__c_in__ESZ, 4
PROBE__psc_sc__c_in__ESZ:
	.word	4
	.globl	PROBE__psc_sc__c_in__TSZ
	.align	2
	.type	PROBE__psc_sc__c_in__TSZ, @object
	.size	PROBE__psc_sc__c_in__TSZ, 4
PROBE__psc_sc__c_in__TSZ:
	.word	4
	.globl	PROBE__psc_sc__c_in__SGN
	.align	2
	.type	PROBE__psc_sc__c_in__SGN, @object
	.size	PROBE__psc_sc__c_in__SGN, 4
PROBE__psc_sc__c_in__SGN:
	.space	4
	.globl	PROBE__psc_sc__c_out__OFF
	.align	2
	.type	PROBE__psc_sc__c_out__OFF, @object
	.size	PROBE__psc_sc__c_out__OFF, 4
PROBE__psc_sc__c_out__OFF:
	.word	12
	.globl	PROBE__psc_sc__c_out__ESZ
	.align	2
	.type	PROBE__psc_sc__c_out__ESZ, @object
	.size	PROBE__psc_sc__c_out__ESZ, 4
PROBE__psc_sc__c_out__ESZ:
	.word	4
	.globl	PROBE__psc_sc__c_out__TSZ
	.align	2
	.type	PROBE__psc_sc__c_out__TSZ, @object
	.size	PROBE__psc_sc__c_out__TSZ, 4
PROBE__psc_sc__c_out__TSZ:
	.word	4
	.globl	PROBE__psc_sc__c_out__SGN
	.align	2
	.type	PROBE__psc_sc__c_out__SGN, @object
	.size	PROBE__psc_sc__c_out__SGN, 4
PROBE__psc_sc__c_out__SGN:
	.space	4
	.globl	PROBE__psc_sc__dtick__OFF
	.align	2
	.type	PROBE__psc_sc__dtick__OFF, @object
	.size	PROBE__psc_sc__dtick__OFF, 4
PROBE__psc_sc__dtick__OFF:
	.word	16
	.globl	PROBE__psc_sc__dtick__ESZ
	.align	2
	.type	PROBE__psc_sc__dtick__ESZ, @object
	.size	PROBE__psc_sc__dtick__ESZ, 4
PROBE__psc_sc__dtick__ESZ:
	.word	2
	.globl	PROBE__psc_sc__dtick__TSZ
	.align	2
	.type	PROBE__psc_sc__dtick__TSZ, @object
	.size	PROBE__psc_sc__dtick__TSZ, 4
PROBE__psc_sc__dtick__TSZ:
	.word	2
	.globl	PROBE__psc_sc__dtick__SGN
	.align	2
	.type	PROBE__psc_sc__dtick__SGN, @object
	.size	PROBE__psc_sc__dtick__SGN, 4
PROBE__psc_sc__dtick__SGN:
	.space	4
	.globl	PROBE__psc_sc__cmd__OFF
	.align	2
	.type	PROBE__psc_sc__cmd__OFF, @object
	.size	PROBE__psc_sc__cmd__OFF, 4
PROBE__psc_sc__cmd__OFF:
	.word	18
	.globl	PROBE__psc_sc__cmd__ESZ
	.align	2
	.type	PROBE__psc_sc__cmd__ESZ, @object
	.size	PROBE__psc_sc__cmd__ESZ, 4
PROBE__psc_sc__cmd__ESZ:
	.word	1
	.globl	PROBE__psc_sc__cmd__TSZ
	.align	2
	.type	PROBE__psc_sc__cmd__TSZ, @object
	.size	PROBE__psc_sc__cmd__TSZ, 4
PROBE__psc_sc__cmd__TSZ:
	.word	1
	.globl	PROBE__psc_sc__cmd__SGN
	.align	2
	.type	PROBE__psc_sc__cmd__SGN, @object
	.size	PROBE__psc_sc__cmd__SGN, 4
PROBE__psc_sc__cmd__SGN:
	.space	4
	.globl	PROBE__psc_sc__txlen__OFF
	.align	2
	.type	PROBE__psc_sc__txlen__OFF, @object
	.size	PROBE__psc_sc__txlen__OFF, 4
PROBE__psc_sc__txlen__OFF:
	.word	19
	.globl	PROBE__psc_sc__txlen__ESZ
	.align	2
	.type	PROBE__psc_sc__txlen__ESZ, @object
	.size	PROBE__psc_sc__txlen__ESZ, 4
PROBE__psc_sc__txlen__ESZ:
	.word	1
	.globl	PROBE__psc_sc__txlen__TSZ
	.align	2
	.type	PROBE__psc_sc__txlen__TSZ, @object
	.size	PROBE__psc_sc__txlen__TSZ, 4
PROBE__psc_sc__txlen__TSZ:
	.word	1
	.globl	PROBE__psc_sc__txlen__SGN
	.align	2
	.type	PROBE__psc_sc__txlen__SGN, @object
	.size	PROBE__psc_sc__txlen__SGN, 4
PROBE__psc_sc__txlen__SGN:
	.space	4
	.globl	PROBE__psc_sc__ret__OFF
	.align	2
	.type	PROBE__psc_sc__ret__OFF, @object
	.size	PROBE__psc_sc__ret__OFF, 4
PROBE__psc_sc__ret__OFF:
	.word	20
	.globl	PROBE__psc_sc__ret__ESZ
	.align	2
	.type	PROBE__psc_sc__ret__ESZ, @object
	.size	PROBE__psc_sc__ret__ESZ, 4
PROBE__psc_sc__ret__ESZ:
	.word	2
	.globl	PROBE__psc_sc__ret__TSZ
	.align	2
	.type	PROBE__psc_sc__ret__TSZ, @object
	.size	PROBE__psc_sc__ret__TSZ, 4
PROBE__psc_sc__ret__TSZ:
	.word	2
	.globl	PROBE__psc_sc__ret__SGN
	.align	2
	.type	PROBE__psc_sc__ret__SGN, @object
	.size	PROBE__psc_sc__ret__SGN, 4
PROBE__psc_sc__ret__SGN:
	.word	1
	.globl	PROBE__psc_sc__nwords__OFF
	.align	2
	.type	PROBE__psc_sc__nwords__OFF, @object
	.size	PROBE__psc_sc__nwords__OFF, 4
PROBE__psc_sc__nwords__OFF:
	.word	22
	.globl	PROBE__psc_sc__nwords__ESZ
	.align	2
	.type	PROBE__psc_sc__nwords__ESZ, @object
	.size	PROBE__psc_sc__nwords__ESZ, 4
PROBE__psc_sc__nwords__ESZ:
	.word	1
	.globl	PROBE__psc_sc__nwords__TSZ
	.align	2
	.type	PROBE__psc_sc__nwords__TSZ, @object
	.size	PROBE__psc_sc__nwords__TSZ, 4
PROBE__psc_sc__nwords__TSZ:
	.word	1
	.globl	PROBE__psc_sc__nwords__SGN
	.align	2
	.type	PROBE__psc_sc__nwords__SGN, @object
	.size	PROBE__psc_sc__nwords__SGN, 4
PROBE__psc_sc__nwords__SGN:
	.space	4
	.globl	PROBE__psc_sc__retries__OFF
	.align	2
	.type	PROBE__psc_sc__retries__OFF, @object
	.size	PROBE__psc_sc__retries__OFF, 4
PROBE__psc_sc__retries__OFF:
	.word	23
	.globl	PROBE__psc_sc__retries__ESZ
	.align	2
	.type	PROBE__psc_sc__retries__ESZ, @object
	.size	PROBE__psc_sc__retries__ESZ, 4
PROBE__psc_sc__retries__ESZ:
	.word	1
	.globl	PROBE__psc_sc__retries__TSZ
	.align	2
	.type	PROBE__psc_sc__retries__TSZ, @object
	.size	PROBE__psc_sc__retries__TSZ, 4
PROBE__psc_sc__retries__TSZ:
	.word	1
	.globl	PROBE__psc_sc__retries__SGN
	.align	2
	.type	PROBE__psc_sc__retries__SGN, @object
	.size	PROBE__psc_sc__retries__SGN, 4
PROBE__psc_sc__retries__SGN:
	.space	4
	.globl	PROBE__psc_sc__ack_polls__OFF
	.align	2
	.type	PROBE__psc_sc__ack_polls__OFF, @object
	.size	PROBE__psc_sc__ack_polls__OFF, 4
PROBE__psc_sc__ack_polls__OFF:
	.word	24
	.globl	PROBE__psc_sc__ack_polls__ESZ
	.align	2
	.type	PROBE__psc_sc__ack_polls__ESZ, @object
	.size	PROBE__psc_sc__ack_polls__ESZ, 4
PROBE__psc_sc__ack_polls__ESZ:
	.word	4
	.globl	PROBE__psc_sc__ack_polls__TSZ
	.align	2
	.type	PROBE__psc_sc__ack_polls__TSZ, @object
	.size	PROBE__psc_sc__ack_polls__TSZ, 4
PROBE__psc_sc__ack_polls__TSZ:
	.word	4
	.globl	PROBE__psc_sc__ack_polls__SGN
	.align	2
	.type	PROBE__psc_sc__ack_polls__SGN, @object
	.size	PROBE__psc_sc__ack_polls__SGN, 4
PROBE__psc_sc__ack_polls__SGN:
	.space	4
	.globl	PROBE__psc_sc__drain__OFF
	.align	2
	.type	PROBE__psc_sc__drain__OFF, @object
	.size	PROBE__psc_sc__drain__OFF, 4
PROBE__psc_sc__drain__OFF:
	.word	28
	.globl	PROBE__psc_sc__drain__ESZ
	.align	2
	.type	PROBE__psc_sc__drain__ESZ, @object
	.size	PROBE__psc_sc__drain__ESZ, 4
PROBE__psc_sc__drain__ESZ:
	.word	2
	.globl	PROBE__psc_sc__drain__TSZ
	.align	2
	.type	PROBE__psc_sc__drain__TSZ, @object
	.size	PROBE__psc_sc__drain__TSZ, 4
PROBE__psc_sc__drain__TSZ:
	.word	2
	.globl	PROBE__psc_sc__drain__SGN
	.align	2
	.type	PROBE__psc_sc__drain__SGN, @object
	.size	PROBE__psc_sc__drain__SGN, 4
PROBE__psc_sc__drain__SGN:
	.space	4
	.globl	PROBE__psc_sc__drain_last__OFF
	.align	2
	.type	PROBE__psc_sc__drain_last__OFF, @object
	.size	PROBE__psc_sc__drain_last__OFF, 4
PROBE__psc_sc__drain_last__OFF:
	.word	30
	.globl	PROBE__psc_sc__drain_last__ESZ
	.align	2
	.type	PROBE__psc_sc__drain_last__ESZ, @object
	.size	PROBE__psc_sc__drain_last__ESZ, 4
PROBE__psc_sc__drain_last__ESZ:
	.word	2
	.globl	PROBE__psc_sc__drain_last__TSZ
	.align	2
	.type	PROBE__psc_sc__drain_last__TSZ, @object
	.size	PROBE__psc_sc__drain_last__TSZ, 4
PROBE__psc_sc__drain_last__TSZ:
	.word	2
	.globl	PROBE__psc_sc__drain_last__SGN
	.align	2
	.type	PROBE__psc_sc__drain_last__SGN, @object
	.size	PROBE__psc_sc__drain_last__SGN, 4
PROBE__psc_sc__drain_last__SGN:
	.space	4
	.globl	PROBE__psc_sc__gpio_in__OFF
	.align	2
	.type	PROBE__psc_sc__gpio_in__OFF, @object
	.size	PROBE__psc_sc__gpio_in__OFF, 4
PROBE__psc_sc__gpio_in__OFF:
	.word	32
	.globl	PROBE__psc_sc__gpio_in__ESZ
	.align	2
	.type	PROBE__psc_sc__gpio_in__ESZ, @object
	.size	PROBE__psc_sc__gpio_in__ESZ, 4
PROBE__psc_sc__gpio_in__ESZ:
	.word	2
	.globl	PROBE__psc_sc__gpio_in__TSZ
	.align	2
	.type	PROBE__psc_sc__gpio_in__TSZ, @object
	.size	PROBE__psc_sc__gpio_in__TSZ, 4
PROBE__psc_sc__gpio_in__TSZ:
	.word	2
	.globl	PROBE__psc_sc__gpio_in__SGN
	.align	2
	.type	PROBE__psc_sc__gpio_in__SGN, @object
	.size	PROBE__psc_sc__gpio_in__SGN, 4
PROBE__psc_sc__gpio_in__SGN:
	.space	4
	.globl	PROBE__psc_sc__spi_st9__OFF
	.align	2
	.type	PROBE__psc_sc__spi_st9__OFF, @object
	.size	PROBE__psc_sc__spi_st9__OFF, 4
PROBE__psc_sc__spi_st9__OFF:
	.word	34
	.globl	PROBE__psc_sc__spi_st9__ESZ
	.align	2
	.type	PROBE__psc_sc__spi_st9__ESZ, @object
	.size	PROBE__psc_sc__spi_st9__ESZ, 4
PROBE__psc_sc__spi_st9__ESZ:
	.word	2
	.globl	PROBE__psc_sc__spi_st9__TSZ
	.align	2
	.type	PROBE__psc_sc__spi_st9__TSZ, @object
	.size	PROBE__psc_sc__spi_st9__TSZ, 4
PROBE__psc_sc__spi_st9__TSZ:
	.word	2
	.globl	PROBE__psc_sc__spi_st9__SGN
	.align	2
	.type	PROBE__psc_sc__spi_st9__SGN, @object
	.size	PROBE__psc_sc__spi_st9__SGN, 4
PROBE__psc_sc__spi_st9__SGN:
	.space	4
	.globl	PROBE__psc_sc__spi_sttx__OFF
	.align	2
	.type	PROBE__psc_sc__spi_sttx__OFF, @object
	.size	PROBE__psc_sc__spi_sttx__OFF, 4
PROBE__psc_sc__spi_sttx__OFF:
	.word	36
	.globl	PROBE__psc_sc__spi_sttx__ESZ
	.align	2
	.type	PROBE__psc_sc__spi_sttx__ESZ, @object
	.size	PROBE__psc_sc__spi_sttx__ESZ, 4
PROBE__psc_sc__spi_sttx__ESZ:
	.word	2
	.globl	PROBE__psc_sc__spi_sttx__TSZ
	.align	2
	.type	PROBE__psc_sc__spi_sttx__TSZ, @object
	.size	PROBE__psc_sc__spi_sttx__TSZ, 4
PROBE__psc_sc__spi_sttx__TSZ:
	.word	2
	.globl	PROBE__psc_sc__spi_sttx__SGN
	.align	2
	.type	PROBE__psc_sc__spi_sttx__SGN, @object
	.size	PROBE__psc_sc__spi_sttx__SGN, 4
PROBE__psc_sc__spi_sttx__SGN:
	.space	4
	.globl	PROBE__psc_sc__ctx__OFF
	.align	2
	.type	PROBE__psc_sc__ctx__OFF, @object
	.size	PROBE__psc_sc__ctx__OFF, 4
PROBE__psc_sc__ctx__OFF:
	.word	38
	.globl	PROBE__psc_sc__ctx__ESZ
	.align	2
	.type	PROBE__psc_sc__ctx__ESZ, @object
	.size	PROBE__psc_sc__ctx__ESZ, 4
PROBE__psc_sc__ctx__ESZ:
	.word	1
	.globl	PROBE__psc_sc__ctx__TSZ
	.align	2
	.type	PROBE__psc_sc__ctx__TSZ, @object
	.size	PROBE__psc_sc__ctx__TSZ, 4
PROBE__psc_sc__ctx__TSZ:
	.word	1
	.globl	PROBE__psc_sc__ctx__SGN
	.align	2
	.type	PROBE__psc_sc__ctx__SGN, @object
	.size	PROBE__psc_sc__ctx__SGN, 4
PROBE__psc_sc__ctx__SGN:
	.space	4
	.globl	PROBE__psc_sc__wn__OFF
	.align	2
	.type	PROBE__psc_sc__wn__OFF, @object
	.size	PROBE__psc_sc__wn__OFF, 4
PROBE__psc_sc__wn__OFF:
	.word	39
	.globl	PROBE__psc_sc__wn__ESZ
	.align	2
	.type	PROBE__psc_sc__wn__ESZ, @object
	.size	PROBE__psc_sc__wn__ESZ, 4
PROBE__psc_sc__wn__ESZ:
	.word	1
	.globl	PROBE__psc_sc__wn__TSZ
	.align	2
	.type	PROBE__psc_sc__wn__TSZ, @object
	.size	PROBE__psc_sc__wn__TSZ, 4
PROBE__psc_sc__wn__TSZ:
	.word	1
	.globl	PROBE__psc_sc__wn__SGN
	.align	2
	.type	PROBE__psc_sc__wn__SGN, @object
	.size	PROBE__psc_sc__wn__SGN, 4
PROBE__psc_sc__wn__SGN:
	.space	4
	.globl	PROBE__psc_sc__w_head_lo__OFF
	.align	2
	.type	PROBE__psc_sc__w_head_lo__OFF, @object
	.size	PROBE__psc_sc__w_head_lo__OFF, 4
PROBE__psc_sc__w_head_lo__OFF:
	.word	40
	.globl	PROBE__psc_sc__w_head_lo__ESZ
	.align	2
	.type	PROBE__psc_sc__w_head_lo__ESZ, @object
	.size	PROBE__psc_sc__w_head_lo__ESZ, 4
PROBE__psc_sc__w_head_lo__ESZ:
	.word	2
	.globl	PROBE__psc_sc__w_head_lo__TSZ
	.align	2
	.type	PROBE__psc_sc__w_head_lo__TSZ, @object
	.size	PROBE__psc_sc__w_head_lo__TSZ, 4
PROBE__psc_sc__w_head_lo__TSZ:
	.word	2
	.globl	PROBE__psc_sc__w_head_lo__SGN
	.align	2
	.type	PROBE__psc_sc__w_head_lo__SGN, @object
	.size	PROBE__psc_sc__w_head_lo__SGN, 4
PROBE__psc_sc__w_head_lo__SGN:
	.space	4
	.globl	PROBE__psc_sc__pre_wrk__OFF
	.align	2
	.type	PROBE__psc_sc__pre_wrk__OFF, @object
	.size	PROBE__psc_sc__pre_wrk__OFF, 4
PROBE__psc_sc__pre_wrk__OFF:
	.word	42
	.globl	PROBE__psc_sc__pre_wrk__ESZ
	.align	2
	.type	PROBE__psc_sc__pre_wrk__ESZ, @object
	.size	PROBE__psc_sc__pre_wrk__ESZ, 4
PROBE__psc_sc__pre_wrk__ESZ:
	.word	2
	.globl	PROBE__psc_sc__pre_wrk__TSZ
	.align	2
	.type	PROBE__psc_sc__pre_wrk__TSZ, @object
	.size	PROBE__psc_sc__pre_wrk__TSZ, 4
PROBE__psc_sc__pre_wrk__TSZ:
	.word	2
	.globl	PROBE__psc_sc__pre_wrk__SGN
	.align	2
	.type	PROBE__psc_sc__pre_wrk__SGN, @object
	.size	PROBE__psc_sc__pre_wrk__SGN, 4
PROBE__psc_sc__pre_wrk__SGN:
	.space	4
	.globl	PROBE__psc_sc__pre_cls__OFF
	.align	2
	.type	PROBE__psc_sc__pre_cls__OFF, @object
	.size	PROBE__psc_sc__pre_cls__OFF, 4
PROBE__psc_sc__pre_cls__OFF:
	.word	44
	.globl	PROBE__psc_sc__pre_cls__ESZ
	.align	2
	.type	PROBE__psc_sc__pre_cls__ESZ, @object
	.size	PROBE__psc_sc__pre_cls__ESZ, 4
PROBE__psc_sc__pre_cls__ESZ:
	.word	1
	.globl	PROBE__psc_sc__pre_cls__TSZ
	.align	2
	.type	PROBE__psc_sc__pre_cls__TSZ, @object
	.size	PROBE__psc_sc__pre_cls__TSZ, 4
PROBE__psc_sc__pre_cls__TSZ:
	.word	1
	.globl	PROBE__psc_sc__pre_cls__SGN
	.align	2
	.type	PROBE__psc_sc__pre_cls__SGN, @object
	.size	PROBE__psc_sc__pre_cls__SGN, 4
PROBE__psc_sc__pre_cls__SGN:
	.space	4
	.globl	PROBE__psc_sc__ms_delta__OFF
	.align	2
	.type	PROBE__psc_sc__ms_delta__OFF, @object
	.size	PROBE__psc_sc__ms_delta__OFF, 4
PROBE__psc_sc__ms_delta__OFF:
	.word	45
	.globl	PROBE__psc_sc__ms_delta__ESZ
	.align	2
	.type	PROBE__psc_sc__ms_delta__ESZ, @object
	.size	PROBE__psc_sc__ms_delta__ESZ, 4
PROBE__psc_sc__ms_delta__ESZ:
	.word	1
	.globl	PROBE__psc_sc__ms_delta__TSZ
	.align	2
	.type	PROBE__psc_sc__ms_delta__TSZ, @object
	.size	PROBE__psc_sc__ms_delta__TSZ, 4
PROBE__psc_sc__ms_delta__TSZ:
	.word	1
	.globl	PROBE__psc_sc__ms_delta__SGN
	.align	2
	.type	PROBE__psc_sc__ms_delta__SGN, @object
	.size	PROBE__psc_sc__ms_delta__SGN, 4
PROBE__psc_sc__ms_delta__SGN:
	.space	4
	.globl	PROBE__psc_sc__pre_flags__OFF
	.align	2
	.type	PROBE__psc_sc__pre_flags__OFF, @object
	.size	PROBE__psc_sc__pre_flags__OFF, 4
PROBE__psc_sc__pre_flags__OFF:
	.word	46
	.globl	PROBE__psc_sc__pre_flags__ESZ
	.align	2
	.type	PROBE__psc_sc__pre_flags__ESZ, @object
	.size	PROBE__psc_sc__pre_flags__ESZ, 4
PROBE__psc_sc__pre_flags__ESZ:
	.word	1
	.globl	PROBE__psc_sc__pre_flags__TSZ
	.align	2
	.type	PROBE__psc_sc__pre_flags__TSZ, @object
	.size	PROBE__psc_sc__pre_flags__TSZ, 4
PROBE__psc_sc__pre_flags__TSZ:
	.word	1
	.globl	PROBE__psc_sc__pre_flags__SGN
	.align	2
	.type	PROBE__psc_sc__pre_flags__SGN, @object
	.size	PROBE__psc_sc__pre_flags__SGN, 4
PROBE__psc_sc__pre_flags__SGN:
	.space	4
	.globl	PROBE__psc_sc__preempt_delta__OFF
	.align	2
	.type	PROBE__psc_sc__preempt_delta__OFF, @object
	.size	PROBE__psc_sc__preempt_delta__OFF, 4
PROBE__psc_sc__preempt_delta__OFF:
	.word	47
	.globl	PROBE__psc_sc__preempt_delta__ESZ
	.align	2
	.type	PROBE__psc_sc__preempt_delta__ESZ, @object
	.size	PROBE__psc_sc__preempt_delta__ESZ, 4
PROBE__psc_sc__preempt_delta__ESZ:
	.word	1
	.globl	PROBE__psc_sc__preempt_delta__TSZ
	.align	2
	.type	PROBE__psc_sc__preempt_delta__TSZ, @object
	.size	PROBE__psc_sc__preempt_delta__TSZ, 4
PROBE__psc_sc__preempt_delta__TSZ:
	.word	1
	.globl	PROBE__psc_sc__preempt_delta__SGN
	.align	2
	.type	PROBE__psc_sc__preempt_delta__SGN, @object
	.size	PROBE__psc_sc__preempt_delta__SGN, 4
PROBE__psc_sc__preempt_delta__SGN:
	.space	4
	.globl	PROBE__psc_sc__rx__OFF
	.align	2
	.type	PROBE__psc_sc__rx__OFF, @object
	.size	PROBE__psc_sc__rx__OFF, 4
PROBE__psc_sc__rx__OFF:
	.word	48
	.globl	PROBE__psc_sc__rx__ESZ
	.align	2
	.type	PROBE__psc_sc__rx__ESZ, @object
	.size	PROBE__psc_sc__rx__ESZ, 4
PROBE__psc_sc__rx__ESZ:
	.word	1
	.globl	PROBE__psc_sc__rx__TSZ
	.align	2
	.type	PROBE__psc_sc__rx__TSZ, @object
	.size	PROBE__psc_sc__rx__TSZ, 4
PROBE__psc_sc__rx__TSZ:
	.word	16
	.globl	PROBE__psc_sc__rx__SGN
	.align	2
	.type	PROBE__psc_sc__rx__SGN, @object
	.size	PROBE__psc_sc__rx__SGN, 4
PROBE__psc_sc__rx__SGN:
	.space	4
	.globl	PROBE__psc_sc__lc_epc__OFF
	.align	2
	.type	PROBE__psc_sc__lc_epc__OFF, @object
	.size	PROBE__psc_sc__lc_epc__OFF, 4
PROBE__psc_sc__lc_epc__OFF:
	.word	64
	.globl	PROBE__psc_sc__lc_epc__ESZ
	.align	2
	.type	PROBE__psc_sc__lc_epc__ESZ, @object
	.size	PROBE__psc_sc__lc_epc__ESZ, 4
PROBE__psc_sc__lc_epc__ESZ:
	.word	4
	.globl	PROBE__psc_sc__lc_epc__TSZ
	.align	2
	.type	PROBE__psc_sc__lc_epc__TSZ, @object
	.size	PROBE__psc_sc__lc_epc__TSZ, 4
PROBE__psc_sc__lc_epc__TSZ:
	.word	4
	.globl	PROBE__psc_sc__lc_epc__SGN
	.align	2
	.type	PROBE__psc_sc__lc_epc__SGN, @object
	.size	PROBE__psc_sc__lc_epc__SGN, 4
PROBE__psc_sc__lc_epc__SGN:
	.space	4
	.globl	PROBE__psc_sc__lc_dtick__OFF
	.align	2
	.type	PROBE__psc_sc__lc_dtick__OFF, @object
	.size	PROBE__psc_sc__lc_dtick__OFF, 4
PROBE__psc_sc__lc_dtick__OFF:
	.word	68
	.globl	PROBE__psc_sc__lc_dtick__ESZ
	.align	2
	.type	PROBE__psc_sc__lc_dtick__ESZ, @object
	.size	PROBE__psc_sc__lc_dtick__ESZ, 4
PROBE__psc_sc__lc_dtick__ESZ:
	.word	2
	.globl	PROBE__psc_sc__lc_dtick__TSZ
	.align	2
	.type	PROBE__psc_sc__lc_dtick__TSZ, @object
	.size	PROBE__psc_sc__lc_dtick__TSZ, 4
PROBE__psc_sc__lc_dtick__TSZ:
	.word	2
	.globl	PROBE__psc_sc__lc_dtick__SGN
	.align	2
	.type	PROBE__psc_sc__lc_dtick__SGN, @object
	.size	PROBE__psc_sc__lc_dtick__SGN, 4
PROBE__psc_sc__lc_dtick__SGN:
	.space	4
	.globl	PROBE__psc_sc__lc_n__OFF
	.align	2
	.type	PROBE__psc_sc__lc_n__OFF, @object
	.size	PROBE__psc_sc__lc_n__OFF, 4
PROBE__psc_sc__lc_n__OFF:
	.word	70
	.globl	PROBE__psc_sc__lc_n__ESZ
	.align	2
	.type	PROBE__psc_sc__lc_n__ESZ, @object
	.size	PROBE__psc_sc__lc_n__ESZ, 4
PROBE__psc_sc__lc_n__ESZ:
	.word	1
	.globl	PROBE__psc_sc__lc_n__TSZ
	.align	2
	.type	PROBE__psc_sc__lc_n__TSZ, @object
	.size	PROBE__psc_sc__lc_n__TSZ, 4
PROBE__psc_sc__lc_n__TSZ:
	.word	1
	.globl	PROBE__psc_sc__lc_n__SGN
	.align	2
	.type	PROBE__psc_sc__lc_n__SGN, @object
	.size	PROBE__psc_sc__lc_n__SGN, 4
PROBE__psc_sc__lc_n__SGN:
	.space	4
	.globl	PROBE__psc_sc__lc_flags__OFF
	.align	2
	.type	PROBE__psc_sc__lc_flags__OFF, @object
	.size	PROBE__psc_sc__lc_flags__OFF, 4
PROBE__psc_sc__lc_flags__OFF:
	.word	71
	.globl	PROBE__psc_sc__lc_flags__ESZ
	.align	2
	.type	PROBE__psc_sc__lc_flags__ESZ, @object
	.size	PROBE__psc_sc__lc_flags__ESZ, 4
PROBE__psc_sc__lc_flags__ESZ:
	.word	1
	.globl	PROBE__psc_sc__lc_flags__TSZ
	.align	2
	.type	PROBE__psc_sc__lc_flags__TSZ, @object
	.size	PROBE__psc_sc__lc_flags__TSZ, 4
PROBE__psc_sc__lc_flags__TSZ:
	.word	1
	.globl	PROBE__psc_sc__lc_flags__SGN
	.align	2
	.type	PROBE__psc_sc__lc_flags__SGN, @object
	.size	PROBE__psc_sc__lc_flags__SGN, 4
PROBE__psc_sc__lc_flags__SGN:
	.space	4
	.globl	PROBE__psc_sc__led_or__OFF
	.align	2
	.type	PROBE__psc_sc__led_or__OFF, @object
	.size	PROBE__psc_sc__led_or__OFF, 4
PROBE__psc_sc__led_or__OFF:
	.word	72
	.globl	PROBE__psc_sc__led_or__ESZ
	.align	2
	.type	PROBE__psc_sc__led_or__ESZ, @object
	.size	PROBE__psc_sc__led_or__ESZ, 4
PROBE__psc_sc__led_or__ESZ:
	.word	4
	.globl	PROBE__psc_sc__led_or__TSZ
	.align	2
	.type	PROBE__psc_sc__led_or__TSZ, @object
	.size	PROBE__psc_sc__led_or__TSZ, 4
PROBE__psc_sc__led_or__TSZ:
	.word	4
	.globl	PROBE__psc_sc__led_or__SGN
	.align	2
	.type	PROBE__psc_sc__led_or__SGN, @object
	.size	PROBE__psc_sc__led_or__SGN, 4
PROBE__psc_sc__led_or__SGN:
	.space	4
	.globl	PROBE__psc_sc__led_pid__OFF
	.align	2
	.type	PROBE__psc_sc__led_pid__OFF, @object
	.size	PROBE__psc_sc__led_pid__OFF, 4
PROBE__psc_sc__led_pid__OFF:
	.word	76
	.globl	PROBE__psc_sc__led_pid__ESZ
	.align	2
	.type	PROBE__psc_sc__led_pid__ESZ, @object
	.size	PROBE__psc_sc__led_pid__ESZ, 4
PROBE__psc_sc__led_pid__ESZ:
	.word	2
	.globl	PROBE__psc_sc__led_pid__TSZ
	.align	2
	.type	PROBE__psc_sc__led_pid__TSZ, @object
	.size	PROBE__psc_sc__led_pid__TSZ, 4
PROBE__psc_sc__led_pid__TSZ:
	.word	2
	.globl	PROBE__psc_sc__led_pid__SGN
	.align	2
	.type	PROBE__psc_sc__led_pid__SGN, @object
	.size	PROBE__psc_sc__led_pid__SGN, 4
PROBE__psc_sc__led_pid__SGN:
	.space	4
	.globl	PROBE__psc_sc__pre_tot__OFF
	.align	2
	.type	PROBE__psc_sc__pre_tot__OFF, @object
	.size	PROBE__psc_sc__pre_tot__OFF, 4
PROBE__psc_sc__pre_tot__OFF:
	.word	78
	.globl	PROBE__psc_sc__pre_tot__ESZ
	.align	2
	.type	PROBE__psc_sc__pre_tot__ESZ, @object
	.size	PROBE__psc_sc__pre_tot__ESZ, 4
PROBE__psc_sc__pre_tot__ESZ:
	.word	2
	.globl	PROBE__psc_sc__pre_tot__TSZ
	.align	2
	.type	PROBE__psc_sc__pre_tot__TSZ, @object
	.size	PROBE__psc_sc__pre_tot__TSZ, 4
PROBE__psc_sc__pre_tot__TSZ:
	.word	2
	.globl	PROBE__psc_sc__pre_tot__SGN
	.align	2
	.type	PROBE__psc_sc__pre_tot__SGN, @object
	.size	PROBE__psc_sc__pre_tot__SGN, 4
PROBE__psc_sc__pre_tot__SGN:
	.space	4
	.globl	PROBE__psc_wext__SIZE
	.align	2
	.type	PROBE__psc_wext__SIZE, @object
	.size	PROBE__psc_wext__SIZE, 4
PROBE__psc_wext__SIZE:
	.word	208
	.globl	PROBE__psc_wext__epc__OFF
	.align	2
	.type	PROBE__psc_wext__epc__OFF, @object
	.size	PROBE__psc_wext__epc__OFF, 4
PROBE__psc_wext__epc__OFF:
	.space	4
	.globl	PROBE__psc_wext__epc__ESZ
	.align	2
	.type	PROBE__psc_wext__epc__ESZ, @object
	.size	PROBE__psc_wext__epc__ESZ, 4
PROBE__psc_wext__epc__ESZ:
	.word	4
	.globl	PROBE__psc_wext__epc__TSZ
	.align	2
	.type	PROBE__psc_wext__epc__TSZ, @object
	.size	PROBE__psc_wext__epc__TSZ, 4
PROBE__psc_wext__epc__TSZ:
	.word	4
	.globl	PROBE__psc_wext__epc__SGN
	.align	2
	.type	PROBE__psc_wext__epc__SGN, @object
	.size	PROBE__psc_wext__epc__SGN, 4
PROBE__psc_wext__epc__SGN:
	.space	4
	.globl	PROBE__psc_wext__cause__OFF
	.align	2
	.type	PROBE__psc_wext__cause__OFF, @object
	.size	PROBE__psc_wext__cause__OFF, 4
PROBE__psc_wext__cause__OFF:
	.word	4
	.globl	PROBE__psc_wext__cause__ESZ
	.align	2
	.type	PROBE__psc_wext__cause__ESZ, @object
	.size	PROBE__psc_wext__cause__ESZ, 4
PROBE__psc_wext__cause__ESZ:
	.word	4
	.globl	PROBE__psc_wext__cause__TSZ
	.align	2
	.type	PROBE__psc_wext__cause__TSZ, @object
	.size	PROBE__psc_wext__cause__TSZ, 4
PROBE__psc_wext__cause__TSZ:
	.word	4
	.globl	PROBE__psc_wext__cause__SGN
	.align	2
	.type	PROBE__psc_wext__cause__SGN, @object
	.size	PROBE__psc_wext__cause__SGN, 4
PROBE__psc_wext__cause__SGN:
	.space	4
	.globl	PROBE__psc_wext__status__OFF
	.align	2
	.type	PROBE__psc_wext__status__OFF, @object
	.size	PROBE__psc_wext__status__OFF, 4
PROBE__psc_wext__status__OFF:
	.word	8
	.globl	PROBE__psc_wext__status__ESZ
	.align	2
	.type	PROBE__psc_wext__status__ESZ, @object
	.size	PROBE__psc_wext__status__ESZ, 4
PROBE__psc_wext__status__ESZ:
	.word	4
	.globl	PROBE__psc_wext__status__TSZ
	.align	2
	.type	PROBE__psc_wext__status__TSZ, @object
	.size	PROBE__psc_wext__status__TSZ, 4
PROBE__psc_wext__status__TSZ:
	.word	4
	.globl	PROBE__psc_wext__status__SGN
	.align	2
	.type	PROBE__psc_wext__status__SGN, @object
	.size	PROBE__psc_wext__status__SGN, 4
PROBE__psc_wext__status__SGN:
	.space	4
	.globl	PROBE__psc_wext__ra__OFF
	.align	2
	.type	PROBE__psc_wext__ra__OFF, @object
	.size	PROBE__psc_wext__ra__OFF, 4
PROBE__psc_wext__ra__OFF:
	.word	12
	.globl	PROBE__psc_wext__ra__ESZ
	.align	2
	.type	PROBE__psc_wext__ra__ESZ, @object
	.size	PROBE__psc_wext__ra__ESZ, 4
PROBE__psc_wext__ra__ESZ:
	.word	4
	.globl	PROBE__psc_wext__ra__TSZ
	.align	2
	.type	PROBE__psc_wext__ra__TSZ, @object
	.size	PROBE__psc_wext__ra__TSZ, 4
PROBE__psc_wext__ra__TSZ:
	.word	4
	.globl	PROBE__psc_wext__ra__SGN
	.align	2
	.type	PROBE__psc_wext__ra__SGN, @object
	.size	PROBE__psc_wext__ra__SGN, 4
PROBE__psc_wext__ra__SGN:
	.space	4
	.globl	PROBE__psc_wext__sp__OFF
	.align	2
	.type	PROBE__psc_wext__sp__OFF, @object
	.size	PROBE__psc_wext__sp__OFF, 4
PROBE__psc_wext__sp__OFF:
	.word	16
	.globl	PROBE__psc_wext__sp__ESZ
	.align	2
	.type	PROBE__psc_wext__sp__ESZ, @object
	.size	PROBE__psc_wext__sp__ESZ, 4
PROBE__psc_wext__sp__ESZ:
	.word	4
	.globl	PROBE__psc_wext__sp__TSZ
	.align	2
	.type	PROBE__psc_wext__sp__TSZ, @object
	.size	PROBE__psc_wext__sp__TSZ, 4
PROBE__psc_wext__sp__TSZ:
	.word	4
	.globl	PROBE__psc_wext__sp__SGN
	.align	2
	.type	PROBE__psc_wext__sp__SGN, @object
	.size	PROBE__psc_wext__sp__SGN, 4
PROBE__psc_wext__sp__SGN:
	.space	4
	.globl	PROBE__psc_wext__r__OFF
	.align	2
	.type	PROBE__psc_wext__r__OFF, @object
	.size	PROBE__psc_wext__r__OFF, 4
PROBE__psc_wext__r__OFF:
	.word	20
	.globl	PROBE__psc_wext__r__ESZ
	.align	2
	.type	PROBE__psc_wext__r__ESZ, @object
	.size	PROBE__psc_wext__r__ESZ, 4
PROBE__psc_wext__r__ESZ:
	.word	4
	.globl	PROBE__psc_wext__r__TSZ
	.align	2
	.type	PROBE__psc_wext__r__TSZ, @object
	.size	PROBE__psc_wext__r__TSZ, 4
PROBE__psc_wext__r__TSZ:
	.word	64
	.globl	PROBE__psc_wext__r__SGN
	.align	2
	.type	PROBE__psc_wext__r__SGN, @object
	.size	PROBE__psc_wext__r__SGN, 4
PROBE__psc_wext__r__SGN:
	.space	4
	.globl	PROBE__psc_wext__pid__OFF
	.align	2
	.type	PROBE__psc_wext__pid__OFF, @object
	.size	PROBE__psc_wext__pid__OFF, 4
PROBE__psc_wext__pid__OFF:
	.word	84
	.globl	PROBE__psc_wext__pid__ESZ
	.align	2
	.type	PROBE__psc_wext__pid__ESZ, @object
	.size	PROBE__psc_wext__pid__ESZ, 4
PROBE__psc_wext__pid__ESZ:
	.word	4
	.globl	PROBE__psc_wext__pid__TSZ
	.align	2
	.type	PROBE__psc_wext__pid__TSZ, @object
	.size	PROBE__psc_wext__pid__TSZ, 4
PROBE__psc_wext__pid__TSZ:
	.word	4
	.globl	PROBE__psc_wext__pid__SGN
	.align	2
	.type	PROBE__psc_wext__pid__SGN, @object
	.size	PROBE__psc_wext__pid__SGN, 4
PROBE__psc_wext__pid__SGN:
	.space	4
	.globl	PROBE__psc_wext__p_head__OFF
	.align	2
	.type	PROBE__psc_wext__p_head__OFF, @object
	.size	PROBE__psc_wext__p_head__OFF, 4
PROBE__psc_wext__p_head__OFF:
	.word	88
	.globl	PROBE__psc_wext__p_head__ESZ
	.align	2
	.type	PROBE__psc_wext__p_head__ESZ, @object
	.size	PROBE__psc_wext__p_head__ESZ, 4
PROBE__psc_wext__p_head__ESZ:
	.word	4
	.globl	PROBE__psc_wext__p_head__TSZ
	.align	2
	.type	PROBE__psc_wext__p_head__TSZ, @object
	.size	PROBE__psc_wext__p_head__TSZ, 4
PROBE__psc_wext__p_head__TSZ:
	.word	4
	.globl	PROBE__psc_wext__p_head__SGN
	.align	2
	.type	PROBE__psc_wext__p_head__SGN, @object
	.size	PROBE__psc_wext__p_head__SGN, 4
PROBE__psc_wext__p_head__SGN:
	.space	4
	.globl	PROBE__psc_wext__jp_loop__OFF
	.align	2
	.type	PROBE__psc_wext__jp_loop__OFF, @object
	.size	PROBE__psc_wext__jp_loop__OFF, 4
PROBE__psc_wext__jp_loop__OFF:
	.word	92
	.globl	PROBE__psc_wext__jp_loop__ESZ
	.align	2
	.type	PROBE__psc_wext__jp_loop__ESZ, @object
	.size	PROBE__psc_wext__jp_loop__ESZ, 4
PROBE__psc_wext__jp_loop__ESZ:
	.word	4
	.globl	PROBE__psc_wext__jp_loop__TSZ
	.align	2
	.type	PROBE__psc_wext__jp_loop__TSZ, @object
	.size	PROBE__psc_wext__jp_loop__TSZ, 4
PROBE__psc_wext__jp_loop__TSZ:
	.word	4
	.globl	PROBE__psc_wext__jp_loop__SGN
	.align	2
	.type	PROBE__psc_wext__jp_loop__SGN, @object
	.size	PROBE__psc_wext__jp_loop__SGN, 4
PROBE__psc_wext__jp_loop__SGN:
	.space	4
	.globl	PROBE__psc_wext__t_entry_tick__OFF
	.align	2
	.type	PROBE__psc_wext__t_entry_tick__OFF, @object
	.size	PROBE__psc_wext__t_entry_tick__OFF, 4
PROBE__psc_wext__t_entry_tick__OFF:
	.word	96
	.globl	PROBE__psc_wext__t_entry_tick__ESZ
	.align	2
	.type	PROBE__psc_wext__t_entry_tick__ESZ, @object
	.size	PROBE__psc_wext__t_entry_tick__ESZ, 4
PROBE__psc_wext__t_entry_tick__ESZ:
	.word	4
	.globl	PROBE__psc_wext__t_entry_tick__TSZ
	.align	2
	.type	PROBE__psc_wext__t_entry_tick__TSZ, @object
	.size	PROBE__psc_wext__t_entry_tick__TSZ, 4
PROBE__psc_wext__t_entry_tick__TSZ:
	.word	4
	.globl	PROBE__psc_wext__t_entry_tick__SGN
	.align	2
	.type	PROBE__psc_wext__t_entry_tick__SGN, @object
	.size	PROBE__psc_wext__t_entry_tick__SGN, 4
PROBE__psc_wext__t_entry_tick__SGN:
	.space	4
	.globl	PROBE__psc_wext__t_entry_c__OFF
	.align	2
	.type	PROBE__psc_wext__t_entry_c__OFF, @object
	.size	PROBE__psc_wext__t_entry_c__OFF, 4
PROBE__psc_wext__t_entry_c__OFF:
	.word	100
	.globl	PROBE__psc_wext__t_entry_c__ESZ
	.align	2
	.type	PROBE__psc_wext__t_entry_c__ESZ, @object
	.size	PROBE__psc_wext__t_entry_c__ESZ, 4
PROBE__psc_wext__t_entry_c__ESZ:
	.word	4
	.globl	PROBE__psc_wext__t_entry_c__TSZ
	.align	2
	.type	PROBE__psc_wext__t_entry_c__TSZ, @object
	.size	PROBE__psc_wext__t_entry_c__TSZ, 4
PROBE__psc_wext__t_entry_c__TSZ:
	.word	4
	.globl	PROBE__psc_wext__t_entry_c__SGN
	.align	2
	.type	PROBE__psc_wext__t_entry_c__SGN, @object
	.size	PROBE__psc_wext__t_entry_c__SGN, 4
PROBE__psc_wext__t_entry_c__SGN:
	.space	4
	.globl	PROBE__psc_wext__t_busy__OFF
	.align	2
	.type	PROBE__psc_wext__t_busy__OFF, @object
	.size	PROBE__psc_wext__t_busy__OFF, 4
PROBE__psc_wext__t_busy__OFF:
	.word	104
	.globl	PROBE__psc_wext__t_busy__ESZ
	.align	2
	.type	PROBE__psc_wext__t_busy__ESZ, @object
	.size	PROBE__psc_wext__t_busy__ESZ, 4
PROBE__psc_wext__t_busy__ESZ:
	.word	1
	.globl	PROBE__psc_wext__t_busy__TSZ
	.align	2
	.type	PROBE__psc_wext__t_busy__TSZ, @object
	.size	PROBE__psc_wext__t_busy__TSZ, 4
PROBE__psc_wext__t_busy__TSZ:
	.word	1
	.globl	PROBE__psc_wext__t_busy__SGN
	.align	2
	.type	PROBE__psc_wext__t_busy__SGN, @object
	.size	PROBE__psc_wext__t_busy__SGN, 4
PROBE__psc_wext__t_busy__SGN:
	.space	4
	.globl	PROBE__psc_wext__jp_stage__OFF
	.align	2
	.type	PROBE__psc_wext__jp_stage__OFF, @object
	.size	PROBE__psc_wext__jp_stage__OFF, 4
PROBE__psc_wext__jp_stage__OFF:
	.word	105
	.globl	PROBE__psc_wext__jp_stage__ESZ
	.align	2
	.type	PROBE__psc_wext__jp_stage__ESZ, @object
	.size	PROBE__psc_wext__jp_stage__ESZ, 4
PROBE__psc_wext__jp_stage__ESZ:
	.word	1
	.globl	PROBE__psc_wext__jp_stage__TSZ
	.align	2
	.type	PROBE__psc_wext__jp_stage__TSZ, @object
	.size	PROBE__psc_wext__jp_stage__TSZ, 4
PROBE__psc_wext__jp_stage__TSZ:
	.word	1
	.globl	PROBE__psc_wext__jp_stage__SGN
	.align	2
	.type	PROBE__psc_wext__jp_stage__SGN, @object
	.size	PROBE__psc_wext__jp_stage__SGN, 4
PROBE__psc_wext__jp_stage__SGN:
	.space	4
	.globl	PROBE__psc_wext__ext_flags__OFF
	.align	2
	.type	PROBE__psc_wext__ext_flags__OFF, @object
	.size	PROBE__psc_wext__ext_flags__OFF, 4
PROBE__psc_wext__ext_flags__OFF:
	.word	106
	.globl	PROBE__psc_wext__ext_flags__ESZ
	.align	2
	.type	PROBE__psc_wext__ext_flags__ESZ, @object
	.size	PROBE__psc_wext__ext_flags__ESZ, 4
PROBE__psc_wext__ext_flags__ESZ:
	.word	1
	.globl	PROBE__psc_wext__ext_flags__TSZ
	.align	2
	.type	PROBE__psc_wext__ext_flags__TSZ, @object
	.size	PROBE__psc_wext__ext_flags__TSZ, 4
PROBE__psc_wext__ext_flags__TSZ:
	.word	1
	.globl	PROBE__psc_wext__ext_flags__SGN
	.align	2
	.type	PROBE__psc_wext__ext_flags__SGN, @object
	.size	PROBE__psc_wext__ext_flags__SGN, 4
PROBE__psc_wext__ext_flags__SGN:
	.space	4
	.globl	PROBE__psc_wext__cur_pcnt__OFF
	.align	2
	.type	PROBE__psc_wext__cur_pcnt__OFF, @object
	.size	PROBE__psc_wext__cur_pcnt__OFF, 4
PROBE__psc_wext__cur_pcnt__OFF:
	.word	107
	.globl	PROBE__psc_wext__cur_pcnt__ESZ
	.align	2
	.type	PROBE__psc_wext__cur_pcnt__ESZ, @object
	.size	PROBE__psc_wext__cur_pcnt__ESZ, 4
PROBE__psc_wext__cur_pcnt__ESZ:
	.word	1
	.globl	PROBE__psc_wext__cur_pcnt__TSZ
	.align	2
	.type	PROBE__psc_wext__cur_pcnt__TSZ, @object
	.size	PROBE__psc_wext__cur_pcnt__TSZ, 4
PROBE__psc_wext__cur_pcnt__TSZ:
	.word	1
	.globl	PROBE__psc_wext__cur_pcnt__SGN
	.align	2
	.type	PROBE__psc_wext__cur_pcnt__SGN, @object
	.size	PROBE__psc_wext__cur_pcnt__SGN, 4
PROBE__psc_wext__cur_pcnt__SGN:
	.space	4
	.globl	PROBE__psc_wext__c_pre__OFF
	.align	2
	.type	PROBE__psc_wext__c_pre__OFF, @object
	.size	PROBE__psc_wext__c_pre__OFF, 4
PROBE__psc_wext__c_pre__OFF:
	.word	108
	.globl	PROBE__psc_wext__c_pre__ESZ
	.align	2
	.type	PROBE__psc_wext__c_pre__ESZ, @object
	.size	PROBE__psc_wext__c_pre__ESZ, 4
PROBE__psc_wext__c_pre__ESZ:
	.word	4
	.globl	PROBE__psc_wext__c_pre__TSZ
	.align	2
	.type	PROBE__psc_wext__c_pre__TSZ, @object
	.size	PROBE__psc_wext__c_pre__TSZ, 4
PROBE__psc_wext__c_pre__TSZ:
	.word	4
	.globl	PROBE__psc_wext__c_pre__SGN
	.align	2
	.type	PROBE__psc_wext__c_pre__SGN, @object
	.size	PROBE__psc_wext__c_pre__SGN, 4
PROBE__psc_wext__c_pre__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_tick__OFF
	.align	2
	.type	PROBE__psc_wext__lc_tick__OFF, @object
	.size	PROBE__psc_wext__lc_tick__OFF, 4
PROBE__psc_wext__lc_tick__OFF:
	.word	112
	.globl	PROBE__psc_wext__lc_tick__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_tick__ESZ, @object
	.size	PROBE__psc_wext__lc_tick__ESZ, 4
PROBE__psc_wext__lc_tick__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_tick__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_tick__TSZ, @object
	.size	PROBE__psc_wext__lc_tick__TSZ, 4
PROBE__psc_wext__lc_tick__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_tick__SGN
	.align	2
	.type	PROBE__psc_wext__lc_tick__SGN, @object
	.size	PROBE__psc_wext__lc_tick__SGN, 4
PROBE__psc_wext__lc_tick__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_c_pre__OFF
	.align	2
	.type	PROBE__psc_wext__lc_c_pre__OFF, @object
	.size	PROBE__psc_wext__lc_c_pre__OFF, 4
PROBE__psc_wext__lc_c_pre__OFF:
	.word	116
	.globl	PROBE__psc_wext__lc_c_pre__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_c_pre__ESZ, @object
	.size	PROBE__psc_wext__lc_c_pre__ESZ, 4
PROBE__psc_wext__lc_c_pre__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_c_pre__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_c_pre__TSZ, @object
	.size	PROBE__psc_wext__lc_c_pre__TSZ, 4
PROBE__psc_wext__lc_c_pre__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_c_pre__SGN
	.align	2
	.type	PROBE__psc_wext__lc_c_pre__SGN, @object
	.size	PROBE__psc_wext__lc_c_pre__SGN, 4
PROBE__psc_wext__lc_c_pre__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_cmd_id__OFF
	.align	2
	.type	PROBE__psc_wext__lc_cmd_id__OFF, @object
	.size	PROBE__psc_wext__lc_cmd_id__OFF, 4
PROBE__psc_wext__lc_cmd_id__OFF:
	.word	120
	.globl	PROBE__psc_wext__lc_cmd_id__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_cmd_id__ESZ, @object
	.size	PROBE__psc_wext__lc_cmd_id__ESZ, 4
PROBE__psc_wext__lc_cmd_id__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_cmd_id__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_cmd_id__TSZ, @object
	.size	PROBE__psc_wext__lc_cmd_id__TSZ, 4
PROBE__psc_wext__lc_cmd_id__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_cmd_id__SGN
	.align	2
	.type	PROBE__psc_wext__lc_cmd_id__SGN, @object
	.size	PROBE__psc_wext__lc_cmd_id__SGN, 4
PROBE__psc_wext__lc_cmd_id__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_epc__OFF
	.align	2
	.type	PROBE__psc_wext__lc_epc__OFF, @object
	.size	PROBE__psc_wext__lc_epc__OFF, 4
PROBE__psc_wext__lc_epc__OFF:
	.word	124
	.globl	PROBE__psc_wext__lc_epc__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_epc__ESZ, @object
	.size	PROBE__psc_wext__lc_epc__ESZ, 4
PROBE__psc_wext__lc_epc__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_epc__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_epc__TSZ, @object
	.size	PROBE__psc_wext__lc_epc__TSZ, 4
PROBE__psc_wext__lc_epc__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_epc__SGN
	.align	2
	.type	PROBE__psc_wext__lc_epc__SGN, @object
	.size	PROBE__psc_wext__lc_epc__SGN, 4
PROBE__psc_wext__lc_epc__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_cause__OFF
	.align	2
	.type	PROBE__psc_wext__lc_cause__OFF, @object
	.size	PROBE__psc_wext__lc_cause__OFF, 4
PROBE__psc_wext__lc_cause__OFF:
	.word	128
	.globl	PROBE__psc_wext__lc_cause__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_cause__ESZ, @object
	.size	PROBE__psc_wext__lc_cause__ESZ, 4
PROBE__psc_wext__lc_cause__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_cause__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_cause__TSZ, @object
	.size	PROBE__psc_wext__lc_cause__TSZ, 4
PROBE__psc_wext__lc_cause__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_cause__SGN
	.align	2
	.type	PROBE__psc_wext__lc_cause__SGN, @object
	.size	PROBE__psc_wext__lc_cause__SGN, 4
PROBE__psc_wext__lc_cause__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_ra__OFF
	.align	2
	.type	PROBE__psc_wext__lc_ra__OFF, @object
	.size	PROBE__psc_wext__lc_ra__OFF, 4
PROBE__psc_wext__lc_ra__OFF:
	.word	132
	.globl	PROBE__psc_wext__lc_ra__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_ra__ESZ, @object
	.size	PROBE__psc_wext__lc_ra__ESZ, 4
PROBE__psc_wext__lc_ra__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_ra__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_ra__TSZ, @object
	.size	PROBE__psc_wext__lc_ra__TSZ, 4
PROBE__psc_wext__lc_ra__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_ra__SGN
	.align	2
	.type	PROBE__psc_wext__lc_ra__SGN, @object
	.size	PROBE__psc_wext__lc_ra__SGN, 4
PROBE__psc_wext__lc_ra__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_sp__OFF
	.align	2
	.type	PROBE__psc_wext__lc_sp__OFF, @object
	.size	PROBE__psc_wext__lc_sp__OFF, 4
PROBE__psc_wext__lc_sp__OFF:
	.word	136
	.globl	PROBE__psc_wext__lc_sp__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_sp__ESZ, @object
	.size	PROBE__psc_wext__lc_sp__ESZ, 4
PROBE__psc_wext__lc_sp__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_sp__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_sp__TSZ, @object
	.size	PROBE__psc_wext__lc_sp__TSZ, 4
PROBE__psc_wext__lc_sp__TSZ:
	.word	4
	.globl	PROBE__psc_wext__lc_sp__SGN
	.align	2
	.type	PROBE__psc_wext__lc_sp__SGN, @object
	.size	PROBE__psc_wext__lc_sp__SGN, 4
PROBE__psc_wext__lc_sp__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_r__OFF
	.align	2
	.type	PROBE__psc_wext__lc_r__OFF, @object
	.size	PROBE__psc_wext__lc_r__OFF, 4
PROBE__psc_wext__lc_r__OFF:
	.word	140
	.globl	PROBE__psc_wext__lc_r__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_r__ESZ, @object
	.size	PROBE__psc_wext__lc_r__ESZ, 4
PROBE__psc_wext__lc_r__ESZ:
	.word	4
	.globl	PROBE__psc_wext__lc_r__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_r__TSZ, @object
	.size	PROBE__psc_wext__lc_r__TSZ, 4
PROBE__psc_wext__lc_r__TSZ:
	.word	64
	.globl	PROBE__psc_wext__lc_r__SGN
	.align	2
	.type	PROBE__psc_wext__lc_r__SGN, @object
	.size	PROBE__psc_wext__lc_r__SGN, 4
PROBE__psc_wext__lc_r__SGN:
	.space	4
	.globl	PROBE__psc_wext__lc_n__OFF
	.align	2
	.type	PROBE__psc_wext__lc_n__OFF, @object
	.size	PROBE__psc_wext__lc_n__OFF, 4
PROBE__psc_wext__lc_n__OFF:
	.word	204
	.globl	PROBE__psc_wext__lc_n__ESZ
	.align	2
	.type	PROBE__psc_wext__lc_n__ESZ, @object
	.size	PROBE__psc_wext__lc_n__ESZ, 4
PROBE__psc_wext__lc_n__ESZ:
	.word	2
	.globl	PROBE__psc_wext__lc_n__TSZ
	.align	2
	.type	PROBE__psc_wext__lc_n__TSZ, @object
	.size	PROBE__psc_wext__lc_n__TSZ, 4
PROBE__psc_wext__lc_n__TSZ:
	.word	2
	.globl	PROBE__psc_wext__lc_n__SGN
	.align	2
	.type	PROBE__psc_wext__lc_n__SGN, @object
	.size	PROBE__psc_wext__lc_n__SGN, 4
PROBE__psc_wext__lc_n__SGN:
	.space	4
	.globl	PROBE__psc_wext__rsv__OFF
	.align	2
	.type	PROBE__psc_wext__rsv__OFF, @object
	.size	PROBE__psc_wext__rsv__OFF, 4
PROBE__psc_wext__rsv__OFF:
	.word	206
	.globl	PROBE__psc_wext__rsv__ESZ
	.align	2
	.type	PROBE__psc_wext__rsv__ESZ, @object
	.size	PROBE__psc_wext__rsv__ESZ, 4
PROBE__psc_wext__rsv__ESZ:
	.word	2
	.globl	PROBE__psc_wext__rsv__TSZ
	.align	2
	.type	PROBE__psc_wext__rsv__TSZ, @object
	.size	PROBE__psc_wext__rsv__TSZ, 4
PROBE__psc_wext__rsv__TSZ:
	.word	2
	.globl	PROBE__psc_wext__rsv__SGN
	.align	2
	.type	PROBE__psc_wext__rsv__SGN, @object
	.size	PROBE__psc_wext__rsv__SGN, 4
PROBE__psc_wext__rsv__SGN:
	.space	4
	.globl	PROBE__psc_w__SIZE
	.align	2
	.type	PROBE__psc_w__SIZE, @object
	.size	PROBE__psc_w__SIZE, 4
PROBE__psc_w__SIZE:
	.word	288
	.globl	PROBE__psc_w__sc_D_seq__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_seq__OFF, @object
	.size	PROBE__psc_w__sc_D_seq__OFF, 4
PROBE__psc_w__sc_D_seq__OFF:
	.space	4
	.globl	PROBE__psc_w__sc_D_seq__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_seq__ESZ, @object
	.size	PROBE__psc_w__sc_D_seq__ESZ, 4
PROBE__psc_w__sc_D_seq__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_seq__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_seq__TSZ, @object
	.size	PROBE__psc_w__sc_D_seq__TSZ, 4
PROBE__psc_w__sc_D_seq__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_seq__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_seq__SGN, @object
	.size	PROBE__psc_w__sc_D_seq__SGN, 4
PROBE__psc_w__sc_D_seq__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_tick_in__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_tick_in__OFF, @object
	.size	PROBE__psc_w__sc_D_tick_in__OFF, 4
PROBE__psc_w__sc_D_tick_in__OFF:
	.word	4
	.globl	PROBE__psc_w__sc_D_tick_in__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_tick_in__ESZ, @object
	.size	PROBE__psc_w__sc_D_tick_in__ESZ, 4
PROBE__psc_w__sc_D_tick_in__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_tick_in__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_tick_in__TSZ, @object
	.size	PROBE__psc_w__sc_D_tick_in__TSZ, 4
PROBE__psc_w__sc_D_tick_in__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_tick_in__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_tick_in__SGN, @object
	.size	PROBE__psc_w__sc_D_tick_in__SGN, 4
PROBE__psc_w__sc_D_tick_in__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_c_in__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_c_in__OFF, @object
	.size	PROBE__psc_w__sc_D_c_in__OFF, 4
PROBE__psc_w__sc_D_c_in__OFF:
	.word	8
	.globl	PROBE__psc_w__sc_D_c_in__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_c_in__ESZ, @object
	.size	PROBE__psc_w__sc_D_c_in__ESZ, 4
PROBE__psc_w__sc_D_c_in__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_c_in__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_c_in__TSZ, @object
	.size	PROBE__psc_w__sc_D_c_in__TSZ, 4
PROBE__psc_w__sc_D_c_in__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_c_in__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_c_in__SGN, @object
	.size	PROBE__psc_w__sc_D_c_in__SGN, 4
PROBE__psc_w__sc_D_c_in__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_c_out__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_c_out__OFF, @object
	.size	PROBE__psc_w__sc_D_c_out__OFF, 4
PROBE__psc_w__sc_D_c_out__OFF:
	.word	12
	.globl	PROBE__psc_w__sc_D_c_out__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_c_out__ESZ, @object
	.size	PROBE__psc_w__sc_D_c_out__ESZ, 4
PROBE__psc_w__sc_D_c_out__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_c_out__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_c_out__TSZ, @object
	.size	PROBE__psc_w__sc_D_c_out__TSZ, 4
PROBE__psc_w__sc_D_c_out__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_c_out__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_c_out__SGN, @object
	.size	PROBE__psc_w__sc_D_c_out__SGN, 4
PROBE__psc_w__sc_D_c_out__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_dtick__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_dtick__OFF, @object
	.size	PROBE__psc_w__sc_D_dtick__OFF, 4
PROBE__psc_w__sc_D_dtick__OFF:
	.word	16
	.globl	PROBE__psc_w__sc_D_dtick__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_dtick__ESZ, @object
	.size	PROBE__psc_w__sc_D_dtick__ESZ, 4
PROBE__psc_w__sc_D_dtick__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_dtick__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_dtick__TSZ, @object
	.size	PROBE__psc_w__sc_D_dtick__TSZ, 4
PROBE__psc_w__sc_D_dtick__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_dtick__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_dtick__SGN, @object
	.size	PROBE__psc_w__sc_D_dtick__SGN, 4
PROBE__psc_w__sc_D_dtick__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_cmd__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_cmd__OFF, @object
	.size	PROBE__psc_w__sc_D_cmd__OFF, 4
PROBE__psc_w__sc_D_cmd__OFF:
	.word	18
	.globl	PROBE__psc_w__sc_D_cmd__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_cmd__ESZ, @object
	.size	PROBE__psc_w__sc_D_cmd__ESZ, 4
PROBE__psc_w__sc_D_cmd__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_cmd__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_cmd__TSZ, @object
	.size	PROBE__psc_w__sc_D_cmd__TSZ, 4
PROBE__psc_w__sc_D_cmd__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_cmd__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_cmd__SGN, @object
	.size	PROBE__psc_w__sc_D_cmd__SGN, 4
PROBE__psc_w__sc_D_cmd__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_txlen__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_txlen__OFF, @object
	.size	PROBE__psc_w__sc_D_txlen__OFF, 4
PROBE__psc_w__sc_D_txlen__OFF:
	.word	19
	.globl	PROBE__psc_w__sc_D_txlen__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_txlen__ESZ, @object
	.size	PROBE__psc_w__sc_D_txlen__ESZ, 4
PROBE__psc_w__sc_D_txlen__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_txlen__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_txlen__TSZ, @object
	.size	PROBE__psc_w__sc_D_txlen__TSZ, 4
PROBE__psc_w__sc_D_txlen__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_txlen__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_txlen__SGN, @object
	.size	PROBE__psc_w__sc_D_txlen__SGN, 4
PROBE__psc_w__sc_D_txlen__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_ret__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_ret__OFF, @object
	.size	PROBE__psc_w__sc_D_ret__OFF, 4
PROBE__psc_w__sc_D_ret__OFF:
	.word	20
	.globl	PROBE__psc_w__sc_D_ret__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_ret__ESZ, @object
	.size	PROBE__psc_w__sc_D_ret__ESZ, 4
PROBE__psc_w__sc_D_ret__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_ret__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_ret__TSZ, @object
	.size	PROBE__psc_w__sc_D_ret__TSZ, 4
PROBE__psc_w__sc_D_ret__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_ret__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_ret__SGN, @object
	.size	PROBE__psc_w__sc_D_ret__SGN, 4
PROBE__psc_w__sc_D_ret__SGN:
	.word	1
	.globl	PROBE__psc_w__sc_D_nwords__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_nwords__OFF, @object
	.size	PROBE__psc_w__sc_D_nwords__OFF, 4
PROBE__psc_w__sc_D_nwords__OFF:
	.word	22
	.globl	PROBE__psc_w__sc_D_nwords__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_nwords__ESZ, @object
	.size	PROBE__psc_w__sc_D_nwords__ESZ, 4
PROBE__psc_w__sc_D_nwords__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_nwords__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_nwords__TSZ, @object
	.size	PROBE__psc_w__sc_D_nwords__TSZ, 4
PROBE__psc_w__sc_D_nwords__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_nwords__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_nwords__SGN, @object
	.size	PROBE__psc_w__sc_D_nwords__SGN, 4
PROBE__psc_w__sc_D_nwords__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_retries__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_retries__OFF, @object
	.size	PROBE__psc_w__sc_D_retries__OFF, 4
PROBE__psc_w__sc_D_retries__OFF:
	.word	23
	.globl	PROBE__psc_w__sc_D_retries__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_retries__ESZ, @object
	.size	PROBE__psc_w__sc_D_retries__ESZ, 4
PROBE__psc_w__sc_D_retries__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_retries__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_retries__TSZ, @object
	.size	PROBE__psc_w__sc_D_retries__TSZ, 4
PROBE__psc_w__sc_D_retries__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_retries__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_retries__SGN, @object
	.size	PROBE__psc_w__sc_D_retries__SGN, 4
PROBE__psc_w__sc_D_retries__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_ack_polls__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_ack_polls__OFF, @object
	.size	PROBE__psc_w__sc_D_ack_polls__OFF, 4
PROBE__psc_w__sc_D_ack_polls__OFF:
	.word	24
	.globl	PROBE__psc_w__sc_D_ack_polls__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_ack_polls__ESZ, @object
	.size	PROBE__psc_w__sc_D_ack_polls__ESZ, 4
PROBE__psc_w__sc_D_ack_polls__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_ack_polls__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_ack_polls__TSZ, @object
	.size	PROBE__psc_w__sc_D_ack_polls__TSZ, 4
PROBE__psc_w__sc_D_ack_polls__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_ack_polls__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_ack_polls__SGN, @object
	.size	PROBE__psc_w__sc_D_ack_polls__SGN, 4
PROBE__psc_w__sc_D_ack_polls__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_drain__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_drain__OFF, @object
	.size	PROBE__psc_w__sc_D_drain__OFF, 4
PROBE__psc_w__sc_D_drain__OFF:
	.word	28
	.globl	PROBE__psc_w__sc_D_drain__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_drain__ESZ, @object
	.size	PROBE__psc_w__sc_D_drain__ESZ, 4
PROBE__psc_w__sc_D_drain__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_drain__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_drain__TSZ, @object
	.size	PROBE__psc_w__sc_D_drain__TSZ, 4
PROBE__psc_w__sc_D_drain__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_drain__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_drain__SGN, @object
	.size	PROBE__psc_w__sc_D_drain__SGN, 4
PROBE__psc_w__sc_D_drain__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_drain_last__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_drain_last__OFF, @object
	.size	PROBE__psc_w__sc_D_drain_last__OFF, 4
PROBE__psc_w__sc_D_drain_last__OFF:
	.word	30
	.globl	PROBE__psc_w__sc_D_drain_last__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_drain_last__ESZ, @object
	.size	PROBE__psc_w__sc_D_drain_last__ESZ, 4
PROBE__psc_w__sc_D_drain_last__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_drain_last__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_drain_last__TSZ, @object
	.size	PROBE__psc_w__sc_D_drain_last__TSZ, 4
PROBE__psc_w__sc_D_drain_last__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_drain_last__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_drain_last__SGN, @object
	.size	PROBE__psc_w__sc_D_drain_last__SGN, 4
PROBE__psc_w__sc_D_drain_last__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_gpio_in__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_gpio_in__OFF, @object
	.size	PROBE__psc_w__sc_D_gpio_in__OFF, 4
PROBE__psc_w__sc_D_gpio_in__OFF:
	.word	32
	.globl	PROBE__psc_w__sc_D_gpio_in__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_gpio_in__ESZ, @object
	.size	PROBE__psc_w__sc_D_gpio_in__ESZ, 4
PROBE__psc_w__sc_D_gpio_in__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_gpio_in__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_gpio_in__TSZ, @object
	.size	PROBE__psc_w__sc_D_gpio_in__TSZ, 4
PROBE__psc_w__sc_D_gpio_in__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_gpio_in__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_gpio_in__SGN, @object
	.size	PROBE__psc_w__sc_D_gpio_in__SGN, 4
PROBE__psc_w__sc_D_gpio_in__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_spi_st9__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_spi_st9__OFF, @object
	.size	PROBE__psc_w__sc_D_spi_st9__OFF, 4
PROBE__psc_w__sc_D_spi_st9__OFF:
	.word	34
	.globl	PROBE__psc_w__sc_D_spi_st9__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_spi_st9__ESZ, @object
	.size	PROBE__psc_w__sc_D_spi_st9__ESZ, 4
PROBE__psc_w__sc_D_spi_st9__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_spi_st9__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_spi_st9__TSZ, @object
	.size	PROBE__psc_w__sc_D_spi_st9__TSZ, 4
PROBE__psc_w__sc_D_spi_st9__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_spi_st9__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_spi_st9__SGN, @object
	.size	PROBE__psc_w__sc_D_spi_st9__SGN, 4
PROBE__psc_w__sc_D_spi_st9__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_spi_sttx__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_spi_sttx__OFF, @object
	.size	PROBE__psc_w__sc_D_spi_sttx__OFF, 4
PROBE__psc_w__sc_D_spi_sttx__OFF:
	.word	36
	.globl	PROBE__psc_w__sc_D_spi_sttx__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_spi_sttx__ESZ, @object
	.size	PROBE__psc_w__sc_D_spi_sttx__ESZ, 4
PROBE__psc_w__sc_D_spi_sttx__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_spi_sttx__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_spi_sttx__TSZ, @object
	.size	PROBE__psc_w__sc_D_spi_sttx__TSZ, 4
PROBE__psc_w__sc_D_spi_sttx__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_spi_sttx__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_spi_sttx__SGN, @object
	.size	PROBE__psc_w__sc_D_spi_sttx__SGN, 4
PROBE__psc_w__sc_D_spi_sttx__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_ctx__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_ctx__OFF, @object
	.size	PROBE__psc_w__sc_D_ctx__OFF, 4
PROBE__psc_w__sc_D_ctx__OFF:
	.word	38
	.globl	PROBE__psc_w__sc_D_ctx__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_ctx__ESZ, @object
	.size	PROBE__psc_w__sc_D_ctx__ESZ, 4
PROBE__psc_w__sc_D_ctx__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_ctx__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_ctx__TSZ, @object
	.size	PROBE__psc_w__sc_D_ctx__TSZ, 4
PROBE__psc_w__sc_D_ctx__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_ctx__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_ctx__SGN, @object
	.size	PROBE__psc_w__sc_D_ctx__SGN, 4
PROBE__psc_w__sc_D_ctx__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_wn__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_wn__OFF, @object
	.size	PROBE__psc_w__sc_D_wn__OFF, 4
PROBE__psc_w__sc_D_wn__OFF:
	.word	39
	.globl	PROBE__psc_w__sc_D_wn__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_wn__ESZ, @object
	.size	PROBE__psc_w__sc_D_wn__ESZ, 4
PROBE__psc_w__sc_D_wn__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_wn__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_wn__TSZ, @object
	.size	PROBE__psc_w__sc_D_wn__TSZ, 4
PROBE__psc_w__sc_D_wn__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_wn__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_wn__SGN, @object
	.size	PROBE__psc_w__sc_D_wn__SGN, 4
PROBE__psc_w__sc_D_wn__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_w_head_lo__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_w_head_lo__OFF, @object
	.size	PROBE__psc_w__sc_D_w_head_lo__OFF, 4
PROBE__psc_w__sc_D_w_head_lo__OFF:
	.word	40
	.globl	PROBE__psc_w__sc_D_w_head_lo__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_w_head_lo__ESZ, @object
	.size	PROBE__psc_w__sc_D_w_head_lo__ESZ, 4
PROBE__psc_w__sc_D_w_head_lo__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_w_head_lo__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_w_head_lo__TSZ, @object
	.size	PROBE__psc_w__sc_D_w_head_lo__TSZ, 4
PROBE__psc_w__sc_D_w_head_lo__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_w_head_lo__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_w_head_lo__SGN, @object
	.size	PROBE__psc_w__sc_D_w_head_lo__SGN, 4
PROBE__psc_w__sc_D_w_head_lo__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_pre_wrk__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_pre_wrk__OFF, @object
	.size	PROBE__psc_w__sc_D_pre_wrk__OFF, 4
PROBE__psc_w__sc_D_pre_wrk__OFF:
	.word	42
	.globl	PROBE__psc_w__sc_D_pre_wrk__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_wrk__ESZ, @object
	.size	PROBE__psc_w__sc_D_pre_wrk__ESZ, 4
PROBE__psc_w__sc_D_pre_wrk__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_pre_wrk__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_wrk__TSZ, @object
	.size	PROBE__psc_w__sc_D_pre_wrk__TSZ, 4
PROBE__psc_w__sc_D_pre_wrk__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_pre_wrk__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_pre_wrk__SGN, @object
	.size	PROBE__psc_w__sc_D_pre_wrk__SGN, 4
PROBE__psc_w__sc_D_pre_wrk__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_pre_cls__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_pre_cls__OFF, @object
	.size	PROBE__psc_w__sc_D_pre_cls__OFF, 4
PROBE__psc_w__sc_D_pre_cls__OFF:
	.word	44
	.globl	PROBE__psc_w__sc_D_pre_cls__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_cls__ESZ, @object
	.size	PROBE__psc_w__sc_D_pre_cls__ESZ, 4
PROBE__psc_w__sc_D_pre_cls__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_pre_cls__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_cls__TSZ, @object
	.size	PROBE__psc_w__sc_D_pre_cls__TSZ, 4
PROBE__psc_w__sc_D_pre_cls__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_pre_cls__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_pre_cls__SGN, @object
	.size	PROBE__psc_w__sc_D_pre_cls__SGN, 4
PROBE__psc_w__sc_D_pre_cls__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_ms_delta__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_ms_delta__OFF, @object
	.size	PROBE__psc_w__sc_D_ms_delta__OFF, 4
PROBE__psc_w__sc_D_ms_delta__OFF:
	.word	45
	.globl	PROBE__psc_w__sc_D_ms_delta__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_ms_delta__ESZ, @object
	.size	PROBE__psc_w__sc_D_ms_delta__ESZ, 4
PROBE__psc_w__sc_D_ms_delta__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_ms_delta__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_ms_delta__TSZ, @object
	.size	PROBE__psc_w__sc_D_ms_delta__TSZ, 4
PROBE__psc_w__sc_D_ms_delta__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_ms_delta__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_ms_delta__SGN, @object
	.size	PROBE__psc_w__sc_D_ms_delta__SGN, 4
PROBE__psc_w__sc_D_ms_delta__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_pre_flags__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_pre_flags__OFF, @object
	.size	PROBE__psc_w__sc_D_pre_flags__OFF, 4
PROBE__psc_w__sc_D_pre_flags__OFF:
	.word	46
	.globl	PROBE__psc_w__sc_D_pre_flags__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_flags__ESZ, @object
	.size	PROBE__psc_w__sc_D_pre_flags__ESZ, 4
PROBE__psc_w__sc_D_pre_flags__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_pre_flags__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_flags__TSZ, @object
	.size	PROBE__psc_w__sc_D_pre_flags__TSZ, 4
PROBE__psc_w__sc_D_pre_flags__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_pre_flags__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_pre_flags__SGN, @object
	.size	PROBE__psc_w__sc_D_pre_flags__SGN, 4
PROBE__psc_w__sc_D_pre_flags__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_preempt_delta__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_preempt_delta__OFF, @object
	.size	PROBE__psc_w__sc_D_preempt_delta__OFF, 4
PROBE__psc_w__sc_D_preempt_delta__OFF:
	.word	47
	.globl	PROBE__psc_w__sc_D_preempt_delta__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_preempt_delta__ESZ, @object
	.size	PROBE__psc_w__sc_D_preempt_delta__ESZ, 4
PROBE__psc_w__sc_D_preempt_delta__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_preempt_delta__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_preempt_delta__TSZ, @object
	.size	PROBE__psc_w__sc_D_preempt_delta__TSZ, 4
PROBE__psc_w__sc_D_preempt_delta__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_preempt_delta__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_preempt_delta__SGN, @object
	.size	PROBE__psc_w__sc_D_preempt_delta__SGN, 4
PROBE__psc_w__sc_D_preempt_delta__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_rx__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_rx__OFF, @object
	.size	PROBE__psc_w__sc_D_rx__OFF, 4
PROBE__psc_w__sc_D_rx__OFF:
	.word	48
	.globl	PROBE__psc_w__sc_D_rx__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_rx__ESZ, @object
	.size	PROBE__psc_w__sc_D_rx__ESZ, 4
PROBE__psc_w__sc_D_rx__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_rx__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_rx__TSZ, @object
	.size	PROBE__psc_w__sc_D_rx__TSZ, 4
PROBE__psc_w__sc_D_rx__TSZ:
	.word	16
	.globl	PROBE__psc_w__sc_D_rx__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_rx__SGN, @object
	.size	PROBE__psc_w__sc_D_rx__SGN, 4
PROBE__psc_w__sc_D_rx__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_lc_epc__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_lc_epc__OFF, @object
	.size	PROBE__psc_w__sc_D_lc_epc__OFF, 4
PROBE__psc_w__sc_D_lc_epc__OFF:
	.word	64
	.globl	PROBE__psc_w__sc_D_lc_epc__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_epc__ESZ, @object
	.size	PROBE__psc_w__sc_D_lc_epc__ESZ, 4
PROBE__psc_w__sc_D_lc_epc__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_lc_epc__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_epc__TSZ, @object
	.size	PROBE__psc_w__sc_D_lc_epc__TSZ, 4
PROBE__psc_w__sc_D_lc_epc__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_lc_epc__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_lc_epc__SGN, @object
	.size	PROBE__psc_w__sc_D_lc_epc__SGN, 4
PROBE__psc_w__sc_D_lc_epc__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_lc_dtick__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_lc_dtick__OFF, @object
	.size	PROBE__psc_w__sc_D_lc_dtick__OFF, 4
PROBE__psc_w__sc_D_lc_dtick__OFF:
	.word	68
	.globl	PROBE__psc_w__sc_D_lc_dtick__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_dtick__ESZ, @object
	.size	PROBE__psc_w__sc_D_lc_dtick__ESZ, 4
PROBE__psc_w__sc_D_lc_dtick__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_lc_dtick__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_dtick__TSZ, @object
	.size	PROBE__psc_w__sc_D_lc_dtick__TSZ, 4
PROBE__psc_w__sc_D_lc_dtick__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_lc_dtick__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_lc_dtick__SGN, @object
	.size	PROBE__psc_w__sc_D_lc_dtick__SGN, 4
PROBE__psc_w__sc_D_lc_dtick__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_lc_n__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_lc_n__OFF, @object
	.size	PROBE__psc_w__sc_D_lc_n__OFF, 4
PROBE__psc_w__sc_D_lc_n__OFF:
	.word	70
	.globl	PROBE__psc_w__sc_D_lc_n__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_n__ESZ, @object
	.size	PROBE__psc_w__sc_D_lc_n__ESZ, 4
PROBE__psc_w__sc_D_lc_n__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_lc_n__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_n__TSZ, @object
	.size	PROBE__psc_w__sc_D_lc_n__TSZ, 4
PROBE__psc_w__sc_D_lc_n__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_lc_n__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_lc_n__SGN, @object
	.size	PROBE__psc_w__sc_D_lc_n__SGN, 4
PROBE__psc_w__sc_D_lc_n__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_lc_flags__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_lc_flags__OFF, @object
	.size	PROBE__psc_w__sc_D_lc_flags__OFF, 4
PROBE__psc_w__sc_D_lc_flags__OFF:
	.word	71
	.globl	PROBE__psc_w__sc_D_lc_flags__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_flags__ESZ, @object
	.size	PROBE__psc_w__sc_D_lc_flags__ESZ, 4
PROBE__psc_w__sc_D_lc_flags__ESZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_lc_flags__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_lc_flags__TSZ, @object
	.size	PROBE__psc_w__sc_D_lc_flags__TSZ, 4
PROBE__psc_w__sc_D_lc_flags__TSZ:
	.word	1
	.globl	PROBE__psc_w__sc_D_lc_flags__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_lc_flags__SGN, @object
	.size	PROBE__psc_w__sc_D_lc_flags__SGN, 4
PROBE__psc_w__sc_D_lc_flags__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_led_or__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_led_or__OFF, @object
	.size	PROBE__psc_w__sc_D_led_or__OFF, 4
PROBE__psc_w__sc_D_led_or__OFF:
	.word	72
	.globl	PROBE__psc_w__sc_D_led_or__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_led_or__ESZ, @object
	.size	PROBE__psc_w__sc_D_led_or__ESZ, 4
PROBE__psc_w__sc_D_led_or__ESZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_led_or__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_led_or__TSZ, @object
	.size	PROBE__psc_w__sc_D_led_or__TSZ, 4
PROBE__psc_w__sc_D_led_or__TSZ:
	.word	4
	.globl	PROBE__psc_w__sc_D_led_or__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_led_or__SGN, @object
	.size	PROBE__psc_w__sc_D_led_or__SGN, 4
PROBE__psc_w__sc_D_led_or__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_led_pid__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_led_pid__OFF, @object
	.size	PROBE__psc_w__sc_D_led_pid__OFF, 4
PROBE__psc_w__sc_D_led_pid__OFF:
	.word	76
	.globl	PROBE__psc_w__sc_D_led_pid__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_led_pid__ESZ, @object
	.size	PROBE__psc_w__sc_D_led_pid__ESZ, 4
PROBE__psc_w__sc_D_led_pid__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_led_pid__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_led_pid__TSZ, @object
	.size	PROBE__psc_w__sc_D_led_pid__TSZ, 4
PROBE__psc_w__sc_D_led_pid__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_led_pid__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_led_pid__SGN, @object
	.size	PROBE__psc_w__sc_D_led_pid__SGN, 4
PROBE__psc_w__sc_D_led_pid__SGN:
	.space	4
	.globl	PROBE__psc_w__sc_D_pre_tot__OFF
	.align	2
	.type	PROBE__psc_w__sc_D_pre_tot__OFF, @object
	.size	PROBE__psc_w__sc_D_pre_tot__OFF, 4
PROBE__psc_w__sc_D_pre_tot__OFF:
	.word	78
	.globl	PROBE__psc_w__sc_D_pre_tot__ESZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_tot__ESZ, @object
	.size	PROBE__psc_w__sc_D_pre_tot__ESZ, 4
PROBE__psc_w__sc_D_pre_tot__ESZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_pre_tot__TSZ
	.align	2
	.type	PROBE__psc_w__sc_D_pre_tot__TSZ, @object
	.size	PROBE__psc_w__sc_D_pre_tot__TSZ, 4
PROBE__psc_w__sc_D_pre_tot__TSZ:
	.word	2
	.globl	PROBE__psc_w__sc_D_pre_tot__SGN
	.align	2
	.type	PROBE__psc_w__sc_D_pre_tot__SGN, @object
	.size	PROBE__psc_w__sc_D_pre_tot__SGN, 4
PROBE__psc_w__sc_D_pre_tot__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_epc__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_epc__OFF, @object
	.size	PROBE__psc_w__ext_D_epc__OFF, 4
PROBE__psc_w__ext_D_epc__OFF:
	.word	80
	.globl	PROBE__psc_w__ext_D_epc__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_epc__ESZ, @object
	.size	PROBE__psc_w__ext_D_epc__ESZ, 4
PROBE__psc_w__ext_D_epc__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_epc__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_epc__TSZ, @object
	.size	PROBE__psc_w__ext_D_epc__TSZ, 4
PROBE__psc_w__ext_D_epc__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_epc__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_epc__SGN, @object
	.size	PROBE__psc_w__ext_D_epc__SGN, 4
PROBE__psc_w__ext_D_epc__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_cause__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_cause__OFF, @object
	.size	PROBE__psc_w__ext_D_cause__OFF, 4
PROBE__psc_w__ext_D_cause__OFF:
	.word	84
	.globl	PROBE__psc_w__ext_D_cause__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_cause__ESZ, @object
	.size	PROBE__psc_w__ext_D_cause__ESZ, 4
PROBE__psc_w__ext_D_cause__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_cause__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_cause__TSZ, @object
	.size	PROBE__psc_w__ext_D_cause__TSZ, 4
PROBE__psc_w__ext_D_cause__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_cause__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_cause__SGN, @object
	.size	PROBE__psc_w__ext_D_cause__SGN, 4
PROBE__psc_w__ext_D_cause__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_status__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_status__OFF, @object
	.size	PROBE__psc_w__ext_D_status__OFF, 4
PROBE__psc_w__ext_D_status__OFF:
	.word	88
	.globl	PROBE__psc_w__ext_D_status__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_status__ESZ, @object
	.size	PROBE__psc_w__ext_D_status__ESZ, 4
PROBE__psc_w__ext_D_status__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_status__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_status__TSZ, @object
	.size	PROBE__psc_w__ext_D_status__TSZ, 4
PROBE__psc_w__ext_D_status__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_status__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_status__SGN, @object
	.size	PROBE__psc_w__ext_D_status__SGN, 4
PROBE__psc_w__ext_D_status__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_ra__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_ra__OFF, @object
	.size	PROBE__psc_w__ext_D_ra__OFF, 4
PROBE__psc_w__ext_D_ra__OFF:
	.word	92
	.globl	PROBE__psc_w__ext_D_ra__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_ra__ESZ, @object
	.size	PROBE__psc_w__ext_D_ra__ESZ, 4
PROBE__psc_w__ext_D_ra__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_ra__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_ra__TSZ, @object
	.size	PROBE__psc_w__ext_D_ra__TSZ, 4
PROBE__psc_w__ext_D_ra__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_ra__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_ra__SGN, @object
	.size	PROBE__psc_w__ext_D_ra__SGN, 4
PROBE__psc_w__ext_D_ra__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_sp__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_sp__OFF, @object
	.size	PROBE__psc_w__ext_D_sp__OFF, 4
PROBE__psc_w__ext_D_sp__OFF:
	.word	96
	.globl	PROBE__psc_w__ext_D_sp__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_sp__ESZ, @object
	.size	PROBE__psc_w__ext_D_sp__ESZ, 4
PROBE__psc_w__ext_D_sp__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_sp__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_sp__TSZ, @object
	.size	PROBE__psc_w__ext_D_sp__TSZ, 4
PROBE__psc_w__ext_D_sp__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_sp__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_sp__SGN, @object
	.size	PROBE__psc_w__ext_D_sp__SGN, 4
PROBE__psc_w__ext_D_sp__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_r__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_r__OFF, @object
	.size	PROBE__psc_w__ext_D_r__OFF, 4
PROBE__psc_w__ext_D_r__OFF:
	.word	100
	.globl	PROBE__psc_w__ext_D_r__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_r__ESZ, @object
	.size	PROBE__psc_w__ext_D_r__ESZ, 4
PROBE__psc_w__ext_D_r__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_r__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_r__TSZ, @object
	.size	PROBE__psc_w__ext_D_r__TSZ, 4
PROBE__psc_w__ext_D_r__TSZ:
	.word	64
	.globl	PROBE__psc_w__ext_D_r__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_r__SGN, @object
	.size	PROBE__psc_w__ext_D_r__SGN, 4
PROBE__psc_w__ext_D_r__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_pid__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_pid__OFF, @object
	.size	PROBE__psc_w__ext_D_pid__OFF, 4
PROBE__psc_w__ext_D_pid__OFF:
	.word	164
	.globl	PROBE__psc_w__ext_D_pid__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_pid__ESZ, @object
	.size	PROBE__psc_w__ext_D_pid__ESZ, 4
PROBE__psc_w__ext_D_pid__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_pid__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_pid__TSZ, @object
	.size	PROBE__psc_w__ext_D_pid__TSZ, 4
PROBE__psc_w__ext_D_pid__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_pid__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_pid__SGN, @object
	.size	PROBE__psc_w__ext_D_pid__SGN, 4
PROBE__psc_w__ext_D_pid__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_p_head__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_p_head__OFF, @object
	.size	PROBE__psc_w__ext_D_p_head__OFF, 4
PROBE__psc_w__ext_D_p_head__OFF:
	.word	168
	.globl	PROBE__psc_w__ext_D_p_head__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_p_head__ESZ, @object
	.size	PROBE__psc_w__ext_D_p_head__ESZ, 4
PROBE__psc_w__ext_D_p_head__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_p_head__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_p_head__TSZ, @object
	.size	PROBE__psc_w__ext_D_p_head__TSZ, 4
PROBE__psc_w__ext_D_p_head__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_p_head__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_p_head__SGN, @object
	.size	PROBE__psc_w__ext_D_p_head__SGN, 4
PROBE__psc_w__ext_D_p_head__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_jp_loop__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_jp_loop__OFF, @object
	.size	PROBE__psc_w__ext_D_jp_loop__OFF, 4
PROBE__psc_w__ext_D_jp_loop__OFF:
	.word	172
	.globl	PROBE__psc_w__ext_D_jp_loop__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_jp_loop__ESZ, @object
	.size	PROBE__psc_w__ext_D_jp_loop__ESZ, 4
PROBE__psc_w__ext_D_jp_loop__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_jp_loop__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_jp_loop__TSZ, @object
	.size	PROBE__psc_w__ext_D_jp_loop__TSZ, 4
PROBE__psc_w__ext_D_jp_loop__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_jp_loop__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_jp_loop__SGN, @object
	.size	PROBE__psc_w__ext_D_jp_loop__SGN, 4
PROBE__psc_w__ext_D_jp_loop__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_t_entry_tick__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_tick__OFF, @object
	.size	PROBE__psc_w__ext_D_t_entry_tick__OFF, 4
PROBE__psc_w__ext_D_t_entry_tick__OFF:
	.word	176
	.globl	PROBE__psc_w__ext_D_t_entry_tick__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_tick__ESZ, @object
	.size	PROBE__psc_w__ext_D_t_entry_tick__ESZ, 4
PROBE__psc_w__ext_D_t_entry_tick__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_t_entry_tick__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_tick__TSZ, @object
	.size	PROBE__psc_w__ext_D_t_entry_tick__TSZ, 4
PROBE__psc_w__ext_D_t_entry_tick__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_t_entry_tick__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_tick__SGN, @object
	.size	PROBE__psc_w__ext_D_t_entry_tick__SGN, 4
PROBE__psc_w__ext_D_t_entry_tick__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_t_entry_c__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_c__OFF, @object
	.size	PROBE__psc_w__ext_D_t_entry_c__OFF, 4
PROBE__psc_w__ext_D_t_entry_c__OFF:
	.word	180
	.globl	PROBE__psc_w__ext_D_t_entry_c__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_c__ESZ, @object
	.size	PROBE__psc_w__ext_D_t_entry_c__ESZ, 4
PROBE__psc_w__ext_D_t_entry_c__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_t_entry_c__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_c__TSZ, @object
	.size	PROBE__psc_w__ext_D_t_entry_c__TSZ, 4
PROBE__psc_w__ext_D_t_entry_c__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_t_entry_c__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_t_entry_c__SGN, @object
	.size	PROBE__psc_w__ext_D_t_entry_c__SGN, 4
PROBE__psc_w__ext_D_t_entry_c__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_t_busy__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_t_busy__OFF, @object
	.size	PROBE__psc_w__ext_D_t_busy__OFF, 4
PROBE__psc_w__ext_D_t_busy__OFF:
	.word	184
	.globl	PROBE__psc_w__ext_D_t_busy__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_t_busy__ESZ, @object
	.size	PROBE__psc_w__ext_D_t_busy__ESZ, 4
PROBE__psc_w__ext_D_t_busy__ESZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_t_busy__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_t_busy__TSZ, @object
	.size	PROBE__psc_w__ext_D_t_busy__TSZ, 4
PROBE__psc_w__ext_D_t_busy__TSZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_t_busy__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_t_busy__SGN, @object
	.size	PROBE__psc_w__ext_D_t_busy__SGN, 4
PROBE__psc_w__ext_D_t_busy__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_jp_stage__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_jp_stage__OFF, @object
	.size	PROBE__psc_w__ext_D_jp_stage__OFF, 4
PROBE__psc_w__ext_D_jp_stage__OFF:
	.word	185
	.globl	PROBE__psc_w__ext_D_jp_stage__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_jp_stage__ESZ, @object
	.size	PROBE__psc_w__ext_D_jp_stage__ESZ, 4
PROBE__psc_w__ext_D_jp_stage__ESZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_jp_stage__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_jp_stage__TSZ, @object
	.size	PROBE__psc_w__ext_D_jp_stage__TSZ, 4
PROBE__psc_w__ext_D_jp_stage__TSZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_jp_stage__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_jp_stage__SGN, @object
	.size	PROBE__psc_w__ext_D_jp_stage__SGN, 4
PROBE__psc_w__ext_D_jp_stage__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_ext_flags__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_ext_flags__OFF, @object
	.size	PROBE__psc_w__ext_D_ext_flags__OFF, 4
PROBE__psc_w__ext_D_ext_flags__OFF:
	.word	186
	.globl	PROBE__psc_w__ext_D_ext_flags__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_ext_flags__ESZ, @object
	.size	PROBE__psc_w__ext_D_ext_flags__ESZ, 4
PROBE__psc_w__ext_D_ext_flags__ESZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_ext_flags__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_ext_flags__TSZ, @object
	.size	PROBE__psc_w__ext_D_ext_flags__TSZ, 4
PROBE__psc_w__ext_D_ext_flags__TSZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_ext_flags__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_ext_flags__SGN, @object
	.size	PROBE__psc_w__ext_D_ext_flags__SGN, 4
PROBE__psc_w__ext_D_ext_flags__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_cur_pcnt__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_cur_pcnt__OFF, @object
	.size	PROBE__psc_w__ext_D_cur_pcnt__OFF, 4
PROBE__psc_w__ext_D_cur_pcnt__OFF:
	.word	187
	.globl	PROBE__psc_w__ext_D_cur_pcnt__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_cur_pcnt__ESZ, @object
	.size	PROBE__psc_w__ext_D_cur_pcnt__ESZ, 4
PROBE__psc_w__ext_D_cur_pcnt__ESZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_cur_pcnt__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_cur_pcnt__TSZ, @object
	.size	PROBE__psc_w__ext_D_cur_pcnt__TSZ, 4
PROBE__psc_w__ext_D_cur_pcnt__TSZ:
	.word	1
	.globl	PROBE__psc_w__ext_D_cur_pcnt__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_cur_pcnt__SGN, @object
	.size	PROBE__psc_w__ext_D_cur_pcnt__SGN, 4
PROBE__psc_w__ext_D_cur_pcnt__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_c_pre__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_c_pre__OFF, @object
	.size	PROBE__psc_w__ext_D_c_pre__OFF, 4
PROBE__psc_w__ext_D_c_pre__OFF:
	.word	188
	.globl	PROBE__psc_w__ext_D_c_pre__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_c_pre__ESZ, @object
	.size	PROBE__psc_w__ext_D_c_pre__ESZ, 4
PROBE__psc_w__ext_D_c_pre__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_c_pre__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_c_pre__TSZ, @object
	.size	PROBE__psc_w__ext_D_c_pre__TSZ, 4
PROBE__psc_w__ext_D_c_pre__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_c_pre__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_c_pre__SGN, @object
	.size	PROBE__psc_w__ext_D_c_pre__SGN, 4
PROBE__psc_w__ext_D_c_pre__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_tick__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_tick__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_tick__OFF, 4
PROBE__psc_w__ext_D_lc_tick__OFF:
	.word	192
	.globl	PROBE__psc_w__ext_D_lc_tick__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_tick__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_tick__ESZ, 4
PROBE__psc_w__ext_D_lc_tick__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_tick__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_tick__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_tick__TSZ, 4
PROBE__psc_w__ext_D_lc_tick__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_tick__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_tick__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_tick__SGN, 4
PROBE__psc_w__ext_D_lc_tick__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_c_pre__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_c_pre__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_c_pre__OFF, 4
PROBE__psc_w__ext_D_lc_c_pre__OFF:
	.word	196
	.globl	PROBE__psc_w__ext_D_lc_c_pre__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_c_pre__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_c_pre__ESZ, 4
PROBE__psc_w__ext_D_lc_c_pre__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_c_pre__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_c_pre__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_c_pre__TSZ, 4
PROBE__psc_w__ext_D_lc_c_pre__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_c_pre__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_c_pre__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_c_pre__SGN, 4
PROBE__psc_w__ext_D_lc_c_pre__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_cmd_id__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cmd_id__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_cmd_id__OFF, 4
PROBE__psc_w__ext_D_lc_cmd_id__OFF:
	.word	200
	.globl	PROBE__psc_w__ext_D_lc_cmd_id__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cmd_id__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_cmd_id__ESZ, 4
PROBE__psc_w__ext_D_lc_cmd_id__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_cmd_id__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cmd_id__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_cmd_id__TSZ, 4
PROBE__psc_w__ext_D_lc_cmd_id__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_cmd_id__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cmd_id__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_cmd_id__SGN, 4
PROBE__psc_w__ext_D_lc_cmd_id__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_epc__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_epc__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_epc__OFF, 4
PROBE__psc_w__ext_D_lc_epc__OFF:
	.word	204
	.globl	PROBE__psc_w__ext_D_lc_epc__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_epc__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_epc__ESZ, 4
PROBE__psc_w__ext_D_lc_epc__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_epc__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_epc__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_epc__TSZ, 4
PROBE__psc_w__ext_D_lc_epc__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_epc__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_epc__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_epc__SGN, 4
PROBE__psc_w__ext_D_lc_epc__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_cause__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cause__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_cause__OFF, 4
PROBE__psc_w__ext_D_lc_cause__OFF:
	.word	208
	.globl	PROBE__psc_w__ext_D_lc_cause__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cause__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_cause__ESZ, 4
PROBE__psc_w__ext_D_lc_cause__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_cause__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cause__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_cause__TSZ, 4
PROBE__psc_w__ext_D_lc_cause__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_cause__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_cause__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_cause__SGN, 4
PROBE__psc_w__ext_D_lc_cause__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_ra__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_ra__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_ra__OFF, 4
PROBE__psc_w__ext_D_lc_ra__OFF:
	.word	212
	.globl	PROBE__psc_w__ext_D_lc_ra__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_ra__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_ra__ESZ, 4
PROBE__psc_w__ext_D_lc_ra__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_ra__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_ra__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_ra__TSZ, 4
PROBE__psc_w__ext_D_lc_ra__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_ra__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_ra__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_ra__SGN, 4
PROBE__psc_w__ext_D_lc_ra__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_sp__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_sp__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_sp__OFF, 4
PROBE__psc_w__ext_D_lc_sp__OFF:
	.word	216
	.globl	PROBE__psc_w__ext_D_lc_sp__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_sp__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_sp__ESZ, 4
PROBE__psc_w__ext_D_lc_sp__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_sp__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_sp__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_sp__TSZ, 4
PROBE__psc_w__ext_D_lc_sp__TSZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_sp__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_sp__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_sp__SGN, 4
PROBE__psc_w__ext_D_lc_sp__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_r__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_r__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_r__OFF, 4
PROBE__psc_w__ext_D_lc_r__OFF:
	.word	220
	.globl	PROBE__psc_w__ext_D_lc_r__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_r__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_r__ESZ, 4
PROBE__psc_w__ext_D_lc_r__ESZ:
	.word	4
	.globl	PROBE__psc_w__ext_D_lc_r__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_r__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_r__TSZ, 4
PROBE__psc_w__ext_D_lc_r__TSZ:
	.word	64
	.globl	PROBE__psc_w__ext_D_lc_r__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_r__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_r__SGN, 4
PROBE__psc_w__ext_D_lc_r__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_lc_n__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_lc_n__OFF, @object
	.size	PROBE__psc_w__ext_D_lc_n__OFF, 4
PROBE__psc_w__ext_D_lc_n__OFF:
	.word	284
	.globl	PROBE__psc_w__ext_D_lc_n__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_n__ESZ, @object
	.size	PROBE__psc_w__ext_D_lc_n__ESZ, 4
PROBE__psc_w__ext_D_lc_n__ESZ:
	.word	2
	.globl	PROBE__psc_w__ext_D_lc_n__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_lc_n__TSZ, @object
	.size	PROBE__psc_w__ext_D_lc_n__TSZ, 4
PROBE__psc_w__ext_D_lc_n__TSZ:
	.word	2
	.globl	PROBE__psc_w__ext_D_lc_n__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_lc_n__SGN, @object
	.size	PROBE__psc_w__ext_D_lc_n__SGN, 4
PROBE__psc_w__ext_D_lc_n__SGN:
	.space	4
	.globl	PROBE__psc_w__ext_D_rsv__OFF
	.align	2
	.type	PROBE__psc_w__ext_D_rsv__OFF, @object
	.size	PROBE__psc_w__ext_D_rsv__OFF, 4
PROBE__psc_w__ext_D_rsv__OFF:
	.word	286
	.globl	PROBE__psc_w__ext_D_rsv__ESZ
	.align	2
	.type	PROBE__psc_w__ext_D_rsv__ESZ, @object
	.size	PROBE__psc_w__ext_D_rsv__ESZ, 4
PROBE__psc_w__ext_D_rsv__ESZ:
	.word	2
	.globl	PROBE__psc_w__ext_D_rsv__TSZ
	.align	2
	.type	PROBE__psc_w__ext_D_rsv__TSZ, @object
	.size	PROBE__psc_w__ext_D_rsv__TSZ, 4
PROBE__psc_w__ext_D_rsv__TSZ:
	.word	2
	.globl	PROBE__psc_w__ext_D_rsv__SGN
	.align	2
	.type	PROBE__psc_w__ext_D_rsv__SGN, @object
	.size	PROBE__psc_w__ext_D_rsv__SGN, 4
PROBE__psc_w__ext_D_rsv__SGN:
	.space	4
	.globl	PROBE__psc_poll__SIZE
	.align	2
	.type	PROBE__psc_poll__SIZE, @object
	.size	PROBE__psc_poll__SIZE, 4
PROBE__psc_poll__SIZE:
	.word	40
	.globl	PROBE__psc_poll__seq__OFF
	.align	2
	.type	PROBE__psc_poll__seq__OFF, @object
	.size	PROBE__psc_poll__seq__OFF, 4
PROBE__psc_poll__seq__OFF:
	.space	4
	.globl	PROBE__psc_poll__seq__ESZ
	.align	2
	.type	PROBE__psc_poll__seq__ESZ, @object
	.size	PROBE__psc_poll__seq__ESZ, 4
PROBE__psc_poll__seq__ESZ:
	.word	4
	.globl	PROBE__psc_poll__seq__TSZ
	.align	2
	.type	PROBE__psc_poll__seq__TSZ, @object
	.size	PROBE__psc_poll__seq__TSZ, 4
PROBE__psc_poll__seq__TSZ:
	.word	4
	.globl	PROBE__psc_poll__seq__SGN
	.align	2
	.type	PROBE__psc_poll__seq__SGN, @object
	.size	PROBE__psc_poll__seq__SGN, 4
PROBE__psc_poll__seq__SGN:
	.space	4
	.globl	PROBE__psc_poll__tick_start__OFF
	.align	2
	.type	PROBE__psc_poll__tick_start__OFF, @object
	.size	PROBE__psc_poll__tick_start__OFF, 4
PROBE__psc_poll__tick_start__OFF:
	.word	4
	.globl	PROBE__psc_poll__tick_start__ESZ
	.align	2
	.type	PROBE__psc_poll__tick_start__ESZ, @object
	.size	PROBE__psc_poll__tick_start__ESZ, 4
PROBE__psc_poll__tick_start__ESZ:
	.word	4
	.globl	PROBE__psc_poll__tick_start__TSZ
	.align	2
	.type	PROBE__psc_poll__tick_start__TSZ, @object
	.size	PROBE__psc_poll__tick_start__TSZ, 4
PROBE__psc_poll__tick_start__TSZ:
	.word	4
	.globl	PROBE__psc_poll__tick_start__SGN
	.align	2
	.type	PROBE__psc_poll__tick_start__SGN, @object
	.size	PROBE__psc_poll__tick_start__SGN, 4
PROBE__psc_poll__tick_start__SGN:
	.space	4
	.globl	PROBE__psc_poll__c_start__OFF
	.align	2
	.type	PROBE__psc_poll__c_start__OFF, @object
	.size	PROBE__psc_poll__c_start__OFF, 4
PROBE__psc_poll__c_start__OFF:
	.word	8
	.globl	PROBE__psc_poll__c_start__ESZ
	.align	2
	.type	PROBE__psc_poll__c_start__ESZ, @object
	.size	PROBE__psc_poll__c_start__ESZ, 4
PROBE__psc_poll__c_start__ESZ:
	.word	4
	.globl	PROBE__psc_poll__c_start__TSZ
	.align	2
	.type	PROBE__psc_poll__c_start__TSZ, @object
	.size	PROBE__psc_poll__c_start__TSZ, 4
PROBE__psc_poll__c_start__TSZ:
	.word	4
	.globl	PROBE__psc_poll__c_start__SGN
	.align	2
	.type	PROBE__psc_poll__c_start__SGN, @object
	.size	PROBE__psc_poll__c_start__SGN, 4
PROBE__psc_poll__c_start__SGN:
	.space	4
	.globl	PROBE__psc_poll__c_end__OFF
	.align	2
	.type	PROBE__psc_poll__c_end__OFF, @object
	.size	PROBE__psc_poll__c_end__OFF, 4
PROBE__psc_poll__c_end__OFF:
	.word	12
	.globl	PROBE__psc_poll__c_end__ESZ
	.align	2
	.type	PROBE__psc_poll__c_end__ESZ, @object
	.size	PROBE__psc_poll__c_end__ESZ, 4
PROBE__psc_poll__c_end__ESZ:
	.word	4
	.globl	PROBE__psc_poll__c_end__TSZ
	.align	2
	.type	PROBE__psc_poll__c_end__TSZ, @object
	.size	PROBE__psc_poll__c_end__TSZ, 4
PROBE__psc_poll__c_end__TSZ:
	.word	4
	.globl	PROBE__psc_poll__c_end__SGN
	.align	2
	.type	PROBE__psc_poll__c_end__SGN, @object
	.size	PROBE__psc_poll__c_end__SGN, 4
PROBE__psc_poll__c_end__SGN:
	.space	4
	.globl	PROBE__psc_poll__sc_seq_lo__OFF
	.align	2
	.type	PROBE__psc_poll__sc_seq_lo__OFF, @object
	.size	PROBE__psc_poll__sc_seq_lo__OFF, 4
PROBE__psc_poll__sc_seq_lo__OFF:
	.word	16
	.globl	PROBE__psc_poll__sc_seq_lo__ESZ
	.align	2
	.type	PROBE__psc_poll__sc_seq_lo__ESZ, @object
	.size	PROBE__psc_poll__sc_seq_lo__ESZ, 4
PROBE__psc_poll__sc_seq_lo__ESZ:
	.word	2
	.globl	PROBE__psc_poll__sc_seq_lo__TSZ
	.align	2
	.type	PROBE__psc_poll__sc_seq_lo__TSZ, @object
	.size	PROBE__psc_poll__sc_seq_lo__TSZ, 4
PROBE__psc_poll__sc_seq_lo__TSZ:
	.word	2
	.globl	PROBE__psc_poll__sc_seq_lo__SGN
	.align	2
	.type	PROBE__psc_poll__sc_seq_lo__SGN, @object
	.size	PROBE__psc_poll__sc_seq_lo__SGN, 4
PROBE__psc_poll__sc_seq_lo__SGN:
	.space	4
	.globl	PROBE__psc_poll__body_ticks__OFF
	.align	2
	.type	PROBE__psc_poll__body_ticks__OFF, @object
	.size	PROBE__psc_poll__body_ticks__OFF, 4
PROBE__psc_poll__body_ticks__OFF:
	.word	18
	.globl	PROBE__psc_poll__body_ticks__ESZ
	.align	2
	.type	PROBE__psc_poll__body_ticks__ESZ, @object
	.size	PROBE__psc_poll__body_ticks__ESZ, 4
PROBE__psc_poll__body_ticks__ESZ:
	.word	1
	.globl	PROBE__psc_poll__body_ticks__TSZ
	.align	2
	.type	PROBE__psc_poll__body_ticks__TSZ, @object
	.size	PROBE__psc_poll__body_ticks__TSZ, 4
PROBE__psc_poll__body_ticks__TSZ:
	.word	1
	.globl	PROBE__psc_poll__body_ticks__SGN
	.align	2
	.type	PROBE__psc_poll__body_ticks__SGN, @object
	.size	PROBE__psc_poll__body_ticks__SGN, 4
PROBE__psc_poll__body_ticks__SGN:
	.space	4
	.globl	PROBE__psc_poll__ri_branch__OFF
	.align	2
	.type	PROBE__psc_poll__ri_branch__OFF, @object
	.size	PROBE__psc_poll__ri_branch__OFF, 4
PROBE__psc_poll__ri_branch__OFF:
	.word	19
	.globl	PROBE__psc_poll__ri_branch__ESZ
	.align	2
	.type	PROBE__psc_poll__ri_branch__ESZ, @object
	.size	PROBE__psc_poll__ri_branch__ESZ, 4
PROBE__psc_poll__ri_branch__ESZ:
	.word	1
	.globl	PROBE__psc_poll__ri_branch__TSZ
	.align	2
	.type	PROBE__psc_poll__ri_branch__TSZ, @object
	.size	PROBE__psc_poll__ri_branch__TSZ, 4
PROBE__psc_poll__ri_branch__TSZ:
	.word	1
	.globl	PROBE__psc_poll__ri_branch__SGN
	.align	2
	.type	PROBE__psc_poll__ri_branch__SGN, @object
	.size	PROBE__psc_poll__ri_branch__SGN, 4
PROBE__psc_poll__ri_branch__SGN:
	.space	4
	.globl	PROBE__psc_poll__pi_flags__OFF
	.align	2
	.type	PROBE__psc_poll__pi_flags__OFF, @object
	.size	PROBE__psc_poll__pi_flags__OFF, 4
PROBE__psc_poll__pi_flags__OFF:
	.word	20
	.globl	PROBE__psc_poll__pi_flags__ESZ
	.align	2
	.type	PROBE__psc_poll__pi_flags__ESZ, @object
	.size	PROBE__psc_poll__pi_flags__ESZ, 4
PROBE__psc_poll__pi_flags__ESZ:
	.word	1
	.globl	PROBE__psc_poll__pi_flags__TSZ
	.align	2
	.type	PROBE__psc_poll__pi_flags__TSZ, @object
	.size	PROBE__psc_poll__pi_flags__TSZ, 4
PROBE__psc_poll__pi_flags__TSZ:
	.word	1
	.globl	PROBE__psc_poll__pi_flags__SGN
	.align	2
	.type	PROBE__psc_poll__pi_flags__SGN, @object
	.size	PROBE__psc_poll__pi_flags__SGN, 4
PROBE__psc_poll__pi_flags__SGN:
	.space	4
	.globl	PROBE__psc_poll__nqueues__OFF
	.align	2
	.type	PROBE__psc_poll__nqueues__OFF, @object
	.size	PROBE__psc_poll__nqueues__OFF, 4
PROBE__psc_poll__nqueues__OFF:
	.word	21
	.globl	PROBE__psc_poll__nqueues__ESZ
	.align	2
	.type	PROBE__psc_poll__nqueues__ESZ, @object
	.size	PROBE__psc_poll__nqueues__ESZ, 4
PROBE__psc_poll__nqueues__ESZ:
	.word	1
	.globl	PROBE__psc_poll__nqueues__TSZ
	.align	2
	.type	PROBE__psc_poll__nqueues__TSZ, @object
	.size	PROBE__psc_poll__nqueues__TSZ, 4
PROBE__psc_poll__nqueues__TSZ:
	.word	1
	.globl	PROBE__psc_poll__nqueues__SGN
	.align	2
	.type	PROBE__psc_poll__nqueues__SGN, @object
	.size	PROBE__psc_poll__nqueues__SGN, 4
PROBE__psc_poll__nqueues__SGN:
	.space	4
	.globl	PROBE__psc_poll__push_ok__OFF
	.align	2
	.type	PROBE__psc_poll__push_ok__OFF, @object
	.size	PROBE__psc_poll__push_ok__OFF, 4
PROBE__psc_poll__push_ok__OFF:
	.word	22
	.globl	PROBE__psc_poll__push_ok__ESZ
	.align	2
	.type	PROBE__psc_poll__push_ok__ESZ, @object
	.size	PROBE__psc_poll__push_ok__ESZ, 4
PROBE__psc_poll__push_ok__ESZ:
	.word	1
	.globl	PROBE__psc_poll__push_ok__TSZ
	.align	2
	.type	PROBE__psc_poll__push_ok__TSZ, @object
	.size	PROBE__psc_poll__push_ok__TSZ, 4
PROBE__psc_poll__push_ok__TSZ:
	.word	1
	.globl	PROBE__psc_poll__push_ok__SGN
	.align	2
	.type	PROBE__psc_poll__push_ok__SGN, @object
	.size	PROBE__psc_poll__push_ok__SGN, 4
PROBE__psc_poll__push_ok__SGN:
	.space	4
	.globl	PROBE__psc_poll__push_fail__OFF
	.align	2
	.type	PROBE__psc_poll__push_fail__OFF, @object
	.size	PROBE__psc_poll__push_fail__OFF, 4
PROBE__psc_poll__push_fail__OFF:
	.word	23
	.globl	PROBE__psc_poll__push_fail__ESZ
	.align	2
	.type	PROBE__psc_poll__push_fail__ESZ, @object
	.size	PROBE__psc_poll__push_fail__ESZ, 4
PROBE__psc_poll__push_fail__ESZ:
	.word	1
	.globl	PROBE__psc_poll__push_fail__TSZ
	.align	2
	.type	PROBE__psc_poll__push_fail__TSZ, @object
	.size	PROBE__psc_poll__push_fail__TSZ, 4
PROBE__psc_poll__push_fail__TSZ:
	.word	1
	.globl	PROBE__psc_poll__push_fail__SGN
	.align	2
	.type	PROBE__psc_poll__push_fail__SGN, @object
	.size	PROBE__psc_poll__push_fail__SGN, 4
PROBE__psc_poll__push_fail__SGN:
	.space	4
	.globl	PROBE__psc_poll__mouse_flags__OFF
	.align	2
	.type	PROBE__psc_poll__mouse_flags__OFF, @object
	.size	PROBE__psc_poll__mouse_flags__OFF, 4
PROBE__psc_poll__mouse_flags__OFF:
	.word	24
	.globl	PROBE__psc_poll__mouse_flags__ESZ
	.align	2
	.type	PROBE__psc_poll__mouse_flags__ESZ, @object
	.size	PROBE__psc_poll__mouse_flags__ESZ, 4
PROBE__psc_poll__mouse_flags__ESZ:
	.word	1
	.globl	PROBE__psc_poll__mouse_flags__TSZ
	.align	2
	.type	PROBE__psc_poll__mouse_flags__TSZ, @object
	.size	PROBE__psc_poll__mouse_flags__TSZ, 4
PROBE__psc_poll__mouse_flags__TSZ:
	.word	1
	.globl	PROBE__psc_poll__mouse_flags__SGN
	.align	2
	.type	PROBE__psc_poll__mouse_flags__SGN, @object
	.size	PROBE__psc_poll__mouse_flags__SGN, 4
PROBE__psc_poll__mouse_flags__SGN:
	.space	4
	.globl	PROBE__psc_poll__dx__OFF
	.align	2
	.type	PROBE__psc_poll__dx__OFF, @object
	.size	PROBE__psc_poll__dx__OFF, 4
PROBE__psc_poll__dx__OFF:
	.word	25
	.globl	PROBE__psc_poll__dx__ESZ
	.align	2
	.type	PROBE__psc_poll__dx__ESZ, @object
	.size	PROBE__psc_poll__dx__ESZ, 4
PROBE__psc_poll__dx__ESZ:
	.word	1
	.globl	PROBE__psc_poll__dx__TSZ
	.align	2
	.type	PROBE__psc_poll__dx__TSZ, @object
	.size	PROBE__psc_poll__dx__TSZ, 4
PROBE__psc_poll__dx__TSZ:
	.word	1
	.globl	PROBE__psc_poll__dx__SGN
	.align	2
	.type	PROBE__psc_poll__dx__SGN, @object
	.size	PROBE__psc_poll__dx__SGN, 4
PROBE__psc_poll__dx__SGN:
	.word	1
	.globl	PROBE__psc_poll__dy__OFF
	.align	2
	.type	PROBE__psc_poll__dy__OFF, @object
	.size	PROBE__psc_poll__dy__OFF, 4
PROBE__psc_poll__dy__OFF:
	.word	26
	.globl	PROBE__psc_poll__dy__ESZ
	.align	2
	.type	PROBE__psc_poll__dy__ESZ, @object
	.size	PROBE__psc_poll__dy__ESZ, 4
PROBE__psc_poll__dy__ESZ:
	.word	1
	.globl	PROBE__psc_poll__dy__TSZ
	.align	2
	.type	PROBE__psc_poll__dy__TSZ, @object
	.size	PROBE__psc_poll__dy__TSZ, 4
PROBE__psc_poll__dy__TSZ:
	.word	1
	.globl	PROBE__psc_poll__dy__SGN
	.align	2
	.type	PROBE__psc_poll__dy__SGN, @object
	.size	PROBE__psc_poll__dy__SGN, 4
PROBE__psc_poll__dy__SGN:
	.word	1
	.globl	PROBE__psc_poll__sig__OFF
	.align	2
	.type	PROBE__psc_poll__sig__OFF, @object
	.size	PROBE__psc_poll__sig__OFF, 4
PROBE__psc_poll__sig__OFF:
	.word	27
	.globl	PROBE__psc_poll__sig__ESZ
	.align	2
	.type	PROBE__psc_poll__sig__ESZ, @object
	.size	PROBE__psc_poll__sig__ESZ, 4
PROBE__psc_poll__sig__ESZ:
	.word	1
	.globl	PROBE__psc_poll__sig__TSZ
	.align	2
	.type	PROBE__psc_poll__sig__TSZ, @object
	.size	PROBE__psc_poll__sig__TSZ, 4
PROBE__psc_poll__sig__TSZ:
	.word	1
	.globl	PROBE__psc_poll__sig__SGN
	.align	2
	.type	PROBE__psc_poll__sig__SGN, @object
	.size	PROBE__psc_poll__sig__SGN, 4
PROBE__psc_poll__sig__SGN:
	.space	4
	.globl	PROBE__psc_poll__period__OFF
	.align	2
	.type	PROBE__psc_poll__period__OFF, @object
	.size	PROBE__psc_poll__period__OFF, 4
PROBE__psc_poll__period__OFF:
	.word	28
	.globl	PROBE__psc_poll__period__ESZ
	.align	2
	.type	PROBE__psc_poll__period__ESZ, @object
	.size	PROBE__psc_poll__period__ESZ, 4
PROBE__psc_poll__period__ESZ:
	.word	1
	.globl	PROBE__psc_poll__period__TSZ
	.align	2
	.type	PROBE__psc_poll__period__TSZ, @object
	.size	PROBE__psc_poll__period__TSZ, 4
PROBE__psc_poll__period__TSZ:
	.word	1
	.globl	PROBE__psc_poll__period__SGN
	.align	2
	.type	PROBE__psc_poll__period__SGN, @object
	.size	PROBE__psc_poll__period__SGN, 4
PROBE__psc_poll__period__SGN:
	.space	4
	.globl	PROBE__psc_poll__preempt_delta__OFF
	.align	2
	.type	PROBE__psc_poll__preempt_delta__OFF, @object
	.size	PROBE__psc_poll__preempt_delta__OFF, 4
PROBE__psc_poll__preempt_delta__OFF:
	.word	29
	.globl	PROBE__psc_poll__preempt_delta__ESZ
	.align	2
	.type	PROBE__psc_poll__preempt_delta__ESZ, @object
	.size	PROBE__psc_poll__preempt_delta__ESZ, 4
PROBE__psc_poll__preempt_delta__ESZ:
	.word	1
	.globl	PROBE__psc_poll__preempt_delta__TSZ
	.align	2
	.type	PROBE__psc_poll__preempt_delta__TSZ, @object
	.size	PROBE__psc_poll__preempt_delta__TSZ, 4
PROBE__psc_poll__preempt_delta__TSZ:
	.word	1
	.globl	PROBE__psc_poll__preempt_delta__SGN
	.align	2
	.type	PROBE__psc_poll__preempt_delta__SGN, @object
	.size	PROBE__psc_poll__preempt_delta__SGN, 4
PROBE__psc_poll__preempt_delta__SGN:
	.space	4
	.globl	PROBE__psc_poll__stage_max__OFF
	.align	2
	.type	PROBE__psc_poll__stage_max__OFF, @object
	.size	PROBE__psc_poll__stage_max__OFF, 4
PROBE__psc_poll__stage_max__OFF:
	.word	30
	.globl	PROBE__psc_poll__stage_max__ESZ
	.align	2
	.type	PROBE__psc_poll__stage_max__ESZ, @object
	.size	PROBE__psc_poll__stage_max__ESZ, 4
PROBE__psc_poll__stage_max__ESZ:
	.word	1
	.globl	PROBE__psc_poll__stage_max__TSZ
	.align	2
	.type	PROBE__psc_poll__stage_max__TSZ, @object
	.size	PROBE__psc_poll__stage_max__TSZ, 4
PROBE__psc_poll__stage_max__TSZ:
	.word	1
	.globl	PROBE__psc_poll__stage_max__SGN
	.align	2
	.type	PROBE__psc_poll__stage_max__SGN, @object
	.size	PROBE__psc_poll__stage_max__SGN, 4
PROBE__psc_poll__stage_max__SGN:
	.space	4
	.globl	PROBE__psc_poll__nsc__OFF
	.align	2
	.type	PROBE__psc_poll__nsc__OFF, @object
	.size	PROBE__psc_poll__nsc__OFF, 4
PROBE__psc_poll__nsc__OFF:
	.word	31
	.globl	PROBE__psc_poll__nsc__ESZ
	.align	2
	.type	PROBE__psc_poll__nsc__ESZ, @object
	.size	PROBE__psc_poll__nsc__ESZ, 4
PROBE__psc_poll__nsc__ESZ:
	.word	1
	.globl	PROBE__psc_poll__nsc__TSZ
	.align	2
	.type	PROBE__psc_poll__nsc__TSZ, @object
	.size	PROBE__psc_poll__nsc__TSZ, 4
PROBE__psc_poll__nsc__TSZ:
	.word	1
	.globl	PROBE__psc_poll__nsc__SGN
	.align	2
	.type	PROBE__psc_poll__nsc__SGN, @object
	.size	PROBE__psc_poll__nsc__SGN, 4
PROBE__psc_poll__nsc__SGN:
	.space	4
	.globl	PROBE__psc_poll__wk_delay__OFF
	.align	2
	.type	PROBE__psc_poll__wk_delay__OFF, @object
	.size	PROBE__psc_poll__wk_delay__OFF, 4
PROBE__psc_poll__wk_delay__OFF:
	.word	32
	.globl	PROBE__psc_poll__wk_delay__ESZ
	.align	2
	.type	PROBE__psc_poll__wk_delay__ESZ, @object
	.size	PROBE__psc_poll__wk_delay__ESZ, 4
PROBE__psc_poll__wk_delay__ESZ:
	.word	2
	.globl	PROBE__psc_poll__wk_delay__TSZ
	.align	2
	.type	PROBE__psc_poll__wk_delay__TSZ, @object
	.size	PROBE__psc_poll__wk_delay__TSZ, 4
PROBE__psc_poll__wk_delay__TSZ:
	.word	2
	.globl	PROBE__psc_poll__wk_delay__SGN
	.align	2
	.type	PROBE__psc_poll__wk_delay__SGN, @object
	.size	PROBE__psc_poll__wk_delay__SGN, 4
PROBE__psc_poll__wk_delay__SGN:
	.space	4
	.globl	PROBE__psc_poll__wk_wrk__OFF
	.align	2
	.type	PROBE__psc_poll__wk_wrk__OFF, @object
	.size	PROBE__psc_poll__wk_wrk__OFF, 4
PROBE__psc_poll__wk_wrk__OFF:
	.word	34
	.globl	PROBE__psc_poll__wk_wrk__ESZ
	.align	2
	.type	PROBE__psc_poll__wk_wrk__ESZ, @object
	.size	PROBE__psc_poll__wk_wrk__ESZ, 4
PROBE__psc_poll__wk_wrk__ESZ:
	.word	2
	.globl	PROBE__psc_poll__wk_wrk__TSZ
	.align	2
	.type	PROBE__psc_poll__wk_wrk__TSZ, @object
	.size	PROBE__psc_poll__wk_wrk__TSZ, 4
PROBE__psc_poll__wk_wrk__TSZ:
	.word	2
	.globl	PROBE__psc_poll__wk_wrk__SGN
	.align	2
	.type	PROBE__psc_poll__wk_wrk__SGN, @object
	.size	PROBE__psc_poll__wk_wrk__SGN, 4
PROBE__psc_poll__wk_wrk__SGN:
	.space	4
	.globl	PROBE__psc_poll__wk_cls0__OFF
	.align	2
	.type	PROBE__psc_poll__wk_cls0__OFF, @object
	.size	PROBE__psc_poll__wk_cls0__OFF, 4
PROBE__psc_poll__wk_cls0__OFF:
	.word	36
	.globl	PROBE__psc_poll__wk_cls0__ESZ
	.align	2
	.type	PROBE__psc_poll__wk_cls0__ESZ, @object
	.size	PROBE__psc_poll__wk_cls0__ESZ, 4
PROBE__psc_poll__wk_cls0__ESZ:
	.word	1
	.globl	PROBE__psc_poll__wk_cls0__TSZ
	.align	2
	.type	PROBE__psc_poll__wk_cls0__TSZ, @object
	.size	PROBE__psc_poll__wk_cls0__TSZ, 4
PROBE__psc_poll__wk_cls0__TSZ:
	.word	1
	.globl	PROBE__psc_poll__wk_cls0__SGN
	.align	2
	.type	PROBE__psc_poll__wk_cls0__SGN, @object
	.size	PROBE__psc_poll__wk_cls0__SGN, 4
PROBE__psc_poll__wk_cls0__SGN:
	.space	4
	.globl	PROBE__psc_poll__wk_cls1__OFF
	.align	2
	.type	PROBE__psc_poll__wk_cls1__OFF, @object
	.size	PROBE__psc_poll__wk_cls1__OFF, 4
PROBE__psc_poll__wk_cls1__OFF:
	.word	37
	.globl	PROBE__psc_poll__wk_cls1__ESZ
	.align	2
	.type	PROBE__psc_poll__wk_cls1__ESZ, @object
	.size	PROBE__psc_poll__wk_cls1__ESZ, 4
PROBE__psc_poll__wk_cls1__ESZ:
	.word	1
	.globl	PROBE__psc_poll__wk_cls1__TSZ
	.align	2
	.type	PROBE__psc_poll__wk_cls1__TSZ, @object
	.size	PROBE__psc_poll__wk_cls1__TSZ, 4
PROBE__psc_poll__wk_cls1__TSZ:
	.word	1
	.globl	PROBE__psc_poll__wk_cls1__SGN
	.align	2
	.type	PROBE__psc_poll__wk_cls1__SGN, @object
	.size	PROBE__psc_poll__wk_cls1__SGN, 4
PROBE__psc_poll__wk_cls1__SGN:
	.space	4
	.globl	PROBE__psc_poll__wk_nsw__OFF
	.align	2
	.type	PROBE__psc_poll__wk_nsw__OFF, @object
	.size	PROBE__psc_poll__wk_nsw__OFF, 4
PROBE__psc_poll__wk_nsw__OFF:
	.word	38
	.globl	PROBE__psc_poll__wk_nsw__ESZ
	.align	2
	.type	PROBE__psc_poll__wk_nsw__ESZ, @object
	.size	PROBE__psc_poll__wk_nsw__ESZ, 4
PROBE__psc_poll__wk_nsw__ESZ:
	.word	1
	.globl	PROBE__psc_poll__wk_nsw__TSZ
	.align	2
	.type	PROBE__psc_poll__wk_nsw__TSZ, @object
	.size	PROBE__psc_poll__wk_nsw__TSZ, 4
PROBE__psc_poll__wk_nsw__TSZ:
	.word	1
	.globl	PROBE__psc_poll__wk_nsw__SGN
	.align	2
	.type	PROBE__psc_poll__wk_nsw__SGN, @object
	.size	PROBE__psc_poll__wk_nsw__SGN, 4
PROBE__psc_poll__wk_nsw__SGN:
	.space	4
	.globl	PROBE__psc_poll__rsv__OFF
	.align	2
	.type	PROBE__psc_poll__rsv__OFF, @object
	.size	PROBE__psc_poll__rsv__OFF, 4
PROBE__psc_poll__rsv__OFF:
	.word	39
	.globl	PROBE__psc_poll__rsv__ESZ
	.align	2
	.type	PROBE__psc_poll__rsv__ESZ, @object
	.size	PROBE__psc_poll__rsv__ESZ, 4
PROBE__psc_poll__rsv__ESZ:
	.word	1
	.globl	PROBE__psc_poll__rsv__TSZ
	.align	2
	.type	PROBE__psc_poll__rsv__TSZ, @object
	.size	PROBE__psc_poll__rsv__TSZ, 4
PROBE__psc_poll__rsv__TSZ:
	.word	1
	.globl	PROBE__psc_poll__rsv__SGN
	.align	2
	.type	PROBE__psc_poll__rsv__SGN, @object
	.size	PROBE__psc_poll__rsv__SGN, 4
PROBE__psc_poll__rsv__SGN:
	.space	4
	.globl	PROBE__psc_s__SIZE
	.align	2
	.type	PROBE__psc_s__SIZE, @object
	.size	PROBE__psc_s__SIZE, 4
PROBE__psc_s__SIZE:
	.word	40
	.globl	PROBE__psc_s__seq__OFF
	.align	2
	.type	PROBE__psc_s__seq__OFF, @object
	.size	PROBE__psc_s__seq__OFF, 4
PROBE__psc_s__seq__OFF:
	.space	4
	.globl	PROBE__psc_s__seq__ESZ
	.align	2
	.type	PROBE__psc_s__seq__ESZ, @object
	.size	PROBE__psc_s__seq__ESZ, 4
PROBE__psc_s__seq__ESZ:
	.word	4
	.globl	PROBE__psc_s__seq__TSZ
	.align	2
	.type	PROBE__psc_s__seq__TSZ, @object
	.size	PROBE__psc_s__seq__TSZ, 4
PROBE__psc_s__seq__TSZ:
	.word	4
	.globl	PROBE__psc_s__seq__SGN
	.align	2
	.type	PROBE__psc_s__seq__SGN, @object
	.size	PROBE__psc_s__seq__SGN, 4
PROBE__psc_s__seq__SGN:
	.space	4
	.globl	PROBE__psc_s__tick_on__OFF
	.align	2
	.type	PROBE__psc_s__tick_on__OFF, @object
	.size	PROBE__psc_s__tick_on__OFF, 4
PROBE__psc_s__tick_on__OFF:
	.word	4
	.globl	PROBE__psc_s__tick_on__ESZ
	.align	2
	.type	PROBE__psc_s__tick_on__ESZ, @object
	.size	PROBE__psc_s__tick_on__ESZ, 4
PROBE__psc_s__tick_on__ESZ:
	.word	4
	.globl	PROBE__psc_s__tick_on__TSZ
	.align	2
	.type	PROBE__psc_s__tick_on__TSZ, @object
	.size	PROBE__psc_s__tick_on__TSZ, 4
PROBE__psc_s__tick_on__TSZ:
	.word	4
	.globl	PROBE__psc_s__tick_on__SGN
	.align	2
	.type	PROBE__psc_s__tick_on__SGN, @object
	.size	PROBE__psc_s__tick_on__SGN, 4
PROBE__psc_s__tick_on__SGN:
	.space	4
	.globl	PROBE__psc_s__c_on__OFF
	.align	2
	.type	PROBE__psc_s__c_on__OFF, @object
	.size	PROBE__psc_s__c_on__OFF, 4
PROBE__psc_s__c_on__OFF:
	.word	8
	.globl	PROBE__psc_s__c_on__ESZ
	.align	2
	.type	PROBE__psc_s__c_on__ESZ, @object
	.size	PROBE__psc_s__c_on__ESZ, 4
PROBE__psc_s__c_on__ESZ:
	.word	4
	.globl	PROBE__psc_s__c_on__TSZ
	.align	2
	.type	PROBE__psc_s__c_on__TSZ, @object
	.size	PROBE__psc_s__c_on__TSZ, 4
PROBE__psc_s__c_on__TSZ:
	.word	4
	.globl	PROBE__psc_s__c_on__SGN
	.align	2
	.type	PROBE__psc_s__c_on__SGN, @object
	.size	PROBE__psc_s__c_on__SGN, 4
PROBE__psc_s__c_on__SGN:
	.space	4
	.globl	PROBE__psc_s__c_off__OFF
	.align	2
	.type	PROBE__psc_s__c_off__OFF, @object
	.size	PROBE__psc_s__c_off__OFF, 4
PROBE__psc_s__c_off__OFF:
	.word	12
	.globl	PROBE__psc_s__c_off__ESZ
	.align	2
	.type	PROBE__psc_s__c_off__ESZ, @object
	.size	PROBE__psc_s__c_off__ESZ, 4
PROBE__psc_s__c_off__ESZ:
	.word	4
	.globl	PROBE__psc_s__c_off__TSZ
	.align	2
	.type	PROBE__psc_s__c_off__TSZ, @object
	.size	PROBE__psc_s__c_off__TSZ, 4
PROBE__psc_s__c_off__TSZ:
	.word	4
	.globl	PROBE__psc_s__c_off__SGN
	.align	2
	.type	PROBE__psc_s__c_off__SGN, @object
	.size	PROBE__psc_s__c_off__SGN, 4
PROBE__psc_s__c_off__SGN:
	.space	4
	.globl	PROBE__psc_s__sector__OFF
	.align	2
	.type	PROBE__psc_s__sector__OFF, @object
	.size	PROBE__psc_s__sector__OFF, 4
PROBE__psc_s__sector__OFF:
	.word	16
	.globl	PROBE__psc_s__sector__ESZ
	.align	2
	.type	PROBE__psc_s__sector__ESZ, @object
	.size	PROBE__psc_s__sector__ESZ, 4
PROBE__psc_s__sector__ESZ:
	.word	4
	.globl	PROBE__psc_s__sector__TSZ
	.align	2
	.type	PROBE__psc_s__sector__TSZ, @object
	.size	PROBE__psc_s__sector__TSZ, 4
PROBE__psc_s__sector__TSZ:
	.word	4
	.globl	PROBE__psc_s__sector__SGN
	.align	2
	.type	PROBE__psc_s__sector__SGN, @object
	.size	PROBE__psc_s__sector__SGN, 4
PROBE__psc_s__sector__SGN:
	.space	4
	.globl	PROBE__psc_s__dtick__OFF
	.align	2
	.type	PROBE__psc_s__dtick__OFF, @object
	.size	PROBE__psc_s__dtick__OFF, 4
PROBE__psc_s__dtick__OFF:
	.word	20
	.globl	PROBE__psc_s__dtick__ESZ
	.align	2
	.type	PROBE__psc_s__dtick__ESZ, @object
	.size	PROBE__psc_s__dtick__ESZ, 4
PROBE__psc_s__dtick__ESZ:
	.word	2
	.globl	PROBE__psc_s__dtick__TSZ
	.align	2
	.type	PROBE__psc_s__dtick__TSZ, @object
	.size	PROBE__psc_s__dtick__TSZ, 4
PROBE__psc_s__dtick__TSZ:
	.word	2
	.globl	PROBE__psc_s__dtick__SGN
	.align	2
	.type	PROBE__psc_s__dtick__SGN, @object
	.size	PROBE__psc_s__dtick__SGN, 4
PROBE__psc_s__dtick__SGN:
	.space	4
	.globl	PROBE__psc_s__pid__OFF
	.align	2
	.type	PROBE__psc_s__pid__OFF, @object
	.size	PROBE__psc_s__pid__OFF, 4
PROBE__psc_s__pid__OFF:
	.word	22
	.globl	PROBE__psc_s__pid__ESZ
	.align	2
	.type	PROBE__psc_s__pid__ESZ, @object
	.size	PROBE__psc_s__pid__ESZ, 4
PROBE__psc_s__pid__ESZ:
	.word	2
	.globl	PROBE__psc_s__pid__TSZ
	.align	2
	.type	PROBE__psc_s__pid__TSZ, @object
	.size	PROBE__psc_s__pid__TSZ, 4
PROBE__psc_s__pid__TSZ:
	.word	2
	.globl	PROBE__psc_s__pid__SGN
	.align	2
	.type	PROBE__psc_s__pid__SGN, @object
	.size	PROBE__psc_s__pid__SGN, 4
PROBE__psc_s__pid__SGN:
	.space	4
	.globl	PROBE__psc_s__nsect__OFF
	.align	2
	.type	PROBE__psc_s__nsect__OFF, @object
	.size	PROBE__psc_s__nsect__OFF, 4
PROBE__psc_s__nsect__OFF:
	.word	24
	.globl	PROBE__psc_s__nsect__ESZ
	.align	2
	.type	PROBE__psc_s__nsect__ESZ, @object
	.size	PROBE__psc_s__nsect__ESZ, 4
PROBE__psc_s__nsect__ESZ:
	.word	1
	.globl	PROBE__psc_s__nsect__TSZ
	.align	2
	.type	PROBE__psc_s__nsect__TSZ, @object
	.size	PROBE__psc_s__nsect__TSZ, 4
PROBE__psc_s__nsect__TSZ:
	.word	1
	.globl	PROBE__psc_s__nsect__SGN
	.align	2
	.type	PROBE__psc_s__nsect__SGN, @object
	.size	PROBE__psc_s__nsect__SGN, 4
PROBE__psc_s__nsect__SGN:
	.space	4
	.globl	PROBE__psc_s__flags__OFF
	.align	2
	.type	PROBE__psc_s__flags__OFF, @object
	.size	PROBE__psc_s__flags__OFF, 4
PROBE__psc_s__flags__OFF:
	.word	25
	.globl	PROBE__psc_s__flags__ESZ
	.align	2
	.type	PROBE__psc_s__flags__ESZ, @object
	.size	PROBE__psc_s__flags__ESZ, 4
PROBE__psc_s__flags__ESZ:
	.word	1
	.globl	PROBE__psc_s__flags__TSZ
	.align	2
	.type	PROBE__psc_s__flags__TSZ, @object
	.size	PROBE__psc_s__flags__TSZ, 4
PROBE__psc_s__flags__TSZ:
	.word	1
	.globl	PROBE__psc_s__flags__SGN
	.align	2
	.type	PROBE__psc_s__flags__SGN, @object
	.size	PROBE__psc_s__flags__SGN, 4
PROBE__psc_s__flags__SGN:
	.space	4
	.globl	PROBE__psc_s__p_head_lo__OFF
	.align	2
	.type	PROBE__psc_s__p_head_lo__OFF, @object
	.size	PROBE__psc_s__p_head_lo__OFF, 4
PROBE__psc_s__p_head_lo__OFF:
	.word	26
	.globl	PROBE__psc_s__p_head_lo__ESZ
	.align	2
	.type	PROBE__psc_s__p_head_lo__ESZ, @object
	.size	PROBE__psc_s__p_head_lo__ESZ, 4
PROBE__psc_s__p_head_lo__ESZ:
	.word	2
	.globl	PROBE__psc_s__p_head_lo__TSZ
	.align	2
	.type	PROBE__psc_s__p_head_lo__TSZ, @object
	.size	PROBE__psc_s__p_head_lo__TSZ, 4
PROBE__psc_s__p_head_lo__TSZ:
	.word	2
	.globl	PROBE__psc_s__p_head_lo__SGN
	.align	2
	.type	PROBE__psc_s__p_head_lo__SGN, @object
	.size	PROBE__psc_s__p_head_lo__SGN, 4
PROBE__psc_s__p_head_lo__SGN:
	.space	4
	.globl	PROBE__psc_s__led_ops__OFF
	.align	2
	.type	PROBE__psc_s__led_ops__OFF, @object
	.size	PROBE__psc_s__led_ops__OFF, 4
PROBE__psc_s__led_ops__OFF:
	.word	28
	.globl	PROBE__psc_s__led_ops__ESZ
	.align	2
	.type	PROBE__psc_s__led_ops__ESZ, @object
	.size	PROBE__psc_s__led_ops__ESZ, 4
PROBE__psc_s__led_ops__ESZ:
	.word	1
	.globl	PROBE__psc_s__led_ops__TSZ
	.align	2
	.type	PROBE__psc_s__led_ops__TSZ, @object
	.size	PROBE__psc_s__led_ops__TSZ, 4
PROBE__psc_s__led_ops__TSZ:
	.word	1
	.globl	PROBE__psc_s__led_ops__SGN
	.align	2
	.type	PROBE__psc_s__led_ops__SGN, @object
	.size	PROBE__psc_s__led_ops__SGN, 4
PROBE__psc_s__led_ops__SGN:
	.space	4
	.globl	PROBE__psc_s__rsv29__OFF
	.align	2
	.type	PROBE__psc_s__rsv29__OFF, @object
	.size	PROBE__psc_s__rsv29__OFF, 4
PROBE__psc_s__rsv29__OFF:
	.word	29
	.globl	PROBE__psc_s__rsv29__ESZ
	.align	2
	.type	PROBE__psc_s__rsv29__ESZ, @object
	.size	PROBE__psc_s__rsv29__ESZ, 4
PROBE__psc_s__rsv29__ESZ:
	.word	1
	.globl	PROBE__psc_s__rsv29__TSZ
	.align	2
	.type	PROBE__psc_s__rsv29__TSZ, @object
	.size	PROBE__psc_s__rsv29__TSZ, 4
PROBE__psc_s__rsv29__TSZ:
	.word	1
	.globl	PROBE__psc_s__rsv29__SGN
	.align	2
	.type	PROBE__psc_s__rsv29__SGN, @object
	.size	PROBE__psc_s__rsv29__SGN, 4
PROBE__psc_s__rsv29__SGN:
	.space	4
	.globl	PROBE__psc_s__rsv30__OFF
	.align	2
	.type	PROBE__psc_s__rsv30__OFF, @object
	.size	PROBE__psc_s__rsv30__OFF, 4
PROBE__psc_s__rsv30__OFF:
	.word	30
	.globl	PROBE__psc_s__rsv30__ESZ
	.align	2
	.type	PROBE__psc_s__rsv30__ESZ, @object
	.size	PROBE__psc_s__rsv30__ESZ, 4
PROBE__psc_s__rsv30__ESZ:
	.word	2
	.globl	PROBE__psc_s__rsv30__TSZ
	.align	2
	.type	PROBE__psc_s__rsv30__TSZ, @object
	.size	PROBE__psc_s__rsv30__TSZ, 4
PROBE__psc_s__rsv30__TSZ:
	.word	2
	.globl	PROBE__psc_s__rsv30__SGN
	.align	2
	.type	PROBE__psc_s__rsv30__SGN, @object
	.size	PROBE__psc_s__rsv30__SGN, 4
PROBE__psc_s__rsv30__SGN:
	.space	4
	.globl	PROBE__psc_s__rd_set_or__OFF
	.align	2
	.type	PROBE__psc_s__rd_set_or__OFF, @object
	.size	PROBE__psc_s__rd_set_or__OFF, 4
PROBE__psc_s__rd_set_or__OFF:
	.word	32
	.globl	PROBE__psc_s__rd_set_or__ESZ
	.align	2
	.type	PROBE__psc_s__rd_set_or__ESZ, @object
	.size	PROBE__psc_s__rd_set_or__ESZ, 4
PROBE__psc_s__rd_set_or__ESZ:
	.word	4
	.globl	PROBE__psc_s__rd_set_or__TSZ
	.align	2
	.type	PROBE__psc_s__rd_set_or__TSZ, @object
	.size	PROBE__psc_s__rd_set_or__TSZ, 4
PROBE__psc_s__rd_set_or__TSZ:
	.word	4
	.globl	PROBE__psc_s__rd_set_or__SGN
	.align	2
	.type	PROBE__psc_s__rd_set_or__SGN, @object
	.size	PROBE__psc_s__rd_set_or__SGN, 4
PROBE__psc_s__rd_set_or__SGN:
	.space	4
	.globl	PROBE__psc_s__rd_clr_or__OFF
	.align	2
	.type	PROBE__psc_s__rd_clr_or__OFF, @object
	.size	PROBE__psc_s__rd_clr_or__OFF, 4
PROBE__psc_s__rd_clr_or__OFF:
	.word	36
	.globl	PROBE__psc_s__rd_clr_or__ESZ
	.align	2
	.type	PROBE__psc_s__rd_clr_or__ESZ, @object
	.size	PROBE__psc_s__rd_clr_or__ESZ, 4
PROBE__psc_s__rd_clr_or__ESZ:
	.word	4
	.globl	PROBE__psc_s__rd_clr_or__TSZ
	.align	2
	.type	PROBE__psc_s__rd_clr_or__TSZ, @object
	.size	PROBE__psc_s__rd_clr_or__TSZ, 4
PROBE__psc_s__rd_clr_or__TSZ:
	.word	4
	.globl	PROBE__psc_s__rd_clr_or__SGN
	.align	2
	.type	PROBE__psc_s__rd_clr_or__SGN, @object
	.size	PROBE__psc_s__rd_clr_or__SGN, 4
PROBE__psc_s__rd_clr_or__SGN:
	.space	4
	.globl	PROBE__psc_stats__SIZE
	.align	2
	.type	PROBE__psc_stats__SIZE, @object
	.size	PROBE__psc_stats__SIZE, 4
PROBE__psc_stats__SIZE:
	.word	768
	.globl	PROBE__psc_stats__magic__OFF
	.align	2
	.type	PROBE__psc_stats__magic__OFF, @object
	.size	PROBE__psc_stats__magic__OFF, 4
PROBE__psc_stats__magic__OFF:
	.space	4
	.globl	PROBE__psc_stats__magic__ESZ
	.align	2
	.type	PROBE__psc_stats__magic__ESZ, @object
	.size	PROBE__psc_stats__magic__ESZ, 4
PROBE__psc_stats__magic__ESZ:
	.word	4
	.globl	PROBE__psc_stats__magic__TSZ
	.align	2
	.type	PROBE__psc_stats__magic__TSZ, @object
	.size	PROBE__psc_stats__magic__TSZ, 4
PROBE__psc_stats__magic__TSZ:
	.word	4
	.globl	PROBE__psc_stats__magic__SGN
	.align	2
	.type	PROBE__psc_stats__magic__SGN, @object
	.size	PROBE__psc_stats__magic__SGN, 4
PROBE__psc_stats__magic__SGN:
	.space	4
	.globl	PROBE__psc_stats__version_size__OFF
	.align	2
	.type	PROBE__psc_stats__version_size__OFF, @object
	.size	PROBE__psc_stats__version_size__OFF, 4
PROBE__psc_stats__version_size__OFF:
	.word	4
	.globl	PROBE__psc_stats__version_size__ESZ
	.align	2
	.type	PROBE__psc_stats__version_size__ESZ, @object
	.size	PROBE__psc_stats__version_size__ESZ, 4
PROBE__psc_stats__version_size__ESZ:
	.word	4
	.globl	PROBE__psc_stats__version_size__TSZ
	.align	2
	.type	PROBE__psc_stats__version_size__TSZ, @object
	.size	PROBE__psc_stats__version_size__TSZ, 4
PROBE__psc_stats__version_size__TSZ:
	.word	4
	.globl	PROBE__psc_stats__version_size__SGN
	.align	2
	.type	PROBE__psc_stats__version_size__SGN, @object
	.size	PROBE__psc_stats__version_size__SGN, 4
PROBE__psc_stats__version_size__SGN:
	.space	4
	.globl	PROBE__psc_stats__build_id__OFF
	.align	2
	.type	PROBE__psc_stats__build_id__OFF, @object
	.size	PROBE__psc_stats__build_id__OFF, 4
PROBE__psc_stats__build_id__OFF:
	.word	8
	.globl	PROBE__psc_stats__build_id__ESZ
	.align	2
	.type	PROBE__psc_stats__build_id__ESZ, @object
	.size	PROBE__psc_stats__build_id__ESZ, 4
PROBE__psc_stats__build_id__ESZ:
	.word	4
	.globl	PROBE__psc_stats__build_id__TSZ
	.align	2
	.type	PROBE__psc_stats__build_id__TSZ, @object
	.size	PROBE__psc_stats__build_id__TSZ, 4
PROBE__psc_stats__build_id__TSZ:
	.word	4
	.globl	PROBE__psc_stats__build_id__SGN
	.align	2
	.type	PROBE__psc_stats__build_id__SGN, @object
	.size	PROBE__psc_stats__build_id__SGN, 4
PROBE__psc_stats__build_id__SGN:
	.space	4
	.globl	PROBE__psc_stats__hz__OFF
	.align	2
	.type	PROBE__psc_stats__hz__OFF, @object
	.size	PROBE__psc_stats__hz__OFF, 4
PROBE__psc_stats__hz__OFF:
	.word	12
	.globl	PROBE__psc_stats__hz__ESZ
	.align	2
	.type	PROBE__psc_stats__hz__ESZ, @object
	.size	PROBE__psc_stats__hz__ESZ, 4
PROBE__psc_stats__hz__ESZ:
	.word	4
	.globl	PROBE__psc_stats__hz__TSZ
	.align	2
	.type	PROBE__psc_stats__hz__TSZ, @object
	.size	PROBE__psc_stats__hz__TSZ, 4
PROBE__psc_stats__hz__TSZ:
	.word	4
	.globl	PROBE__psc_stats__hz__SGN
	.align	2
	.type	PROBE__psc_stats__hz__SGN, @object
	.size	PROBE__psc_stats__hz__SGN, 4
PROBE__psc_stats__hz__SGN:
	.space	4
	.globl	PROBE__psc_stats__counts_per_tick__OFF
	.align	2
	.type	PROBE__psc_stats__counts_per_tick__OFF, @object
	.size	PROBE__psc_stats__counts_per_tick__OFF, 4
PROBE__psc_stats__counts_per_tick__OFF:
	.word	16
	.globl	PROBE__psc_stats__counts_per_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__counts_per_tick__ESZ, @object
	.size	PROBE__psc_stats__counts_per_tick__ESZ, 4
PROBE__psc_stats__counts_per_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__counts_per_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__counts_per_tick__TSZ, @object
	.size	PROBE__psc_stats__counts_per_tick__TSZ, 4
PROBE__psc_stats__counts_per_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__counts_per_tick__SGN
	.align	2
	.type	PROBE__psc_stats__counts_per_tick__SGN, @object
	.size	PROBE__psc_stats__counts_per_tick__SGN, 4
PROBE__psc_stats__counts_per_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__last_reader_tick__OFF
	.align	2
	.type	PROBE__psc_stats__last_reader_tick__OFF, @object
	.size	PROBE__psc_stats__last_reader_tick__OFF, 4
PROBE__psc_stats__last_reader_tick__OFF:
	.word	20
	.globl	PROBE__psc_stats__last_reader_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__last_reader_tick__ESZ, @object
	.size	PROBE__psc_stats__last_reader_tick__ESZ, 4
PROBE__psc_stats__last_reader_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__last_reader_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__last_reader_tick__TSZ, @object
	.size	PROBE__psc_stats__last_reader_tick__TSZ, 4
PROBE__psc_stats__last_reader_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__last_reader_tick__SGN
	.align	2
	.type	PROBE__psc_stats__last_reader_tick__SGN, @object
	.size	PROBE__psc_stats__last_reader_tick__SGN, 4
PROBE__psc_stats__last_reader_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__initial_jiffies__OFF
	.align	2
	.type	PROBE__psc_stats__initial_jiffies__OFF, @object
	.size	PROBE__psc_stats__initial_jiffies__OFF, 4
PROBE__psc_stats__initial_jiffies__OFF:
	.word	24
	.globl	PROBE__psc_stats__initial_jiffies__ESZ
	.align	2
	.type	PROBE__psc_stats__initial_jiffies__ESZ, @object
	.size	PROBE__psc_stats__initial_jiffies__ESZ, 4
PROBE__psc_stats__initial_jiffies__ESZ:
	.word	4
	.globl	PROBE__psc_stats__initial_jiffies__TSZ
	.align	2
	.type	PROBE__psc_stats__initial_jiffies__TSZ, @object
	.size	PROBE__psc_stats__initial_jiffies__TSZ, 4
PROBE__psc_stats__initial_jiffies__TSZ:
	.word	4
	.globl	PROBE__psc_stats__initial_jiffies__SGN
	.align	2
	.type	PROBE__psc_stats__initial_jiffies__SGN, @object
	.size	PROBE__psc_stats__initial_jiffies__SGN, 4
PROBE__psc_stats__initial_jiffies__SGN:
	.space	4
	.globl	PROBE__psc_stats__now_tick__OFF
	.align	2
	.type	PROBE__psc_stats__now_tick__OFF, @object
	.size	PROBE__psc_stats__now_tick__OFF, 4
PROBE__psc_stats__now_tick__OFF:
	.word	28
	.globl	PROBE__psc_stats__now_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__now_tick__ESZ, @object
	.size	PROBE__psc_stats__now_tick__ESZ, 4
PROBE__psc_stats__now_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__now_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__now_tick__TSZ, @object
	.size	PROBE__psc_stats__now_tick__TSZ, 4
PROBE__psc_stats__now_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__now_tick__SGN
	.align	2
	.type	PROBE__psc_stats__now_tick__SGN, @object
	.size	PROBE__psc_stats__now_tick__SGN, 4
PROBE__psc_stats__now_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__now_count__OFF
	.align	2
	.type	PROBE__psc_stats__now_count__OFF, @object
	.size	PROBE__psc_stats__now_count__OFF, 4
PROBE__psc_stats__now_count__OFF:
	.word	32
	.globl	PROBE__psc_stats__now_count__ESZ
	.align	2
	.type	PROBE__psc_stats__now_count__ESZ, @object
	.size	PROBE__psc_stats__now_count__ESZ, 4
PROBE__psc_stats__now_count__ESZ:
	.word	4
	.globl	PROBE__psc_stats__now_count__TSZ
	.align	2
	.type	PROBE__psc_stats__now_count__TSZ, @object
	.size	PROBE__psc_stats__now_count__TSZ, 4
PROBE__psc_stats__now_count__TSZ:
	.word	4
	.globl	PROBE__psc_stats__now_count__SGN
	.align	2
	.type	PROBE__psc_stats__now_count__SGN, @object
	.size	PROBE__psc_stats__now_count__SGN, 4
PROBE__psc_stats__now_count__SGN:
	.space	4
	.globl	PROBE__psc_stats__now_jiffies__OFF
	.align	2
	.type	PROBE__psc_stats__now_jiffies__OFF, @object
	.size	PROBE__psc_stats__now_jiffies__OFF, 4
PROBE__psc_stats__now_jiffies__OFF:
	.word	36
	.globl	PROBE__psc_stats__now_jiffies__ESZ
	.align	2
	.type	PROBE__psc_stats__now_jiffies__ESZ, @object
	.size	PROBE__psc_stats__now_jiffies__ESZ, 4
PROBE__psc_stats__now_jiffies__ESZ:
	.word	4
	.globl	PROBE__psc_stats__now_jiffies__TSZ
	.align	2
	.type	PROBE__psc_stats__now_jiffies__TSZ, @object
	.size	PROBE__psc_stats__now_jiffies__TSZ, 4
PROBE__psc_stats__now_jiffies__TSZ:
	.word	4
	.globl	PROBE__psc_stats__now_jiffies__SGN
	.align	2
	.type	PROBE__psc_stats__now_jiffies__SGN, @object
	.size	PROBE__psc_stats__now_jiffies__SGN, 4
PROBE__psc_stats__now_jiffies__SGN:
	.space	4
	.globl	PROBE__psc_stats__total_counts_lo__OFF
	.align	2
	.type	PROBE__psc_stats__total_counts_lo__OFF, @object
	.size	PROBE__psc_stats__total_counts_lo__OFF, 4
PROBE__psc_stats__total_counts_lo__OFF:
	.word	40
	.globl	PROBE__psc_stats__total_counts_lo__ESZ
	.align	2
	.type	PROBE__psc_stats__total_counts_lo__ESZ, @object
	.size	PROBE__psc_stats__total_counts_lo__ESZ, 4
PROBE__psc_stats__total_counts_lo__ESZ:
	.word	4
	.globl	PROBE__psc_stats__total_counts_lo__TSZ
	.align	2
	.type	PROBE__psc_stats__total_counts_lo__TSZ, @object
	.size	PROBE__psc_stats__total_counts_lo__TSZ, 4
PROBE__psc_stats__total_counts_lo__TSZ:
	.word	4
	.globl	PROBE__psc_stats__total_counts_lo__SGN
	.align	2
	.type	PROBE__psc_stats__total_counts_lo__SGN, @object
	.size	PROBE__psc_stats__total_counts_lo__SGN, 4
PROBE__psc_stats__total_counts_lo__SGN:
	.space	4
	.globl	PROBE__psc_stats__total_counts_hi__OFF
	.align	2
	.type	PROBE__psc_stats__total_counts_hi__OFF, @object
	.size	PROBE__psc_stats__total_counts_hi__OFF, 4
PROBE__psc_stats__total_counts_hi__OFF:
	.word	44
	.globl	PROBE__psc_stats__total_counts_hi__ESZ
	.align	2
	.type	PROBE__psc_stats__total_counts_hi__ESZ, @object
	.size	PROBE__psc_stats__total_counts_hi__ESZ, 4
PROBE__psc_stats__total_counts_hi__ESZ:
	.word	4
	.globl	PROBE__psc_stats__total_counts_hi__TSZ
	.align	2
	.type	PROBE__psc_stats__total_counts_hi__TSZ, @object
	.size	PROBE__psc_stats__total_counts_hi__TSZ, 4
PROBE__psc_stats__total_counts_hi__TSZ:
	.word	4
	.globl	PROBE__psc_stats__total_counts_hi__SGN
	.align	2
	.type	PROBE__psc_stats__total_counts_hi__SGN, @object
	.size	PROBE__psc_stats__total_counts_hi__SGN, 4
PROBE__psc_stats__total_counts_hi__SGN:
	.space	4
	.globl	PROBE__psc_stats__c_pre_max__OFF
	.align	2
	.type	PROBE__psc_stats__c_pre_max__OFF, @object
	.size	PROBE__psc_stats__c_pre_max__OFF, 4
PROBE__psc_stats__c_pre_max__OFF:
	.word	48
	.globl	PROBE__psc_stats__c_pre_max__ESZ
	.align	2
	.type	PROBE__psc_stats__c_pre_max__ESZ, @object
	.size	PROBE__psc_stats__c_pre_max__ESZ, 4
PROBE__psc_stats__c_pre_max__ESZ:
	.word	4
	.globl	PROBE__psc_stats__c_pre_max__TSZ
	.align	2
	.type	PROBE__psc_stats__c_pre_max__TSZ, @object
	.size	PROBE__psc_stats__c_pre_max__TSZ, 4
PROBE__psc_stats__c_pre_max__TSZ:
	.word	4
	.globl	PROBE__psc_stats__c_pre_max__SGN
	.align	2
	.type	PROBE__psc_stats__c_pre_max__SGN, @object
	.size	PROBE__psc_stats__c_pre_max__SGN, 4
PROBE__psc_stats__c_pre_max__SGN:
	.space	4
	.globl	PROBE__psc_stats__long_ticks__OFF
	.align	2
	.type	PROBE__psc_stats__long_ticks__OFF, @object
	.size	PROBE__psc_stats__long_ticks__OFF, 4
PROBE__psc_stats__long_ticks__OFF:
	.word	52
	.globl	PROBE__psc_stats__long_ticks__ESZ
	.align	2
	.type	PROBE__psc_stats__long_ticks__ESZ, @object
	.size	PROBE__psc_stats__long_ticks__ESZ, 4
PROBE__psc_stats__long_ticks__ESZ:
	.word	4
	.globl	PROBE__psc_stats__long_ticks__TSZ
	.align	2
	.type	PROBE__psc_stats__long_ticks__TSZ, @object
	.size	PROBE__psc_stats__long_ticks__TSZ, 4
PROBE__psc_stats__long_ticks__TSZ:
	.word	4
	.globl	PROBE__psc_stats__long_ticks__SGN
	.align	2
	.type	PROBE__psc_stats__long_ticks__SGN, @object
	.size	PROBE__psc_stats__long_ticks__SGN, 4
PROBE__psc_stats__long_ticks__SGN:
	.space	4
	.globl	PROBE__psc_stats__head__OFF
	.align	2
	.type	PROBE__psc_stats__head__OFF, @object
	.size	PROBE__psc_stats__head__OFF, 4
PROBE__psc_stats__head__OFF:
	.word	56
	.globl	PROBE__psc_stats__head__ESZ
	.align	2
	.type	PROBE__psc_stats__head__ESZ, @object
	.size	PROBE__psc_stats__head__ESZ, 4
PROBE__psc_stats__head__ESZ:
	.word	4
	.globl	PROBE__psc_stats__head__TSZ
	.align	2
	.type	PROBE__psc_stats__head__TSZ, @object
	.size	PROBE__psc_stats__head__TSZ, 4
PROBE__psc_stats__head__TSZ:
	.word	20
	.globl	PROBE__psc_stats__head__SGN
	.align	2
	.type	PROBE__psc_stats__head__SGN, @object
	.size	PROBE__psc_stats__head__SGN, 4
PROBE__psc_stats__head__SGN:
	.space	4
	.globl	PROBE__psc_stats__m_dropped__OFF
	.align	2
	.type	PROBE__psc_stats__m_dropped__OFF, @object
	.size	PROBE__psc_stats__m_dropped__OFF, 4
PROBE__psc_stats__m_dropped__OFF:
	.word	76
	.globl	PROBE__psc_stats__m_dropped__ESZ
	.align	2
	.type	PROBE__psc_stats__m_dropped__ESZ, @object
	.size	PROBE__psc_stats__m_dropped__ESZ, 4
PROBE__psc_stats__m_dropped__ESZ:
	.word	4
	.globl	PROBE__psc_stats__m_dropped__TSZ
	.align	2
	.type	PROBE__psc_stats__m_dropped__TSZ, @object
	.size	PROBE__psc_stats__m_dropped__TSZ, 4
PROBE__psc_stats__m_dropped__TSZ:
	.word	4
	.globl	PROBE__psc_stats__m_dropped__SGN
	.align	2
	.type	PROBE__psc_stats__m_dropped__SGN, @object
	.size	PROBE__psc_stats__m_dropped__SGN, 4
PROBE__psc_stats__m_dropped__SGN:
	.space	4
	.globl	PROBE__psc_stats__addr_syscon_cmd__OFF
	.align	2
	.type	PROBE__psc_stats__addr_syscon_cmd__OFF, @object
	.size	PROBE__psc_stats__addr_syscon_cmd__OFF, 4
PROBE__psc_stats__addr_syscon_cmd__OFF:
	.word	80
	.globl	PROBE__psc_stats__addr_syscon_cmd__ESZ
	.align	2
	.type	PROBE__psc_stats__addr_syscon_cmd__ESZ, @object
	.size	PROBE__psc_stats__addr_syscon_cmd__ESZ, 4
PROBE__psc_stats__addr_syscon_cmd__ESZ:
	.word	4
	.globl	PROBE__psc_stats__addr_syscon_cmd__TSZ
	.align	2
	.type	PROBE__psc_stats__addr_syscon_cmd__TSZ, @object
	.size	PROBE__psc_stats__addr_syscon_cmd__TSZ, 4
PROBE__psc_stats__addr_syscon_cmd__TSZ:
	.word	4
	.globl	PROBE__psc_stats__addr_syscon_cmd__SGN
	.align	2
	.type	PROBE__psc_stats__addr_syscon_cmd__SGN, @object
	.size	PROBE__psc_stats__addr_syscon_cmd__SGN, 4
PROBE__psc_stats__addr_syscon_cmd__SGN:
	.space	4
	.globl	PROBE__psc_stats__addr_psc_sc_exit__OFF
	.align	2
	.type	PROBE__psc_stats__addr_psc_sc_exit__OFF, @object
	.size	PROBE__psc_stats__addr_psc_sc_exit__OFF, 4
PROBE__psc_stats__addr_psc_sc_exit__OFF:
	.word	84
	.globl	PROBE__psc_stats__addr_psc_sc_exit__ESZ
	.align	2
	.type	PROBE__psc_stats__addr_psc_sc_exit__ESZ, @object
	.size	PROBE__psc_stats__addr_psc_sc_exit__ESZ, 4
PROBE__psc_stats__addr_psc_sc_exit__ESZ:
	.word	4
	.globl	PROBE__psc_stats__addr_psc_sc_exit__TSZ
	.align	2
	.type	PROBE__psc_stats__addr_psc_sc_exit__TSZ, @object
	.size	PROBE__psc_stats__addr_psc_sc_exit__TSZ, 4
PROBE__psc_stats__addr_psc_sc_exit__TSZ:
	.word	4
	.globl	PROBE__psc_stats__addr_psc_sc_exit__SGN
	.align	2
	.type	PROBE__psc_stats__addr_psc_sc_exit__SGN, @object
	.size	PROBE__psc_stats__addr_psc_sc_exit__SGN, 4
PROBE__psc_stats__addr_psc_sc_exit__SGN:
	.space	4
	.globl	PROBE__psc_stats__addr_getctrl2__OFF
	.align	2
	.type	PROBE__psc_stats__addr_getctrl2__OFF, @object
	.size	PROBE__psc_stats__addr_getctrl2__OFF, 4
PROBE__psc_stats__addr_getctrl2__OFF:
	.word	88
	.globl	PROBE__psc_stats__addr_getctrl2__ESZ
	.align	2
	.type	PROBE__psc_stats__addr_getctrl2__ESZ, @object
	.size	PROBE__psc_stats__addr_getctrl2__ESZ, 4
PROBE__psc_stats__addr_getctrl2__ESZ:
	.word	4
	.globl	PROBE__psc_stats__addr_getctrl2__TSZ
	.align	2
	.type	PROBE__psc_stats__addr_getctrl2__TSZ, @object
	.size	PROBE__psc_stats__addr_getctrl2__TSZ, 4
PROBE__psc_stats__addr_getctrl2__TSZ:
	.word	4
	.globl	PROBE__psc_stats__addr_getctrl2__SGN
	.align	2
	.type	PROBE__psc_stats__addr_getctrl2__SGN, @object
	.size	PROBE__psc_stats__addr_getctrl2__SGN, 4
PROBE__psc_stats__addr_getctrl2__SGN:
	.space	4
	.globl	PROBE__psc_stats__proc_opens__OFF
	.align	2
	.type	PROBE__psc_stats__proc_opens__OFF, @object
	.size	PROBE__psc_stats__proc_opens__OFF, 4
PROBE__psc_stats__proc_opens__OFF:
	.word	92
	.globl	PROBE__psc_stats__proc_opens__ESZ
	.align	2
	.type	PROBE__psc_stats__proc_opens__ESZ, @object
	.size	PROBE__psc_stats__proc_opens__ESZ, 4
PROBE__psc_stats__proc_opens__ESZ:
	.word	4
	.globl	PROBE__psc_stats__proc_opens__TSZ
	.align	2
	.type	PROBE__psc_stats__proc_opens__TSZ, @object
	.size	PROBE__psc_stats__proc_opens__TSZ, 4
PROBE__psc_stats__proc_opens__TSZ:
	.word	4
	.globl	PROBE__psc_stats__proc_opens__SGN
	.align	2
	.type	PROBE__psc_stats__proc_opens__SGN, @object
	.size	PROBE__psc_stats__proc_opens__SGN, 4
PROBE__psc_stats__proc_opens__SGN:
	.space	4
	.globl	PROBE__psc_stats__p_rec_cost_last__OFF
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_last__OFF, @object
	.size	PROBE__psc_stats__p_rec_cost_last__OFF, 4
PROBE__psc_stats__p_rec_cost_last__OFF:
	.word	96
	.globl	PROBE__psc_stats__p_rec_cost_last__ESZ
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_last__ESZ, @object
	.size	PROBE__psc_stats__p_rec_cost_last__ESZ, 4
PROBE__psc_stats__p_rec_cost_last__ESZ:
	.word	4
	.globl	PROBE__psc_stats__p_rec_cost_last__TSZ
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_last__TSZ, @object
	.size	PROBE__psc_stats__p_rec_cost_last__TSZ, 4
PROBE__psc_stats__p_rec_cost_last__TSZ:
	.word	4
	.globl	PROBE__psc_stats__p_rec_cost_last__SGN
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_last__SGN, @object
	.size	PROBE__psc_stats__p_rec_cost_last__SGN, 4
PROBE__psc_stats__p_rec_cost_last__SGN:
	.space	4
	.globl	PROBE__psc_stats__p_rec_cost_max__OFF
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_max__OFF, @object
	.size	PROBE__psc_stats__p_rec_cost_max__OFF, 4
PROBE__psc_stats__p_rec_cost_max__OFF:
	.word	100
	.globl	PROBE__psc_stats__p_rec_cost_max__ESZ
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_max__ESZ, @object
	.size	PROBE__psc_stats__p_rec_cost_max__ESZ, 4
PROBE__psc_stats__p_rec_cost_max__ESZ:
	.word	4
	.globl	PROBE__psc_stats__p_rec_cost_max__TSZ
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_max__TSZ, @object
	.size	PROBE__psc_stats__p_rec_cost_max__TSZ, 4
PROBE__psc_stats__p_rec_cost_max__TSZ:
	.word	4
	.globl	PROBE__psc_stats__p_rec_cost_max__SGN
	.align	2
	.type	PROBE__psc_stats__p_rec_cost_max__SGN, @object
	.size	PROBE__psc_stats__p_rec_cost_max__SGN, 4
PROBE__psc_stats__p_rec_cost_max__SGN:
	.space	4
	.globl	PROBE__psc_stats__w_rec_cost_max__OFF
	.align	2
	.type	PROBE__psc_stats__w_rec_cost_max__OFF, @object
	.size	PROBE__psc_stats__w_rec_cost_max__OFF, 4
PROBE__psc_stats__w_rec_cost_max__OFF:
	.word	104
	.globl	PROBE__psc_stats__w_rec_cost_max__ESZ
	.align	2
	.type	PROBE__psc_stats__w_rec_cost_max__ESZ, @object
	.size	PROBE__psc_stats__w_rec_cost_max__ESZ, 4
PROBE__psc_stats__w_rec_cost_max__ESZ:
	.word	4
	.globl	PROBE__psc_stats__w_rec_cost_max__TSZ
	.align	2
	.type	PROBE__psc_stats__w_rec_cost_max__TSZ, @object
	.size	PROBE__psc_stats__w_rec_cost_max__TSZ, 4
PROBE__psc_stats__w_rec_cost_max__TSZ:
	.word	4
	.globl	PROBE__psc_stats__w_rec_cost_max__SGN
	.align	2
	.type	PROBE__psc_stats__w_rec_cost_max__SGN, @object
	.size	PROBE__psc_stats__w_rec_cost_max__SGN, 4
PROBE__psc_stats__w_rec_cost_max__SGN:
	.space	4
	.globl	PROBE__psc_stats__wd_calls__OFF
	.align	2
	.type	PROBE__psc_stats__wd_calls__OFF, @object
	.size	PROBE__psc_stats__wd_calls__OFF, 4
PROBE__psc_stats__wd_calls__OFF:
	.word	108
	.globl	PROBE__psc_stats__wd_calls__ESZ
	.align	2
	.type	PROBE__psc_stats__wd_calls__ESZ, @object
	.size	PROBE__psc_stats__wd_calls__ESZ, 4
PROBE__psc_stats__wd_calls__ESZ:
	.word	4
	.globl	PROBE__psc_stats__wd_calls__TSZ
	.align	2
	.type	PROBE__psc_stats__wd_calls__TSZ, @object
	.size	PROBE__psc_stats__wd_calls__TSZ, 4
PROBE__psc_stats__wd_calls__TSZ:
	.word	4
	.globl	PROBE__psc_stats__wd_calls__SGN
	.align	2
	.type	PROBE__psc_stats__wd_calls__SGN, @object
	.size	PROBE__psc_stats__wd_calls__SGN, 4
PROBE__psc_stats__wd_calls__SGN:
	.space	4
	.globl	PROBE__psc_stats__wd_last_tick__OFF
	.align	2
	.type	PROBE__psc_stats__wd_last_tick__OFF, @object
	.size	PROBE__psc_stats__wd_last_tick__OFF, 4
PROBE__psc_stats__wd_last_tick__OFF:
	.word	112
	.globl	PROBE__psc_stats__wd_last_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__wd_last_tick__ESZ, @object
	.size	PROBE__psc_stats__wd_last_tick__ESZ, 4
PROBE__psc_stats__wd_last_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__wd_last_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__wd_last_tick__TSZ, @object
	.size	PROBE__psc_stats__wd_last_tick__TSZ, 4
PROBE__psc_stats__wd_last_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__wd_last_tick__SGN
	.align	2
	.type	PROBE__psc_stats__wd_last_tick__SGN, @object
	.size	PROBE__psc_stats__wd_last_tick__SGN, 4
PROBE__psc_stats__wd_last_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__p_nested__OFF
	.align	2
	.type	PROBE__psc_stats__p_nested__OFF, @object
	.size	PROBE__psc_stats__p_nested__OFF, 4
PROBE__psc_stats__p_nested__OFF:
	.word	116
	.globl	PROBE__psc_stats__p_nested__ESZ
	.align	2
	.type	PROBE__psc_stats__p_nested__ESZ, @object
	.size	PROBE__psc_stats__p_nested__ESZ, 4
PROBE__psc_stats__p_nested__ESZ:
	.word	4
	.globl	PROBE__psc_stats__p_nested__TSZ
	.align	2
	.type	PROBE__psc_stats__p_nested__TSZ, @object
	.size	PROBE__psc_stats__p_nested__TSZ, 4
PROBE__psc_stats__p_nested__TSZ:
	.word	4
	.globl	PROBE__psc_stats__p_nested__SGN
	.align	2
	.type	PROBE__psc_stats__p_nested__SGN, @object
	.size	PROBE__psc_stats__p_nested__SGN, 4
PROBE__psc_stats__p_nested__SGN:
	.space	4
	.globl	PROBE__psc_stats__p_ticked__OFF
	.align	2
	.type	PROBE__psc_stats__p_ticked__OFF, @object
	.size	PROBE__psc_stats__p_ticked__OFF, 4
PROBE__psc_stats__p_ticked__OFF:
	.word	120
	.globl	PROBE__psc_stats__p_ticked__ESZ
	.align	2
	.type	PROBE__psc_stats__p_ticked__ESZ, @object
	.size	PROBE__psc_stats__p_ticked__ESZ, 4
PROBE__psc_stats__p_ticked__ESZ:
	.word	4
	.globl	PROBE__psc_stats__p_ticked__TSZ
	.align	2
	.type	PROBE__psc_stats__p_ticked__TSZ, @object
	.size	PROBE__psc_stats__p_ticked__TSZ, 4
PROBE__psc_stats__p_ticked__TSZ:
	.word	4
	.globl	PROBE__psc_stats__p_ticked__SGN
	.align	2
	.type	PROBE__psc_stats__p_ticked__SGN, @object
	.size	PROBE__psc_stats__p_ticked__SGN, 4
PROBE__psc_stats__p_ticked__SGN:
	.space	4
	.globl	PROBE__psc_stats__oc_p08__OFF
	.align	2
	.type	PROBE__psc_stats__oc_p08__OFF, @object
	.size	PROBE__psc_stats__oc_p08__OFF, 4
PROBE__psc_stats__oc_p08__OFF:
	.word	124
	.globl	PROBE__psc_stats__oc_p08__ESZ
	.align	2
	.type	PROBE__psc_stats__oc_p08__ESZ, @object
	.size	PROBE__psc_stats__oc_p08__ESZ, 4
PROBE__psc_stats__oc_p08__ESZ:
	.word	4
	.globl	PROBE__psc_stats__oc_p08__TSZ
	.align	2
	.type	PROBE__psc_stats__oc_p08__TSZ, @object
	.size	PROBE__psc_stats__oc_p08__TSZ, 4
PROBE__psc_stats__oc_p08__TSZ:
	.word	28
	.globl	PROBE__psc_stats__oc_p08__SGN
	.align	2
	.type	PROBE__psc_stats__oc_p08__SGN, @object
	.size	PROBE__psc_stats__oc_p08__SGN, 4
PROBE__psc_stats__oc_p08__SGN:
	.space	4
	.globl	PROBE__psc_stats__oc_p33__OFF
	.align	2
	.type	PROBE__psc_stats__oc_p33__OFF, @object
	.size	PROBE__psc_stats__oc_p33__OFF, 4
PROBE__psc_stats__oc_p33__OFF:
	.word	152
	.globl	PROBE__psc_stats__oc_p33__ESZ
	.align	2
	.type	PROBE__psc_stats__oc_p33__ESZ, @object
	.size	PROBE__psc_stats__oc_p33__ESZ, 4
PROBE__psc_stats__oc_p33__ESZ:
	.word	4
	.globl	PROBE__psc_stats__oc_p33__TSZ
	.align	2
	.type	PROBE__psc_stats__oc_p33__TSZ, @object
	.size	PROBE__psc_stats__oc_p33__TSZ, 4
PROBE__psc_stats__oc_p33__TSZ:
	.word	28
	.globl	PROBE__psc_stats__oc_p33__SGN
	.align	2
	.type	PROBE__psc_stats__oc_p33__SGN, @object
	.size	PROBE__psc_stats__oc_p33__SGN, 4
PROBE__psc_stats__oc_p33__SGN:
	.space	4
	.globl	PROBE__psc_stats__oc_w__OFF
	.align	2
	.type	PROBE__psc_stats__oc_w__OFF, @object
	.size	PROBE__psc_stats__oc_w__OFF, 4
PROBE__psc_stats__oc_w__OFF:
	.word	180
	.globl	PROBE__psc_stats__oc_w__ESZ
	.align	2
	.type	PROBE__psc_stats__oc_w__ESZ, @object
	.size	PROBE__psc_stats__oc_w__ESZ, 4
PROBE__psc_stats__oc_w__ESZ:
	.word	4
	.globl	PROBE__psc_stats__oc_w__TSZ
	.align	2
	.type	PROBE__psc_stats__oc_w__TSZ, @object
	.size	PROBE__psc_stats__oc_w__TSZ, 4
PROBE__psc_stats__oc_w__TSZ:
	.word	28
	.globl	PROBE__psc_stats__oc_w__SGN
	.align	2
	.type	PROBE__psc_stats__oc_w__SGN, @object
	.size	PROBE__psc_stats__oc_w__SGN, 4
PROBE__psc_stats__oc_w__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_pid__OFF
	.align	2
	.type	PROBE__psc_stats__jp_pid__OFF, @object
	.size	PROBE__psc_stats__jp_pid__OFF, 4
PROBE__psc_stats__jp_pid__OFF:
	.word	208
	.globl	PROBE__psc_stats__jp_pid__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_pid__ESZ, @object
	.size	PROBE__psc_stats__jp_pid__ESZ, 4
PROBE__psc_stats__jp_pid__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_pid__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_pid__TSZ, @object
	.size	PROBE__psc_stats__jp_pid__TSZ, 4
PROBE__psc_stats__jp_pid__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_pid__SGN
	.align	2
	.type	PROBE__psc_stats__jp_pid__SGN, @object
	.size	PROBE__psc_stats__jp_pid__SGN, 4
PROBE__psc_stats__jp_pid__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_loop__OFF
	.align	2
	.type	PROBE__psc_stats__jp_loop__OFF, @object
	.size	PROBE__psc_stats__jp_loop__OFF, 4
PROBE__psc_stats__jp_loop__OFF:
	.word	212
	.globl	PROBE__psc_stats__jp_loop__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_loop__ESZ, @object
	.size	PROBE__psc_stats__jp_loop__ESZ, 4
PROBE__psc_stats__jp_loop__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_loop__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_loop__TSZ, @object
	.size	PROBE__psc_stats__jp_loop__TSZ, 4
PROBE__psc_stats__jp_loop__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_loop__SGN
	.align	2
	.type	PROBE__psc_stats__jp_loop__SGN, @object
	.size	PROBE__psc_stats__jp_loop__SGN, 4
PROBE__psc_stats__jp_loop__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_stage__OFF
	.align	2
	.type	PROBE__psc_stats__jp_stage__OFF, @object
	.size	PROBE__psc_stats__jp_stage__OFF, 4
PROBE__psc_stats__jp_stage__OFF:
	.word	216
	.globl	PROBE__psc_stats__jp_stage__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_stage__ESZ, @object
	.size	PROBE__psc_stats__jp_stage__ESZ, 4
PROBE__psc_stats__jp_stage__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_stage__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_stage__TSZ, @object
	.size	PROBE__psc_stats__jp_stage__TSZ, 4
PROBE__psc_stats__jp_stage__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_stage__SGN
	.align	2
	.type	PROBE__psc_stats__jp_stage__SGN, @object
	.size	PROBE__psc_stats__jp_stage__SGN, 4
PROBE__psc_stats__jp_stage__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_stage_arg__OFF
	.align	2
	.type	PROBE__psc_stats__jp_stage_arg__OFF, @object
	.size	PROBE__psc_stats__jp_stage_arg__OFF, 4
PROBE__psc_stats__jp_stage_arg__OFF:
	.word	220
	.globl	PROBE__psc_stats__jp_stage_arg__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_stage_arg__ESZ, @object
	.size	PROBE__psc_stats__jp_stage_arg__ESZ, 4
PROBE__psc_stats__jp_stage_arg__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_stage_arg__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_stage_arg__TSZ, @object
	.size	PROBE__psc_stats__jp_stage_arg__TSZ, 4
PROBE__psc_stats__jp_stage_arg__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_stage_arg__SGN
	.align	2
	.type	PROBE__psc_stats__jp_stage_arg__SGN, @object
	.size	PROBE__psc_stats__jp_stage_arg__SGN, 4
PROBE__psc_stats__jp_stage_arg__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_state__OFF
	.align	2
	.type	PROBE__psc_stats__jp_state__OFF, @object
	.size	PROBE__psc_stats__jp_state__OFF, 4
PROBE__psc_stats__jp_state__OFF:
	.word	224
	.globl	PROBE__psc_stats__jp_state__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_state__ESZ, @object
	.size	PROBE__psc_stats__jp_state__ESZ, 4
PROBE__psc_stats__jp_state__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_state__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_state__TSZ, @object
	.size	PROBE__psc_stats__jp_state__TSZ, 4
PROBE__psc_stats__jp_state__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_state__SGN
	.align	2
	.type	PROBE__psc_stats__jp_state__SGN, @object
	.size	PROBE__psc_stats__jp_state__SGN, 4
PROBE__psc_stats__jp_state__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_sigpending__OFF
	.align	2
	.type	PROBE__psc_stats__jp_sigpending__OFF, @object
	.size	PROBE__psc_stats__jp_sigpending__OFF, 4
PROBE__psc_stats__jp_sigpending__OFF:
	.word	228
	.globl	PROBE__psc_stats__jp_sigpending__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_sigpending__ESZ, @object
	.size	PROBE__psc_stats__jp_sigpending__ESZ, 4
PROBE__psc_stats__jp_sigpending__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_sigpending__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_sigpending__TSZ, @object
	.size	PROBE__psc_stats__jp_sigpending__TSZ, 4
PROBE__psc_stats__jp_sigpending__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_sigpending__SGN
	.align	2
	.type	PROBE__psc_stats__jp_sigpending__SGN, @object
	.size	PROBE__psc_stats__jp_sigpending__SGN, 4
PROBE__psc_stats__jp_sigpending__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_sigword__OFF
	.align	2
	.type	PROBE__psc_stats__jp_sigword__OFF, @object
	.size	PROBE__psc_stats__jp_sigword__OFF, 4
PROBE__psc_stats__jp_sigword__OFF:
	.word	232
	.globl	PROBE__psc_stats__jp_sigword__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_sigword__ESZ, @object
	.size	PROBE__psc_stats__jp_sigword__ESZ, 4
PROBE__psc_stats__jp_sigword__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_sigword__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_sigword__TSZ, @object
	.size	PROBE__psc_stats__jp_sigword__TSZ, 4
PROBE__psc_stats__jp_sigword__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_sigword__SGN
	.align	2
	.type	PROBE__psc_stats__jp_sigword__SGN, @object
	.size	PROBE__psc_stats__jp_sigword__SGN, 4
PROBE__psc_stats__jp_sigword__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_nivcsw__OFF
	.align	2
	.type	PROBE__psc_stats__jp_nivcsw__OFF, @object
	.size	PROBE__psc_stats__jp_nivcsw__OFF, 4
PROBE__psc_stats__jp_nivcsw__OFF:
	.word	236
	.globl	PROBE__psc_stats__jp_nivcsw__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_nivcsw__ESZ, @object
	.size	PROBE__psc_stats__jp_nivcsw__ESZ, 4
PROBE__psc_stats__jp_nivcsw__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_nivcsw__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_nivcsw__TSZ, @object
	.size	PROBE__psc_stats__jp_nivcsw__TSZ, 4
PROBE__psc_stats__jp_nivcsw__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_nivcsw__SGN
	.align	2
	.type	PROBE__psc_stats__jp_nivcsw__SGN, @object
	.size	PROBE__psc_stats__jp_nivcsw__SGN, 4
PROBE__psc_stats__jp_nivcsw__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_keys__OFF
	.align	2
	.type	PROBE__psc_stats__jp_keys__OFF, @object
	.size	PROBE__psc_stats__jp_keys__OFF, 4
PROBE__psc_stats__jp_keys__OFF:
	.word	240
	.globl	PROBE__psc_stats__jp_keys__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_keys__ESZ, @object
	.size	PROBE__psc_stats__jp_keys__ESZ, 4
PROBE__psc_stats__jp_keys__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_keys__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_keys__TSZ, @object
	.size	PROBE__psc_stats__jp_keys__TSZ, 4
PROBE__psc_stats__jp_keys__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_keys__SGN
	.align	2
	.type	PROBE__psc_stats__jp_keys__SGN, @object
	.size	PROBE__psc_stats__jp_keys__SGN, 4
PROBE__psc_stats__jp_keys__SGN:
	.space	4
	.globl	PROBE__psc_stats__console_blanked__OFF
	.align	2
	.type	PROBE__psc_stats__console_blanked__OFF, @object
	.size	PROBE__psc_stats__console_blanked__OFF, 4
PROBE__psc_stats__console_blanked__OFF:
	.word	244
	.globl	PROBE__psc_stats__console_blanked__ESZ
	.align	2
	.type	PROBE__psc_stats__console_blanked__ESZ, @object
	.size	PROBE__psc_stats__console_blanked__ESZ, 4
PROBE__psc_stats__console_blanked__ESZ:
	.word	4
	.globl	PROBE__psc_stats__console_blanked__TSZ
	.align	2
	.type	PROBE__psc_stats__console_blanked__TSZ, @object
	.size	PROBE__psc_stats__console_blanked__TSZ, 4
PROBE__psc_stats__console_blanked__TSZ:
	.word	4
	.globl	PROBE__psc_stats__console_blanked__SGN
	.align	2
	.type	PROBE__psc_stats__console_blanked__SGN, @object
	.size	PROBE__psc_stats__console_blanked__SGN, 4
PROBE__psc_stats__console_blanked__SGN:
	.space	4
	.globl	PROBE__psc_stats__console_sem_count__OFF
	.align	2
	.type	PROBE__psc_stats__console_sem_count__OFF, @object
	.size	PROBE__psc_stats__console_sem_count__OFF, 4
PROBE__psc_stats__console_sem_count__OFF:
	.word	248
	.globl	PROBE__psc_stats__console_sem_count__ESZ
	.align	2
	.type	PROBE__psc_stats__console_sem_count__ESZ, @object
	.size	PROBE__psc_stats__console_sem_count__ESZ, 4
PROBE__psc_stats__console_sem_count__ESZ:
	.word	4
	.globl	PROBE__psc_stats__console_sem_count__TSZ
	.align	2
	.type	PROBE__psc_stats__console_sem_count__TSZ, @object
	.size	PROBE__psc_stats__console_sem_count__TSZ, 4
PROBE__psc_stats__console_sem_count__TSZ:
	.word	4
	.globl	PROBE__psc_stats__console_sem_count__SGN
	.align	2
	.type	PROBE__psc_stats__console_sem_count__SGN, @object
	.size	PROBE__psc_stats__console_sem_count__SGN, 4
PROBE__psc_stats__console_sem_count__SGN:
	.word	1
	.globl	PROBE__psc_stats__list_sem_count__OFF
	.align	2
	.type	PROBE__psc_stats__list_sem_count__OFF, @object
	.size	PROBE__psc_stats__list_sem_count__OFF, 4
PROBE__psc_stats__list_sem_count__OFF:
	.word	252
	.globl	PROBE__psc_stats__list_sem_count__ESZ
	.align	2
	.type	PROBE__psc_stats__list_sem_count__ESZ, @object
	.size	PROBE__psc_stats__list_sem_count__ESZ, 4
PROBE__psc_stats__list_sem_count__ESZ:
	.word	4
	.globl	PROBE__psc_stats__list_sem_count__TSZ
	.align	2
	.type	PROBE__psc_stats__list_sem_count__TSZ, @object
	.size	PROBE__psc_stats__list_sem_count__TSZ, 4
PROBE__psc_stats__list_sem_count__TSZ:
	.word	4
	.globl	PROBE__psc_stats__list_sem_count__SGN
	.align	2
	.type	PROBE__psc_stats__list_sem_count__SGN, @object
	.size	PROBE__psc_stats__list_sem_count__SGN, 4
PROBE__psc_stats__list_sem_count__SGN:
	.word	1
	.globl	PROBE__psc_stats__t_busy__OFF
	.align	2
	.type	PROBE__psc_stats__t_busy__OFF, @object
	.size	PROBE__psc_stats__t_busy__OFF, 4
PROBE__psc_stats__t_busy__OFF:
	.word	256
	.globl	PROBE__psc_stats__t_busy__ESZ
	.align	2
	.type	PROBE__psc_stats__t_busy__ESZ, @object
	.size	PROBE__psc_stats__t_busy__ESZ, 4
PROBE__psc_stats__t_busy__ESZ:
	.word	4
	.globl	PROBE__psc_stats__t_busy__TSZ
	.align	2
	.type	PROBE__psc_stats__t_busy__TSZ, @object
	.size	PROBE__psc_stats__t_busy__TSZ, 4
PROBE__psc_stats__t_busy__TSZ:
	.word	4
	.globl	PROBE__psc_stats__t_busy__SGN
	.align	2
	.type	PROBE__psc_stats__t_busy__SGN, @object
	.size	PROBE__psc_stats__t_busy__SGN, 4
PROBE__psc_stats__t_busy__SGN:
	.space	4
	.globl	PROBE__psc_stats__t_cmd__OFF
	.align	2
	.type	PROBE__psc_stats__t_cmd__OFF, @object
	.size	PROBE__psc_stats__t_cmd__OFF, 4
PROBE__psc_stats__t_cmd__OFF:
	.word	260
	.globl	PROBE__psc_stats__t_cmd__ESZ
	.align	2
	.type	PROBE__psc_stats__t_cmd__ESZ, @object
	.size	PROBE__psc_stats__t_cmd__ESZ, 4
PROBE__psc_stats__t_cmd__ESZ:
	.word	4
	.globl	PROBE__psc_stats__t_cmd__TSZ
	.align	2
	.type	PROBE__psc_stats__t_cmd__TSZ, @object
	.size	PROBE__psc_stats__t_cmd__TSZ, 4
PROBE__psc_stats__t_cmd__TSZ:
	.word	4
	.globl	PROBE__psc_stats__t_cmd__SGN
	.align	2
	.type	PROBE__psc_stats__t_cmd__SGN, @object
	.size	PROBE__psc_stats__t_cmd__SGN, 4
PROBE__psc_stats__t_cmd__SGN:
	.space	4
	.globl	PROBE__psc_stats__t_entry_tick__OFF
	.align	2
	.type	PROBE__psc_stats__t_entry_tick__OFF, @object
	.size	PROBE__psc_stats__t_entry_tick__OFF, 4
PROBE__psc_stats__t_entry_tick__OFF:
	.word	264
	.globl	PROBE__psc_stats__t_entry_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__t_entry_tick__ESZ, @object
	.size	PROBE__psc_stats__t_entry_tick__ESZ, 4
PROBE__psc_stats__t_entry_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__t_entry_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__t_entry_tick__TSZ, @object
	.size	PROBE__psc_stats__t_entry_tick__TSZ, 4
PROBE__psc_stats__t_entry_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__t_entry_tick__SGN
	.align	2
	.type	PROBE__psc_stats__t_entry_tick__SGN, @object
	.size	PROBE__psc_stats__t_entry_tick__SGN, 4
PROBE__psc_stats__t_entry_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__t_entry_c__OFF
	.align	2
	.type	PROBE__psc_stats__t_entry_c__OFF, @object
	.size	PROBE__psc_stats__t_entry_c__OFF, 4
PROBE__psc_stats__t_entry_c__OFF:
	.word	268
	.globl	PROBE__psc_stats__t_entry_c__ESZ
	.align	2
	.type	PROBE__psc_stats__t_entry_c__ESZ, @object
	.size	PROBE__psc_stats__t_entry_c__ESZ, 4
PROBE__psc_stats__t_entry_c__ESZ:
	.word	4
	.globl	PROBE__psc_stats__t_entry_c__TSZ
	.align	2
	.type	PROBE__psc_stats__t_entry_c__TSZ, @object
	.size	PROBE__psc_stats__t_entry_c__TSZ, 4
PROBE__psc_stats__t_entry_c__TSZ:
	.word	4
	.globl	PROBE__psc_stats__t_entry_c__SGN
	.align	2
	.type	PROBE__psc_stats__t_entry_c__SGN, @object
	.size	PROBE__psc_stats__t_entry_c__SGN, 4
PROBE__psc_stats__t_entry_c__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_r3__OFF
	.align	2
	.type	PROBE__psc_stats__jp_r3__OFF, @object
	.size	PROBE__psc_stats__jp_r3__OFF, 4
PROBE__psc_stats__jp_r3__OFF:
	.word	272
	.globl	PROBE__psc_stats__jp_r3__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_r3__ESZ, @object
	.size	PROBE__psc_stats__jp_r3__ESZ, 4
PROBE__psc_stats__jp_r3__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_r3__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_r3__TSZ, @object
	.size	PROBE__psc_stats__jp_r3__TSZ, 4
PROBE__psc_stats__jp_r3__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_r3__SGN
	.align	2
	.type	PROBE__psc_stats__jp_r3__SGN, @object
	.size	PROBE__psc_stats__jp_r3__SGN, 4
PROBE__psc_stats__jp_r3__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_r4__OFF
	.align	2
	.type	PROBE__psc_stats__jp_r4__OFF, @object
	.size	PROBE__psc_stats__jp_r4__OFF, 4
PROBE__psc_stats__jp_r4__OFF:
	.word	276
	.globl	PROBE__psc_stats__jp_r4__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_r4__ESZ, @object
	.size	PROBE__psc_stats__jp_r4__ESZ, 4
PROBE__psc_stats__jp_r4__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_r4__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_r4__TSZ, @object
	.size	PROBE__psc_stats__jp_r4__TSZ, 4
PROBE__psc_stats__jp_r4__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_r4__SGN
	.align	2
	.type	PROBE__psc_stats__jp_r4__SGN, @object
	.size	PROBE__psc_stats__jp_r4__SGN, 4
PROBE__psc_stats__jp_r4__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_r5__OFF
	.align	2
	.type	PROBE__psc_stats__jp_r5__OFF, @object
	.size	PROBE__psc_stats__jp_r5__OFF, 4
PROBE__psc_stats__jp_r5__OFF:
	.word	280
	.globl	PROBE__psc_stats__jp_r5__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_r5__ESZ, @object
	.size	PROBE__psc_stats__jp_r5__ESZ, 4
PROBE__psc_stats__jp_r5__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_r5__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_r5__TSZ, @object
	.size	PROBE__psc_stats__jp_r5__TSZ, 4
PROBE__psc_stats__jp_r5__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_r5__SGN
	.align	2
	.type	PROBE__psc_stats__jp_r5__SGN, @object
	.size	PROBE__psc_stats__jp_r5__SGN, 4
PROBE__psc_stats__jp_r5__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_proc_calls__OFF
	.align	2
	.type	PROBE__psc_stats__jp_proc_calls__OFF, @object
	.size	PROBE__psc_stats__jp_proc_calls__OFF, 4
PROBE__psc_stats__jp_proc_calls__OFF:
	.word	284
	.globl	PROBE__psc_stats__jp_proc_calls__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_proc_calls__ESZ, @object
	.size	PROBE__psc_stats__jp_proc_calls__ESZ, 4
PROBE__psc_stats__jp_proc_calls__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_proc_calls__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_proc_calls__TSZ, @object
	.size	PROBE__psc_stats__jp_proc_calls__TSZ, 4
PROBE__psc_stats__jp_proc_calls__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_proc_calls__SGN
	.align	2
	.type	PROBE__psc_stats__jp_proc_calls__SGN, @object
	.size	PROBE__psc_stats__jp_proc_calls__SGN, 4
PROBE__psc_stats__jp_proc_calls__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_dedupe__OFF
	.align	2
	.type	PROBE__psc_stats__jp_dedupe__OFF, @object
	.size	PROBE__psc_stats__jp_dedupe__OFF, 4
PROBE__psc_stats__jp_dedupe__OFF:
	.word	288
	.globl	PROBE__psc_stats__jp_dedupe__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_dedupe__ESZ, @object
	.size	PROBE__psc_stats__jp_dedupe__ESZ, 4
PROBE__psc_stats__jp_dedupe__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_dedupe__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_dedupe__TSZ, @object
	.size	PROBE__psc_stats__jp_dedupe__TSZ, 4
PROBE__psc_stats__jp_dedupe__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_dedupe__SGN
	.align	2
	.type	PROBE__psc_stats__jp_dedupe__SGN, @object
	.size	PROBE__psc_stats__jp_dedupe__SGN, 4
PROBE__psc_stats__jp_dedupe__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_changed__OFF
	.align	2
	.type	PROBE__psc_stats__jp_changed__OFF, @object
	.size	PROBE__psc_stats__jp_changed__OFF, 4
PROBE__psc_stats__jp_changed__OFF:
	.word	292
	.globl	PROBE__psc_stats__jp_changed__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_changed__ESZ, @object
	.size	PROBE__psc_stats__jp_changed__ESZ, 4
PROBE__psc_stats__jp_changed__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_changed__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_changed__TSZ, @object
	.size	PROBE__psc_stats__jp_changed__TSZ, 4
PROBE__psc_stats__jp_changed__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_changed__SGN
	.align	2
	.type	PROBE__psc_stats__jp_changed__SGN, @object
	.size	PROBE__psc_stats__jp_changed__SGN, 4
PROBE__psc_stats__jp_changed__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_lcd_unblank__OFF
	.align	2
	.type	PROBE__psc_stats__jp_lcd_unblank__OFF, @object
	.size	PROBE__psc_stats__jp_lcd_unblank__OFF, 4
PROBE__psc_stats__jp_lcd_unblank__OFF:
	.word	296
	.globl	PROBE__psc_stats__jp_lcd_unblank__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_lcd_unblank__ESZ, @object
	.size	PROBE__psc_stats__jp_lcd_unblank__ESZ, 4
PROBE__psc_stats__jp_lcd_unblank__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_lcd_unblank__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_lcd_unblank__TSZ, @object
	.size	PROBE__psc_stats__jp_lcd_unblank__TSZ, 4
PROBE__psc_stats__jp_lcd_unblank__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_lcd_unblank__SGN
	.align	2
	.type	PROBE__psc_stats__jp_lcd_unblank__SGN, @object
	.size	PROBE__psc_stats__jp_lcd_unblank__SGN, 4
PROBE__psc_stats__jp_lcd_unblank__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_mode_toggles__OFF
	.align	2
	.type	PROBE__psc_stats__jp_mode_toggles__OFF, @object
	.size	PROBE__psc_stats__jp_mode_toggles__OFF, 4
PROBE__psc_stats__jp_mode_toggles__OFF:
	.word	300
	.globl	PROBE__psc_stats__jp_mode_toggles__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_mode_toggles__ESZ, @object
	.size	PROBE__psc_stats__jp_mode_toggles__ESZ, 4
PROBE__psc_stats__jp_mode_toggles__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mode_toggles__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_mode_toggles__TSZ, @object
	.size	PROBE__psc_stats__jp_mode_toggles__TSZ, 4
PROBE__psc_stats__jp_mode_toggles__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mode_toggles__SGN
	.align	2
	.type	PROBE__psc_stats__jp_mode_toggles__SGN, @object
	.size	PROBE__psc_stats__jp_mode_toggles__SGN, 4
PROBE__psc_stats__jp_mode_toggles__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_listsem_fail__OFF
	.align	2
	.type	PROBE__psc_stats__jp_listsem_fail__OFF, @object
	.size	PROBE__psc_stats__jp_listsem_fail__OFF, 4
PROBE__psc_stats__jp_listsem_fail__OFF:
	.word	304
	.globl	PROBE__psc_stats__jp_listsem_fail__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_listsem_fail__ESZ, @object
	.size	PROBE__psc_stats__jp_listsem_fail__ESZ, 4
PROBE__psc_stats__jp_listsem_fail__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_listsem_fail__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_listsem_fail__TSZ, @object
	.size	PROBE__psc_stats__jp_listsem_fail__TSZ, 4
PROBE__psc_stats__jp_listsem_fail__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_listsem_fail__SGN
	.align	2
	.type	PROBE__psc_stats__jp_listsem_fail__SGN, @object
	.size	PROBE__psc_stats__jp_listsem_fail__SGN, 4
PROBE__psc_stats__jp_listsem_fail__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_push_ok__OFF
	.align	2
	.type	PROBE__psc_stats__jp_push_ok__OFF, @object
	.size	PROBE__psc_stats__jp_push_ok__OFF, 4
PROBE__psc_stats__jp_push_ok__OFF:
	.word	308
	.globl	PROBE__psc_stats__jp_push_ok__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_push_ok__ESZ, @object
	.size	PROBE__psc_stats__jp_push_ok__ESZ, 4
PROBE__psc_stats__jp_push_ok__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_push_ok__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_push_ok__TSZ, @object
	.size	PROBE__psc_stats__jp_push_ok__TSZ, 4
PROBE__psc_stats__jp_push_ok__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_push_ok__SGN
	.align	2
	.type	PROBE__psc_stats__jp_push_ok__SGN, @object
	.size	PROBE__psc_stats__jp_push_ok__SGN, 4
PROBE__psc_stats__jp_push_ok__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_push_full__OFF
	.align	2
	.type	PROBE__psc_stats__jp_push_full__OFF, @object
	.size	PROBE__psc_stats__jp_push_full__OFF, 4
PROBE__psc_stats__jp_push_full__OFF:
	.word	312
	.globl	PROBE__psc_stats__jp_push_full__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_push_full__ESZ, @object
	.size	PROBE__psc_stats__jp_push_full__ESZ, 4
PROBE__psc_stats__jp_push_full__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_push_full__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_push_full__TSZ, @object
	.size	PROBE__psc_stats__jp_push_full__TSZ, 4
PROBE__psc_stats__jp_push_full__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_push_full__SGN
	.align	2
	.type	PROBE__psc_stats__jp_push_full__SGN, @object
	.size	PROBE__psc_stats__jp_push_full__SGN, 4
PROBE__psc_stats__jp_push_full__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_push_eintr__OFF
	.align	2
	.type	PROBE__psc_stats__jp_push_eintr__OFF, @object
	.size	PROBE__psc_stats__jp_push_eintr__OFF, 4
PROBE__psc_stats__jp_push_eintr__OFF:
	.word	316
	.globl	PROBE__psc_stats__jp_push_eintr__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_push_eintr__ESZ, @object
	.size	PROBE__psc_stats__jp_push_eintr__ESZ, 4
PROBE__psc_stats__jp_push_eintr__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_push_eintr__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_push_eintr__TSZ, @object
	.size	PROBE__psc_stats__jp_push_eintr__TSZ, 4
PROBE__psc_stats__jp_push_eintr__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_push_eintr__SGN
	.align	2
	.type	PROBE__psc_stats__jp_push_eintr__SGN, @object
	.size	PROBE__psc_stats__jp_push_eintr__SGN, 4
PROBE__psc_stats__jp_push_eintr__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_wake__OFF
	.align	2
	.type	PROBE__psc_stats__jp_wake__OFF, @object
	.size	PROBE__psc_stats__jp_wake__OFF, 4
PROBE__psc_stats__jp_wake__OFF:
	.word	320
	.globl	PROBE__psc_stats__jp_wake__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_wake__ESZ, @object
	.size	PROBE__psc_stats__jp_wake__ESZ, 4
PROBE__psc_stats__jp_wake__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_wake__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_wake__TSZ, @object
	.size	PROBE__psc_stats__jp_wake__TSZ, 4
PROBE__psc_stats__jp_wake__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_wake__SGN
	.align	2
	.type	PROBE__psc_stats__jp_wake__SGN, @object
	.size	PROBE__psc_stats__jp_wake__SGN, 4
PROBE__psc_stats__jp_wake__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_mouse_calls__OFF
	.align	2
	.type	PROBE__psc_stats__jp_mouse_calls__OFF, @object
	.size	PROBE__psc_stats__jp_mouse_calls__OFF, 4
PROBE__psc_stats__jp_mouse_calls__OFF:
	.word	324
	.globl	PROBE__psc_stats__jp_mouse_calls__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_mouse_calls__ESZ, @object
	.size	PROBE__psc_stats__jp_mouse_calls__ESZ, 4
PROBE__psc_stats__jp_mouse_calls__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mouse_calls__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_mouse_calls__TSZ, @object
	.size	PROBE__psc_stats__jp_mouse_calls__TSZ, 4
PROBE__psc_stats__jp_mouse_calls__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mouse_calls__SGN
	.align	2
	.type	PROBE__psc_stats__jp_mouse_calls__SGN, @object
	.size	PROBE__psc_stats__jp_mouse_calls__SGN, 4
PROBE__psc_stats__jp_mouse_calls__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_mouse_noop__OFF
	.align	2
	.type	PROBE__psc_stats__jp_mouse_noop__OFF, @object
	.size	PROBE__psc_stats__jp_mouse_noop__OFF, 4
PROBE__psc_stats__jp_mouse_noop__OFF:
	.word	328
	.globl	PROBE__psc_stats__jp_mouse_noop__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_mouse_noop__ESZ, @object
	.size	PROBE__psc_stats__jp_mouse_noop__ESZ, 4
PROBE__psc_stats__jp_mouse_noop__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mouse_noop__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_mouse_noop__TSZ, @object
	.size	PROBE__psc_stats__jp_mouse_noop__TSZ, 4
PROBE__psc_stats__jp_mouse_noop__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mouse_noop__SGN
	.align	2
	.type	PROBE__psc_stats__jp_mouse_noop__SGN, @object
	.size	PROBE__psc_stats__jp_mouse_noop__SGN, 4
PROBE__psc_stats__jp_mouse_noop__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_mouse_reports__OFF
	.align	2
	.type	PROBE__psc_stats__jp_mouse_reports__OFF, @object
	.size	PROBE__psc_stats__jp_mouse_reports__OFF, 4
PROBE__psc_stats__jp_mouse_reports__OFF:
	.word	332
	.globl	PROBE__psc_stats__jp_mouse_reports__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_mouse_reports__ESZ, @object
	.size	PROBE__psc_stats__jp_mouse_reports__ESZ, 4
PROBE__psc_stats__jp_mouse_reports__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mouse_reports__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_mouse_reports__TSZ, @object
	.size	PROBE__psc_stats__jp_mouse_reports__TSZ, 4
PROBE__psc_stats__jp_mouse_reports__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_mouse_reports__SGN
	.align	2
	.type	PROBE__psc_stats__jp_mouse_reports__SGN, @object
	.size	PROBE__psc_stats__jp_mouse_reports__SGN, 4
PROBE__psc_stats__jp_mouse_reports__SGN:
	.space	4
	.globl	PROBE__psc_stats__fop_open__OFF
	.align	2
	.type	PROBE__psc_stats__fop_open__OFF, @object
	.size	PROBE__psc_stats__fop_open__OFF, 4
PROBE__psc_stats__fop_open__OFF:
	.word	336
	.globl	PROBE__psc_stats__fop_open__ESZ
	.align	2
	.type	PROBE__psc_stats__fop_open__ESZ, @object
	.size	PROBE__psc_stats__fop_open__ESZ, 4
PROBE__psc_stats__fop_open__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fop_open__TSZ
	.align	2
	.type	PROBE__psc_stats__fop_open__TSZ, @object
	.size	PROBE__psc_stats__fop_open__TSZ, 4
PROBE__psc_stats__fop_open__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fop_open__SGN
	.align	2
	.type	PROBE__psc_stats__fop_open__SGN, @object
	.size	PROBE__psc_stats__fop_open__SGN, 4
PROBE__psc_stats__fop_open__SGN:
	.space	4
	.globl	PROBE__psc_stats__fop_release__OFF
	.align	2
	.type	PROBE__psc_stats__fop_release__OFF, @object
	.size	PROBE__psc_stats__fop_release__OFF, 4
PROBE__psc_stats__fop_release__OFF:
	.word	340
	.globl	PROBE__psc_stats__fop_release__ESZ
	.align	2
	.type	PROBE__psc_stats__fop_release__ESZ, @object
	.size	PROBE__psc_stats__fop_release__ESZ, 4
PROBE__psc_stats__fop_release__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fop_release__TSZ
	.align	2
	.type	PROBE__psc_stats__fop_release__TSZ, @object
	.size	PROBE__psc_stats__fop_release__TSZ, 4
PROBE__psc_stats__fop_release__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fop_release__SGN
	.align	2
	.type	PROBE__psc_stats__fop_release__SGN, @object
	.size	PROBE__psc_stats__fop_release__SGN, 4
PROBE__psc_stats__fop_release__SGN:
	.space	4
	.globl	PROBE__psc_stats__fop_read_enter__OFF
	.align	2
	.type	PROBE__psc_stats__fop_read_enter__OFF, @object
	.size	PROBE__psc_stats__fop_read_enter__OFF, 4
PROBE__psc_stats__fop_read_enter__OFF:
	.word	344
	.globl	PROBE__psc_stats__fop_read_enter__ESZ
	.align	2
	.type	PROBE__psc_stats__fop_read_enter__ESZ, @object
	.size	PROBE__psc_stats__fop_read_enter__ESZ, 4
PROBE__psc_stats__fop_read_enter__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fop_read_enter__TSZ
	.align	2
	.type	PROBE__psc_stats__fop_read_enter__TSZ, @object
	.size	PROBE__psc_stats__fop_read_enter__TSZ, 4
PROBE__psc_stats__fop_read_enter__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fop_read_enter__SGN
	.align	2
	.type	PROBE__psc_stats__fop_read_enter__SGN, @object
	.size	PROBE__psc_stats__fop_read_enter__SGN, 4
PROBE__psc_stats__fop_read_enter__SGN:
	.space	4
	.globl	PROBE__psc_stats__fop_read_ret__OFF
	.align	2
	.type	PROBE__psc_stats__fop_read_ret__OFF, @object
	.size	PROBE__psc_stats__fop_read_ret__OFF, 4
PROBE__psc_stats__fop_read_ret__OFF:
	.word	348
	.globl	PROBE__psc_stats__fop_read_ret__ESZ
	.align	2
	.type	PROBE__psc_stats__fop_read_ret__ESZ, @object
	.size	PROBE__psc_stats__fop_read_ret__ESZ, 4
PROBE__psc_stats__fop_read_ret__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fop_read_ret__TSZ
	.align	2
	.type	PROBE__psc_stats__fop_read_ret__TSZ, @object
	.size	PROBE__psc_stats__fop_read_ret__TSZ, 4
PROBE__psc_stats__fop_read_ret__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fop_read_ret__SGN
	.align	2
	.type	PROBE__psc_stats__fop_read_ret__SGN, @object
	.size	PROBE__psc_stats__fop_read_ret__SGN, 4
PROBE__psc_stats__fop_read_ret__SGN:
	.space	4
	.globl	PROBE__psc_stats__fop_read_eintr__OFF
	.align	2
	.type	PROBE__psc_stats__fop_read_eintr__OFF, @object
	.size	PROBE__psc_stats__fop_read_eintr__OFF, 4
PROBE__psc_stats__fop_read_eintr__OFF:
	.word	352
	.globl	PROBE__psc_stats__fop_read_eintr__ESZ
	.align	2
	.type	PROBE__psc_stats__fop_read_eintr__ESZ, @object
	.size	PROBE__psc_stats__fop_read_eintr__ESZ, 4
PROBE__psc_stats__fop_read_eintr__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fop_read_eintr__TSZ
	.align	2
	.type	PROBE__psc_stats__fop_read_eintr__TSZ, @object
	.size	PROBE__psc_stats__fop_read_eintr__TSZ, 4
PROBE__psc_stats__fop_read_eintr__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fop_read_eintr__SGN
	.align	2
	.type	PROBE__psc_stats__fop_read_eintr__SGN, @object
	.size	PROBE__psc_stats__fop_read_eintr__SGN, 4
PROBE__psc_stats__fop_read_eintr__SGN:
	.space	4
	.globl	PROBE__psc_stats__fop_ioctl__OFF
	.align	2
	.type	PROBE__psc_stats__fop_ioctl__OFF, @object
	.size	PROBE__psc_stats__fop_ioctl__OFF, 4
PROBE__psc_stats__fop_ioctl__OFF:
	.word	356
	.globl	PROBE__psc_stats__fop_ioctl__ESZ
	.align	2
	.type	PROBE__psc_stats__fop_ioctl__ESZ, @object
	.size	PROBE__psc_stats__fop_ioctl__ESZ, 4
PROBE__psc_stats__fop_ioctl__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fop_ioctl__TSZ
	.align	2
	.type	PROBE__psc_stats__fop_ioctl__TSZ, @object
	.size	PROBE__psc_stats__fop_ioctl__TSZ, 4
PROBE__psc_stats__fop_ioctl__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fop_ioctl__SGN
	.align	2
	.type	PROBE__psc_stats__fop_ioctl__SGN, @object
	.size	PROBE__psc_stats__fop_ioctl__SGN, 4
PROBE__psc_stats__fop_ioctl__SGN:
	.space	4
	.globl	PROBE__psc_stats__qfree_stage__OFF
	.align	2
	.type	PROBE__psc_stats__qfree_stage__OFF, @object
	.size	PROBE__psc_stats__qfree_stage__OFF, 4
PROBE__psc_stats__qfree_stage__OFF:
	.word	360
	.globl	PROBE__psc_stats__qfree_stage__ESZ
	.align	2
	.type	PROBE__psc_stats__qfree_stage__ESZ, @object
	.size	PROBE__psc_stats__qfree_stage__ESZ, 4
PROBE__psc_stats__qfree_stage__ESZ:
	.word	4
	.globl	PROBE__psc_stats__qfree_stage__TSZ
	.align	2
	.type	PROBE__psc_stats__qfree_stage__TSZ, @object
	.size	PROBE__psc_stats__qfree_stage__TSZ, 4
PROBE__psc_stats__qfree_stage__TSZ:
	.word	4
	.globl	PROBE__psc_stats__qfree_stage__SGN
	.align	2
	.type	PROBE__psc_stats__qfree_stage__SGN, @object
	.size	PROBE__psc_stats__qfree_stage__SGN, 4
PROBE__psc_stats__qfree_stage__SGN:
	.space	4
	.globl	PROBE__psc_stats__qfree_queue__OFF
	.align	2
	.type	PROBE__psc_stats__qfree_queue__OFF, @object
	.size	PROBE__psc_stats__qfree_queue__OFF, 4
PROBE__psc_stats__qfree_queue__OFF:
	.word	364
	.globl	PROBE__psc_stats__qfree_queue__ESZ
	.align	2
	.type	PROBE__psc_stats__qfree_queue__ESZ, @object
	.size	PROBE__psc_stats__qfree_queue__ESZ, 4
PROBE__psc_stats__qfree_queue__ESZ:
	.word	4
	.globl	PROBE__psc_stats__qfree_queue__TSZ
	.align	2
	.type	PROBE__psc_stats__qfree_queue__TSZ, @object
	.size	PROBE__psc_stats__qfree_queue__TSZ, 4
PROBE__psc_stats__qfree_queue__TSZ:
	.word	4
	.globl	PROBE__psc_stats__qfree_queue__SGN
	.align	2
	.type	PROBE__psc_stats__qfree_queue__SGN, @object
	.size	PROBE__psc_stats__qfree_queue__SGN, 4
PROBE__psc_stats__qfree_queue__SGN:
	.space	4
	.globl	PROBE__psc_stats__qfree_pid__OFF
	.align	2
	.type	PROBE__psc_stats__qfree_pid__OFF, @object
	.size	PROBE__psc_stats__qfree_pid__OFF, 4
PROBE__psc_stats__qfree_pid__OFF:
	.word	368
	.globl	PROBE__psc_stats__qfree_pid__ESZ
	.align	2
	.type	PROBE__psc_stats__qfree_pid__ESZ, @object
	.size	PROBE__psc_stats__qfree_pid__ESZ, 4
PROBE__psc_stats__qfree_pid__ESZ:
	.word	4
	.globl	PROBE__psc_stats__qfree_pid__TSZ
	.align	2
	.type	PROBE__psc_stats__qfree_pid__TSZ, @object
	.size	PROBE__psc_stats__qfree_pid__TSZ, 4
PROBE__psc_stats__qfree_pid__TSZ:
	.word	4
	.globl	PROBE__psc_stats__qfree_pid__SGN
	.align	2
	.type	PROBE__psc_stats__qfree_pid__SGN, @object
	.size	PROBE__psc_stats__qfree_pid__SGN, 4
PROBE__psc_stats__qfree_pid__SGN:
	.space	4
	.globl	PROBE__psc_stats__vcs_putchar__OFF
	.align	2
	.type	PROBE__psc_stats__vcs_putchar__OFF, @object
	.size	PROBE__psc_stats__vcs_putchar__OFF, 4
PROBE__psc_stats__vcs_putchar__OFF:
	.word	372
	.globl	PROBE__psc_stats__vcs_putchar__ESZ
	.align	2
	.type	PROBE__psc_stats__vcs_putchar__ESZ, @object
	.size	PROBE__psc_stats__vcs_putchar__ESZ, 4
PROBE__psc_stats__vcs_putchar__ESZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_putchar__TSZ
	.align	2
	.type	PROBE__psc_stats__vcs_putchar__TSZ, @object
	.size	PROBE__psc_stats__vcs_putchar__TSZ, 4
PROBE__psc_stats__vcs_putchar__TSZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_putchar__SGN
	.align	2
	.type	PROBE__psc_stats__vcs_putchar__SGN, @object
	.size	PROBE__psc_stats__vcs_putchar__SGN, 4
PROBE__psc_stats__vcs_putchar__SGN:
	.space	4
	.globl	PROBE__psc_stats__vcs_changecon__OFF
	.align	2
	.type	PROBE__psc_stats__vcs_changecon__OFF, @object
	.size	PROBE__psc_stats__vcs_changecon__OFF, 4
PROBE__psc_stats__vcs_changecon__OFF:
	.word	376
	.globl	PROBE__psc_stats__vcs_changecon__ESZ
	.align	2
	.type	PROBE__psc_stats__vcs_changecon__ESZ, @object
	.size	PROBE__psc_stats__vcs_changecon__ESZ, 4
PROBE__psc_stats__vcs_changecon__ESZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_changecon__TSZ
	.align	2
	.type	PROBE__psc_stats__vcs_changecon__TSZ, @object
	.size	PROBE__psc_stats__vcs_changecon__TSZ, 4
PROBE__psc_stats__vcs_changecon__TSZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_changecon__SGN
	.align	2
	.type	PROBE__psc_stats__vcs_changecon__SGN, @object
	.size	PROBE__psc_stats__vcs_changecon__SGN, 4
PROBE__psc_stats__vcs_changecon__SGN:
	.space	4
	.globl	PROBE__psc_stats__vcs_updscr__OFF
	.align	2
	.type	PROBE__psc_stats__vcs_updscr__OFF, @object
	.size	PROBE__psc_stats__vcs_updscr__OFF, 4
PROBE__psc_stats__vcs_updscr__OFF:
	.word	380
	.globl	PROBE__psc_stats__vcs_updscr__ESZ
	.align	2
	.type	PROBE__psc_stats__vcs_updscr__ESZ, @object
	.size	PROBE__psc_stats__vcs_updscr__ESZ, 4
PROBE__psc_stats__vcs_updscr__ESZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_updscr__TSZ
	.align	2
	.type	PROBE__psc_stats__vcs_updscr__TSZ, @object
	.size	PROBE__psc_stats__vcs_updscr__TSZ, 4
PROBE__psc_stats__vcs_updscr__TSZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_updscr__SGN
	.align	2
	.type	PROBE__psc_stats__vcs_updscr__SGN, @object
	.size	PROBE__psc_stats__vcs_updscr__SGN, 4
PROBE__psc_stats__vcs_updscr__SGN:
	.space	4
	.globl	PROBE__psc_stats__vcs_getsize__OFF
	.align	2
	.type	PROBE__psc_stats__vcs_getsize__OFF, @object
	.size	PROBE__psc_stats__vcs_getsize__OFF, 4
PROBE__psc_stats__vcs_getsize__OFF:
	.word	384
	.globl	PROBE__psc_stats__vcs_getsize__ESZ
	.align	2
	.type	PROBE__psc_stats__vcs_getsize__ESZ, @object
	.size	PROBE__psc_stats__vcs_getsize__ESZ, 4
PROBE__psc_stats__vcs_getsize__ESZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_getsize__TSZ
	.align	2
	.type	PROBE__psc_stats__vcs_getsize__TSZ, @object
	.size	PROBE__psc_stats__vcs_getsize__TSZ, 4
PROBE__psc_stats__vcs_getsize__TSZ:
	.word	4
	.globl	PROBE__psc_stats__vcs_getsize__SGN
	.align	2
	.type	PROBE__psc_stats__vcs_getsize__SGN, @object
	.size	PROBE__psc_stats__vcs_getsize__SGN, 4
PROBE__psc_stats__vcs_getsize__SGN:
	.space	4
	.globl	PROBE__psc_stats__md_event_syn__OFF
	.align	2
	.type	PROBE__psc_stats__md_event_syn__OFF, @object
	.size	PROBE__psc_stats__md_event_syn__OFF, 4
PROBE__psc_stats__md_event_syn__OFF:
	.word	388
	.globl	PROBE__psc_stats__md_event_syn__ESZ
	.align	2
	.type	PROBE__psc_stats__md_event_syn__ESZ, @object
	.size	PROBE__psc_stats__md_event_syn__ESZ, 4
PROBE__psc_stats__md_event_syn__ESZ:
	.word	4
	.globl	PROBE__psc_stats__md_event_syn__TSZ
	.align	2
	.type	PROBE__psc_stats__md_event_syn__TSZ, @object
	.size	PROBE__psc_stats__md_event_syn__TSZ, 4
PROBE__psc_stats__md_event_syn__TSZ:
	.word	4
	.globl	PROBE__psc_stats__md_event_syn__SGN
	.align	2
	.type	PROBE__psc_stats__md_event_syn__SGN, @object
	.size	PROBE__psc_stats__md_event_syn__SGN, 4
PROBE__psc_stats__md_event_syn__SGN:
	.space	4
	.globl	PROBE__psc_stats__md_notify_calls__OFF
	.align	2
	.type	PROBE__psc_stats__md_notify_calls__OFF, @object
	.size	PROBE__psc_stats__md_notify_calls__OFF, 4
PROBE__psc_stats__md_notify_calls__OFF:
	.word	392
	.globl	PROBE__psc_stats__md_notify_calls__ESZ
	.align	2
	.type	PROBE__psc_stats__md_notify_calls__ESZ, @object
	.size	PROBE__psc_stats__md_notify_calls__ESZ, 4
PROBE__psc_stats__md_notify_calls__ESZ:
	.word	4
	.globl	PROBE__psc_stats__md_notify_calls__TSZ
	.align	2
	.type	PROBE__psc_stats__md_notify_calls__TSZ, @object
	.size	PROBE__psc_stats__md_notify_calls__TSZ, 4
PROBE__psc_stats__md_notify_calls__TSZ:
	.word	4
	.globl	PROBE__psc_stats__md_notify_calls__SGN
	.align	2
	.type	PROBE__psc_stats__md_notify_calls__SGN, @object
	.size	PROBE__psc_stats__md_notify_calls__SGN, 4
PROBE__psc_stats__md_notify_calls__SGN:
	.space	4
	.globl	PROBE__psc_stats__md_read_ret__OFF
	.align	2
	.type	PROBE__psc_stats__md_read_ret__OFF, @object
	.size	PROBE__psc_stats__md_read_ret__OFF, 4
PROBE__psc_stats__md_read_ret__OFF:
	.word	396
	.globl	PROBE__psc_stats__md_read_ret__ESZ
	.align	2
	.type	PROBE__psc_stats__md_read_ret__ESZ, @object
	.size	PROBE__psc_stats__md_read_ret__ESZ, 4
PROBE__psc_stats__md_read_ret__ESZ:
	.word	4
	.globl	PROBE__psc_stats__md_read_ret__TSZ
	.align	2
	.type	PROBE__psc_stats__md_read_ret__TSZ, @object
	.size	PROBE__psc_stats__md_read_ret__TSZ, 4
PROBE__psc_stats__md_read_ret__TSZ:
	.word	4
	.globl	PROBE__psc_stats__md_read_ret__SGN
	.align	2
	.type	PROBE__psc_stats__md_read_ret__SGN, @object
	.size	PROBE__psc_stats__md_read_ret__SGN, 4
PROBE__psc_stats__md_read_ret__SGN:
	.space	4
	.globl	PROBE__psc_stats__led_calls__OFF
	.align	2
	.type	PROBE__psc_stats__led_calls__OFF, @object
	.size	PROBE__psc_stats__led_calls__OFF, 4
PROBE__psc_stats__led_calls__OFF:
	.word	400
	.globl	PROBE__psc_stats__led_calls__ESZ
	.align	2
	.type	PROBE__psc_stats__led_calls__ESZ, @object
	.size	PROBE__psc_stats__led_calls__ESZ, 4
PROBE__psc_stats__led_calls__ESZ:
	.word	4
	.globl	PROBE__psc_stats__led_calls__TSZ
	.align	2
	.type	PROBE__psc_stats__led_calls__TSZ, @object
	.size	PROBE__psc_stats__led_calls__TSZ, 4
PROBE__psc_stats__led_calls__TSZ:
	.word	4
	.globl	PROBE__psc_stats__led_calls__SGN
	.align	2
	.type	PROBE__psc_stats__led_calls__SGN, @object
	.size	PROBE__psc_stats__led_calls__SGN, 4
PROBE__psc_stats__led_calls__SGN:
	.space	4
	.globl	PROBE__psc_stats__led_calls_t_busy__OFF
	.align	2
	.type	PROBE__psc_stats__led_calls_t_busy__OFF, @object
	.size	PROBE__psc_stats__led_calls_t_busy__OFF, 4
PROBE__psc_stats__led_calls_t_busy__OFF:
	.word	404
	.globl	PROBE__psc_stats__led_calls_t_busy__ESZ
	.align	2
	.type	PROBE__psc_stats__led_calls_t_busy__ESZ, @object
	.size	PROBE__psc_stats__led_calls_t_busy__ESZ, 4
PROBE__psc_stats__led_calls_t_busy__ESZ:
	.word	4
	.globl	PROBE__psc_stats__led_calls_t_busy__TSZ
	.align	2
	.type	PROBE__psc_stats__led_calls_t_busy__TSZ, @object
	.size	PROBE__psc_stats__led_calls_t_busy__TSZ, 4
PROBE__psc_stats__led_calls_t_busy__TSZ:
	.word	4
	.globl	PROBE__psc_stats__led_calls_t_busy__SGN
	.align	2
	.type	PROBE__psc_stats__led_calls_t_busy__SGN, @object
	.size	PROBE__psc_stats__led_calls_t_busy__SGN, 4
PROBE__psc_stats__led_calls_t_busy__SGN:
	.space	4
	.globl	PROBE__psc_stats__led_or_set_run__OFF
	.align	2
	.type	PROBE__psc_stats__led_or_set_run__OFF, @object
	.size	PROBE__psc_stats__led_or_set_run__OFF, 4
PROBE__psc_stats__led_or_set_run__OFF:
	.word	408
	.globl	PROBE__psc_stats__led_or_set_run__ESZ
	.align	2
	.type	PROBE__psc_stats__led_or_set_run__ESZ, @object
	.size	PROBE__psc_stats__led_or_set_run__ESZ, 4
PROBE__psc_stats__led_or_set_run__ESZ:
	.word	4
	.globl	PROBE__psc_stats__led_or_set_run__TSZ
	.align	2
	.type	PROBE__psc_stats__led_or_set_run__TSZ, @object
	.size	PROBE__psc_stats__led_or_set_run__TSZ, 4
PROBE__psc_stats__led_or_set_run__TSZ:
	.word	4
	.globl	PROBE__psc_stats__led_or_set_run__SGN
	.align	2
	.type	PROBE__psc_stats__led_or_set_run__SGN, @object
	.size	PROBE__psc_stats__led_or_set_run__SGN, 4
PROBE__psc_stats__led_or_set_run__SGN:
	.space	4
	.globl	PROBE__psc_stats__led_or_clr_run__OFF
	.align	2
	.type	PROBE__psc_stats__led_or_clr_run__OFF, @object
	.size	PROBE__psc_stats__led_or_clr_run__OFF, 4
PROBE__psc_stats__led_or_clr_run__OFF:
	.word	412
	.globl	PROBE__psc_stats__led_or_clr_run__ESZ
	.align	2
	.type	PROBE__psc_stats__led_or_clr_run__ESZ, @object
	.size	PROBE__psc_stats__led_or_clr_run__ESZ, 4
PROBE__psc_stats__led_or_clr_run__ESZ:
	.word	4
	.globl	PROBE__psc_stats__led_or_clr_run__TSZ
	.align	2
	.type	PROBE__psc_stats__led_or_clr_run__TSZ, @object
	.size	PROBE__psc_stats__led_or_clr_run__TSZ, 4
PROBE__psc_stats__led_or_clr_run__TSZ:
	.word	4
	.globl	PROBE__psc_stats__led_or_clr_run__SGN
	.align	2
	.type	PROBE__psc_stats__led_or_clr_run__SGN, @object
	.size	PROBE__psc_stats__led_or_clr_run__SGN, 4
PROBE__psc_stats__led_or_clr_run__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_seg_wr__OFF
	.align	2
	.type	PROBE__psc_stats__ms_seg_wr__OFF, @object
	.size	PROBE__psc_stats__ms_seg_wr__OFF, 4
PROBE__psc_stats__ms_seg_wr__OFF:
	.word	416
	.globl	PROBE__psc_stats__ms_seg_wr__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_seg_wr__ESZ, @object
	.size	PROBE__psc_stats__ms_seg_wr__ESZ, 4
PROBE__psc_stats__ms_seg_wr__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_seg_wr__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_seg_wr__TSZ, @object
	.size	PROBE__psc_stats__ms_seg_wr__TSZ, 4
PROBE__psc_stats__ms_seg_wr__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_seg_wr__SGN
	.align	2
	.type	PROBE__psc_stats__ms_seg_wr__SGN, @object
	.size	PROBE__psc_stats__ms_seg_wr__SGN, 4
PROBE__psc_stats__ms_seg_wr__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_seg_rd__OFF
	.align	2
	.type	PROBE__psc_stats__ms_seg_rd__OFF, @object
	.size	PROBE__psc_stats__ms_seg_rd__OFF, 4
PROBE__psc_stats__ms_seg_rd__OFF:
	.word	420
	.globl	PROBE__psc_stats__ms_seg_rd__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_seg_rd__ESZ, @object
	.size	PROBE__psc_stats__ms_seg_rd__ESZ, 4
PROBE__psc_stats__ms_seg_rd__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_seg_rd__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_seg_rd__TSZ, @object
	.size	PROBE__psc_stats__ms_seg_rd__TSZ, 4
PROBE__psc_stats__ms_seg_rd__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_seg_rd__SGN
	.align	2
	.type	PROBE__psc_stats__ms_seg_rd__SGN, @object
	.size	PROBE__psc_stats__ms_seg_rd__SGN, 4
PROBE__psc_stats__ms_seg_rd__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_err__OFF
	.align	2
	.type	PROBE__psc_stats__ms_err__OFF, @object
	.size	PROBE__psc_stats__ms_err__OFF, 4
PROBE__psc_stats__ms_err__OFF:
	.word	424
	.globl	PROBE__psc_stats__ms_err__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_err__ESZ, @object
	.size	PROBE__psc_stats__ms_err__ESZ, 4
PROBE__psc_stats__ms_err__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_err__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_err__TSZ, @object
	.size	PROBE__psc_stats__ms_err__TSZ, 4
PROBE__psc_stats__ms_err__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_err__SGN
	.align	2
	.type	PROBE__psc_stats__ms_err__SGN, @object
	.size	PROBE__psc_stats__ms_err__SGN, 4
PROBE__psc_stats__ms_err__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_ip_tick__OFF
	.align	2
	.type	PROBE__psc_stats__ms_ip_tick__OFF, @object
	.size	PROBE__psc_stats__ms_ip_tick__OFF, 4
PROBE__psc_stats__ms_ip_tick__OFF:
	.word	428
	.globl	PROBE__psc_stats__ms_ip_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_ip_tick__ESZ, @object
	.size	PROBE__psc_stats__ms_ip_tick__ESZ, 4
PROBE__psc_stats__ms_ip_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_ip_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_ip_tick__TSZ, @object
	.size	PROBE__psc_stats__ms_ip_tick__TSZ, 4
PROBE__psc_stats__ms_ip_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_ip_tick__SGN
	.align	2
	.type	PROBE__psc_stats__ms_ip_tick__SGN, @object
	.size	PROBE__psc_stats__ms_ip_tick__SGN, 4
PROBE__psc_stats__ms_ip_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_ip_sector__OFF
	.align	2
	.type	PROBE__psc_stats__ms_ip_sector__OFF, @object
	.size	PROBE__psc_stats__ms_ip_sector__OFF, 4
PROBE__psc_stats__ms_ip_sector__OFF:
	.word	432
	.globl	PROBE__psc_stats__ms_ip_sector__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_ip_sector__ESZ, @object
	.size	PROBE__psc_stats__ms_ip_sector__ESZ, 4
PROBE__psc_stats__ms_ip_sector__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_ip_sector__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_ip_sector__TSZ, @object
	.size	PROBE__psc_stats__ms_ip_sector__TSZ, 4
PROBE__psc_stats__ms_ip_sector__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_ip_sector__SGN
	.align	2
	.type	PROBE__psc_stats__ms_ip_sector__SGN, @object
	.size	PROBE__psc_stats__ms_ip_sector__SGN, 4
PROBE__psc_stats__ms_ip_sector__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_ip_word__OFF
	.align	2
	.type	PROBE__psc_stats__ms_ip_word__OFF, @object
	.size	PROBE__psc_stats__ms_ip_word__OFF, 4
PROBE__psc_stats__ms_ip_word__OFF:
	.word	436
	.globl	PROBE__psc_stats__ms_ip_word__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_ip_word__ESZ, @object
	.size	PROBE__psc_stats__ms_ip_word__ESZ, 4
PROBE__psc_stats__ms_ip_word__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_ip_word__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_ip_word__TSZ, @object
	.size	PROBE__psc_stats__ms_ip_word__TSZ, 4
PROBE__psc_stats__ms_ip_word__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_ip_word__SGN
	.align	2
	.type	PROBE__psc_stats__ms_ip_word__SGN, @object
	.size	PROBE__psc_stats__ms_ip_word__SGN, 4
PROBE__psc_stats__ms_ip_word__SGN:
	.space	4
	.globl	PROBE__psc_stats__kupd_count__OFF
	.align	2
	.type	PROBE__psc_stats__kupd_count__OFF, @object
	.size	PROBE__psc_stats__kupd_count__OFF, 4
PROBE__psc_stats__kupd_count__OFF:
	.word	440
	.globl	PROBE__psc_stats__kupd_count__ESZ
	.align	2
	.type	PROBE__psc_stats__kupd_count__ESZ, @object
	.size	PROBE__psc_stats__kupd_count__ESZ, 4
PROBE__psc_stats__kupd_count__ESZ:
	.word	4
	.globl	PROBE__psc_stats__kupd_count__TSZ
	.align	2
	.type	PROBE__psc_stats__kupd_count__TSZ, @object
	.size	PROBE__psc_stats__kupd_count__TSZ, 4
PROBE__psc_stats__kupd_count__TSZ:
	.word	4
	.globl	PROBE__psc_stats__kupd_count__SGN
	.align	2
	.type	PROBE__psc_stats__kupd_count__SGN, @object
	.size	PROBE__psc_stats__kupd_count__SGN, 4
PROBE__psc_stats__kupd_count__SGN:
	.space	4
	.globl	PROBE__psc_stats__kupd_last_tick__OFF
	.align	2
	.type	PROBE__psc_stats__kupd_last_tick__OFF, @object
	.size	PROBE__psc_stats__kupd_last_tick__OFF, 4
PROBE__psc_stats__kupd_last_tick__OFF:
	.word	444
	.globl	PROBE__psc_stats__kupd_last_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__kupd_last_tick__ESZ, @object
	.size	PROBE__psc_stats__kupd_last_tick__ESZ, 4
PROBE__psc_stats__kupd_last_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__kupd_last_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__kupd_last_tick__TSZ, @object
	.size	PROBE__psc_stats__kupd_last_tick__TSZ, 4
PROBE__psc_stats__kupd_last_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__kupd_last_tick__SGN
	.align	2
	.type	PROBE__psc_stats__kupd_last_tick__SGN, @object
	.size	PROBE__psc_stats__kupd_last_tick__SGN, 4
PROBE__psc_stats__kupd_last_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__durable_tick__OFF
	.align	2
	.type	PROBE__psc_stats__durable_tick__OFF, @object
	.size	PROBE__psc_stats__durable_tick__OFF, 4
PROBE__psc_stats__durable_tick__OFF:
	.word	448
	.globl	PROBE__psc_stats__durable_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__durable_tick__ESZ, @object
	.size	PROBE__psc_stats__durable_tick__ESZ, 4
PROBE__psc_stats__durable_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__durable_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__durable_tick__TSZ, @object
	.size	PROBE__psc_stats__durable_tick__TSZ, 4
PROBE__psc_stats__durable_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__durable_tick__SGN
	.align	2
	.type	PROBE__psc_stats__durable_tick__SGN, @object
	.size	PROBE__psc_stats__durable_tick__SGN, 4
PROBE__psc_stats__durable_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__durable_next__OFF
	.align	2
	.type	PROBE__psc_stats__durable_next__OFF, @object
	.size	PROBE__psc_stats__durable_next__OFF, 4
PROBE__psc_stats__durable_next__OFF:
	.word	452
	.globl	PROBE__psc_stats__durable_next__ESZ
	.align	2
	.type	PROBE__psc_stats__durable_next__ESZ, @object
	.size	PROBE__psc_stats__durable_next__ESZ, 4
PROBE__psc_stats__durable_next__ESZ:
	.word	4
	.globl	PROBE__psc_stats__durable_next__TSZ
	.align	2
	.type	PROBE__psc_stats__durable_next__TSZ, @object
	.size	PROBE__psc_stats__durable_next__TSZ, 4
PROBE__psc_stats__durable_next__TSZ:
	.word	20
	.globl	PROBE__psc_stats__durable_next__SGN
	.align	2
	.type	PROBE__psc_stats__durable_next__SGN, @object
	.size	PROBE__psc_stats__durable_next__SGN, 4
PROBE__psc_stats__durable_next__SGN:
	.space	4
	.globl	PROBE__psc_stats__ctl_writes__OFF
	.align	2
	.type	PROBE__psc_stats__ctl_writes__OFF, @object
	.size	PROBE__psc_stats__ctl_writes__OFF, 4
PROBE__psc_stats__ctl_writes__OFF:
	.word	472
	.globl	PROBE__psc_stats__ctl_writes__ESZ
	.align	2
	.type	PROBE__psc_stats__ctl_writes__ESZ, @object
	.size	PROBE__psc_stats__ctl_writes__ESZ, 4
PROBE__psc_stats__ctl_writes__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ctl_writes__TSZ
	.align	2
	.type	PROBE__psc_stats__ctl_writes__TSZ, @object
	.size	PROBE__psc_stats__ctl_writes__TSZ, 4
PROBE__psc_stats__ctl_writes__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ctl_writes__SGN
	.align	2
	.type	PROBE__psc_stats__ctl_writes__SGN, @object
	.size	PROBE__psc_stats__ctl_writes__SGN, 4
PROBE__psc_stats__ctl_writes__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_paints__OFF
	.align	2
	.type	PROBE__psc_stats__panel_paints__OFF, @object
	.size	PROBE__psc_stats__panel_paints__OFF, 4
PROBE__psc_stats__panel_paints__OFF:
	.word	476
	.globl	PROBE__psc_stats__panel_paints__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_paints__ESZ, @object
	.size	PROBE__psc_stats__panel_paints__ESZ, 4
PROBE__psc_stats__panel_paints__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_paints__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_paints__TSZ, @object
	.size	PROBE__psc_stats__panel_paints__TSZ, 4
PROBE__psc_stats__panel_paints__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_paints__SGN
	.align	2
	.type	PROBE__psc_stats__panel_paints__SGN, @object
	.size	PROBE__psc_stats__panel_paints__SGN, 4
PROBE__psc_stats__panel_paints__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_last_tick__OFF
	.align	2
	.type	PROBE__psc_stats__panel_last_tick__OFF, @object
	.size	PROBE__psc_stats__panel_last_tick__OFF, 4
PROBE__psc_stats__panel_last_tick__OFF:
	.word	480
	.globl	PROBE__psc_stats__panel_last_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_last_tick__ESZ, @object
	.size	PROBE__psc_stats__panel_last_tick__ESZ, 4
PROBE__psc_stats__panel_last_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_last_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_last_tick__TSZ, @object
	.size	PROBE__psc_stats__panel_last_tick__TSZ, 4
PROBE__psc_stats__panel_last_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_last_tick__SGN
	.align	2
	.type	PROBE__psc_stats__panel_last_tick__SGN, @object
	.size	PROBE__psc_stats__panel_last_tick__SGN, 4
PROBE__psc_stats__panel_last_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_test_seq__OFF
	.align	2
	.type	PROBE__psc_stats__panel_test_seq__OFF, @object
	.size	PROBE__psc_stats__panel_test_seq__OFF, 4
PROBE__psc_stats__panel_test_seq__OFF:
	.word	484
	.globl	PROBE__psc_stats__panel_test_seq__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_test_seq__ESZ, @object
	.size	PROBE__psc_stats__panel_test_seq__ESZ, 4
PROBE__psc_stats__panel_test_seq__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_test_seq__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_test_seq__TSZ, @object
	.size	PROBE__psc_stats__panel_test_seq__TSZ, 4
PROBE__psc_stats__panel_test_seq__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_test_seq__SGN
	.align	2
	.type	PROBE__psc_stats__panel_test_seq__SGN, @object
	.size	PROBE__psc_stats__panel_test_seq__SGN, 4
PROBE__psc_stats__panel_test_seq__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_test_done__OFF
	.align	2
	.type	PROBE__psc_stats__panel_test_done__OFF, @object
	.size	PROBE__psc_stats__panel_test_done__OFF, 4
PROBE__psc_stats__panel_test_done__OFF:
	.word	488
	.globl	PROBE__psc_stats__panel_test_done__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_test_done__ESZ, @object
	.size	PROBE__psc_stats__panel_test_done__ESZ, 4
PROBE__psc_stats__panel_test_done__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_test_done__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_test_done__TSZ, @object
	.size	PROBE__psc_stats__panel_test_done__TSZ, 4
PROBE__psc_stats__panel_test_done__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_test_done__SGN
	.align	2
	.type	PROBE__psc_stats__panel_test_done__SGN, @object
	.size	PROBE__psc_stats__panel_test_done__SGN, 4
PROBE__psc_stats__panel_test_done__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_cost_max__OFF
	.align	2
	.type	PROBE__psc_stats__panel_cost_max__OFF, @object
	.size	PROBE__psc_stats__panel_cost_max__OFF, 4
PROBE__psc_stats__panel_cost_max__OFF:
	.word	492
	.globl	PROBE__psc_stats__panel_cost_max__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_cost_max__ESZ, @object
	.size	PROBE__psc_stats__panel_cost_max__ESZ, 4
PROBE__psc_stats__panel_cost_max__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_cost_max__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_cost_max__TSZ, @object
	.size	PROBE__psc_stats__panel_cost_max__TSZ, 4
PROBE__psc_stats__panel_cost_max__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_cost_max__SGN
	.align	2
	.type	PROBE__psc_stats__panel_cost_max__SGN, @object
	.size	PROBE__psc_stats__panel_cost_max__SGN, 4
PROBE__psc_stats__panel_cost_max__SGN:
	.space	4
	.globl	PROBE__psc_stats__lc_nested__OFF
	.align	2
	.type	PROBE__psc_stats__lc_nested__OFF, @object
	.size	PROBE__psc_stats__lc_nested__OFF, 4
PROBE__psc_stats__lc_nested__OFF:
	.word	496
	.globl	PROBE__psc_stats__lc_nested__ESZ
	.align	2
	.type	PROBE__psc_stats__lc_nested__ESZ, @object
	.size	PROBE__psc_stats__lc_nested__ESZ, 4
PROBE__psc_stats__lc_nested__ESZ:
	.word	4
	.globl	PROBE__psc_stats__lc_nested__TSZ
	.align	2
	.type	PROBE__psc_stats__lc_nested__TSZ, @object
	.size	PROBE__psc_stats__lc_nested__TSZ, 4
PROBE__psc_stats__lc_nested__TSZ:
	.word	4
	.globl	PROBE__psc_stats__lc_nested__SGN
	.align	2
	.type	PROBE__psc_stats__lc_nested__SGN, @object
	.size	PROBE__psc_stats__lc_nested__SGN, 4
PROBE__psc_stats__lc_nested__SGN:
	.space	4
	.globl	PROBE__psc_stats__kguard_bad__OFF
	.align	2
	.type	PROBE__psc_stats__kguard_bad__OFF, @object
	.size	PROBE__psc_stats__kguard_bad__OFF, 4
PROBE__psc_stats__kguard_bad__OFF:
	.word	500
	.globl	PROBE__psc_stats__kguard_bad__ESZ
	.align	2
	.type	PROBE__psc_stats__kguard_bad__ESZ, @object
	.size	PROBE__psc_stats__kguard_bad__ESZ, 4
PROBE__psc_stats__kguard_bad__ESZ:
	.word	4
	.globl	PROBE__psc_stats__kguard_bad__TSZ
	.align	2
	.type	PROBE__psc_stats__kguard_bad__TSZ, @object
	.size	PROBE__psc_stats__kguard_bad__TSZ, 4
PROBE__psc_stats__kguard_bad__TSZ:
	.word	4
	.globl	PROBE__psc_stats__kguard_bad__SGN
	.align	2
	.type	PROBE__psc_stats__kguard_bad__SGN, @object
	.size	PROBE__psc_stats__kguard_bad__SGN, 4
PROBE__psc_stats__kguard_bad__SGN:
	.space	4
	.globl	PROBE__psc_stats__ring_rewinds__OFF
	.align	2
	.type	PROBE__psc_stats__ring_rewinds__OFF, @object
	.size	PROBE__psc_stats__ring_rewinds__OFF, 4
PROBE__psc_stats__ring_rewinds__OFF:
	.word	504
	.globl	PROBE__psc_stats__ring_rewinds__ESZ
	.align	2
	.type	PROBE__psc_stats__ring_rewinds__ESZ, @object
	.size	PROBE__psc_stats__ring_rewinds__ESZ, 4
PROBE__psc_stats__ring_rewinds__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ring_rewinds__TSZ
	.align	2
	.type	PROBE__psc_stats__ring_rewinds__TSZ, @object
	.size	PROBE__psc_stats__ring_rewinds__TSZ, 4
PROBE__psc_stats__ring_rewinds__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ring_rewinds__SGN
	.align	2
	.type	PROBE__psc_stats__ring_rewinds__SGN, @object
	.size	PROBE__psc_stats__ring_rewinds__SGN, 4
PROBE__psc_stats__ring_rewinds__SGN:
	.space	4
	.globl	PROBE__psc_stats__head_regress__OFF
	.align	2
	.type	PROBE__psc_stats__head_regress__OFF, @object
	.size	PROBE__psc_stats__head_regress__OFF, 4
PROBE__psc_stats__head_regress__OFF:
	.word	508
	.globl	PROBE__psc_stats__head_regress__ESZ
	.align	2
	.type	PROBE__psc_stats__head_regress__ESZ, @object
	.size	PROBE__psc_stats__head_regress__ESZ, 4
PROBE__psc_stats__head_regress__ESZ:
	.word	4
	.globl	PROBE__psc_stats__head_regress__TSZ
	.align	2
	.type	PROBE__psc_stats__head_regress__TSZ, @object
	.size	PROBE__psc_stats__head_regress__TSZ, 4
PROBE__psc_stats__head_regress__TSZ:
	.word	4
	.globl	PROBE__psc_stats__head_regress__SGN
	.align	2
	.type	PROBE__psc_stats__head_regress__SGN, @object
	.size	PROBE__psc_stats__head_regress__SGN, 4
PROBE__psc_stats__head_regress__SGN:
	.space	4
	.globl	PROBE__psc_stats__slot_bad__OFF
	.align	2
	.type	PROBE__psc_stats__slot_bad__OFF, @object
	.size	PROBE__psc_stats__slot_bad__OFF, 4
PROBE__psc_stats__slot_bad__OFF:
	.word	512
	.globl	PROBE__psc_stats__slot_bad__ESZ
	.align	2
	.type	PROBE__psc_stats__slot_bad__ESZ, @object
	.size	PROBE__psc_stats__slot_bad__ESZ, 4
PROBE__psc_stats__slot_bad__ESZ:
	.word	4
	.globl	PROBE__psc_stats__slot_bad__TSZ
	.align	2
	.type	PROBE__psc_stats__slot_bad__TSZ, @object
	.size	PROBE__psc_stats__slot_bad__TSZ, 4
PROBE__psc_stats__slot_bad__TSZ:
	.word	20
	.globl	PROBE__psc_stats__slot_bad__SGN
	.align	2
	.type	PROBE__psc_stats__slot_bad__SGN, @object
	.size	PROBE__psc_stats__slot_bad__SGN, 4
PROBE__psc_stats__slot_bad__SGN:
	.space	4
	.globl	PROBE__psc_stats__fat_panics__OFF
	.align	2
	.type	PROBE__psc_stats__fat_panics__OFF, @object
	.size	PROBE__psc_stats__fat_panics__OFF, 4
PROBE__psc_stats__fat_panics__OFF:
	.word	532
	.globl	PROBE__psc_stats__fat_panics__ESZ
	.align	2
	.type	PROBE__psc_stats__fat_panics__ESZ, @object
	.size	PROBE__psc_stats__fat_panics__ESZ, 4
PROBE__psc_stats__fat_panics__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fat_panics__TSZ
	.align	2
	.type	PROBE__psc_stats__fat_panics__TSZ, @object
	.size	PROBE__psc_stats__fat_panics__TSZ, 4
PROBE__psc_stats__fat_panics__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fat_panics__SGN
	.align	2
	.type	PROBE__psc_stats__fat_panics__SGN, @object
	.size	PROBE__psc_stats__fat_panics__SGN, 4
PROBE__psc_stats__fat_panics__SGN:
	.space	4
	.globl	PROBE__psc_stats__fat_panic_tick__OFF
	.align	2
	.type	PROBE__psc_stats__fat_panic_tick__OFF, @object
	.size	PROBE__psc_stats__fat_panic_tick__OFF, 4
PROBE__psc_stats__fat_panic_tick__OFF:
	.word	536
	.globl	PROBE__psc_stats__fat_panic_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__fat_panic_tick__ESZ, @object
	.size	PROBE__psc_stats__fat_panic_tick__ESZ, 4
PROBE__psc_stats__fat_panic_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fat_panic_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__fat_panic_tick__TSZ, @object
	.size	PROBE__psc_stats__fat_panic_tick__TSZ, 4
PROBE__psc_stats__fat_panic_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fat_panic_tick__SGN
	.align	2
	.type	PROBE__psc_stats__fat_panic_tick__SGN, @object
	.size	PROBE__psc_stats__fat_panic_tick__SGN, 4
PROBE__psc_stats__fat_panic_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_rdonly__OFF
	.align	2
	.type	PROBE__psc_stats__ms_rdonly__OFF, @object
	.size	PROBE__psc_stats__ms_rdonly__OFF, 4
PROBE__psc_stats__ms_rdonly__OFF:
	.word	540
	.globl	PROBE__psc_stats__ms_rdonly__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_rdonly__ESZ, @object
	.size	PROBE__psc_stats__ms_rdonly__ESZ, 4
PROBE__psc_stats__ms_rdonly__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_rdonly__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_rdonly__TSZ, @object
	.size	PROBE__psc_stats__ms_rdonly__TSZ, 4
PROBE__psc_stats__ms_rdonly__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_rdonly__SGN
	.align	2
	.type	PROBE__psc_stats__ms_rdonly__SGN, @object
	.size	PROBE__psc_stats__ms_rdonly__SGN, 4
PROBE__psc_stats__ms_rdonly__SGN:
	.space	4
	.globl	PROBE__psc_stats__wk_count__OFF
	.align	2
	.type	PROBE__psc_stats__wk_count__OFF, @object
	.size	PROBE__psc_stats__wk_count__OFF, 4
PROBE__psc_stats__wk_count__OFF:
	.word	544
	.globl	PROBE__psc_stats__wk_count__ESZ
	.align	2
	.type	PROBE__psc_stats__wk_count__ESZ, @object
	.size	PROBE__psc_stats__wk_count__ESZ, 4
PROBE__psc_stats__wk_count__ESZ:
	.word	4
	.globl	PROBE__psc_stats__wk_count__TSZ
	.align	2
	.type	PROBE__psc_stats__wk_count__TSZ, @object
	.size	PROBE__psc_stats__wk_count__TSZ, 4
PROBE__psc_stats__wk_count__TSZ:
	.word	4
	.globl	PROBE__psc_stats__wk_count__SGN
	.align	2
	.type	PROBE__psc_stats__wk_count__SGN, @object
	.size	PROBE__psc_stats__wk_count__SGN, 4
PROBE__psc_stats__wk_count__SGN:
	.space	4
	.globl	PROBE__psc_stats__wk_max__OFF
	.align	2
	.type	PROBE__psc_stats__wk_max__OFF, @object
	.size	PROBE__psc_stats__wk_max__OFF, 4
PROBE__psc_stats__wk_max__OFF:
	.word	548
	.globl	PROBE__psc_stats__wk_max__ESZ
	.align	2
	.type	PROBE__psc_stats__wk_max__ESZ, @object
	.size	PROBE__psc_stats__wk_max__ESZ, 4
PROBE__psc_stats__wk_max__ESZ:
	.word	4
	.globl	PROBE__psc_stats__wk_max__TSZ
	.align	2
	.type	PROBE__psc_stats__wk_max__TSZ, @object
	.size	PROBE__psc_stats__wk_max__TSZ, 4
PROBE__psc_stats__wk_max__TSZ:
	.word	4
	.globl	PROBE__psc_stats__wk_max__SGN
	.align	2
	.type	PROBE__psc_stats__wk_max__SGN, @object
	.size	PROBE__psc_stats__wk_max__SGN, 4
PROBE__psc_stats__wk_max__SGN:
	.space	4
	.globl	PROBE__psc_stats__jp_exit_tick__OFF
	.align	2
	.type	PROBE__psc_stats__jp_exit_tick__OFF, @object
	.size	PROBE__psc_stats__jp_exit_tick__OFF, 4
PROBE__psc_stats__jp_exit_tick__OFF:
	.word	552
	.globl	PROBE__psc_stats__jp_exit_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__jp_exit_tick__ESZ, @object
	.size	PROBE__psc_stats__jp_exit_tick__ESZ, 4
PROBE__psc_stats__jp_exit_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__jp_exit_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__jp_exit_tick__TSZ, @object
	.size	PROBE__psc_stats__jp_exit_tick__TSZ, 4
PROBE__psc_stats__jp_exit_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__jp_exit_tick__SGN
	.align	2
	.type	PROBE__psc_stats__jp_exit_tick__SGN, @object
	.size	PROBE__psc_stats__jp_exit_tick__SGN, 4
PROBE__psc_stats__jp_exit_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__kguard_first_tick__OFF
	.align	2
	.type	PROBE__psc_stats__kguard_first_tick__OFF, @object
	.size	PROBE__psc_stats__kguard_first_tick__OFF, 4
PROBE__psc_stats__kguard_first_tick__OFF:
	.word	556
	.globl	PROBE__psc_stats__kguard_first_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__kguard_first_tick__ESZ, @object
	.size	PROBE__psc_stats__kguard_first_tick__ESZ, 4
PROBE__psc_stats__kguard_first_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__kguard_first_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__kguard_first_tick__TSZ, @object
	.size	PROBE__psc_stats__kguard_first_tick__TSZ, 4
PROBE__psc_stats__kguard_first_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__kguard_first_tick__SGN
	.align	2
	.type	PROBE__psc_stats__kguard_first_tick__SGN, @object
	.size	PROBE__psc_stats__kguard_first_tick__SGN, 4
PROBE__psc_stats__kguard_first_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__pid_class__OFF
	.align	2
	.type	PROBE__psc_stats__pid_class__OFF, @object
	.size	PROBE__psc_stats__pid_class__OFF, 4
PROBE__psc_stats__pid_class__OFF:
	.word	560
	.globl	PROBE__psc_stats__pid_class__ESZ
	.align	2
	.type	PROBE__psc_stats__pid_class__ESZ, @object
	.size	PROBE__psc_stats__pid_class__ESZ, 4
PROBE__psc_stats__pid_class__ESZ:
	.word	4
	.globl	PROBE__psc_stats__pid_class__TSZ
	.align	2
	.type	PROBE__psc_stats__pid_class__TSZ, @object
	.size	PROBE__psc_stats__pid_class__TSZ, 4
PROBE__psc_stats__pid_class__TSZ:
	.word	32
	.globl	PROBE__psc_stats__pid_class__SGN
	.align	2
	.type	PROBE__psc_stats__pid_class__SGN, @object
	.size	PROBE__psc_stats__pid_class__SGN, 4
PROBE__psc_stats__pid_class__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_cost_last__OFF
	.align	2
	.type	PROBE__psc_stats__panel_cost_last__OFF, @object
	.size	PROBE__psc_stats__panel_cost_last__OFF, 4
PROBE__psc_stats__panel_cost_last__OFF:
	.word	592
	.globl	PROBE__psc_stats__panel_cost_last__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_cost_last__ESZ, @object
	.size	PROBE__psc_stats__panel_cost_last__ESZ, 4
PROBE__psc_stats__panel_cost_last__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_cost_last__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_cost_last__TSZ, @object
	.size	PROBE__psc_stats__panel_cost_last__TSZ, 4
PROBE__psc_stats__panel_cost_last__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_cost_last__SGN
	.align	2
	.type	PROBE__psc_stats__panel_cost_last__SGN, @object
	.size	PROBE__psc_stats__panel_cost_last__SGN, 4
PROBE__psc_stats__panel_cost_last__SGN:
	.space	4
	.globl	PROBE__psc_stats__panel_state__OFF
	.align	2
	.type	PROBE__psc_stats__panel_state__OFF, @object
	.size	PROBE__psc_stats__panel_state__OFF, 4
PROBE__psc_stats__panel_state__OFF:
	.word	596
	.globl	PROBE__psc_stats__panel_state__ESZ
	.align	2
	.type	PROBE__psc_stats__panel_state__ESZ, @object
	.size	PROBE__psc_stats__panel_state__ESZ, 4
PROBE__psc_stats__panel_state__ESZ:
	.word	4
	.globl	PROBE__psc_stats__panel_state__TSZ
	.align	2
	.type	PROBE__psc_stats__panel_state__TSZ, @object
	.size	PROBE__psc_stats__panel_state__TSZ, 4
PROBE__psc_stats__panel_state__TSZ:
	.word	4
	.globl	PROBE__psc_stats__panel_state__SGN
	.align	2
	.type	PROBE__psc_stats__panel_state__SGN, @object
	.size	PROBE__psc_stats__panel_state__SGN, 4
PROBE__psc_stats__panel_state__SGN:
	.space	4
	.globl	PROBE__psc_stats__meta_sector__OFF
	.align	2
	.type	PROBE__psc_stats__meta_sector__OFF, @object
	.size	PROBE__psc_stats__meta_sector__OFF, 4
PROBE__psc_stats__meta_sector__OFF:
	.word	600
	.globl	PROBE__psc_stats__meta_sector__ESZ
	.align	2
	.type	PROBE__psc_stats__meta_sector__ESZ, @object
	.size	PROBE__psc_stats__meta_sector__ESZ, 4
PROBE__psc_stats__meta_sector__ESZ:
	.word	4
	.globl	PROBE__psc_stats__meta_sector__TSZ
	.align	2
	.type	PROBE__psc_stats__meta_sector__TSZ, @object
	.size	PROBE__psc_stats__meta_sector__TSZ, 4
PROBE__psc_stats__meta_sector__TSZ:
	.word	4
	.globl	PROBE__psc_stats__meta_sector__SGN
	.align	2
	.type	PROBE__psc_stats__meta_sector__SGN, @object
	.size	PROBE__psc_stats__meta_sector__SGN, 4
PROBE__psc_stats__meta_sector__SGN:
	.space	4
	.globl	PROBE__psc_stats__meta_tick__OFF
	.align	2
	.type	PROBE__psc_stats__meta_tick__OFF, @object
	.size	PROBE__psc_stats__meta_tick__OFF, 4
PROBE__psc_stats__meta_tick__OFF:
	.word	604
	.globl	PROBE__psc_stats__meta_tick__ESZ
	.align	2
	.type	PROBE__psc_stats__meta_tick__ESZ, @object
	.size	PROBE__psc_stats__meta_tick__ESZ, 4
PROBE__psc_stats__meta_tick__ESZ:
	.word	4
	.globl	PROBE__psc_stats__meta_tick__TSZ
	.align	2
	.type	PROBE__psc_stats__meta_tick__TSZ, @object
	.size	PROBE__psc_stats__meta_tick__TSZ, 4
PROBE__psc_stats__meta_tick__TSZ:
	.word	4
	.globl	PROBE__psc_stats__meta_tick__SGN
	.align	2
	.type	PROBE__psc_stats__meta_tick__SGN, @object
	.size	PROBE__psc_stats__meta_tick__SGN, 4
PROBE__psc_stats__meta_tick__SGN:
	.space	4
	.globl	PROBE__psc_stats__pre_count__OFF
	.align	2
	.type	PROBE__psc_stats__pre_count__OFF, @object
	.size	PROBE__psc_stats__pre_count__OFF, 4
PROBE__psc_stats__pre_count__OFF:
	.word	608
	.globl	PROBE__psc_stats__pre_count__ESZ
	.align	2
	.type	PROBE__psc_stats__pre_count__ESZ, @object
	.size	PROBE__psc_stats__pre_count__ESZ, 4
PROBE__psc_stats__pre_count__ESZ:
	.word	4
	.globl	PROBE__psc_stats__pre_count__TSZ
	.align	2
	.type	PROBE__psc_stats__pre_count__TSZ, @object
	.size	PROBE__psc_stats__pre_count__TSZ, 4
PROBE__psc_stats__pre_count__TSZ:
	.word	4
	.globl	PROBE__psc_stats__pre_count__SGN
	.align	2
	.type	PROBE__psc_stats__pre_count__SGN, @object
	.size	PROBE__psc_stats__pre_count__SGN, 4
PROBE__psc_stats__pre_count__SGN:
	.space	4
	.globl	PROBE__psc_stats__ms_part_start__OFF
	.align	2
	.type	PROBE__psc_stats__ms_part_start__OFF, @object
	.size	PROBE__psc_stats__ms_part_start__OFF, 4
PROBE__psc_stats__ms_part_start__OFF:
	.word	612
	.globl	PROBE__psc_stats__ms_part_start__ESZ
	.align	2
	.type	PROBE__psc_stats__ms_part_start__ESZ, @object
	.size	PROBE__psc_stats__ms_part_start__ESZ, 4
PROBE__psc_stats__ms_part_start__ESZ:
	.word	4
	.globl	PROBE__psc_stats__ms_part_start__TSZ
	.align	2
	.type	PROBE__psc_stats__ms_part_start__TSZ, @object
	.size	PROBE__psc_stats__ms_part_start__TSZ, 4
PROBE__psc_stats__ms_part_start__TSZ:
	.word	4
	.globl	PROBE__psc_stats__ms_part_start__SGN
	.align	2
	.type	PROBE__psc_stats__ms_part_start__SGN, @object
	.size	PROBE__psc_stats__ms_part_start__SGN, 4
PROBE__psc_stats__ms_part_start__SGN:
	.space	4
	.globl	PROBE__psc_stats__fat_start__OFF
	.align	2
	.type	PROBE__psc_stats__fat_start__OFF, @object
	.size	PROBE__psc_stats__fat_start__OFF, 4
PROBE__psc_stats__fat_start__OFF:
	.word	616
	.globl	PROBE__psc_stats__fat_start__ESZ
	.align	2
	.type	PROBE__psc_stats__fat_start__ESZ, @object
	.size	PROBE__psc_stats__fat_start__ESZ, 4
PROBE__psc_stats__fat_start__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fat_start__TSZ
	.align	2
	.type	PROBE__psc_stats__fat_start__TSZ, @object
	.size	PROBE__psc_stats__fat_start__TSZ, 4
PROBE__psc_stats__fat_start__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fat_start__SGN
	.align	2
	.type	PROBE__psc_stats__fat_start__SGN, @object
	.size	PROBE__psc_stats__fat_start__SGN, 4
PROBE__psc_stats__fat_start__SGN:
	.space	4
	.globl	PROBE__psc_stats__fat_length__OFF
	.align	2
	.type	PROBE__psc_stats__fat_length__OFF, @object
	.size	PROBE__psc_stats__fat_length__OFF, 4
PROBE__psc_stats__fat_length__OFF:
	.word	620
	.globl	PROBE__psc_stats__fat_length__ESZ
	.align	2
	.type	PROBE__psc_stats__fat_length__ESZ, @object
	.size	PROBE__psc_stats__fat_length__ESZ, 4
PROBE__psc_stats__fat_length__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fat_length__TSZ
	.align	2
	.type	PROBE__psc_stats__fat_length__TSZ, @object
	.size	PROBE__psc_stats__fat_length__TSZ, 4
PROBE__psc_stats__fat_length__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fat_length__SGN
	.align	2
	.type	PROBE__psc_stats__fat_length__SGN, @object
	.size	PROBE__psc_stats__fat_length__SGN, 4
PROBE__psc_stats__fat_length__SGN:
	.space	4
	.globl	PROBE__psc_stats__fats__OFF
	.align	2
	.type	PROBE__psc_stats__fats__OFF, @object
	.size	PROBE__psc_stats__fats__OFF, 4
PROBE__psc_stats__fats__OFF:
	.word	624
	.globl	PROBE__psc_stats__fats__ESZ
	.align	2
	.type	PROBE__psc_stats__fats__ESZ, @object
	.size	PROBE__psc_stats__fats__ESZ, 4
PROBE__psc_stats__fats__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fats__TSZ
	.align	2
	.type	PROBE__psc_stats__fats__TSZ, @object
	.size	PROBE__psc_stats__fats__TSZ, 4
PROBE__psc_stats__fats__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fats__SGN
	.align	2
	.type	PROBE__psc_stats__fats__SGN, @object
	.size	PROBE__psc_stats__fats__SGN, 4
PROBE__psc_stats__fats__SGN:
	.space	4
	.globl	PROBE__psc_stats__fsinfo_sector__OFF
	.align	2
	.type	PROBE__psc_stats__fsinfo_sector__OFF, @object
	.size	PROBE__psc_stats__fsinfo_sector__OFF, 4
PROBE__psc_stats__fsinfo_sector__OFF:
	.word	628
	.globl	PROBE__psc_stats__fsinfo_sector__ESZ
	.align	2
	.type	PROBE__psc_stats__fsinfo_sector__ESZ, @object
	.size	PROBE__psc_stats__fsinfo_sector__ESZ, 4
PROBE__psc_stats__fsinfo_sector__ESZ:
	.word	4
	.globl	PROBE__psc_stats__fsinfo_sector__TSZ
	.align	2
	.type	PROBE__psc_stats__fsinfo_sector__TSZ, @object
	.size	PROBE__psc_stats__fsinfo_sector__TSZ, 4
PROBE__psc_stats__fsinfo_sector__TSZ:
	.word	4
	.globl	PROBE__psc_stats__fsinfo_sector__SGN
	.align	2
	.type	PROBE__psc_stats__fsinfo_sector__SGN, @object
	.size	PROBE__psc_stats__fsinfo_sector__SGN, 4
PROBE__psc_stats__fsinfo_sector__SGN:
	.space	4
	.globl	PROBE__psc_stats__data_start__OFF
	.align	2
	.type	PROBE__psc_stats__data_start__OFF, @object
	.size	PROBE__psc_stats__data_start__OFF, 4
PROBE__psc_stats__data_start__OFF:
	.word	632
	.globl	PROBE__psc_stats__data_start__ESZ
	.align	2
	.type	PROBE__psc_stats__data_start__ESZ, @object
	.size	PROBE__psc_stats__data_start__ESZ, 4
PROBE__psc_stats__data_start__ESZ:
	.word	4
	.globl	PROBE__psc_stats__data_start__TSZ
	.align	2
	.type	PROBE__psc_stats__data_start__TSZ, @object
	.size	PROBE__psc_stats__data_start__TSZ, 4
PROBE__psc_stats__data_start__TSZ:
	.word	4
	.globl	PROBE__psc_stats__data_start__SGN
	.align	2
	.type	PROBE__psc_stats__data_start__SGN, @object
	.size	PROBE__psc_stats__data_start__SGN, 4
PROBE__psc_stats__data_start__SGN:
	.space	4
	.globl	PROBE__psc_stats__sec_per_clus_bits__OFF
	.align	2
	.type	PROBE__psc_stats__sec_per_clus_bits__OFF, @object
	.size	PROBE__psc_stats__sec_per_clus_bits__OFF, 4
PROBE__psc_stats__sec_per_clus_bits__OFF:
	.word	636
	.globl	PROBE__psc_stats__sec_per_clus_bits__ESZ
	.align	2
	.type	PROBE__psc_stats__sec_per_clus_bits__ESZ, @object
	.size	PROBE__psc_stats__sec_per_clus_bits__ESZ, 4
PROBE__psc_stats__sec_per_clus_bits__ESZ:
	.word	4
	.globl	PROBE__psc_stats__sec_per_clus_bits__TSZ
	.align	2
	.type	PROBE__psc_stats__sec_per_clus_bits__TSZ, @object
	.size	PROBE__psc_stats__sec_per_clus_bits__TSZ, 4
PROBE__psc_stats__sec_per_clus_bits__TSZ:
	.word	4
	.globl	PROBE__psc_stats__sec_per_clus_bits__SGN
	.align	2
	.type	PROBE__psc_stats__sec_per_clus_bits__SGN, @object
	.size	PROBE__psc_stats__sec_per_clus_bits__SGN, 4
PROBE__psc_stats__sec_per_clus_bits__SGN:
	.space	4
	.globl	PROBE__psc_stats__reserved__OFF
	.align	2
	.type	PROBE__psc_stats__reserved__OFF, @object
	.size	PROBE__psc_stats__reserved__OFF, 4
PROBE__psc_stats__reserved__OFF:
	.word	640
	.globl	PROBE__psc_stats__reserved__ESZ
	.align	2
	.type	PROBE__psc_stats__reserved__ESZ, @object
	.size	PROBE__psc_stats__reserved__ESZ, 4
PROBE__psc_stats__reserved__ESZ:
	.word	4
	.globl	PROBE__psc_stats__reserved__TSZ
	.align	2
	.type	PROBE__psc_stats__reserved__TSZ, @object
	.size	PROBE__psc_stats__reserved__TSZ, 4
PROBE__psc_stats__reserved__TSZ:
	.word	128
	.globl	PROBE__psc_stats__reserved__SGN
	.align	2
	.type	PROBE__psc_stats__reserved__SGN, @object
	.size	PROBE__psc_stats__reserved__SGN, 4
PROBE__psc_stats__reserved__SGN:
	.space	4
	.globl	PROBE__psc_ctl__SIZE
	.align	2
	.type	PROBE__psc_ctl__SIZE, @object
	.size	PROBE__psc_ctl__SIZE, 4
PROBE__psc_ctl__SIZE:
	.word	32
	.globl	PROBE__psc_ctl__op__OFF
	.align	2
	.type	PROBE__psc_ctl__op__OFF, @object
	.size	PROBE__psc_ctl__op__OFF, 4
PROBE__psc_ctl__op__OFF:
	.space	4
	.globl	PROBE__psc_ctl__op__ESZ
	.align	2
	.type	PROBE__psc_ctl__op__ESZ, @object
	.size	PROBE__psc_ctl__op__ESZ, 4
PROBE__psc_ctl__op__ESZ:
	.word	4
	.globl	PROBE__psc_ctl__op__TSZ
	.align	2
	.type	PROBE__psc_ctl__op__TSZ, @object
	.size	PROBE__psc_ctl__op__TSZ, 4
PROBE__psc_ctl__op__TSZ:
	.word	4
	.globl	PROBE__psc_ctl__op__SGN
	.align	2
	.type	PROBE__psc_ctl__op__SGN, @object
	.size	PROBE__psc_ctl__op__SGN, 4
PROBE__psc_ctl__op__SGN:
	.space	4
	.globl	PROBE__psc_ctl__arg__OFF
	.align	2
	.type	PROBE__psc_ctl__arg__OFF, @object
	.size	PROBE__psc_ctl__arg__OFF, 4
PROBE__psc_ctl__arg__OFF:
	.word	4
	.globl	PROBE__psc_ctl__arg__ESZ
	.align	2
	.type	PROBE__psc_ctl__arg__ESZ, @object
	.size	PROBE__psc_ctl__arg__ESZ, 4
PROBE__psc_ctl__arg__ESZ:
	.word	4
	.globl	PROBE__psc_ctl__arg__TSZ
	.align	2
	.type	PROBE__psc_ctl__arg__TSZ, @object
	.size	PROBE__psc_ctl__arg__TSZ, 4
PROBE__psc_ctl__arg__TSZ:
	.word	28
	.globl	PROBE__psc_ctl__arg__SGN
	.align	2
	.type	PROBE__psc_ctl__arg__SGN, @object
	.size	PROBE__psc_ctl__arg__SGN, 4
PROBE__psc_ctl__arg__SGN:
	.space	4
	.globl	PROBE__psc_chunk_hdr__SIZE
	.align	2
	.type	PROBE__psc_chunk_hdr__SIZE, @object
	.size	PROBE__psc_chunk_hdr__SIZE, 4
PROBE__psc_chunk_hdr__SIZE:
	.word	20
	.globl	PROBE__psc_chunk_hdr__magic__OFF
	.align	2
	.type	PROBE__psc_chunk_hdr__magic__OFF, @object
	.size	PROBE__psc_chunk_hdr__magic__OFF, 4
PROBE__psc_chunk_hdr__magic__OFF:
	.space	4
	.globl	PROBE__psc_chunk_hdr__magic__ESZ
	.align	2
	.type	PROBE__psc_chunk_hdr__magic__ESZ, @object
	.size	PROBE__psc_chunk_hdr__magic__ESZ, 4
PROBE__psc_chunk_hdr__magic__ESZ:
	.word	1
	.globl	PROBE__psc_chunk_hdr__magic__TSZ
	.align	2
	.type	PROBE__psc_chunk_hdr__magic__TSZ, @object
	.size	PROBE__psc_chunk_hdr__magic__TSZ, 4
PROBE__psc_chunk_hdr__magic__TSZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__magic__SGN
	.align	2
	.type	PROBE__psc_chunk_hdr__magic__SGN, @object
	.size	PROBE__psc_chunk_hdr__magic__SGN, 4
PROBE__psc_chunk_hdr__magic__SGN:
	.space	4
	.globl	PROBE__psc_chunk_hdr__type__OFF
	.align	2
	.type	PROBE__psc_chunk_hdr__type__OFF, @object
	.size	PROBE__psc_chunk_hdr__type__OFF, 4
PROBE__psc_chunk_hdr__type__OFF:
	.word	4
	.globl	PROBE__psc_chunk_hdr__type__ESZ
	.align	2
	.type	PROBE__psc_chunk_hdr__type__ESZ, @object
	.size	PROBE__psc_chunk_hdr__type__ESZ, 4
PROBE__psc_chunk_hdr__type__ESZ:
	.word	2
	.globl	PROBE__psc_chunk_hdr__type__TSZ
	.align	2
	.type	PROBE__psc_chunk_hdr__type__TSZ, @object
	.size	PROBE__psc_chunk_hdr__type__TSZ, 4
PROBE__psc_chunk_hdr__type__TSZ:
	.word	2
	.globl	PROBE__psc_chunk_hdr__type__SGN
	.align	2
	.type	PROBE__psc_chunk_hdr__type__SGN, @object
	.size	PROBE__psc_chunk_hdr__type__SGN, 4
PROBE__psc_chunk_hdr__type__SGN:
	.space	4
	.globl	PROBE__psc_chunk_hdr__hver__OFF
	.align	2
	.type	PROBE__psc_chunk_hdr__hver__OFF, @object
	.size	PROBE__psc_chunk_hdr__hver__OFF, 4
PROBE__psc_chunk_hdr__hver__OFF:
	.word	6
	.globl	PROBE__psc_chunk_hdr__hver__ESZ
	.align	2
	.type	PROBE__psc_chunk_hdr__hver__ESZ, @object
	.size	PROBE__psc_chunk_hdr__hver__ESZ, 4
PROBE__psc_chunk_hdr__hver__ESZ:
	.word	2
	.globl	PROBE__psc_chunk_hdr__hver__TSZ
	.align	2
	.type	PROBE__psc_chunk_hdr__hver__TSZ, @object
	.size	PROBE__psc_chunk_hdr__hver__TSZ, 4
PROBE__psc_chunk_hdr__hver__TSZ:
	.word	2
	.globl	PROBE__psc_chunk_hdr__hver__SGN
	.align	2
	.type	PROBE__psc_chunk_hdr__hver__SGN, @object
	.size	PROBE__psc_chunk_hdr__hver__SGN, 4
PROBE__psc_chunk_hdr__hver__SGN:
	.space	4
	.globl	PROBE__psc_chunk_hdr__len__OFF
	.align	2
	.type	PROBE__psc_chunk_hdr__len__OFF, @object
	.size	PROBE__psc_chunk_hdr__len__OFF, 4
PROBE__psc_chunk_hdr__len__OFF:
	.word	8
	.globl	PROBE__psc_chunk_hdr__len__ESZ
	.align	2
	.type	PROBE__psc_chunk_hdr__len__ESZ, @object
	.size	PROBE__psc_chunk_hdr__len__ESZ, 4
PROBE__psc_chunk_hdr__len__ESZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__len__TSZ
	.align	2
	.type	PROBE__psc_chunk_hdr__len__TSZ, @object
	.size	PROBE__psc_chunk_hdr__len__TSZ, 4
PROBE__psc_chunk_hdr__len__TSZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__len__SGN
	.align	2
	.type	PROBE__psc_chunk_hdr__len__SGN, @object
	.size	PROBE__psc_chunk_hdr__len__SGN, 4
PROBE__psc_chunk_hdr__len__SGN:
	.space	4
	.globl	PROBE__psc_chunk_hdr__fseq__OFF
	.align	2
	.type	PROBE__psc_chunk_hdr__fseq__OFF, @object
	.size	PROBE__psc_chunk_hdr__fseq__OFF, 4
PROBE__psc_chunk_hdr__fseq__OFF:
	.word	12
	.globl	PROBE__psc_chunk_hdr__fseq__ESZ
	.align	2
	.type	PROBE__psc_chunk_hdr__fseq__ESZ, @object
	.size	PROBE__psc_chunk_hdr__fseq__ESZ, 4
PROBE__psc_chunk_hdr__fseq__ESZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__fseq__TSZ
	.align	2
	.type	PROBE__psc_chunk_hdr__fseq__TSZ, @object
	.size	PROBE__psc_chunk_hdr__fseq__TSZ, 4
PROBE__psc_chunk_hdr__fseq__TSZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__fseq__SGN
	.align	2
	.type	PROBE__psc_chunk_hdr__fseq__SGN, @object
	.size	PROBE__psc_chunk_hdr__fseq__SGN, 4
PROBE__psc_chunk_hdr__fseq__SGN:
	.space	4
	.globl	PROBE__psc_chunk_hdr__crc__OFF
	.align	2
	.type	PROBE__psc_chunk_hdr__crc__OFF, @object
	.size	PROBE__psc_chunk_hdr__crc__OFF, 4
PROBE__psc_chunk_hdr__crc__OFF:
	.word	16
	.globl	PROBE__psc_chunk_hdr__crc__ESZ
	.align	2
	.type	PROBE__psc_chunk_hdr__crc__ESZ, @object
	.size	PROBE__psc_chunk_hdr__crc__ESZ, 4
PROBE__psc_chunk_hdr__crc__ESZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__crc__TSZ
	.align	2
	.type	PROBE__psc_chunk_hdr__crc__TSZ, @object
	.size	PROBE__psc_chunk_hdr__crc__TSZ, 4
PROBE__psc_chunk_hdr__crc__TSZ:
	.word	4
	.globl	PROBE__psc_chunk_hdr__crc__SGN
	.align	2
	.type	PROBE__psc_chunk_hdr__crc__SGN, @object
	.size	PROBE__psc_chunk_hdr__crc__SGN, 4
PROBE__psc_chunk_hdr__crc__SGN:
	.space	4
	.globl	PROBE__psc_block_hdr__SIZE
	.align	2
	.type	PROBE__psc_block_hdr__SIZE, @object
	.size	PROBE__psc_block_hdr__SIZE, 4
PROBE__psc_block_hdr__SIZE:
	.word	8
	.globl	PROBE__psc_block_hdr__ring__OFF
	.align	2
	.type	PROBE__psc_block_hdr__ring__OFF, @object
	.size	PROBE__psc_block_hdr__ring__OFF, 4
PROBE__psc_block_hdr__ring__OFF:
	.space	4
	.globl	PROBE__psc_block_hdr__ring__ESZ
	.align	2
	.type	PROBE__psc_block_hdr__ring__ESZ, @object
	.size	PROBE__psc_block_hdr__ring__ESZ, 4
PROBE__psc_block_hdr__ring__ESZ:
	.word	1
	.globl	PROBE__psc_block_hdr__ring__TSZ
	.align	2
	.type	PROBE__psc_block_hdr__ring__TSZ, @object
	.size	PROBE__psc_block_hdr__ring__TSZ, 4
PROBE__psc_block_hdr__ring__TSZ:
	.word	1
	.globl	PROBE__psc_block_hdr__ring__SGN
	.align	2
	.type	PROBE__psc_block_hdr__ring__SGN, @object
	.size	PROBE__psc_block_hdr__ring__SGN, 4
PROBE__psc_block_hdr__ring__SGN:
	.space	4
	.globl	PROBE__psc_block_hdr__recsize_div4__OFF
	.align	2
	.type	PROBE__psc_block_hdr__recsize_div4__OFF, @object
	.size	PROBE__psc_block_hdr__recsize_div4__OFF, 4
PROBE__psc_block_hdr__recsize_div4__OFF:
	.word	1
	.globl	PROBE__psc_block_hdr__recsize_div4__ESZ
	.align	2
	.type	PROBE__psc_block_hdr__recsize_div4__ESZ, @object
	.size	PROBE__psc_block_hdr__recsize_div4__ESZ, 4
PROBE__psc_block_hdr__recsize_div4__ESZ:
	.word	1
	.globl	PROBE__psc_block_hdr__recsize_div4__TSZ
	.align	2
	.type	PROBE__psc_block_hdr__recsize_div4__TSZ, @object
	.size	PROBE__psc_block_hdr__recsize_div4__TSZ, 4
PROBE__psc_block_hdr__recsize_div4__TSZ:
	.word	1
	.globl	PROBE__psc_block_hdr__recsize_div4__SGN
	.align	2
	.type	PROBE__psc_block_hdr__recsize_div4__SGN, @object
	.size	PROBE__psc_block_hdr__recsize_div4__SGN, 4
PROBE__psc_block_hdr__recsize_div4__SGN:
	.space	4
	.globl	PROBE__psc_block_hdr__count__OFF
	.align	2
	.type	PROBE__psc_block_hdr__count__OFF, @object
	.size	PROBE__psc_block_hdr__count__OFF, 4
PROBE__psc_block_hdr__count__OFF:
	.word	2
	.globl	PROBE__psc_block_hdr__count__ESZ
	.align	2
	.type	PROBE__psc_block_hdr__count__ESZ, @object
	.size	PROBE__psc_block_hdr__count__ESZ, 4
PROBE__psc_block_hdr__count__ESZ:
	.word	2
	.globl	PROBE__psc_block_hdr__count__TSZ
	.align	2
	.type	PROBE__psc_block_hdr__count__TSZ, @object
	.size	PROBE__psc_block_hdr__count__TSZ, 4
PROBE__psc_block_hdr__count__TSZ:
	.word	2
	.globl	PROBE__psc_block_hdr__count__SGN
	.align	2
	.type	PROBE__psc_block_hdr__count__SGN, @object
	.size	PROBE__psc_block_hdr__count__SGN, 4
PROBE__psc_block_hdr__count__SGN:
	.space	4
	.globl	PROBE__psc_block_hdr__lost__OFF
	.align	2
	.type	PROBE__psc_block_hdr__lost__OFF, @object
	.size	PROBE__psc_block_hdr__lost__OFF, 4
PROBE__psc_block_hdr__lost__OFF:
	.word	4
	.globl	PROBE__psc_block_hdr__lost__ESZ
	.align	2
	.type	PROBE__psc_block_hdr__lost__ESZ, @object
	.size	PROBE__psc_block_hdr__lost__ESZ, 4
PROBE__psc_block_hdr__lost__ESZ:
	.word	4
	.globl	PROBE__psc_block_hdr__lost__TSZ
	.align	2
	.type	PROBE__psc_block_hdr__lost__TSZ, @object
	.size	PROBE__psc_block_hdr__lost__TSZ, 4
PROBE__psc_block_hdr__lost__TSZ:
	.word	4
	.globl	PROBE__psc_block_hdr__lost__SGN
	.align	2
	.type	PROBE__psc_block_hdr__lost__SGN, @object
	.size	PROBE__psc_block_hdr__lost__SGN, 4
PROBE__psc_block_hdr__lost__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__SIZE
	.align	2
	.type	PROBE__psc_filehdr__SIZE, @object
	.size	PROBE__psc_filehdr__SIZE, 4
PROBE__psc_filehdr__SIZE:
	.word	44
	.globl	PROBE__psc_filehdr__magic__OFF
	.align	2
	.type	PROBE__psc_filehdr__magic__OFF, @object
	.size	PROBE__psc_filehdr__magic__OFF, 4
PROBE__psc_filehdr__magic__OFF:
	.space	4
	.globl	PROBE__psc_filehdr__magic__ESZ
	.align	2
	.type	PROBE__psc_filehdr__magic__ESZ, @object
	.size	PROBE__psc_filehdr__magic__ESZ, 4
PROBE__psc_filehdr__magic__ESZ:
	.word	1
	.globl	PROBE__psc_filehdr__magic__TSZ
	.align	2
	.type	PROBE__psc_filehdr__magic__TSZ, @object
	.size	PROBE__psc_filehdr__magic__TSZ, 4
PROBE__psc_filehdr__magic__TSZ:
	.word	8
	.globl	PROBE__psc_filehdr__magic__SGN
	.align	2
	.type	PROBE__psc_filehdr__magic__SGN, @object
	.size	PROBE__psc_filehdr__magic__SGN, 4
PROBE__psc_filehdr__magic__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__fmt__OFF
	.align	2
	.type	PROBE__psc_filehdr__fmt__OFF, @object
	.size	PROBE__psc_filehdr__fmt__OFF, 4
PROBE__psc_filehdr__fmt__OFF:
	.word	8
	.globl	PROBE__psc_filehdr__fmt__ESZ
	.align	2
	.type	PROBE__psc_filehdr__fmt__ESZ, @object
	.size	PROBE__psc_filehdr__fmt__ESZ, 4
PROBE__psc_filehdr__fmt__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__fmt__TSZ
	.align	2
	.type	PROBE__psc_filehdr__fmt__TSZ, @object
	.size	PROBE__psc_filehdr__fmt__TSZ, 4
PROBE__psc_filehdr__fmt__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__fmt__SGN
	.align	2
	.type	PROBE__psc_filehdr__fmt__SGN, @object
	.size	PROBE__psc_filehdr__fmt__SGN, 4
PROBE__psc_filehdr__fmt__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__run__OFF
	.align	2
	.type	PROBE__psc_filehdr__run__OFF, @object
	.size	PROBE__psc_filehdr__run__OFF, 4
PROBE__psc_filehdr__run__OFF:
	.word	12
	.globl	PROBE__psc_filehdr__run__ESZ
	.align	2
	.type	PROBE__psc_filehdr__run__ESZ, @object
	.size	PROBE__psc_filehdr__run__ESZ, 4
PROBE__psc_filehdr__run__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__run__TSZ
	.align	2
	.type	PROBE__psc_filehdr__run__TSZ, @object
	.size	PROBE__psc_filehdr__run__TSZ, 4
PROBE__psc_filehdr__run__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__run__SGN
	.align	2
	.type	PROBE__psc_filehdr__run__SGN, @object
	.size	PROBE__psc_filehdr__run__SGN, 4
PROBE__psc_filehdr__run__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__seg__OFF
	.align	2
	.type	PROBE__psc_filehdr__seg__OFF, @object
	.size	PROBE__psc_filehdr__seg__OFF, 4
PROBE__psc_filehdr__seg__OFF:
	.word	16
	.globl	PROBE__psc_filehdr__seg__ESZ
	.align	2
	.type	PROBE__psc_filehdr__seg__ESZ, @object
	.size	PROBE__psc_filehdr__seg__ESZ, 4
PROBE__psc_filehdr__seg__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__seg__TSZ
	.align	2
	.type	PROBE__psc_filehdr__seg__TSZ, @object
	.size	PROBE__psc_filehdr__seg__TSZ, 4
PROBE__psc_filehdr__seg__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__seg__SGN
	.align	2
	.type	PROBE__psc_filehdr__seg__SGN, @object
	.size	PROBE__psc_filehdr__seg__SGN, 4
PROBE__psc_filehdr__seg__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__inst__OFF
	.align	2
	.type	PROBE__psc_filehdr__inst__OFF, @object
	.size	PROBE__psc_filehdr__inst__OFF, 4
PROBE__psc_filehdr__inst__OFF:
	.word	20
	.globl	PROBE__psc_filehdr__inst__ESZ
	.align	2
	.type	PROBE__psc_filehdr__inst__ESZ, @object
	.size	PROBE__psc_filehdr__inst__ESZ, 4
PROBE__psc_filehdr__inst__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__inst__TSZ
	.align	2
	.type	PROBE__psc_filehdr__inst__TSZ, @object
	.size	PROBE__psc_filehdr__inst__TSZ, 4
PROBE__psc_filehdr__inst__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__inst__SGN
	.align	2
	.type	PROBE__psc_filehdr__inst__SGN, @object
	.size	PROBE__psc_filehdr__inst__SGN, 4
PROBE__psc_filehdr__inst__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__writer_pid__OFF
	.align	2
	.type	PROBE__psc_filehdr__writer_pid__OFF, @object
	.size	PROBE__psc_filehdr__writer_pid__OFF, 4
PROBE__psc_filehdr__writer_pid__OFF:
	.word	24
	.globl	PROBE__psc_filehdr__writer_pid__ESZ
	.align	2
	.type	PROBE__psc_filehdr__writer_pid__ESZ, @object
	.size	PROBE__psc_filehdr__writer_pid__ESZ, 4
PROBE__psc_filehdr__writer_pid__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__writer_pid__TSZ
	.align	2
	.type	PROBE__psc_filehdr__writer_pid__TSZ, @object
	.size	PROBE__psc_filehdr__writer_pid__TSZ, 4
PROBE__psc_filehdr__writer_pid__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__writer_pid__SGN
	.align	2
	.type	PROBE__psc_filehdr__writer_pid__SGN, @object
	.size	PROBE__psc_filehdr__writer_pid__SGN, 4
PROBE__psc_filehdr__writer_pid__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__sup_pid__OFF
	.align	2
	.type	PROBE__psc_filehdr__sup_pid__OFF, @object
	.size	PROBE__psc_filehdr__sup_pid__OFF, 4
PROBE__psc_filehdr__sup_pid__OFF:
	.word	28
	.globl	PROBE__psc_filehdr__sup_pid__ESZ
	.align	2
	.type	PROBE__psc_filehdr__sup_pid__ESZ, @object
	.size	PROBE__psc_filehdr__sup_pid__ESZ, 4
PROBE__psc_filehdr__sup_pid__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__sup_pid__TSZ
	.align	2
	.type	PROBE__psc_filehdr__sup_pid__TSZ, @object
	.size	PROBE__psc_filehdr__sup_pid__TSZ, 4
PROBE__psc_filehdr__sup_pid__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__sup_pid__SGN
	.align	2
	.type	PROBE__psc_filehdr__sup_pid__SGN, @object
	.size	PROBE__psc_filehdr__sup_pid__SGN, 4
PROBE__psc_filehdr__sup_pid__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__now_tick__OFF
	.align	2
	.type	PROBE__psc_filehdr__now_tick__OFF, @object
	.size	PROBE__psc_filehdr__now_tick__OFF, 4
PROBE__psc_filehdr__now_tick__OFF:
	.word	32
	.globl	PROBE__psc_filehdr__now_tick__ESZ
	.align	2
	.type	PROBE__psc_filehdr__now_tick__ESZ, @object
	.size	PROBE__psc_filehdr__now_tick__ESZ, 4
PROBE__psc_filehdr__now_tick__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__now_tick__TSZ
	.align	2
	.type	PROBE__psc_filehdr__now_tick__TSZ, @object
	.size	PROBE__psc_filehdr__now_tick__TSZ, 4
PROBE__psc_filehdr__now_tick__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__now_tick__SGN
	.align	2
	.type	PROBE__psc_filehdr__now_tick__SGN, @object
	.size	PROBE__psc_filehdr__now_tick__SGN, 4
PROBE__psc_filehdr__now_tick__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__now_jiffies__OFF
	.align	2
	.type	PROBE__psc_filehdr__now_jiffies__OFF, @object
	.size	PROBE__psc_filehdr__now_jiffies__OFF, 4
PROBE__psc_filehdr__now_jiffies__OFF:
	.word	36
	.globl	PROBE__psc_filehdr__now_jiffies__ESZ
	.align	2
	.type	PROBE__psc_filehdr__now_jiffies__ESZ, @object
	.size	PROBE__psc_filehdr__now_jiffies__ESZ, 4
PROBE__psc_filehdr__now_jiffies__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__now_jiffies__TSZ
	.align	2
	.type	PROBE__psc_filehdr__now_jiffies__TSZ, @object
	.size	PROBE__psc_filehdr__now_jiffies__TSZ, 4
PROBE__psc_filehdr__now_jiffies__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__now_jiffies__SGN
	.align	2
	.type	PROBE__psc_filehdr__now_jiffies__SGN, @object
	.size	PROBE__psc_filehdr__now_jiffies__SGN, 4
PROBE__psc_filehdr__now_jiffies__SGN:
	.space	4
	.globl	PROBE__psc_filehdr__nonce__OFF
	.align	2
	.type	PROBE__psc_filehdr__nonce__OFF, @object
	.size	PROBE__psc_filehdr__nonce__OFF, 4
PROBE__psc_filehdr__nonce__OFF:
	.word	40
	.globl	PROBE__psc_filehdr__nonce__ESZ
	.align	2
	.type	PROBE__psc_filehdr__nonce__ESZ, @object
	.size	PROBE__psc_filehdr__nonce__ESZ, 4
PROBE__psc_filehdr__nonce__ESZ:
	.word	4
	.globl	PROBE__psc_filehdr__nonce__TSZ
	.align	2
	.type	PROBE__psc_filehdr__nonce__TSZ, @object
	.size	PROBE__psc_filehdr__nonce__TSZ, 4
PROBE__psc_filehdr__nonce__TSZ:
	.word	4
	.globl	PROBE__psc_filehdr__nonce__SGN
	.align	2
	.type	PROBE__psc_filehdr__nonce__SGN, @object
	.size	PROBE__psc_filehdr__nonce__SGN, 4
PROBE__psc_filehdr__nonce__SGN:
	.space	4
	.globl	PROBE__psc_uhb__SIZE
	.align	2
	.type	PROBE__psc_uhb__SIZE, @object
	.size	PROBE__psc_uhb__SIZE, 4
PROBE__psc_uhb__SIZE:
	.word	84
	.globl	PROBE__psc_uhb__tickno__OFF
	.align	2
	.type	PROBE__psc_uhb__tickno__OFF, @object
	.size	PROBE__psc_uhb__tickno__OFF, 4
PROBE__psc_uhb__tickno__OFF:
	.space	4
	.globl	PROBE__psc_uhb__tickno__ESZ
	.align	2
	.type	PROBE__psc_uhb__tickno__ESZ, @object
	.size	PROBE__psc_uhb__tickno__ESZ, 4
PROBE__psc_uhb__tickno__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__tickno__TSZ
	.align	2
	.type	PROBE__psc_uhb__tickno__TSZ, @object
	.size	PROBE__psc_uhb__tickno__TSZ, 4
PROBE__psc_uhb__tickno__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__tickno__SGN
	.align	2
	.type	PROBE__psc_uhb__tickno__SGN, @object
	.size	PROBE__psc_uhb__tickno__SGN, 4
PROBE__psc_uhb__tickno__SGN:
	.space	4
	.globl	PROBE__psc_uhb__stats_now_tick__OFF
	.align	2
	.type	PROBE__psc_uhb__stats_now_tick__OFF, @object
	.size	PROBE__psc_uhb__stats_now_tick__OFF, 4
PROBE__psc_uhb__stats_now_tick__OFF:
	.word	4
	.globl	PROBE__psc_uhb__stats_now_tick__ESZ
	.align	2
	.type	PROBE__psc_uhb__stats_now_tick__ESZ, @object
	.size	PROBE__psc_uhb__stats_now_tick__ESZ, 4
PROBE__psc_uhb__stats_now_tick__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__stats_now_tick__TSZ
	.align	2
	.type	PROBE__psc_uhb__stats_now_tick__TSZ, @object
	.size	PROBE__psc_uhb__stats_now_tick__TSZ, 4
PROBE__psc_uhb__stats_now_tick__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__stats_now_tick__SGN
	.align	2
	.type	PROBE__psc_uhb__stats_now_tick__SGN, @object
	.size	PROBE__psc_uhb__stats_now_tick__SGN, 4
PROBE__psc_uhb__stats_now_tick__SGN:
	.space	4
	.globl	PROBE__psc_uhb__gtod_sec__OFF
	.align	2
	.type	PROBE__psc_uhb__gtod_sec__OFF, @object
	.size	PROBE__psc_uhb__gtod_sec__OFF, 4
PROBE__psc_uhb__gtod_sec__OFF:
	.word	8
	.globl	PROBE__psc_uhb__gtod_sec__ESZ
	.align	2
	.type	PROBE__psc_uhb__gtod_sec__ESZ, @object
	.size	PROBE__psc_uhb__gtod_sec__ESZ, 4
PROBE__psc_uhb__gtod_sec__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__gtod_sec__TSZ
	.align	2
	.type	PROBE__psc_uhb__gtod_sec__TSZ, @object
	.size	PROBE__psc_uhb__gtod_sec__TSZ, 4
PROBE__psc_uhb__gtod_sec__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__gtod_sec__SGN
	.align	2
	.type	PROBE__psc_uhb__gtod_sec__SGN, @object
	.size	PROBE__psc_uhb__gtod_sec__SGN, 4
PROBE__psc_uhb__gtod_sec__SGN:
	.space	4
	.globl	PROBE__psc_uhb__gtod_usec__OFF
	.align	2
	.type	PROBE__psc_uhb__gtod_usec__OFF, @object
	.size	PROBE__psc_uhb__gtod_usec__OFF, 4
PROBE__psc_uhb__gtod_usec__OFF:
	.word	12
	.globl	PROBE__psc_uhb__gtod_usec__ESZ
	.align	2
	.type	PROBE__psc_uhb__gtod_usec__ESZ, @object
	.size	PROBE__psc_uhb__gtod_usec__ESZ, 4
PROBE__psc_uhb__gtod_usec__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__gtod_usec__TSZ
	.align	2
	.type	PROBE__psc_uhb__gtod_usec__TSZ, @object
	.size	PROBE__psc_uhb__gtod_usec__TSZ, 4
PROBE__psc_uhb__gtod_usec__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__gtod_usec__SGN
	.align	2
	.type	PROBE__psc_uhb__gtod_usec__SGN, @object
	.size	PROBE__psc_uhb__gtod_usec__SGN, 4
PROBE__psc_uhb__gtod_usec__SGN:
	.space	4
	.globl	PROBE__psc_uhb__uptime_cs__OFF
	.align	2
	.type	PROBE__psc_uhb__uptime_cs__OFF, @object
	.size	PROBE__psc_uhb__uptime_cs__OFF, 4
PROBE__psc_uhb__uptime_cs__OFF:
	.word	16
	.globl	PROBE__psc_uhb__uptime_cs__ESZ
	.align	2
	.type	PROBE__psc_uhb__uptime_cs__ESZ, @object
	.size	PROBE__psc_uhb__uptime_cs__ESZ, 4
PROBE__psc_uhb__uptime_cs__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__uptime_cs__TSZ
	.align	2
	.type	PROBE__psc_uhb__uptime_cs__TSZ, @object
	.size	PROBE__psc_uhb__uptime_cs__TSZ, 4
PROBE__psc_uhb__uptime_cs__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__uptime_cs__SGN
	.align	2
	.type	PROBE__psc_uhb__uptime_cs__SGN, @object
	.size	PROBE__psc_uhb__uptime_cs__SGN, 4
PROBE__psc_uhb__uptime_cs__SGN:
	.space	4
	.globl	PROBE__psc_uhb__memfree_kb__OFF
	.align	2
	.type	PROBE__psc_uhb__memfree_kb__OFF, @object
	.size	PROBE__psc_uhb__memfree_kb__OFF, 4
PROBE__psc_uhb__memfree_kb__OFF:
	.word	20
	.globl	PROBE__psc_uhb__memfree_kb__ESZ
	.align	2
	.type	PROBE__psc_uhb__memfree_kb__ESZ, @object
	.size	PROBE__psc_uhb__memfree_kb__ESZ, 4
PROBE__psc_uhb__memfree_kb__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__memfree_kb__TSZ
	.align	2
	.type	PROBE__psc_uhb__memfree_kb__TSZ, @object
	.size	PROBE__psc_uhb__memfree_kb__TSZ, 4
PROBE__psc_uhb__memfree_kb__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__memfree_kb__SGN
	.align	2
	.type	PROBE__psc_uhb__memfree_kb__SGN, @object
	.size	PROBE__psc_uhb__memfree_kb__SGN, 4
PROBE__psc_uhb__memfree_kb__SGN:
	.space	4
	.globl	PROBE__psc_uhb__mouse_pkts_total__OFF
	.align	2
	.type	PROBE__psc_uhb__mouse_pkts_total__OFF, @object
	.size	PROBE__psc_uhb__mouse_pkts_total__OFF, 4
PROBE__psc_uhb__mouse_pkts_total__OFF:
	.word	24
	.globl	PROBE__psc_uhb__mouse_pkts_total__ESZ
	.align	2
	.type	PROBE__psc_uhb__mouse_pkts_total__ESZ, @object
	.size	PROBE__psc_uhb__mouse_pkts_total__ESZ, 4
PROBE__psc_uhb__mouse_pkts_total__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__mouse_pkts_total__TSZ
	.align	2
	.type	PROBE__psc_uhb__mouse_pkts_total__TSZ, @object
	.size	PROBE__psc_uhb__mouse_pkts_total__TSZ, 4
PROBE__psc_uhb__mouse_pkts_total__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__mouse_pkts_total__SGN
	.align	2
	.type	PROBE__psc_uhb__mouse_pkts_total__SGN, @object
	.size	PROBE__psc_uhb__mouse_pkts_total__SGN, 4
PROBE__psc_uhb__mouse_pkts_total__SGN:
	.space	4
	.globl	PROBE__psc_uhb__mouse_press_total__OFF
	.align	2
	.type	PROBE__psc_uhb__mouse_press_total__OFF, @object
	.size	PROBE__psc_uhb__mouse_press_total__OFF, 4
PROBE__psc_uhb__mouse_press_total__OFF:
	.word	28
	.globl	PROBE__psc_uhb__mouse_press_total__ESZ
	.align	2
	.type	PROBE__psc_uhb__mouse_press_total__ESZ, @object
	.size	PROBE__psc_uhb__mouse_press_total__ESZ, 4
PROBE__psc_uhb__mouse_press_total__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__mouse_press_total__TSZ
	.align	2
	.type	PROBE__psc_uhb__mouse_press_total__TSZ, @object
	.size	PROBE__psc_uhb__mouse_press_total__TSZ, 4
PROBE__psc_uhb__mouse_press_total__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__mouse_press_total__SGN
	.align	2
	.type	PROBE__psc_uhb__mouse_press_total__SGN, @object
	.size	PROBE__psc_uhb__mouse_press_total__SGN, 4
PROBE__psc_uhb__mouse_press_total__SGN:
	.space	4
	.globl	PROBE__psc_uhb__bytes_synced_total__OFF
	.align	2
	.type	PROBE__psc_uhb__bytes_synced_total__OFF, @object
	.size	PROBE__psc_uhb__bytes_synced_total__OFF, 4
PROBE__psc_uhb__bytes_synced_total__OFF:
	.word	32
	.globl	PROBE__psc_uhb__bytes_synced_total__ESZ
	.align	2
	.type	PROBE__psc_uhb__bytes_synced_total__ESZ, @object
	.size	PROBE__psc_uhb__bytes_synced_total__ESZ, 4
PROBE__psc_uhb__bytes_synced_total__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__bytes_synced_total__TSZ
	.align	2
	.type	PROBE__psc_uhb__bytes_synced_total__TSZ, @object
	.size	PROBE__psc_uhb__bytes_synced_total__TSZ, 4
PROBE__psc_uhb__bytes_synced_total__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__bytes_synced_total__SGN
	.align	2
	.type	PROBE__psc_uhb__bytes_synced_total__SGN, @object
	.size	PROBE__psc_uhb__bytes_synced_total__SGN, 4
PROBE__psc_uhb__bytes_synced_total__SGN:
	.space	4
	.globl	PROBE__psc_uhb__last_write_ms__OFF
	.align	2
	.type	PROBE__psc_uhb__last_write_ms__OFF, @object
	.size	PROBE__psc_uhb__last_write_ms__OFF, 4
PROBE__psc_uhb__last_write_ms__OFF:
	.word	36
	.globl	PROBE__psc_uhb__last_write_ms__ESZ
	.align	2
	.type	PROBE__psc_uhb__last_write_ms__ESZ, @object
	.size	PROBE__psc_uhb__last_write_ms__ESZ, 4
PROBE__psc_uhb__last_write_ms__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__last_write_ms__TSZ
	.align	2
	.type	PROBE__psc_uhb__last_write_ms__TSZ, @object
	.size	PROBE__psc_uhb__last_write_ms__TSZ, 4
PROBE__psc_uhb__last_write_ms__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__last_write_ms__SGN
	.align	2
	.type	PROBE__psc_uhb__last_write_ms__SGN, @object
	.size	PROBE__psc_uhb__last_write_ms__SGN, 4
PROBE__psc_uhb__last_write_ms__SGN:
	.space	4
	.globl	PROBE__psc_uhb__last_fsync_ms__OFF
	.align	2
	.type	PROBE__psc_uhb__last_fsync_ms__OFF, @object
	.size	PROBE__psc_uhb__last_fsync_ms__OFF, 4
PROBE__psc_uhb__last_fsync_ms__OFF:
	.word	40
	.globl	PROBE__psc_uhb__last_fsync_ms__ESZ
	.align	2
	.type	PROBE__psc_uhb__last_fsync_ms__ESZ, @object
	.size	PROBE__psc_uhb__last_fsync_ms__ESZ, 4
PROBE__psc_uhb__last_fsync_ms__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__last_fsync_ms__TSZ
	.align	2
	.type	PROBE__psc_uhb__last_fsync_ms__TSZ, @object
	.size	PROBE__psc_uhb__last_fsync_ms__TSZ, 4
PROBE__psc_uhb__last_fsync_ms__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__last_fsync_ms__SGN
	.align	2
	.type	PROBE__psc_uhb__last_fsync_ms__SGN, @object
	.size	PROBE__psc_uhb__last_fsync_ms__SGN, 4
PROBE__psc_uhb__last_fsync_ms__SGN:
	.space	4
	.globl	PROBE__psc_uhb__max_fsync_ms_60s__OFF
	.align	2
	.type	PROBE__psc_uhb__max_fsync_ms_60s__OFF, @object
	.size	PROBE__psc_uhb__max_fsync_ms_60s__OFF, 4
PROBE__psc_uhb__max_fsync_ms_60s__OFF:
	.word	44
	.globl	PROBE__psc_uhb__max_fsync_ms_60s__ESZ
	.align	2
	.type	PROBE__psc_uhb__max_fsync_ms_60s__ESZ, @object
	.size	PROBE__psc_uhb__max_fsync_ms_60s__ESZ, 4
PROBE__psc_uhb__max_fsync_ms_60s__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__max_fsync_ms_60s__TSZ
	.align	2
	.type	PROBE__psc_uhb__max_fsync_ms_60s__TSZ, @object
	.size	PROBE__psc_uhb__max_fsync_ms_60s__TSZ, 4
PROBE__psc_uhb__max_fsync_ms_60s__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__max_fsync_ms_60s__SGN
	.align	2
	.type	PROBE__psc_uhb__max_fsync_ms_60s__SGN, @object
	.size	PROBE__psc_uhb__max_fsync_ms_60s__SGN, 4
PROBE__psc_uhb__max_fsync_ms_60s__SGN:
	.space	4
	.globl	PROBE__psc_uhb__max_tick_ms_60s__OFF
	.align	2
	.type	PROBE__psc_uhb__max_tick_ms_60s__OFF, @object
	.size	PROBE__psc_uhb__max_tick_ms_60s__OFF, 4
PROBE__psc_uhb__max_tick_ms_60s__OFF:
	.word	48
	.globl	PROBE__psc_uhb__max_tick_ms_60s__ESZ
	.align	2
	.type	PROBE__psc_uhb__max_tick_ms_60s__ESZ, @object
	.size	PROBE__psc_uhb__max_tick_ms_60s__ESZ, 4
PROBE__psc_uhb__max_tick_ms_60s__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__max_tick_ms_60s__TSZ
	.align	2
	.type	PROBE__psc_uhb__max_tick_ms_60s__TSZ, @object
	.size	PROBE__psc_uhb__max_tick_ms_60s__TSZ, 4
PROBE__psc_uhb__max_tick_ms_60s__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__max_tick_ms_60s__SGN
	.align	2
	.type	PROBE__psc_uhb__max_tick_ms_60s__SGN, @object
	.size	PROBE__psc_uhb__max_tick_ms_60s__SGN, 4
PROBE__psc_uhb__max_tick_ms_60s__SGN:
	.space	4
	.globl	PROBE__psc_uhb__write_errs__OFF
	.align	2
	.type	PROBE__psc_uhb__write_errs__OFF, @object
	.size	PROBE__psc_uhb__write_errs__OFF, 4
PROBE__psc_uhb__write_errs__OFF:
	.word	52
	.globl	PROBE__psc_uhb__write_errs__ESZ
	.align	2
	.type	PROBE__psc_uhb__write_errs__ESZ, @object
	.size	PROBE__psc_uhb__write_errs__ESZ, 4
PROBE__psc_uhb__write_errs__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__write_errs__TSZ
	.align	2
	.type	PROBE__psc_uhb__write_errs__TSZ, @object
	.size	PROBE__psc_uhb__write_errs__TSZ, 4
PROBE__psc_uhb__write_errs__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__write_errs__SGN
	.align	2
	.type	PROBE__psc_uhb__write_errs__SGN, @object
	.size	PROBE__psc_uhb__write_errs__SGN, 4
PROBE__psc_uhb__write_errs__SGN:
	.space	4
	.globl	PROBE__psc_uhb__last_errno__OFF
	.align	2
	.type	PROBE__psc_uhb__last_errno__OFF, @object
	.size	PROBE__psc_uhb__last_errno__OFF, 4
PROBE__psc_uhb__last_errno__OFF:
	.word	56
	.globl	PROBE__psc_uhb__last_errno__ESZ
	.align	2
	.type	PROBE__psc_uhb__last_errno__ESZ, @object
	.size	PROBE__psc_uhb__last_errno__ESZ, 4
PROBE__psc_uhb__last_errno__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__last_errno__TSZ
	.align	2
	.type	PROBE__psc_uhb__last_errno__TSZ, @object
	.size	PROBE__psc_uhb__last_errno__TSZ, 4
PROBE__psc_uhb__last_errno__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__last_errno__SGN
	.align	2
	.type	PROBE__psc_uhb__last_errno__SGN, @object
	.size	PROBE__psc_uhb__last_errno__SGN, 4
PROBE__psc_uhb__last_errno__SGN:
	.space	4
	.globl	PROBE__psc_uhb__flags__OFF
	.align	2
	.type	PROBE__psc_uhb__flags__OFF, @object
	.size	PROBE__psc_uhb__flags__OFF, 4
PROBE__psc_uhb__flags__OFF:
	.word	60
	.globl	PROBE__psc_uhb__flags__ESZ
	.align	2
	.type	PROBE__psc_uhb__flags__ESZ, @object
	.size	PROBE__psc_uhb__flags__ESZ, 4
PROBE__psc_uhb__flags__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__flags__TSZ
	.align	2
	.type	PROBE__psc_uhb__flags__TSZ, @object
	.size	PROBE__psc_uhb__flags__TSZ, 4
PROBE__psc_uhb__flags__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__flags__SGN
	.align	2
	.type	PROBE__psc_uhb__flags__SGN, @object
	.size	PROBE__psc_uhb__flags__SGN, 4
PROBE__psc_uhb__flags__SGN:
	.space	4
	.globl	PROBE__psc_uhb__durable_tick__OFF
	.align	2
	.type	PROBE__psc_uhb__durable_tick__OFF, @object
	.size	PROBE__psc_uhb__durable_tick__OFF, 4
PROBE__psc_uhb__durable_tick__OFF:
	.word	64
	.globl	PROBE__psc_uhb__durable_tick__ESZ
	.align	2
	.type	PROBE__psc_uhb__durable_tick__ESZ, @object
	.size	PROBE__psc_uhb__durable_tick__ESZ, 4
PROBE__psc_uhb__durable_tick__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__durable_tick__TSZ
	.align	2
	.type	PROBE__psc_uhb__durable_tick__TSZ, @object
	.size	PROBE__psc_uhb__durable_tick__TSZ, 4
PROBE__psc_uhb__durable_tick__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__durable_tick__SGN
	.align	2
	.type	PROBE__psc_uhb__durable_tick__SGN, @object
	.size	PROBE__psc_uhb__durable_tick__SGN, 4
PROBE__psc_uhb__durable_tick__SGN:
	.space	4
	.globl	PROBE__psc_uhb__lag_max__OFF
	.align	2
	.type	PROBE__psc_uhb__lag_max__OFF, @object
	.size	PROBE__psc_uhb__lag_max__OFF, 4
PROBE__psc_uhb__lag_max__OFF:
	.word	68
	.globl	PROBE__psc_uhb__lag_max__ESZ
	.align	2
	.type	PROBE__psc_uhb__lag_max__ESZ, @object
	.size	PROBE__psc_uhb__lag_max__ESZ, 4
PROBE__psc_uhb__lag_max__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__lag_max__TSZ
	.align	2
	.type	PROBE__psc_uhb__lag_max__TSZ, @object
	.size	PROBE__psc_uhb__lag_max__TSZ, 4
PROBE__psc_uhb__lag_max__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__lag_max__SGN
	.align	2
	.type	PROBE__psc_uhb__lag_max__SGN, @object
	.size	PROBE__psc_uhb__lag_max__SGN, 4
PROBE__psc_uhb__lag_max__SGN:
	.space	4
	.globl	PROBE__psc_uhb__seg__OFF
	.align	2
	.type	PROBE__psc_uhb__seg__OFF, @object
	.size	PROBE__psc_uhb__seg__OFF, 4
PROBE__psc_uhb__seg__OFF:
	.word	72
	.globl	PROBE__psc_uhb__seg__ESZ
	.align	2
	.type	PROBE__psc_uhb__seg__ESZ, @object
	.size	PROBE__psc_uhb__seg__ESZ, 4
PROBE__psc_uhb__seg__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__seg__TSZ
	.align	2
	.type	PROBE__psc_uhb__seg__TSZ, @object
	.size	PROBE__psc_uhb__seg__TSZ, 4
PROBE__psc_uhb__seg__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__seg__SGN
	.align	2
	.type	PROBE__psc_uhb__seg__SGN, @object
	.size	PROBE__psc_uhb__seg__SGN, 4
PROBE__psc_uhb__seg__SGN:
	.space	4
	.globl	PROBE__psc_uhb__drain_stuck__OFF
	.align	2
	.type	PROBE__psc_uhb__drain_stuck__OFF, @object
	.size	PROBE__psc_uhb__drain_stuck__OFF, 4
PROBE__psc_uhb__drain_stuck__OFF:
	.word	76
	.globl	PROBE__psc_uhb__drain_stuck__ESZ
	.align	2
	.type	PROBE__psc_uhb__drain_stuck__ESZ, @object
	.size	PROBE__psc_uhb__drain_stuck__ESZ, 4
PROBE__psc_uhb__drain_stuck__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__drain_stuck__TSZ
	.align	2
	.type	PROBE__psc_uhb__drain_stuck__TSZ, @object
	.size	PROBE__psc_uhb__drain_stuck__TSZ, 4
PROBE__psc_uhb__drain_stuck__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__drain_stuck__SGN
	.align	2
	.type	PROBE__psc_uhb__drain_stuck__SGN, @object
	.size	PROBE__psc_uhb__drain_stuck__SGN, 4
PROBE__psc_uhb__drain_stuck__SGN:
	.space	4
	.globl	PROBE__psc_uhb__nonce__OFF
	.align	2
	.type	PROBE__psc_uhb__nonce__OFF, @object
	.size	PROBE__psc_uhb__nonce__OFF, 4
PROBE__psc_uhb__nonce__OFF:
	.word	80
	.globl	PROBE__psc_uhb__nonce__ESZ
	.align	2
	.type	PROBE__psc_uhb__nonce__ESZ, @object
	.size	PROBE__psc_uhb__nonce__ESZ, 4
PROBE__psc_uhb__nonce__ESZ:
	.word	4
	.globl	PROBE__psc_uhb__nonce__TSZ
	.align	2
	.type	PROBE__psc_uhb__nonce__TSZ, @object
	.size	PROBE__psc_uhb__nonce__TSZ, 4
PROBE__psc_uhb__nonce__TSZ:
	.word	4
	.globl	PROBE__psc_uhb__nonce__SGN
	.align	2
	.type	PROBE__psc_uhb__nonce__SGN, @object
	.size	PROBE__psc_uhb__nonce__SGN, 4
PROBE__psc_uhb__nonce__SGN:
	.space	4
	.ident	"GCC: (GNU) 4.2.1"
