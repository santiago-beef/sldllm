#	 A uClinux port for Sony PlayStation Portable
#	 Created by Jackson Mo, Aug 29, 2007

IPL_SDK_OBJS = cache.o memstk.o psp_uart.o syscon.o sysreg.o
lib-$(CONFIG_SONY_PSP) += psp.o psplo.o \
	$(addprefix ipl_sdk/,$(IPL_SDK_OBJS))
CFLAGS += -I$(CONFIG_PSP_SDK_PATH)/include -I$(CONFIG_PSP_TOOLCHAIN_PATH)/include

# PSC trace (DESIGN 2.8, 2.10): rings, records, /proc/psc, stall panel
obj-$(CONFIG_SONY_PSP) += psc.o psc_panel.o
