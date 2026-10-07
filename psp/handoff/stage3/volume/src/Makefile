# Stage 3 VOLUME harness. Builds the real collector source (unchanged) with the
# harness's own os_* layer. Output: ../build/volsim
PSCOL   := /home/ubuntu/psp/work/pscol
TELEM   := /home/ubuntu/psp/telem/telem.c
BUILD   := ../build
CFLAGS  := -O2 -g -Wall -W -Wno-unused-parameter -DPSCOL_HOST -I$(PSCOL) -I$(BUILD)

all: $(BUILD)/volsim

$(BUILD)/telem_font.h: font_from_telem.py $(TELEM) $(PSCOL)/pscol.c
	mkdir -p $(BUILD)
	python3 font_from_telem.py $(TELEM) $(PSCOL)/pscol.c $@

$(BUILD)/pscol.o: $(PSCOL)/pscol.c $(PSCOL)/pscol.h
	mkdir -p $(BUILD)
	gcc $(CFLAGS) -std=gnu89 -c -o $@ $(PSCOL)/pscol.c

$(BUILD)/volsim.o: volsim.c $(BUILD)/telem_font.h $(PSCOL)/pscol.h
	gcc $(CFLAGS) -std=gnu99 -c -o $@ volsim.c

$(BUILD)/volsim: $(BUILD)/volsim.o $(BUILD)/pscol.o
	gcc -o $@ $^

clean:
	rm -rf $(BUILD)
