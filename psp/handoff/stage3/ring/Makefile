# Stage 3 ring-logic test (handoff/stage3/ring). See README.md; evidence in ../logs/ring-*.
#
#   make            build (after checking the kernel sources are the released ones)
#   make test       unit tests (nwords table, reader, barrier/single-step injection)
#   make dumps      run every scenario, write ../dumps/<name>/ (+ truth.json "observed")
#   make oracle     recompute every record from the event logs, compare byte for byte
#   make crosscheck informational: run work/decoder over every dump
#   make all-checks build + test + dumps + oracle + manifest check
#   make clean
#
# Host: aarch64 Linux, gcc/g++ 13, LP64 little-endian (the target is mipsel,
# also little-endian; the formats are LE only, psc_format.h:35-37).

KSRC    := /home/ubuntu/psp/work/linux
KREV    := 48dcc1b9
BUILD   := /home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD
STAGE3  := /home/ubuntu/psp/handoff/stage3
DUMPS   := $(STAGE3)/dumps
LOGS    := $(STAGE3)/logs
B       := build

# the kernel files compiled under test (unmodified)
KFILES  := arch/mips/psp/psc.c arch/mips/psp/psc_panel.c arch/mips/psp/ipl_sdk/syscon.c \
           drivers/input/joypad_psp.c include/asm-mips/psc.h include/linux/psc_format.h \
           include/asm-mips/psp.h include/asm-mips/ipl_sdk/syscon.h \
           include/asm-mips/ipl_sdk/kprintf.h include/asm-mips/ipl_sdk/sysreg.h \
           include/asm-mips/ipl_sdk/cache.h

INC     := -Isrc/stubinc -Isrc/realinc -Isrc
DEFS    := -DCONFIG_PSP_ADDRESS_BASE=0x80000000 -D__KERNEL__
NOUNW   := -fno-asynchronous-unwind-tables -fno-unwind-tables
KCFLAGS := -std=gnu89 -O2 -g -Wall -Wno-unused-function -Wno-unused-parameter \
           -fno-strict-aliasing -fno-common -ffunction-sections -falign-functions=4 -falign-loops=4 -falign-jumps=4 -falign-labels=4 $(NOUNW) \
           $(INC) $(DEFS)
HCFLAGS := -std=gnu11 -O2 -g -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare \
           -fno-strict-aliasing $(NOUNW) $(INC) $(DEFS)
CXXFLAGS:= -std=gnu++17 -O2 -g -Wall -Wno-unused-parameter -fno-exceptions -fno-rtti \
           -ffunction-sections -falign-functions=4 -falign-loops=4 -falign-jumps=4 -falign-labels=4 $(NOUNW) $(INC) \
           -DSYSCON_C_PATH='"$(KSRC)/arch/mips/psp/ipl_sdk/syscon.c"'

COMMON  := $(B)/psc.o $(B)/psc_panel.o $(B)/syscon_host.o $(B)/joypad_host.o \
           $(B)/sim.o $(B)/mmio.o $(B)/collector.o $(B)/banner.o

.PHONY: all test dumps oracle crosscheck all-checks clean srccheck

all: srccheck $(B)/ringsim $(B)/ringtest

$(B):
	mkdir -p $(B)

# the sources under test must be the released commit's bytes
srccheck: | $(B)
	@cd $(KSRC) && for f in $(KFILES); do \
	  a=$$(sha256sum < $$f | cut -c1-64); b=$$(git show $(KREV):$$f | sha256sum | cut -c1-64); \
	  if [ "$$a" != "$$b" ]; then echo "SOURCE DIFFERS FROM $(KREV): $$f"; exit 1; fi; \
	  echo "$$a  $$f"; done > $(CURDIR)/$(B)/kernel-sources.sha256
	@mkdir -p $(LOGS) && cp $(B)/kernel-sources.sha256 $(LOGS)/ring-kernel-sources.sha256
	@echo "kernel sources = $(KREV): $$(wc -l < $(B)/kernel-sources.sha256) files"

$(B)/banner.c: $(BUILD)/banner.txt $(BUILD)/build_id.txt tools/mkbanner.py | $(B)
	python3 tools/mkbanner.py $(BUILD)/banner.txt $(BUILD)/build_id.txt > $@

$(B)/banner.o: $(B)/banner.c
	gcc -std=gnu11 -O2 -c $< -o $@

