# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A hardware reverse-engineering workspace for the **Plustek MobileOffice S400** sheet-fed scanner (USB `07b3:0465`): GrandTech **GT-6816** controller (8051 core, 8 KiB downloadable code RAM "M1"), a **24LC16B** I²C EEPROM, an **LB1940** stepper driver, an RGB CIS light bar. It is not a conventional software project: no git history yet, no test suite, no linter. State of the work, in short:

- The EEPROM was dumped (CH341A, twice, identical) and its 8051 code disassembled: it is a USB bootstrap, not scan firmware.
- Plustek's scan firmware (`cism603.fw`, from the vendor driver packages) is loaded over USB into code RAM and runs; we drive the **motor, light bar, power LED and read the buttons** with it (hardware facts below).
- Everything is volatile (code RAM only). **Nothing is ever written to the EEPROM.**

[readme.md](readme.md) is the summary; [docs/GT6816_USB_EEPROM_Reverse_Engineering.md](docs/GT6816_USB_EEPROM_Reverse_Engineering.md) holds the chronological notes (numbered sections, cited below as "notes §N"); [docs/GT-6816.pdf](docs/GT-6816.pdf) is the chip datasheet. Update the notes when new experiments are run.

## Evidence discipline (important)

- Distinguish direct observation, datasheet/source claims, and inference, and say which. Many results rest on the owner's eyes and ears (motion, light, sound); record them as such.
- The only verified EEPROM image is `captures/eeprom/gt6816_24lc16b_dump.bin` (SHA-256 `b21587f0…269f`, two identical reads, read-only files). Every file in `captures/ram/` is a code-RAM capture, never an EEPROM image.
- The datasheet's 44-pin drawing and pin table disagree in places (and GPIO0 drives the power LED although the table does not list it as bonded). Board wiring and voltages have not been measured.
- USB bus/device numbers change on every reconnect; never treat them as stable.
- A board **without** its EEPROM enumerates as the chip's ROM identity `055f:0210` ("Mustek ScanExpress A3 USB", notes §39); with it, `07b3:0465`. The "Mustek" was an S400 board; ignore that label in notes §36-38.

## Layout

- `scripts/` host tools, run from the repo root (`python3 -I scripts/<name>.py`); default output paths resolve relative to the repo root.
- `firmware/` 8051 C sources, Makefile, and the built `.ihx/.hex/.bin` images (compiler intermediates are git-ignored).
- `captures/eeprom/` the EEPROM dump; `captures/ram/` documented RAM captures; `logs/` run logs and scan results; `docs/` notes, datasheet, disassembly listings; `sane/` a private SANE config for experiments.
- `vendor/` Plustek's macOS and Windows driver packages and their extractions: untrusted third-party files, **read and disassemble only, never run**, git-ignored. The tools read `vendor/windows_s400/extracted/Data/74RU/cism603.fw`.

## Commands

All live commands are a dry run unless `--execute` is given. The USB node must be accessible (a udev rule makes `07b3:0465` world-accessible and turns autosuspend off; otherwise `sudo setfacl -m u:$(id -un):rw /dev/bus/usb/<bus>/<dev>`).

```bash
# Interactive motor console: finds the scanner, loads our firmware, asks speed / direction / steps
python3 -I scripts/motor_console.py [--no-hold]   # slow-start ramp for heavy loads; `r` releases the motor

# Scripted control
python3 -I scripts/gt6816_ctl.py info --skip-button
python3 -I scripts/gt6816_ctl.py load --execute [--jog-rate N] [--half-step] [--no-hold] [--free-led] [--backup]
python3 -I scripts/gt6816_ctl.py motor --steps 100 --direction b --execute   # b = cmd 14 = clockwise, a = cmd 15 = anticlockwise
python3 -I scripts/gt6816_ctl.py buttons --seconds 20      # A=0x88, B=0x02 (latched), optical = GPIO5 level
python3 -I scripts/gt6816_ctl.py lamp g --seconds 5 --execute        # CIS light bar: r/g/b
python3 -I scripts/gt6816_ctl.py rainbow --seconds 24 --execute
python3 -I scripts/gt6816_ctl.py load --free-led --execute && python3 -I scripts/gt6816_ctl.py blink --hz 2 --execute   # power LED
python3 -I scripts/gt6816_ctl.py normal 0x12 0x01 --execute          # release the motor coils

# EEPROM (CH341A in I2C mode, chip removed from the board; flashrom cannot read I2C EEPROMs)
python3 -I scripts/gt6816_ch341_eeprom_read.py --execute --speed 1   # --speed 0 (20 kHz) hangs

# Analysis
python3 -I scripts/gt6816_disasm.py <image> -o docs/<name>_disassembly.asm      # 8051 recursive disassembler
make -C firmware [motor_step.bin motor_slowstep.bin srom_capture srom_zero_probe]; make -C firmware clean
# Older probes: gt6816_usb_ram_dump.py, gt6816_ram_runner.py, gt6816_srom_capture.py, gt6816_vendor_scan.py
```

