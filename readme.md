# GT-6816 scanner controller and 24LC16B EEPROM investigation

**Status (26 October 2026):** the work has gone well beyond the original EEPROM question.

- **EEPROM dumped.** The 24LC16B was read twice (identical, 2,048 bytes) after being taken off the board with a CH341A in I²C mode: [captures/eeprom/gt6816_24lc16b_dump.bin](captures/eeprom/gt6816_24lc16b_dump.bin), SHA-256 `b21587f0…269f`. It is an 8051 USB bootstrap (descriptors, command dispatcher), disassembled in [docs/eeprom_firmware_disassembly.asm](docs/eeprom_firmware_disassembly.asm); it contains no motor or lamp code. Software-only routes to the EEPROM (SROM reload, vendor requests) all failed.
- **Scan firmware found and running.** Plustek's `cism603.fw` (identical in the macOS and Windows driver packages) is uploaded into the 8 KiB code RAM over USB, exactly as the Windows driver does, and runs (notes §17-20). Everything is volatile; the EEPROM is never written.
- **Hardware now controlled:** the **stepper motor** (clockwise/anticlockwise, speeds from ~5 to ~1000 steps/s, lockable; torque is limited by the LB1940's board-set current), the **RGB CIS light bar** (`10 01` plus a colour command), the **power LED** (blinkable), and the **buttons** (two regular buttons with codes `0x88`/`0x02`, plus an optical input that is also the document sensor). See [CLAUDE.md](CLAUDE.md) for the commands and [docs/GT6816_USB_EEPROM_Reverse_Engineering.md](docs/GT6816_USB_EEPROM_Reverse_Engineering.md) for the evidence behind each claim.
- **Interactive tool:** `python3 -I scripts/motor_console.py` loads the firmware and asks speed, direction and step count.
- **Not done:** a real scan (SANE can drive the unit but its scans are black because it never sends the light-bar enable `10 01`), AFE/exposure tuning, and a re-check of whether other boards' EEPROMs match the dump.

A board without its EEPROM enumerates as the chip's built-in ROM identity `055f:0210` (Mustek); with it, as `07b3:0465`.

## Board and sources

| Item | Finding | Basis |
| --- | --- | --- |
| Controller | GrandTech **GT-6816-HQ011**, 44-pin QFP | Marking observed on the board |
| Adjacent serial memory | Microchip **24LC16B**, 16 Kbit / 2,048 bytes | Marking observed on the board; [Microchip datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/20002213B.pdf) |
| USB identity | `07b3:0465`, product string `600dpi USB Scanner`, `bcdDevice 5.01` | `lsusb` and [saved descriptors](logs/gt6816_usb_descriptors.txt) |
| Scanner model | Plustek MobileOffice S400 | The vendor driver package is named "Plustek MobileOffice S400" and its INF binds exactly to `USB\VID_07b3&PID_0465` (notes §18) |
| CPU and code store | 8051-compatible CPU; 8 KiB downloadable code RAM (M1) | [GT-6816 datasheet](https://www.insidegadgets.com/wp-content/uploads/2018/04/GT-6816.pdf), [controller developer's account](https://chamberplus.blogspot.com/2008/12/usb-controller.html) |
| EEPROM wiring | GT-6816 SDA pin **22**, SCL pin **23** in both the 44-pin drawing and pin-description table | Datasheet; **PCB continuity not measured** |

The datasheet's **44-pin drawing and pin-description table disagree about several other pin numbers**, including some USB and GPIO positions. Only the SDA/SCL positions above agree in both. Verify continuity and supply voltage on the actual board before using any other pin assignment. The 24LC16B has SDA on pin 5 and SCL on pin 6; a plausible connection to the controller is not proof of board routing.

The saved USB descriptor shows one vendor-specific interface, a 64-byte control endpoint, bulk IN endpoint `0x81` and bulk OUT endpoint `0x02`, each with a 64-byte maximum packet. It reports bus power in the configuration descriptor; the device-status read is inconsistent with that, so the actual power arrangement was not inferred from descriptors alone. USB device numbers changed from 079 through 088 during reconnects; they are **not** stable identifiers.

The 24LC16B has eight logical 256-byte blocks at 7-bit I²C addresses `0x50` through `0x57` (2,048 bytes total). Its A0/A1/A2 package pins do not select those addresses. A random read first sends the block address in write direction and the byte offset, then a repeated START and the block address in read direction. A byte-address setup on the I²C bus is not an EEPROM cell write. Block boundaries must be handled explicitly when reading the whole chip. The EEPROM's actual contents, write-protect level, supply voltage, and SDA/SCL activity on this board remain unknown.

## Motor hardware identified after the EEPROM experiments

The motor driver is an **LB1940** with a four-wire stepper. The firmware analysis and live tests (notes §17-20, 27-34) show the four control lines are **PD0-PD3** (the low nibble of the parallel-port data register `FFA2`), not GPIO5/GPIO6 as first assumed: GPIO5 is the document/optical sensor and GPIO6 selects between the two regular buttons. Which LB1940 pin each of the four bits drives is inferred from the phase tables (bits 3 and 1 behave as the two enables, bits 2 and 0 as the two direction inputs), not traced on the board. The motor has been driven in both directions at many speeds.

The [manufacturer LB1940T datasheet](https://www.part-elec.com/datasheet/on-semiconductor/LB1940T-TLM-H.pdf) identifies two H bridges, with polarity inputs `IN1`/`IN2` and active-high enables `ENA1`/`ENA2`. Both enables low gives standby with the outputs off; direction inputs low alone do not turn an enabled bridge off. For the **T package**, ENA1/ENA2 are pins 5/6 and IN1/IN2 pins 7/8; do not apply that pin numbering to the U package. A finite forward/reverse test requires the board's exact control-input mapping and an established way to release the coils afterward.

## Confirmed USB program-RAM protocol

The following requests come from the [SANE GT-6816 implementation](https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_gt6816.c/) and were exercised on `07b3:0465`:

| Operation | `bmRequestType` | `bRequest` | `wValue` | `wIndex` | Data |
| --- | --- | --- | --- | --- | --- |
| Read M1 code RAM | `0xC0` | `0x01` | `0x200C` | M1 offset | 64 bytes IN |
| Write M1 code RAM | `0x40` | `0x01` | `0x200B` | M1 offset | 64 bytes OUT |
| Launch uploaded code | `0x40` | `0x01` | `0x2010` | `0x3F40` | 64-byte packet beginning `69 01 <padded-size-LE>` |
| Read normal response | `0xC0` | `0x01` | `0x2011` | `0x3F00` | 64 bytes IN before custom code takes over |

The upload writes 64-byte blocks, reads each block back, and uses the **padded** byte count in the launch packet. After custom code starts, the original endpoint-0 RAM command can time out or return USB I/O error; custom firmware must provide its own output path. A reversible 64-byte write at M1 `0x1FC0` was read back, then the original block was restored and verified. No EEPROM write command was used.

The SANE firmware-status command `70 01` returned a 64-byte response starting `00 70 00`, rather than SANE's loaded-firmware signature `00 70 FF`. This is evidence about the SANE firmware state only; it does not identify or validate EEPROM contents.

## What ran on this board

| Experiment | Result | Evidence |
| --- | --- | --- |
| Read M1 before upload | Two 2 KiB reads matched exactly; the first 2 KiB of the 8 KiB capture matched them. The initial bytes were `ff 9b ff de ff ee ff ef`, without an obvious 8051 reset vector. | [2 KiB capture](captures/ram/gt6816_ram_2k.bin), [repeat](captures/ram/gt6816_ram_2k_repeat.bin), [8 KiB capture](captures/ram/gt6816_ram_8k.bin) |
| Run a custom marker | A **184-byte** 8051 image (192 bytes after upload padding) executed and sent `a5 a4 a7 a6 a1 a0 a3 a2` through bulk IN `0x81`. | [firmware source](firmware/usb_marker.c), [host runner](scripts/gt6816_ram_runner.py), [live log](logs/gt6816_marker_live.log) |
| SROM reload to M1 `0x1000` | A first attempt did not return data. A revised program returned a PRE marker, then no POST marker after requesting reload. After reconnect, the first eight sentinel bytes remained unchanged; only 33 scattered bytes of the 2 KiB sentinel differed. This is **not** a complete copy. | [firmware](firmware/srom_capture.c), [host capture tool](scripts/gt6816_srom_capture.py), [diagnostic log](logs/gt6816_srom_diagnostic_live.log), [post-reconnect RAM](captures/ram/gt6816_m1_after_srom_reconnect.bin) |
| SROM reload to M1 `0x0000` | Its PRE marker returned. After the reload request and a USB bus reset, the uploaded probe remained byte-for-byte intact in the first 256 M1 bytes; M1 `0x0100..0x07FF` also stayed unchanged. A longer-wait repeat and a later physical reconnect yielded the same 8 KiB image. | [firmware](firmware/srom_zero_probe.c), [first log](logs/gt6816_zero_probe_live.log), [first RAM capture](captures/ram/gt6816_m1_after_zero_reload.bin), [repeat](captures/ram/gt6816_m1_after_zero_reload_repeat.bin), [physical-reconnect capture](captures/ram/gt6816_m1_after_physical_reconnect.bin) |

The second zero-address run's marker read had a USB overflow. Its subsequent full RAM capture is the useful observation: it matched the first zero-address capture exactly. A physical reconnect produced the same hash again. Neither reload address yielded a validated EEPROM byte stream.

### Hashes of the main RAM artifacts

| Artifact(s) | Size | SHA-256 |
| --- | ---: | --- |
| `gt6816_ram_2k.bin`, `gt6816_ram_2k_repeat.bin`, `gt6816_ram_2k_after_status.bin` | 2,048 bytes each | `c7e4e5eea89c32d5a22d3fe08ad332d4bec65dccc25999c7ff705349b2156aa5` |
| `gt6816_ram_8k.bin`, `gt6816_m1_pre_marker.bin` | 8,192 bytes each | `2eb335437f56ade3bc4725afcde4720fcfc1b5d55c8bcf231bb59f4e0b1608bf` |
| `gt6816_m1_after_srom_reconnect.bin`, `gt6816_m1_pre_srom_diagnostic.bin` | 8,192 bytes each | `40d9c42fb9e032af5b599b2df3d00c50a5c8223ee54e54b5ee8ce8334de54676` |
| `gt6816_m1_after_zero_reload.bin`, `gt6816_m1_after_zero_reload_repeat.bin`, `gt6816_m1_after_physical_reconnect.bin` | 8,192 bytes each | `fa4ebb8afa06333f8fa35952a1774bf53566d17f9084ce86d676616263e7e17d` |

Other `gt6816_m1_pre_*.bin` files are the automatic **volatile M1 backups** made before each probe; the corresponding `*.log` files record upload and USB outcomes. None is an EEPROM backup. No file named `gt6816_srom_m1_candidate.bin` was produced by a successful capture.

## Why software-only EEPROM access failed (the dump was finally taken with an external reader)

The [GT-6816 datasheet](https://www.insidegadgets.com/wp-content/uploads/2018/04/GT-6816.pdf) documents `FF80.3` as a request to re-download program code from external serial EEPROM and reset the CPU; `FF83/FF84` set an M1 starting address. It does **not** document a CPU-visible I²C byte address/data register or a way to remap the dedicated SDA/SCL pins as GPIO. The reload operation therefore cannot be assumed to perform arbitrary 24LC16B reads, and the observed experiments did not show it copying the EEPROM into readable M1. The EEPROM could hold code, calibration/configuration, or other data; its contents are still unknown.

The successful marker proves that the USB upload and return channel work. It does **not** prove that the EEPROM can be accessed from custom code. The SROM failures do not prove that the 24LC16B is blank, disconnected, or faulty: its board wiring and bus activity were not measured, and the reload format/behavior is not described in enough detail to diagnose that cause.

## Reproducing the non-EEPROM checks

Requirements: Python 3 with PyUSB, `lsusb`, and SDCC/`packihx` to rebuild 8051 images. Stop scanner software that might initialize the device. Obtain read/write access to the current `/dev/bus/usb/<bus>/<device>` node; this node changes after reconnection. For example, after confirming its current address with `lsusb -d 07b3:0465`, grant the logged-in user access with `sudo setfacl -m u:$(id -un):rw /dev/bus/usb/001/088`, replacing `001/088` with the address currently shown.

```bash
# Read-only code-RAM capture; this is not an EEPROM dump.
python3 scripts/gt6816_usb_ram_dump.py 07b3 0465 --size 8192 --output m1_check.bin

# Build all three volatile test programs.
make -C firmware
make -C firmware srom_capture srom_zero_probe

# Upload and execute the already verified eight-byte USB marker.
python3 scripts/gt6816_ram_runner.py firmware/usb_marker.ihx --execute \
  --backup m1_before_marker.bin --log marker_run.log
```

`gt6816_ram_runner.py` and `gt6816_srom_capture.py` default to an offline dry run; `--execute` performs **volatile M1 writes and launches code**, changing the scanner's USB behavior. The SROM probe programs are retained for investigation, but they **did not dump the EEPROM** in this session. If custom code makes the ROM control commands unavailable, a PyUSB USB bus reset restored them on this board while M1 contents remained readable; a physical USB reconnect also restored access. After recovery, verify access with the read-only RAM command before another upload.

The EEPROM was finally read with a CH341A in I²C mode after taking the chip off the board (notes §14-15): in-circuit the bus was held low by the unpowered controller, off-board SDA and SCL idled high and two 2,048-byte reads over all eight 256-byte blocks were identical. `flashrom` cannot read I²C EEPROMs (its CH341A support is SPI only), so [scripts/gt6816_ch341_eeprom_read.py](scripts/gt6816_ch341_eeprom_read.py) speaks the CH341A's I²C protocol directly. Use `--speed 1` (100 kHz); 20 kHz hangs.

## Primary references

- [GT-6816 datasheet](https://www.insidegadgets.com/wp-content/uploads/2018/04/GT-6816.pdf): pin drawing, M1/M2/DMA/USB registers, `FF80.3` SROM reload.
- [GT-6816 controller developer's account](https://chamberplus.blogspot.com/2008/12/usb-controller.html): 8051 code-store and USB-to-DMA firmware upload design.
- [SANE GT-6816 source](https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_gt6816.c/) and [USB transport source](https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_low.c/): code-RAM requests and launch command.
- [Microchip 24LC16B datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/20002213B.pdf): EEPROM geometry and I²C read protocol.
