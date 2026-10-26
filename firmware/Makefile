SDCC ?= sdcc
PACKIHX ?= packihx
CFLAGS ?= -mmcs51 --model-small --code-size 8192 --xram-size 8192 --iram-size 256

.PHONY: all srom_capture srom_zero_probe clean

all: usb_marker.hex

srom_capture: srom_capture.hex

srom_zero_probe: srom_zero_probe.hex

srom_zero_probe.hex: srom_zero_probe.rel
	$(SDCC) $(CFLAGS) --out-fmt-ihx -o srom_zero_probe.ihx srom_zero_probe.rel
	$(PACKIHX) srom_zero_probe.ihx > $@

srom_zero_probe.rel: srom_zero_probe.c
	$(SDCC) $(CFLAGS) -c $< -o $@

srom_capture.hex: srom_capture.rel
	$(SDCC) $(CFLAGS) --out-fmt-ihx -o srom_capture.ihx srom_capture.rel
	$(PACKIHX) srom_capture.ihx > $@

srom_capture.rel: srom_capture.c
	$(SDCC) $(CFLAGS) -c $< -o $@

usb_marker.hex: usb_marker.rel
	$(SDCC) $(CFLAGS) --out-fmt-ihx -o usb_marker.ihx usb_marker.rel
	$(PACKIHX) usb_marker.ihx > $@

usb_marker.rel: usb_marker.c
	$(SDCC) $(CFLAGS) -c $< -o $@

# raw code-RAM image from the Intel HEX (zero-based), as used by scripts/gt6816_ctl.py run-motor
%.bin: %.ihx
	objcopy -I ihex -O binary $< $@

clean:
	rm -f *.rel *.ihx *.hex *.bin *.lk *.lst *.map *.mem *.rst *.sym *.asm

.PHONY: motor_slowstep
motor_slowstep: motor_slowstep.hex

motor_slowstep.hex: motor_slowstep.rel
	$(SDCC) $(CFLAGS) --out-fmt-ihx -o motor_slowstep.ihx motor_slowstep.rel
	$(PACKIHX) motor_slowstep.ihx > $@

motor_slowstep.rel: motor_slowstep.c
	$(SDCC) $(CFLAGS) -c $< -o $@

.PHONY: motor_step
motor_step: motor_step.hex

motor_step.hex: motor_step.rel
	$(SDCC) $(CFLAGS) --out-fmt-ihx -o motor_step.ihx motor_step.rel
	$(PACKIHX) motor_step.ihx > $@

motor_step.rel: motor_step.c
	$(SDCC) $(CFLAGS) -c $< -o $@