## Protocol and hardware facts (details in the notes)

- **Transport** (SANE `gt68xx_gt6816`): EP0 vendor control transfers, `bRequest 0x01`. RAM write/read `wValue 0x200B/0x200C` (64-byte blocks, `wIndex` = M1 offset). Normal command: write 64 bytes with `wValue 0x2010` / `wIndex 0x3F40`, read the result with `0x2011` / `0x3F00`. Small command (8 bytes, replies 8 bytes once firmware runs): `0x2012`/`0x2013`. Firmware boot: command `69 01 00 20`, **and the result stage must be read** — it runs the firmware's full hardware init (enables the motor lines); skipping it leaves the motor dead (notes §20). `gt6816_ctl.upload_and_boot` does both.
- **Two kinds of firmware:** the EEPROM bootstrap (USB identity, `81 01` → type 3, no motor/lamp commands) and the scan firmware `cism603.fw` (all hardware commands). Both runs are volatile; a re-plug returns to ROM state. The firmware loses its state on every reload.
- **Motor** (notes §18-20, 27-34): phases = `PPHDR` (xdata `FFA2`) bits 3..0 = PD0..PD3 into the LB1940, tables `0F 0B 0A 0E` (full) / `0F 03 0B 08 0A 02 0E 0C` (half). Counted moves: `14 01 <n lo> <n hi>` clockwise, `15 …` anticlockwise; `17 01` = moving status. The LB1940 is a constant-current driver (≤400 mA/coil set by board resistors), so torque cannot be raised from software; the firmware's continuous rate floor is ~61 steps/s, lower rates need host-timed single steps. Sustained ≥1200 half-steps/s stalls. `load` defaults patch the uploaded copy to full steps and to leave the coils energised after a move (holding torque); coils draw bus power, so release when idle.
- **Light bar** (§23): `10 01` (SHRRR `FF16` = 0x80, parks the SHR line) **then** `70/71/72 01` (LEDCR: R/G/B), off with `73 01`, `11 01`. `25 01 01` ("lamp on") only sets firmware flags. Only one colour at a time.
- **Power LED** (§26): GPIO0 (`50 01` on, `51 01` off); the idle interrupt forces it high, so blinking needs `load --free-led`.
- **Buttons** (§21): two regular buttons via small command `74 01` byte 2 (`0x88`, `0x02`, latched, read-and-clear); the optical input is GPIO5 (`85 01` byte 2 = 1 while active) and is also the document-present sensor.
- **Custom code in RAM** (`firmware/motor_*.c`, `usb_marker.c`, …) works but does not answer standard USB requests, so the device may drop off the bus until re-plugged; prefer the real firmware with patches.

## Rules for working here

- Prefer the dry run; only pass `--execute` when the user intends a live hardware test, and keep moves short on unfamiliar hardware.
- Never issue an EEPROM write. Never run anything from `vendor/`.
- After a re-plug the scanner is in ROM state: reload the firmware (`gt6816_ctl.py load --execute`) before any motor/lamp/button command.
- Don't run SANE (`scanimage`) at the same time as these tools. A private SANE config (`SANE_CONFIG_DIR=$PWD/sane`) identified the unit as an OpticSlim M12 but its scans were black because SANE never sends `10 01` (notes §22).