$(B)/psc.o: $(KSRC)/arch/mips/psp/psc.c src/stubinc/host_kernel.h | $(B)
	gcc $(KCFLAGS) -c $< -o $@

$(B)/psc_panel.o: $(KSRC)/arch/mips/psp/psc_panel.c src/stubinc/host_kernel.h | $(B)
	gcc $(KCFLAGS) -c $< -o $@

$(B)/joypad_host.o: src/joypad_host.c $(KSRC)/drivers/input/joypad_psp.c src/host.h | $(B)
	gcc $(KCFLAGS) -DJOYPAD_C_PATH='"$(KSRC)/drivers/input/joypad_psp.c"' -c $< -o $@

$(B)/syscon_host.o: src/syscon_host.cc src/stubinc/psptypes.h $(KSRC)/arch/mips/psp/ipl_sdk/syscon.c | $(B)
	g++ $(CXXFLAGS) -c $< -o $@

$(B)/%.o: src/%.c src/host.h | $(B)
	gcc $(HCFLAGS) -c $< -o $@

$(B)/ringsim: $(COMMON) $(B)/scen.o src/place.ld
	g++ -no-pie -o $@ $(COMMON) $(B)/scen.o -Wl,-Ttext-segment=0x87f00000 -Wl,-T,src/place.ld -lm
	nm -n $@ > $(B)/ringsim.syms

$(B)/ringtest: $(COMMON) $(B)/tests.o $(B)/scenlib.o src/place.ld
	g++ -no-pie -o $@ $(COMMON) $(B)/tests.o $(B)/scenlib.o -Wl,-Ttext-segment=0x87f00000 -Wl,-T,src/place.ld -lm
	nm -n $@ > $(B)/ringtest.syms

# scen.c without its main(), for the unit tests
$(B)/scenlib.o: src/scen.c src/host.h | $(B)
	gcc $(HCFLAGS) -DSCEN_NO_MAIN -c $< -o $@

SCENARIOS := H1 H2 H3 H4 H5 H6 H7 H8 unclassified \
             mid-irq-P0 mid-irq-P1 mid-irq-P2 mid-irq-P3 mid-irq-P4 mid-irq-P5a \
             mid-irq-P5b mid-irq-P6 mid-irq-P6pop mid-irq-P7 mid-irq-append \
             mid-irq-entry

test: all
	$(B)/ringtest all 2>&1 | tee $(LOGS)/ring-unit-tests.log
	@grep -q '^RESULT PASS' $(LOGS)/ring-unit-tests.log

dumps: all
	@mkdir -p $(DUMPS) $(B)/ev
	@for s in $(SCENARIOS); do \
	  rm -rf $(DUMPS)/$$s; \
	  $(B)/ringsim $$s $(DUMPS)/$$s $(B)/ev/$$s.log > $(B)/ev/$$s.out 2>&1 || { echo "FAIL $$s"; cat $(B)/ev/$$s.out; exit 1; }; \
	  echo "== $$s"; cat $(B)/ev/$$s.out; \
	done 2>&1 | tee $(LOGS)/ring-dumps.log
	@! grep -q '^FAIL' $(LOGS)/ring-dumps.log
	python3 tools/signature.py $(DUMPS) $(B)/ev $(SCENARIOS) 2>&1 | tee $(LOGS)/ring-signatures.log
	cd $(DUMPS) && find . -type f | sort | xargs sha256sum > $(LOGS)/ring-dumps.sha256

oracle:
	python3 oracle/oracle.py --events $(B)/ev --dumps $(DUMPS) --syms $(B)/ringsim.syms \
	  $(SCENARIOS) 2>&1 | tee $(LOGS)/ring-oracle.log
	@grep -q 'scenarios failing: 0$$' $(LOGS)/ring-oracle.log

# informational: the analyst's decoder (work/decoder, read-only) over every dump
crosscheck:
	tools/decode_all.sh $(SCENARIOS) 2>&1 | tee $(LOGS)/ring-decoder-crosscheck.log

all-checks: test dumps oracle
	cd /home/ubuntu/psp/build/linux && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256; \
	  echo "original tree manifest exit $$?" | tee $(LOGS)/ring-manifest.log
	sha256sum /home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin | tee -a $(LOGS)/ring-manifest.log
	cd $(KSRC) && git status --porcelain -- arch include drivers | wc -l | sed 's/^/kernel tree modified files: /' | tee -a $(LOGS)/ring-manifest.log

clean:
	rm -rf $(B)
