# GrandTech GT-6816-HQ011 — USB firmware and 24LC16B reverse-engineering notes

**Last updated:** 2026-10-15  
**Project:** Reuse the scanner controller as a programmable USB-connected 8051 device and retrieve its I²C EEPROM contents **without desoldering or writing the EEPROM**.  
**Status:** Chip, package, companion EEPROM, and USB VID:PID observed. USB program-RAM read/write and execution of a 184-byte custom 8051 program were verified on this board; its eight-byte marker returned over USB endpoint 1. An external-SROM reload request has not yielded an EEPROM capture. **The 24LC16B EEPROM itself has not been dumped or verified against any RAM capture.**

## 1. Observed hardware (from the physical board and Ubuntu)

| Item | Observation | Confidence |
| --- | --- | --- |
| Main IC marking | **GrandTech GT-6816-HQ011** | Direct observation |
| IC package | **44-pin QFP** | Direct observation |
| Adjacent EEPROM | **24LC16B**, 8-pin I²C serial EEPROM | Direct observation |
| USB vendor ID | **07b3**, registered to **Plustek** | Direct `lsusb` observation |
| USB product ID | **0465** | Direct `lsusb` observation |
| USB device string | `600dpi USB Scanner` | Direct `lsusb` observation |
| USB bus/device in this session | **Bus 001, Device 079** | Dynamic — will change on reconnection |
| Likely complete scanner model | **Plustek MobileOffice S400** | Good external VID:PID match; verify label or case |
| Package suffix `HQ011` | Function/revision not determined | Unknown |

Exact Ubuntu identification supplied by the owner:

```text
Bus 001 Device 079: ID 07b3:0465 Plustek, Inc. 600dpi USB Scanner
```

A historical Linux support discussion reports **Plustek MobileOffice S400** with precisely `0x07b3:0x0465` and identifies the controller as `GT-6816?` ([source](https://ubuntuforums.popey.com/showthread.php?t=1210316)). The question mark matters: the original report was preliminary, but **our own IC marking verifies that the chip on this board is a GT-6816**. Plustek's own S400 product documentation specifies **USB 1.1, CIS sensor, 600 dpi optical resolution**, and USB bus power ([catalog, printed p. 18 / PDF p. 20](https://downloads.plustek.com/downloads/english/leaflet/ALLAE-03010.pdf)). USB string alone is not proof of the full retail model.

## 2. GT-6816 hardware overview

Sources: [GT-6816 datasheet](https://www.insidegadgets.com/wp-content/uploads/2018/04/GT-6816.pdf); [GT-6816 controller development account](https://chamberplus.blogspot.com/2008/12/usb-controller.html).

| Resource | Findings / limitations |
| --- | --- |
| Device role | Integrated USB scanner controller for CCD/CIS acquisition, analog front end (AFE), motor/control and image-data handling |
| CPU | **8051-compatible core** identified in a published account by a controller developer; runs at 48 MHz, with accelerated instruction timing (~1–2 clocks per simple instruction) |
| Program storage | **8 KiB of downloadable 8051 program-code memory** described in the developer account. This is **not** necessarily ordinary 8051 `xdata` RAM. |
| Host connection | Integrated **USB 1.1** interface (up to 12 Mb/s USB signaling, not guaranteed payload throughput) |
| Clock | Datasheet describes 6 MHz crystal with internal PLL generating a 48 MHz master clock in the usual configuration; actual board clock is not yet measured |
| Image analog front end | **16-bit ADC**, documented up to 6 MHz; scanner-specific peripheral |
| Firmware sources | Internal embedded startup code; optional external serial EEPROM; USB firmware download via controller's DMA/boot mechanism |
| Onboard software tools | **SDCC** can compile standard 8051 instructions; GT-6816-specific SFR, memory map, USB runtime and I²C controller integration must be worked out |
| General GPIO / scanner pins | GPIO5–7 and PD0–3 available at some 44-pin leads; actual board usage unknown |
| Internal nonvolatile flash | **No user-programmable internal flash established**. Do not treat USB firmware upload as permanently flashing the IC. |

### Relevant pins — **44-pin QFP only**

According to the pin configuration diagram in the [GT-6816 datasheet](https://www.insidegadgets.com/wp-content/uploads/2018/04/GT-6816.pdf):

| GT-6816 pin | Signal | Notes |
| ---: | --- | --- |
| 4 | X1 | Crystal/clock |
| 5 | X2 | Crystal/clock |
| 12 | RST | Reset input |
| 13, 14, 15 | GPIO5, GPIO6, GPIO7 | General-purpose pins; may be used by scanner circuitry |
| 17, 18, 19, 20 | PD0, PD1, PD2, PD3 | Parallel control/data pins; do not assume free GPIO |
| **22** | **SDA** | Serial EEPROM data |
| **23** | **SCL** | Serial EEPROM clock |
| 24 | GNDU | USB ground domain |
| **25** | **D−** | USB data minus |
| **26** | **D+** | USB data plus |
| 27 | VDDU | USB supply domain |

**PCB test points:** The likely EEPROM wiring is GT-6816 **pin 22 → EEPROM pin 5 (SDA)** and GT-6816 **pin 23 → EEPROM pin 6 (SCL)**. Verify continuity with the board **unpowered** before relying on this route. Confirm EEPROM VCC using a multimeter; never assume a 3.3 V rail without measurement.

## 3. 24LC16B EEPROM

Primary source: [Microchip 24LC16B datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/20002213B.pdf).

- **16 Kbit = 2,048 bytes** of nonvolatile storage (`0x000`–`0x7FF`).
- **I²C serial interface**, standard/fast mode (up to 400 kHz), open-drain SDA/SCL with pull-up resistors.
- Supply range **2.5–5.5 V** for the listed 24LC16B variant.
- **A0/A1/A2 pins are not connected internally.** The 3-bit block address is instead embedded in the I²C control byte.
- **7-bit I²C addresses: `0x50` through `0x57`**, representing eight blocks of **256 bytes** each. These are *logical block addresses within this one EEPROM*, not eight physical chips.
- EEPROM write protection: **WP high (VCC) prevents writes**, but does not prevent reads; **WP low (VSS)** enables writes.

### 8-pin EEPROM pinout (SOIC/DIP)

| Pin | Signal | Use |
| ---: | --- | --- |
| 1 | A0 | Not internally connected |
| 2 | A1 | Not internally connected |
| 3 | A2 | Not internally connected |
| 4 | VSS | Ground |
| **5** | **SDA** | I²C data |
| **6** | **SCL** | I²C clock |
| 7 | WP | Write-protect input |
| 8 | VCC | Power |

### Typical EEPROM random-read transaction

For byte offset `offset` from `0x000` to `0x7FF`:

```text
block     = (offset >> 8) & 0x07
byte_addr = offset & 0xFF
seven_bit_slave = 0x50 + block

START
[seven_bit_slave, WRITE] + ACK
[byte_addr]              + ACK
REPEATED START
[seven_bit_slave, READ]  + ACK
[byte from EEPROM]       + NACK
STOP
```

At I²C *wire-byte* level, the control byte is `0xA0 | (block << 1)` for write-direction address setup and `0xA1 | (block << 1)` for read. A sequential read can collect multiple bytes, but **do not assume automatic page/block selection across the 256-byte logical-block boundary**. A simple first implementation can issue 2,048 independent random reads or eight block reads, one per block. All operations above are **read-only** at the EEPROM cell level.

### What is stored in this particular EEPROM?

**Unknown until dumped.** Candidates include firmware/startup code, patch code, scanner configuration, sensor calibration data, or a combination. Mere proximity to the GT-6816 does **not** prove it is executable firmware. The GT-6816's datasheet does document a power-on external-EEPROM code-download mechanism, making firmware plausible.

## 4. USB RAM access — protocol from Linux SANE

Primary code: [SANE `gt68xx_gt6816.c`](https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_gt6816.c/), [SANE `gt68xx_low.c`](https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_low.c/), [SANE `gt68xx_devices.c`](https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_devices.c/).

The SANE **Mustek GT-6816** command-set definitions establish USB vendor-control transfers for program memory:

| Function | bmRequestType | bRequest | wValue | wIndex | Payload / reply |
| --- | --- | --- | --- | --- | --- |
| **Read code memory** | `0xC0` (vendor IN) | `0x01` | `0x200C` | **memory offset** | Read 64 bytes |
| **Write code memory** | `0x40` (vendor OUT) | `0x01` | `0x200B` | **memory offset** | Send 64 bytes |

SANE's GT-6816 firmware loader uses **64-byte blocks**, pads the last block, writes each block, then **reads it back and compares** the bytes. Next it sends a **64-byte normal-command packet**, of which the meaningful leading bytes are:

```text
69 01 <firmware_size_low> <firmware_size_high> 00 00 ... 00
```

`firmware_size` is the **address after the last transferred 64-byte block**, not necessarily the raw unpadded file length. The normal-command transport is:

| Action | bmRequestType | bRequest | wValue | wIndex | Length |
| --- | --- | --- | --- | --- | --- |
| Send normal command | `0x40` | `0x01` | `0x2010` | `0x3F40` | 64 bytes |
| Read normal response | `0xC0` | `0x01` | `0x2011` | `0x3F00` | 64 bytes |

**Firmware-loaded probe:** The driver sends small command `70 01 ...`; loaded state is indicated by a response beginning `00 70 FF ...`. The driver notes the response format differs before firmware is present (64 bytes before vs 8 bytes after initialization). See `gt6816_check_firmware()` in the source.

**Important qualifications:**

1. The memory read/write and firmware-launch transfers have succeeded on this USB ID (`07b3:0465`); custom code returned a verified USB marker.
2. In SANE's GT-6816 implementation they access **mapped downloadable program memory**, **not a direct I²C EEPROM address space**. The meaning of the returned bytes on this specific board is not independently established.
3. Reading an address after firmware was loaded *might* expose downloaded program bytes, but there is no guarantee the 24LC16B contents are mirrored there or that every byte is readable under the existing firmware.
4. Writing RAM can change execution state and interrupt USB; recovery generally means unplug/replug. A single block was temporarily written and restored only after its original bytes had been captured and checked. Broader writes or firmware launch need a separate recovery plan.
5. The SANE scanner backend may not recognize this particular `07b3:0465` model automatically; PyUSB addresses it directly by VID:PID instead.

## 5. Read-only first experiment on Ubuntu

A previous conversational artifact is available as **`gt6816_usb_ram_dump.py`** (a separate file; place it in the working directory). It is a **read-only host-side PyUSB memory dumper**, not firmware running on the controller.

```bash
sudo apt update
sudo apt install python3-usb usbutils
lsusb -d 07b3:0465
sudo lsusb -v -d 07b3:0465 > gt6816_usb_descriptors.txt
```

Execute the existing script with the **real IDs**, rather than another scanner's example ID:

```bash
sudo python3 scripts/gt6816_usb_ram_dump.py 07b3 0465 \
  --size 2048 --output gt6816_ram_2k.bin

# If successful, optionally read the whole downloadable code area:
sudo python3 scripts/gt6816_usb_ram_dump.py 07b3 0465 \
  --size 8192 --output gt6816_ram_8k.bin

xxd -l 128 gt6816_ram_2k.bin
sha256sum gt6816_ram_2k.bin gt6816_ram_8k.bin
```

Expected behavior: the host issues 64-byte USB vendor IN transfers. **A successful transfer proves only that the device returned data; it does not prove the bytes came from program memory or EEPROM.** Readbacks consisting only of `00` or `FF`, repeated patterns, exceptions or a USB stall are all diagnostically useful, but must not automatically be interpreted as actual EEPROM data.

If PyUSB reports permission denied, use `sudo` as above. If USB becomes unresponsive, close competing scanner applications, unplug/replug and retry. Avoid running `scanimage` at the same time because it may initialize or download ordinary scanner firmware and change the RAM contents.

Optional baseline diagnostics:

```bash
lsusb -d 07b3:0465
sane-find-scanner -q
# Avoid scanimage -L until the initial passive read has been captured:
# it may access the scanner/initialize its firmware.
```

## 6. Can we run our own program via USB? **Yes; EEPROM access remains unresolved**

Published firmware loading code supports **USB upload, memory readback, and boot**. A published account of the chip's development describes the **8051 code RAM** being updated through USB → DMA and then reset into the new program.

The custom marker establishes RAM execution and an eight-byte USB return path. The missing details for an EEPROM dumper are in the **chip-specific runtime interface**:

- GT-6816's 8051 reset vector, memory banking, interrupt vectors and available data RAM/XRAM.
- Control/status registers for dedicated **serial EEPROM/SROM downloader**; whether firmware can read EEPROM bytes individually via registers, DMA, or directly bit-bang SDA/SCL.
- USB endpoint/control-transfer handling after starting an arbitrary application (the original scanner firmware's USB command handler may no longer be running).
- How to return the collected 2,048 bytes through USB, or copy them to host-readable mapped RAM while leaving the USB bootstrap mechanism accessible.
- Whether this particular board uses internal/external EEPROM startup and how to switch/recover modes.

The datasheet has a **DMA control register at `0xFF80`**, including a documented **bit 3: SROM download** function that requests a *re-download of code* from external EEPROM. **Do not set this bit as an EEPROM-read shortcut**: it resets/replaces running code rather than directly returning the EEPROM as a byte array.

### Suggested custom 8051 firmware design (not yet implemented)

```text
Ubuntu host / PyUSB
    | vendor USB control messages
    v
GT-6816 ROM USB bootstrap -> upload and launch an ~1–3 KiB 8051 test
    |
    +-- establish I²C/SROM access method (registers/DMA/bit-bang)
    +-- read 24LC16B sequentially, no EEPROM writes
    +-- collect 2,048 bytes in a known host-readable area OR USB reply buffer
    +-- expose chunks to host, return status/checksum
    v
Ubuntu saves eeprom_24lc16b_2048.bin + SHA-256
```

**First custom-firmware experiment completed:** an 184-byte program wrote `a5 a4 a7 a6 a1 a0 a3 a2` to the documented USB status-transmit registers and returned those exact eight bytes via endpoint 1. It did not drive GPIO or scanner motor pins. The dedicated SROM interface has no documented CPU byte-read register or documented SDA/SCL GPIO remapping, so the I²C data path remains unresolved.

### Development tools

```bash
sudo apt install sdcc python3-usb usbutils binutils
```

- **SDCC**: 8051 C compiler (`sdcc -mmcs51 ...`), but default linker/startup assumptions may need GT-6816-specific adjustment.
- **PyUSB/libusb**: USB discovery, vendor-control commands, memory dumps.
- **SANE GT68xx source**: working reference implementation for USB transport and firmware lifecycle.
- **Multimeter / logic analyzer**: validate actual SDA/SCL activity, voltages and reset behavior.
- **TL866A programmer**: fallback **read-only** EEPROM dump if in-circuit USB methods fail; first preserve untouched original bytes.

## 7. Plan, in priority order

1. **Capture descriptors:** run `lsusb -v -d 07b3:0465`, preserve output, including endpoints, USB configuration and strings.
2. **Attempt read-only RAM access:** run the provided PyUSB script with `07b3 0465`; capture error text or both 2/8 KiB dumps.
3. **Identify memory content:** check vectors at offsets `0x0000`, `0x0003`, `0x000B` for plausible 8051 code; examine strings, high entropy and repeated bytes; do not assume it originated in the EEPROM.
4. **Confirm EEPROM wiring:** unpowered continuity tests from EEPROM SDA/SCL (pins 5/6) to GT-6816 (pins 22/23); measure powered VCC; record WP level.
5. **Study startup and peripheral register map:** find a supported way to access external SROM through CPU or DMA, noting that the SROM re-download bit restarts firmware rather than reading a selected byte.
6. **Build a minimal 8051 image:** establish custom reset vector, memory layout, simple known marker output and safe USB recovery method.
7. **Build a read-only I²C/SROM EEPROM dumper:** 2,048-byte output, compare repeated reads and SHA-256; save dump **before** attempting any EEPROM update.
8. **Only after the backup:** explore persistent EEPROM boot code, preserving ability to restore the original image.

## 8. What is confirmed vs what is still speculative?

| Claim | Assessment |
| --- | --- |
| Board has GT-6816-HQ011 44-pin plus 24LC16B | **Observed by owner** |
| USB identifies as `07b3:0465` | **Observed by owner** |
| USB ID historically associated with MobileOffice S400 | **Externally corroborated**, not verified by a case label |
| SANE source implements USB program-RAM read/write + launch for GT-6816 | **Confirmed in source** |
| 8051 core and 8 KiB downloadable code memory | **Strong secondary-source evidence** from technical development account |
| GT-6816 has an external-EEPROM boot/download facility | **Documented in chip datasheet** |
| The nearby 24LC16B contains code rather than calibration | **Not established** |
| `07b3:0465` supports the SANE program-RAM read/write requests | **Confirmed by a matching 64-byte marker write/read and restoration; 2 KiB and 8 KiB captures are stable** |
| USB RAM dump necessarily equals EEPROM dump | **Not established; likely false as a general assumption** |
| Custom 8051 code can transmit bytes back over USB | **Confirmed:** an eight-byte marker returned from the internal DSTR registers over endpoint 1 |
| Custom 8051 code can read this specific EEPROM | **Not demonstrated:** no documented CPU byte-read path to the dedicated SDA/SCL pins was found |
| `HQ011` denotes a particular RAM/firmware revision | **Unknown** |

## 9. Sources and starting points

1. **GrandTech GT-6816 datasheet (PDF)** — original chip pinout, EEPROM download mechanism, peripherals, DMA registers: <https://www.insidegadgets.com/wp-content/uploads/2018/04/GT-6816.pdf>
2. **GT-6816 controller design article** — 8051 core, 48 MHz, 8 KiB downloadable program memory, USB/DMA boot concept (Chinese): <https://chamberplus.blogspot.com/2008/12/usb-controller.html>
3. **SANE GT-6816 firmware download source:** <https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_gt6816.c/>
4. **SANE memory transport source:** <https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_low.c/>
5. **SANE model and vendor-request command sets:** <https://sources.debian.org/src/sane-backends/1.3.1-3/backend/gt68xx_devices.c/>
6. **Microchip 24LC16B datasheet (PDF)** — EEPROM pinout, I²C block-addressing and write protection: <https://ww1.microchip.com/downloads/en/DeviceDoc/20002213B.pdf>
7. **Prior report matching USB `07b3:0465` to Plustek MobileOffice S400:** <https://ubuntuforums.popey.com/showthread.php?t=1210316>
8. **Plustek official S400 scanner specifications (catalog PDF):** <https://downloads.plustek.com/downloads/english/leaflet/ALLAE-03010.pdf>
9. **SANE GT68xx manual:** <https://sane-project.org/man/sane-gt68xx.5.html>

---

## 10. USB results on this board — 2026-10-15

The scanner enumerated as `07b3:0465`, Bus 001 Device 079. Its USB device node initially denied control transfers to the current user; a temporary per-user ACL enabled the read-only probe. The USB descriptors are saved in `gt6816_usb_descriptors.txt`.

The SANE program-memory read request returned all requested 64-byte blocks without a short read or USB error. Two independent 2,048-byte reads matched byte-for-byte. The 8,192-byte read has the same first 2,048 bytes.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `gt6816_ram_2k.bin` | 2,048 bytes | `c7e4e5eea89c32d5a22d3fe08ad332d4bec65dccc25999c7ff705349b2156aa5` |
| `gt6816_ram_2k_repeat.bin` | 2,048 bytes | `c7e4e5eea89c32d5a22d3fe08ad332d4bec65dccc25999c7ff705349b2156aa5` |
| `gt6816_ram_8k.bin` | 8,192 bytes | `2eb335437f56ade3bc4725afcde4720fcfc1b5d55c8bcf231bb59f4e0b1608bf` |

The first bytes are `ff 9b ff de ff ee ff ef 5e 5d df 7f ff bf fd 4b`; they do not show an obvious 8051 reset jump at address zero. The capture also has repeated alternating regions rich in `0xFF` and `0x00`. **Stable USB replies do not establish that this is executable program code, nor that any byte came from the 24LC16B.** Do not rename either RAM file as an EEPROM backup.

The SANE firmware-status query (`70 01` sent as a small command) received a 64-byte response beginning `00 70 00`, rather than SANE's loaded-firmware signature `00 70 ff`. An initial 8-byte response request failed with USB overflow, consistent with SANE's note that pre-firmware responses are 64 bytes. This supports the interpretation that the SANE firmware is not loaded, but it does not prove the EEPROM is blank or absent. A third 2 KiB read after this query matched the original capture exactly (`gt6816_ram_2k_after_status.bin`).

To verify the RAM transport, the original block at `0x1fc0` was checked against the saved 8 KiB capture, temporarily replaced with a 64-byte marker via the documented RAM-write request, and read back. The marker matched. The original block was then restored and read back byte-for-byte. This operation did **not** use an EEPROM write command.

**USB-only path:** custom code execution and an eight-byte endpoint-1 return path are established. The documented SROM reload command was exercised with two M1 destinations, but neither produced a verified EEPROM copy; no CPU byte-read register or SDA/SCL GPIO remapping has been found. Do not treat any RAM file as an EEPROM backup.

**Direct verification path if USB-only work does not succeed:** read the physical 24LC16B over I²C or with a compatible programmer, preserving all eight 256-byte blocks, then read it again and compare the two 2,048-byte results. No I²C adapter or EEPROM programmer was connected during this session. If one is connected later, verify the EEPROM's supply voltage and in-circuit bus behavior before driving SDA/SCL; the scanner controller shares those lines.

## 11. Custom RAM execution and SROM experiments — 2026-10-15

The 184-byte `firmware/usb_marker.c` image was uploaded to volatile M1 RAM with block-by-block readback. Its boot command was accepted; the old endpoint-0 command timed out after launch, while USB endpoint 1 returned exactly `a5 a4 a7 a6 a1 a0 a3 a2`. This proves custom 8051 execution and the documented internal eight-byte transmit path. The 8 KiB pre-upload M1 backup is `gt6816_m1_pre_marker.bin`; the execution log is `gt6816_marker_live.log`. No EEPROM access was attempted by that marker.

The chip datasheet documents `FF80.3` as an external SROM re-download request that resets the CPU and copies program code from external EEPROM. It documents `FF83/FF84` as the M1 starting address, but does not document a CPU-visible I²C data/address register or a way to control the dedicated SDA/SCL pins as GPIO. The software-only experiments therefore exercised the SROM reload engine, not a general 24LC16B random-read transaction.

The first `firmware/srom_capture.c` probe installed a 2,048-byte sentinel at M1 `0x1000`, set `FF83/FF84=0x1000`, and requested `FF80.3`. The host did not receive a 2 KiB endpoint-1 stream. After USB reconnect, `gt6816_m1_after_srom_reconnect.bin` retained the probe code; the sentinel's first eight bytes remained unchanged and only 33 of its 2,048 bytes differed, in short scattered regions. This is not evidence of a complete EEPROM copy. A revised probe returned its PRE marker before `FF80.3`, but no POST marker afterward (`gt6816_srom_diagnostic_live.log`), locating the loss of communication at or after the reload request.

The `firmware/srom_zero_probe.c` probe sent and verified its eight-byte marker, then requested `FF80.3` with `FF83/FF84=0x0000`. A USB bus reset restored the ROM RAM-read command without changing the USB device address. `gt6816_m1_after_zero_reload.bin` contained the uploaded probe image byte-for-byte in its first 256 bytes; bytes `0x0100` through `0x07ff` were identical to the pre-probe backup. A second capture after a longer wait, `gt6816_m1_after_zero_reload_repeat.bin`, was byte-for-byte identical to the first (SHA-256 `fa4ebb8afa06333f8fa35952a1774bf53566d17f9084ce86d676616263e7e17d`). This does not show an SROM copy at M1 zero. The second marker read itself had a USB overflow, so the repeated RAM comparison is the reliable observation from that pass.

After a subsequent physical USB reconnect (Bus 001 Device 088), a further read-only 8 KiB capture, `gt6816_m1_after_physical_reconnect.bin`, had the same SHA-256 as both zero-reload captures. The physical reconnect did not reveal a new M1 image or EEPROM bytes.

**Outcome:** no `24LC16B` EEPROM dump was obtained. The custom USB output path works, but the available documentation and these two SROM-reload experiments do not establish a software-accessible route to the EEPROM bytes. The existing `.bin` files in this directory are GT6816 code-RAM captures and must not be labeled or used as EEPROM backups.

## 12. Re-analysis of existing artifacts (no new device access) — 2026-10-15

- **Datasheet re-check:** the 44-pin diagram and pin table list SDA/SCL only as dedicated "Serial EEPROM" pins; the only EEPROM text is "GT6816 searches the external serial EEPROM on the power-on state. If no serial EEPROM is present, embedded program code will be used." No CPU I²C register, GPIO alias of SDA/SCL, or EEPROM byte-read command is documented. A software-only 24LC16B read therefore has no documented route.
- **The 33 changed sentinel bytes** (M1 `0x10B0..0x10BF`, `0x10CE..0x10DF` in `gt6816_m1_after_srom_reconnect.bin`) are mostly `ff`/`7f`/`df`/`bf`-style values with isolated cleared bits and match neither the sentinel nor the pre-probe M1 contents. They have no recognisable structure and are **not** evidence of EEPROM data.
- **Power-on M1 image (`gt6816_ram_8k.bin`):** per-1 KiB entropy 5.5–5.8 bits/byte, about 4.0 set bits per byte, no printable strings, and 16-byte rows alternating between bits-mostly-set and bits-mostly-clear. This looks like uninitialised SRAM, not loaded code or an EEPROM image. Do not treat it as one.
- **Reconnect is not a power cycle on this setup:** after a physical USB reconnect M1 still held the previously uploaded probe (`gt6816_m1_after_physical_reconnect.bin`), so the chip's power-on EEPROM load most likely did not re-run. The power-on SROM load has therefore not been observed in these experiments.
- **Host I²C buses (`/dev/i2c-*`)** belong to this computer's own hardware and are not connected to the scanner board; no USB I²C adapter or EEPROM programmer was attached.

Conclusion unchanged: no EEPROM dump exists, and none can be produced from the current artifacts.

## 13. Read-only vendor IN request scan — 2026-10-15

`gt6816_vendor_scan.py --execute` (Bus 001 Device 089) sent 1,280 device-to-host control transfers (`bmRequestType 0xC0`, `wLength 64`, no payload ever sent): phase 1 `bRequest 0x00..0xFF` with `wValue=wIndex=0`; phase 2 `bRequest 0x01` and `0x04`, `wValue 0x2000..0x20FF`, `wIndex 0x0000` and `0x3F00`. Results: `gt6816_vendor_scan.json`. M1 before/after: `gt6816_m1_pre_vendor_scan.bin` / `gt6816_m1_post_vendor_scan.bin`, identical (SHA-256 `8ff55c16a2b6e38cc55e0e9e0024058e8f8012ca38b6ca2aeb3647a13bcf8091`).

- **No STALLs, timeouts, or errors.** The ROM handler does not validate `bRequest`: `0x00`, `0x01`, `0x04` and all other values answered, so no "unknown request" was discovered at that level. The behaviour is selected by `wValue`/`wIndex`, not `bRequest`.
- **Only five distinct replies** (and an empty reply for write-type `wValue` 0x2009, 0x200B, 0x200D, 0x2010 and others at both indexes): M1-like data at `wIndex 0` (two alignments, one for `wValue` 0x2000–0x2008, one for the rest), `00 fe 00…` at `wIndex 0x3F00` for most `wValue`, and `00 09 00…` at `wIndex 0x3F00` for `wValue` 0x200A/0x200C. No reply contained EEPROM-like content, an ID string, or a distinct status block. The alignment difference between the two `wIndex 0` replies is not explained.
- **The M1 power-on image changed between sessions** (this one: 2,346 of 8,192 bytes equal to `gt6816_ram_8k.bin`, 14.3% of bits differ) and does not contain the previously uploaded probe, so the device was power-cycled and its RAM comes up non-deterministically. A power-on EEPROM load of a valid image would be repeatable, so there is no evidence that valid code is being loaded from the 24LC16B.
- **Not scanned:** the 64-byte "normal command" channel (`0x2010`/`0x2011`, first byte = command). Unknown commands there can carry a payload and could include a write to the EEPROM, so they were deliberately left unprobed.

## 14. First in-circuit CH341A read attempt — 2026-10-15 (no valid data)

Setup as reported by the owner: CH341A (`1a86:5512`, I²C mode) with a clip on the 24LC16B, scanner USB unplugged, CH341A supplying VCC. `gt6816_ch341_eeprom_read.py` drives the CH341 I²C stream protocol with PyUSB and only builds address/random-read frames (no data byte after the byte address, so no EEPROM write is possible).

- The adapter returns no ACK status bytes, so per-block presence cannot be probed.
- Read frames returned exactly the requested count, **all `0x00`**, at block 0 offsets 0 and 224, block 3 offset 64, block 7 offset 224 — and also for the nonexistent 7-bit address `0x7F`. These bytes are **not EEPROM data**.
- CH341 pin-status query (`0xA0`, reply `fe cf 2f 0c 12 00`) showed **SDA=0 and SCL=0 while idle**. On a working bus both are pulled high, so the lines are held low or the EEPROM is unpowered/loaded down.
- The tool now refuses to read when SDA/SCL are not idle-high and flags uniform `0x00`. No `gt6816_24lc16b_*.bin` file exists; the EEPROM contents remain unknown.
- Not yet measured: EEPROM VCC (pin 8) while clipped, SDA/SCL voltages at the EEPROM pins, clip orientation/contact, CH341A voltage jumper.

## 15. 24LC16B dumped — 2026-10-15 (chip removed from the board, CH341A in I²C mode)

The owner desoldered the 24LC16B and read it in a SOIC adapter on a CH341A. With the chip off the board SDA and SCL idled high (`SDA=1 SCL=1`). The 20 kHz setting (`--speed 0`) hung the transfer; `--speed 1` (100 kHz) worked. `gt6816_ch341_eeprom_read.py --execute --speed 1` read all eight 256-byte blocks twice:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `gt6816_24lc16b_read1.bin`, `gt6816_24lc16b_read2.bin`, `gt6816_24lc16b_dump.bin` | 2,048 bytes | `b21587f09153bba8f5be94ed677d3ca1d337948182e3b511c4fd5825fe8d269f` |

Both passes are byte-identical and all eight blocks are distinct (no address aliasing). The files were then made read-only. The tool only ever sent address and read frames; the EEPROM was not written.

Observations about the contents (not yet disassembled):
- The image begins `02 00 49  02 00 94 …` with `02 hh ll` (8051 `LJMP`) at offsets 0x00, 0x03, 0x0B, 0x13, 0x1B, 0x23, 0x2B, i.e. an 8051 interrupt-vector table, so it is executable code.
- Non-`FF` data runs to the last byte (0x7FF); the string `600dpi USB Scanner` is present.
- This implies the earlier "firmware not loaded" and random power-on M1 contents mean the controller did **not** copy this image into M1 at power-on, or the reload format differs from a raw copy. That mismatch is unexplained.
- Cause of the earlier failures in-circuit: with the clip on the board, SDA and SCL were held low; off the board they idled high. Not further diagnosed.

**This dump is the first verified read of the original EEPROM** (two identical reads); it was taken with the chip off-board, so it does not show that the board's own wiring works. Keep the three files as the backup before any reprogramming, and re-solder the chip only after confirming orientation.

## 16. Disassembly of the EEPROM image — 2026-10-15

Tools: `scripts/gt6816_disasm.py` (recursive-descent 8051 disassembler; all 255 legal opcodes were checked by reassembling its output with `sdas8051` and comparing bytes, 0 mismatches) and `scripts/gt6816_regs.py` (register names parsed from the datasheet). Listing: [eeprom_firmware_disassembly.asm](eeprom_firmware_disassembly.asm). The image is treated as raw code at base `0x0000`, consistent with the vector table (all `LJMP` targets fall inside the 2 KiB image). 888 instructions (1,915 bytes) were reached by tracing; the rest is descriptor data and `FF` padding.

**What the image is:** a USB bootstrap/command firmware, not scan firmware.
- Reset (`0x0049`) clears RAM, sets SP, configures timers and USB (`ISR`, `UDCR`, `UIE1R/2R`, `UECR`) and then idles in a `PCON` loop; USB events are interrupt-driven (`0x0094` INT0 handler calls the USB event routine at `0x067C`).
- A device descriptor (`0x00D2`: VID `07B3`, PID `0465`), configuration descriptor (bus powered, 500 mA), endpoints `0x81` bulk IN / `0x02` bulk OUT, and the string `600dpi USB Scanner` at `0x0102`-`0x011B`; a second `B3 07 65 04 01 05` fragment at `0x0183` carries the `bcdDevice` 5.01 seen in `lsusb`. These match the descriptors saved from the live device.
- A request dispatcher at `0x0452`/`0x049D` handles codes `61 62 64 66 68 69 6A 6B 6C 6E 6F 70`, which includes `0x69` (boot/launch) and `0x70` (status) from the SANE protocol, plus `21 22 23 24 27 28 29` (`0x28` is SANE's TA-status code) and `73`, `81`. Lamp (`0x25`), motion (`0x17`) and power-status (`0x3F`) commands are **not** present, so those need the host-downloaded scan firmware.
- The last two bytes (`0x07FE`) are `68 16`, the chip number 6816. This may be a signature checked by the SROM loader; that is a guess, not established.

**Motor control: not present in this image.**
- The code never touches the timing-generator / sensor register block (`FF00`-`FF4F`) or the AFE registers other than `ASR`; its register use is USB, DMA and suspend registers.
- It writes the GPIO registers exactly once, in routine `sub_03BC` at `0x03BC`-`0x03E0` (called from the USB bus-event handler when the device address is non-zero): `GPIODR(FF95) = 0x20`, then `GPIOCR(FF94) = 0x40`. Per the datasheet `GPIOCR` bit n = 1 makes GPIOn an output and `GPIODR` is the pin data. So GPIO6 becomes an output (data bit 6 = 0, i.e. low) and GPIO5 is left an input; the `0x20` written to `GPIODR` has no pin effect on an input, but it is latched. It also writes `FFFF=0x20`, `FFFD=0x00` and `P1=0xFF`. Whether this idles the LB1940 is unknown: the mapping of GPIO5/GPIO6 to its inputs is not established.
- There is no step table, phase sequence, timing loop that writes `GPIODR`, or any other GPIO write. No host-controlled register-write path exists either: the only `DPTR`-from-register copy (`0x0126`) copies fixed descriptor bytes into a RAM buffer.
- The stepping logic must live in the scan firmware the host driver downloads over USB at scan time (the SANE-style `0x200B` write + `69 01` boot). It is not stored in this EEPROM.

## 17. Plustek macOS driver package (MobileOfficeS400_V1000_1L.dmg) — 2026-10-15

Source: the owner's download, kept at `vendor/macos_s400/MobileOfficeS400_V1000_1L.dmg` (2,686,744 bytes, SHA-256 `da4cd2db1ee4743fd673d46df2dcaa85f18026c55f413ee183635ca4edc70896`). Extracted with `7z` into `vendor/macos_s400/extracted/`; **nothing from it was executed** (it is a 2012 PowerPC/i386 Mach-O app and frameworks). Contents: `DigiScan.app` plus frameworks, notably `74R.framework` (the scanner driver, built from "M12 FrameWork" sources) and two firmware files in `Contents/Resources/`:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `cism603.fw` | 8,192 | `6c764399b9ef0de870f791c432aedeecfaddc2633de25511ccee9a3163c160bf` |
| `cism216.fw` | 8,192 | `fe25216a53c6f528c22cbb4ee7a2bf728112820d5a36bc61616c371394d63cbe` |

Both are raw 8051 code images the size of the whole M1 code RAM (the driver strings reference `/Library/Application Support/Plustek/74R/cism216.fw` and `cism603.fw`, and `_apiDownloadFirmware`). Disassembled with `scripts/gt6816_disasm.py` into `cism603.fw_disassembly.asm` and `cism216.fw_disassembly.asm` (3,452 and 3,434 instructions traced). They are real scan firmware, with a command dispatcher, timer interrupts, and TG/AFE/DMA register use that the EEPROM bootstrap (section 16) lacks.

**Caveat on fit:** each image's built-in USB device descriptor has **PID `0412`**, not this board's `0465` (the EEPROM descriptor), and the driver is the "M12" family. It is not established that either image is the firmware this S400 board is meant to run, nor which of the two the driver picks for it. Which image `DigiScan` selects was not determined.

**Stepper motor findings (from the disassembly; not tested on hardware):**
- **Phase outputs are `PPHDR` (xdata `FFA2`) bits 3..0**, i.e. the parallel-port data bus pins PD0..PD3 (datasheet: pins 17..20 in the pin table, which disagrees with the drawing in places). Init sets `FFA3 = 0x80` (data-bus output enable) and `PPHDR = 0xF8`; the routine `sub_1E61` rewrites only the low nibble (`AND F0` / `OR phase`), and every stop path writes `PPHDR = 0x00` (all four low).
- **Phase tables are identical in both images** (code `0x1F6D`/`0x1F71` in `cism603`, `0x1F49`/`0x1F4D` in `cism216`), selected by a half-step flag and an index masked with 3 (full) or 7 (half), incremented or decremented per direction:
  - full-step: `1111, 1011, 1010, 1110` (0F 0B 0A 0E)
  - half-step: `1111, 0011, 1011, 1000, 1010, 0010, 1110, 1100` (0F 03 0B 08 0A 02 0E 0C)
  
  In the full-step sequence bits 3 and 1 stay high while bits 2 and 0 step through a Gray-code cycle; in the half-step sequence bit 3 or bit 1 drops low on alternate states. The most natural reading is two H-bridges with bit3/bit1 = enable and bit2/bit0 = direction, which matches the LB1940's two ENA and two IN inputs, and "all low" = both enables low = standby/off. **That bit-to-pin assignment is an inference**, not confirmed; the board wiring has not been traced.
- **Step timing:** the Timer 1 interrupt (vector `0x1B`, `sub_1CF2`) is the step clock. It advances the phase, reloads `TH1/TL1` from a per-step value (the ramp is computed from RAM variables `62h/63h`; the move command sets `7Ah/7Bh`, stored complemented), counts steps down, and stops itself.
- **Home sensor:** GPIO5 (`GPIODR` bit 5) is **read as an input** in the step interrupt and in status command `0x17` (reports 0/2 in the status bytes at `3F02/3F03`). This conflicts with the owner's report that GPIO5/GPIO6 go to the motor driver; the firmware treats GPIO5 as a sensor-style input. ~~GPIO6 is not used by either scan firmware~~ **(corrected in section 19: GPIO6 is read as an input, the button selector).** The EEPROM bootstrap sets it as an output, low. Needs checking against the board.
- **Other GPIO use:** init sets `GPIOCR = 0x0F` and `GPIODR = 0xFF` (GPIO0..3 outputs high); GPIO0 is toggled alongside writes to the undocumented `xdata FFFF` shadow bit 6. Function not identified (possibly lamp).
- **Command packets** (64-byte "normal command" at xdata `3F40`, sent via `wValue 0x2010`/`wIndex 0x3F40`, result read from `0x2011`/`0x3F00` as in section 4): byte 0 = command, byte 1 = 0x01, bytes 2..7 become parameters R2..R7. Motor-related codes in the scan firmware: `0x14` and `0x15` (move one way / the other; step count in bytes 2-3 via `sub_1ED1`), `0x16` (move with parameters: bytes 2-3 step count, bytes 4-5 timer reload, byte 6 bit 0 = half-step), `0x17` (status). The driver exports `MotorCommand`, `MotorToHome` (sends `12 01`), `MotorOff` (sends `13 01`), `MotorGetStatus`, `IsMotorMoving`, and issues `10 01` / `11 01` as well (the firmware handles `0x10`/`0x11` by setting/clearing GPIO0 and `SHRRR`, probably the lamp). Direction semantics, units and limits were not verified.

Not done: no firmware from this package was uploaded to the scanner, and no motor test was run. Running these images would drive the stepper and lamp from code written for a possibly different board; the home-sensor input and phase wiring above should be verified first.

## 18. Plustek Windows driver package (MobileOfficeS400-V5205_13L.zip) — 2026-10-15

Source: the owner's download, kept at `vendor/windows_s400/MobileOfficeS400-V5205_13L.zip` (73,380,120 bytes, SHA-256 `a8445abc46e5d25c084e7a36f45a271c8e404f655792ce6c7e6f26f249fff7b8`). Unzipped with `7z` into `extracted/`; the InstallShield `data1.cab` was unpacked with `unshield` into `cab_extracted/` (728 files, mostly UI/language resources). **Nothing was run.** `PRODUCT.DAT`/`Model.ini` name the product "Plustek MobileOffice S400" (internal model code `74R`), and `74RU.inf` binds to `USB\VID_07b3&PID_0465`, so this package targets exactly this board's USB ID (this upgrades the S400 identification from a forum report to the vendor package).

**Firmware files** (`extracted/Data/74RU/`, 8,192 bytes each):

| File | SHA-256 | vs. macOS package |
| --- | --- | --- |
| `cism603.fw` | `6c764399…c160bf` | byte-identical |
| `cism216.fw` | `9730a258dc7152184a9c4fb7c8d12abb3b4de537276f4686525beb6a72f98c15` | different build (3,815 bytes differ; same stepper phase tables, at `0x1F57`) |

Both Windows images carry the built-in USB descriptor PID `0412`, as the macOS ones do. Listing of the Windows `cism216`: `cism216_win.fw_disassembly.asm`; `cism216.fw_disassembly.asm` is the macOS build.

**How it is run on Windows** (static analysis of `Data/74RU/scanapi.dll`, a 32-bit PE DLL exporting only `SCANAPI_GetFunctionTable`; `Module.ini` has `scannerid=1971,1125` = `07B3,0465`):
- No custom kernel driver: the INF installs Microsoft's in-box `usbscan.sys` (with the WIA/TWAIN/Plustek `PkWia*` user-mode layers). `scanapi.dll` enumerates with SetupAPI, opens `\\.\usbscan%x`, and uses `DeviceIoControl` (usbscan's `IOCTL_WRITE_REGISTERS` `0x80002010`, with a 16-byte block of `{wValue, length, buffer, wIndex}`), `ReadFile` and `WriteFile`.
- Sequence: (1) send small command `70 01` (`wValue 0x2012`, result `0x2013`) and treat response byte 2 as "firmware loaded" (SANE's `00 70 FF` convention); (2) send `81 01` and read response byte 4 as a device type; (3) if not loaded, read the firmware file (up to 8,192 bytes), round the length up to a multiple of 64, and write it in 64-byte blocks with `wValue 0x2009`, `wIndex` = byte offset; (4) send the boot command as a normal command (`wValue 0x2010`) `69 01 00 20` (always size `0x2000`, not the file length) and read the result (`0x2011`). This is the SANE protocol of section 4, except the write `wValue` is `0x2009` where SANE uses `0x200B`; we verified `0x200B` writes on this board but have not tested `0x2009` (a live scan showed both return a zero-length reply to IN requests). 
- File choice: the registry values under `Software\Plustek\74RU\VxD\VID_07B3&PID_0465\Setting` (defaults in `VXD.Dat`) contain `FIRMWARE = cism216.fw`, `SensorDpi=600`, `MotorStep=2`, paper-sensor and button settings (it is a sheet-fed scanner). However, if the `81 01` device-type reply is 3 the driver overwrites the file name with `cism603.fw` (code at `0x10001A82`..`0x10001AB8`, `cmp al,3`). **The EEPROM bootstrap answers `81 01` with the constant 3** (routine `sub_03A9` writes 3 to the byte at `3F04`), so on this board the driver should download **`cism603.fw`** (identical in both packages), not the `cism216.fw` named in the registry. This is from static reading only.
- A fallback default of `cism603.fw` also exists in the DLL (string at `0x1001A3A0`).

**Consequence for the motor work:** the firmware this scanner runs is most likely `cism603.fw`, whose disassembly and stepper analysis are in sections 16-17 and `cism603.fw_disassembly.asm`. Not yet done: no live `70 01`/`81 01` query was sent to confirm the type byte, no firmware was uploaded, and no motor was driven.


## 19. Live tests on the board: firmware load, buttons, motor — 2026-10-15

Hardware state: board in its scanner with the motor and CIS connected, bus-powered from USB only, **24LC16B removed** (dumped in section 15), so the chip runs its embedded ROM. Tool: `scripts/gt6816_ctl.py` (dry run unless `--execute`). Only volatile code RAM and the motor/GPIO pins were touched; nothing was written to an EEPROM.

**Confirmed on the hardware**
- ROM small commands answer before any firmware is loaded: `81 01` -> device type 3 (byte 4), as the EEPROM bootstrap code predicted. `70 01` returns a 64-byte echo before firmware (not the `00 70 FF` signature).
- **Windows firmware load works:** `cism603.fw` (8,192 bytes) written in 64-byte blocks with `wValue 0x200B` and read back identical, then booted with `69 01 00 20`. Afterwards `70 01` -> `00 70 FF DC` (SANE's "firmware loaded"), small replies are 8 bytes, the device keeps its USB address (no re-enumeration), and `17 01` motion status works. The `0x2009` write code used by the Windows driver was not needed.
- **Button works:** small command `74 01` returns the latched button code in byte 2: **`0x88` (136)** when the button is pressed, matching `ButtonID=…136…` in the Windows settings; reading clears the latch. The firmware logic: button pressed = `ASR` bit 7 (the WAKEUP pin) high, with GPIO6 then selecting the code (`0x88` if GPIO6 high, `0x02` if low). So **GPIO6 is an input** (correcting section 17), and **GPIO5** is read as an input too (small command `85`, normal commands `59` and `17`; likely a paper/home sensor).
- **Motor works, and the mapping is confirmed:** the four phase lines are **PPHDR bits 3..0 (PD0..PD3)**, with the full-step table `0F 0B 0A 0E` and half-step table `0F 03 0B 08 0A 02 0E 0C`, driven with the parallel-port data-bus output enabled (`PPDSR = 0x80`). A custom slow-step program (about 4 then 8 steps/s) produced audible stepping and roller motion. Which LB1940 pin each bit drives is still inferred, not traced.
- **Timer clock:** Timer 0/1 count at **4.0 MHz** (48 MHz / 12), measured by a calibration run (40 steps x 400,000 counts took 4.02 s). A later run planned for 2.74 s took 2.76 s. (An earlier 14.3 MHz figure in this session was a wrong estimate.)
- **Why the factory jog was silent: corrected in section 20** (it was the missing boot-result stage, not speed). The text below was my first, wrong explanation and is kept for the record: ~~`sub_1F79` reloads Timer 1 with `0xD359` = 11,429 counts = 2.86 ms per step, about 350 steps/s with no ramp, which this motor does not start at~~. The two-byte patch (`0x1F7F`: `D3`->`63`, `0x1F82`: `59`->`C0`; `gt6816_ctl.py load --jog-rate N`) does change the counted-move rate as intended, but it is not needed for the motor to work. Commands `15 01 <n lo> <n hi>` and `14 01 …` turn the rollers in opposite directions; they use the half-step table; `17 01` reports "moving" while the count runs down. Which physical direction is `15` versus `14` was not recorded.
- The stock vendor files were never modified; the patch is applied in memory at upload time.

**Problems encountered / lessons**
- Running my own programs in code RAM (`firmware/motor_slowstep.c`, `firmware/motor_step.c`, `gt6816_ctl.py run-motor`) works for the motor and gives a precise ramp, but the idle program does not answer the standard USB requests the 8051 firmware normally handles. After a USB bus reset, or after the host's own power management, the kernel log shows `device descriptor read/64, error -71` and `Device not responding to setup address`, and the device drops off the bus until it is physically re-plugged (it happened four times). Watchdog expiry did **not** reset the CPU or the USB core. Prefer the real firmware (patched jog); use the custom programs only when a re-plug is acceptable.
- A udev rule `/etc/udev/rules.d/99-plustek.rules` (`MODE="0666"` and `power/control=on` for `07b3:0465`) was installed by the owner so the node is accessible after each re-enumeration and USB autosuspend is off.

**Open / not done:** no lamp control, no sensor/paper test, no scan; direction naming; whether higher steady rates (above 100 steps/s) still start reliably, and a ramped move through the real firmware (command `16` selects the custom Timer 1 reload but its exact use was not worked out).


## 20. Root cause of the silent motor, and speed limits — 2026-10-15

**Root cause:** the scan firmware handles a command in two stages, the packet write (`wValue 0x2010`) and the result read (`wValue 0x2011`). For command `69` (boot) the result stage runs a full hardware initialisation (`sub_1470`, called from the second-stage dispatcher at `0x124B`/`0x124E`), which includes setting `PPDSR = 0x80` (DATA_OE) so that PPHDR drives the PD0..PD3 motor lines and configuring GPIO and USB. Plustek's `scanapi.dll` sends `69 01 00 20` and then reads the result (`0x100059e0` with `0x2010`/`0x2011`). My first loader only sent the write, so the motor lines were never enabled: the motor was silent for the first session (stock jog, commands `14`/`15`, with or without `10 01`). It started working later only because my custom programs had set `PPDSR` and a CPU reset does not clear it. After a physical re-plug (clean state), loading the **unpatched** `cism603.fw` with the result stage read made the stock jog (about 350 steps/s) turn the rollers in both directions. `gt6816_ctl.py` (`upload_and_boot`) now does the read, and the boot reply is `00 69 00 …`. No jog patch is needed.

**Long run:** 3,000 steps (about 8.6 s) in each direction on the stock firmware ran for the full expected time, and the owner reported it turned. Earlier, 1,000 steps (10 s) each way at ~100 steps/s were smooth.

**Speed tests** (counted moves, which use the 8-entry half-step table, constant rate with no acceleration ramp, from rest; rate set with `load --jog-rate`; the owner judged by ear and sight):

| Rate (half-steps/s) | Result |
| ---: | --- |
| 100, 150, 200, 250, 300, 325, 350 | smooth |
| 400, 500, 600, 800 | smooth |
| 1000, 1200 | smooth |
| 1600, 2000 | **failed** (the firmware still completed each move in the expected time, so the motor skipped steps or stalled; the step interrupt itself kept up to at least 2000/s) |

The practical limit without a ramp is therefore between 1,200 and 1,600 half-steps/s (about 600-800 full steps/s). The stock 350/s is well inside it; do not run above ~1,000 without a ramp, since skipped steps lose position. The owner could judge only by sound/motion; no step-position check was made. A ramped move through the real firmware, and the direction naming for `14`/`15`, remain untested.

**Also confirmed:** hot-plug/USB-reset behaviour differs by firmware: the scan firmware keeps the device on the bus; my custom RAM programs did not (section 19).


## 21. Button map — 2026-10-15

The board has three user inputs. Each was captured separately with `gt6816_ctl.py watch` (it polls the latch `74 01`, GPIO5 via `85 01` and `59 01`, and status `17 01`; quiet baseline: everything 0). Scan firmware `cism603.fw` loaded as in section 20.

| Input | Signature | Notes |
| --- | --- | --- |
| Regular button A | small command `74 01`, byte 2 = **`0x88`** (136) | latched; read-and-clear; repeats while held (27 events in a 15 s test with about 5 presses) |
| Regular button B | small command `74 01`, byte 2 = **`0x02`** | same behaviour (21 events); the two codes match `ButtonID,2,136,2` in the Windows registry defaults |
| Optical button | **GPIO5 live level**: while active, small `85 01` byte 2 = `01`, normal `59 01` byte 2 = `01`, normal `17 01` byte 3 = `02`; returns to `00` when released | never touches the latch; GPIO5 low = active; the same input the firmware uses as its sensor in the step interrupt, so it may be the paper/document sensor and not a separate button |

The firmware decodes the regular buttons as: `ASR` bit 7 (the WAKEUP pin) high means a press, and GPIO6 selects which one (`0x88` if GPIO6 is high, `0x02` if low), with a two-sample debounce; the code is latched when the button is released. Which physical button (left/right) is A versus B was not recorded. `gt6816_ctl.py buttons` now prints each press by name and the optical level changes.

## 22. Scanner light: investigation so far (unit 1, EEPROM removed) — 2026-10-15

**Not solved: no test lit the light bar on this unit.** What was established:

- **Software path.** `25 01 <mode>` (Windows `LampOn`/`LampOff`, SANE `lamp_control`; mode 1 = on, 0 = off) only sets firmware RAM flags (`24h.4` lamp-on, `26h.2` second mode) and feeds warm-up/timeout counters in the timer interrupt (`sub_0D6A`, `sub_0D80`); `27 01 <lo> <hi>` sets a lamp timeout; `28 01` reads the state (`00 28 01 01 …` after lamp-on). It switches no pin directly.
- **Hardware path (from the firmware and datasheet).** The light is the timing generator's RGB LED outputs: `LEDCR` (`FF10`) enables red/green/blue (bits 0/2/4, polarity bits 1/3/5); `LEDRHR..LEDFLR` (`FF0C..FF0F`) set the pulse window against the 16-bit line counter (`MOD16` `FF03/04`, init value `0x157B`); `TGCR` (`FF00`) bit 0 enables the generator. Init sets the window to rise `0x0008` / fall `0x012C` (about 5% duty). Normal commands `70`/`71`/`72` set `LEDCR` to red/green/blue and `73` to off; `76 01` loads three rise/fall pairs (12 bytes at packet bytes 2..13, little-endian words per colour). Datasheet (44-pin column): `TGR/LEDR` pin 11, `TGG/LEDG` pin 10, `TGB/LEDB` pin 9; `WAKEUP` pin 8. These pin numbers are from the datasheet only; the board was not probed.
- **Live tests, owner watching the bar:** `70/71/72/73` cycled for 3 s and 6 s each: nothing visible. `76` with a ~50% window (rise `0x0010`, fall `0x0AA0`) then `70`..: nothing visible, and 4 s after the green step the scanner disconnected (kernel: `USB disconnect, device number 118`, then a new device 120 on the same port). **That disconnect was the owner swapping in a second scanner at that moment, not a chip reset or brown-out** (an earlier version of this note guessed a brown-out; that was wrong). Unit 2 enumerated at 17:30:02 and, like unit 1, comes up with noise in code RAM (`captures/ram/gt6816_unit2_m1_poweron.bin`, 79 of 2,048 bytes equal to the EEPROM image), i.e. its power-on EEPROM load, if any, is not visible there either.
- **SANE as a reference.** With a private config (`sane/gt68xx.conf`: `usb 0x07b3 0x0465`, `override "plustek-opticslim-m12"`; use `SANE_CONFIG_DIR=$PWD/sane`) the GT68xx backend identifies the unit as a sheet-fed OpticSlim M12 and reuses the loaded firmware. It waits for the document sensor (GPIO5, the "optical button" = paper present) before scanning, so a sheet must be inserted. The sequence it sends (logs: `logs/sane_scan_try3.log`) is: `69 01 00 20`, `2E`, `3F`, `25 01 01`, `28`, `17`, `59`, `82 01 24` (feed), `17`…, `25 01 01`, `20 01 24 00 96 1B …` (scan parameters), `22 01 24 0A 23 0F 23 0B` (AFE), `43` (start), `35` (read), `42`, `83` (stop), `25 01 00`. The scan completed and fed the sheet but returned an 858 x 1177 image whose every pixel is 16 (flat black level), so the sensor path did not produce a usable image on this unit with the M12 model parameters. Whether the light was on during that scan is unknown (the owner saw no light).
- **Next:** try a second unit of the same model (with its own EEPROM) to separate a fault or modification of unit 1 from a genuine software gap.


## 23. The scanner light is driven — 2026-10-15

**Solved on unit 2 (the second scanner of the same model; unit 1 was never tested with this sequence, but its failures came from lacking `10 01`).** The CIS LED lights, in red, green or blue, when the scan firmware has been loaded as in section 20 and the host sends:

1. `10 01` — power/enable: sets `SHRRR` (`FF16`) to `0x80`, a RAM flag (`24h.6`, reported by `3F 01`), the hidden register bit `FFFF`.6 and GPIO0 low;
2. one colour command: `70 01` = red, `71 01` = green, `72 01` = blue (each sets `LEDCR` `FF10` to `0x01` / `0x04` / `0x10`);
3. to turn off: `73 01` (`LEDCR` = 0) and `11 01` (`SHRRR` = 0, clears the flag).

Evidence from the owner watching the light bar: `70/71/72` alone (any LED window, with or without `25 01 01`): dark; `10 01` alone: dark; `10 01` + `70 01` (red): lit; with `10 01` active, `70`, `71`, `72` gave three clearly different colours; `10 01` then `11 01` then `70 01`: dark. Therefore the `SHRRR` write is necessary (`11` clears only `SHRRR` and the RAM flag, leaving `FFFF`.6 and GPIO0 as `10` left them). Whether `SHRRR` alone is sufficient was not isolated: `10` is the only command that sets it, and it sets the other things too.

What `SHRRR = 0x80` means: the datasheet defines `FF16` bit 7 = SHR polarity (1 = invert the output), bit 6 = SHR enable (0 = disable the output). So `0x80` does not pulse the SHR line, it parks it at a constant inverted level, and that static level evidently powers or enables the LED section. The datasheet 44-pin table lists the sample-hold-reset output as `SHB`, pin 44 (unverified on the board). The colour channels are the separate `TGR/LEDR`, `TGG/LEDG`, `TGB/LEDB` outputs (pins 11/10/9 in the same table).

Not needed for the light: `25 01 01` (it only sets lamp-on/warm-up/timeout flags and counters), the wide LED window from `76` (the default window, about 5% duty, was bright enough), and the `FFFF`/GPIO0 side effects (not isolated). Only one colour channel can be active with these commands (`LEDCR` is written whole); white would need another command that writes `LEDCR` = `0x15`.

**Why the SANE scan was black:** SANE's trace (section 22) sends `25 01 01` but never `10 01` and never a colour command before reading, so the LED stayed off and the image was a flat 16. A scan after `10 01` was not yet tried.

`gt6816_ctl.py lamp r|g|b|off [--seconds N] --execute` now does this.

## 24. Rainbow light show (unit 1, EEPROM removed, same firmware and `10 01` sequence) — 2026-10-15

The scanner swapped back to the first unit (ROM state after re-plug, `cism603.fw` loaded as in section 20). Its light works with the same sequence as unit 2 (section 23), so neither unit is faulty. `gt6816_ctl.py rainbow` sweeps the hue (red, orange, yellow, green, cyan, blue, violet) by mixing the three single-channel commands in time, since the chip can light only one LED channel at a time (the firmware only ever writes `LEDCR` = 1, 4, 0x10 or 0) and the three colours share one rise/fall window register pair, so there is no hardware colour mixing.

Findings, judged by the owner watching the bar (each command round trip costs about 0.4 ms):
1. Time-slicing at 125 Hz with the stock window (about 5% duty): coloured but flickery. Cause: the LED fires one short pulse (about 146 µs of every 2.75 ms line period, about 364 Hz), so the slicing only sampled which channel was selected during those pulses (aliasing).
2. Widening the window with `76` (rise `0x0010`, fall `0x1200`, about 84% of the `0x157B` line period) and slicing at 200 Hz: better, still some flicker.
3. 333 Hz slicing with a 97% window: worse (switch time and host scheduling jitter are a large fraction of each 0.9 ms slot).
4. **Best (now the default): one colour per LED pulse.** One command per line period (2.7495 ms = `0x157B` counts at an assumed 2 MHz pixel clock, giving 363.7 Hz in the test), choosing the channel by first-order sigma-delta so the long-run mix follows the hue, with the stock narrow window. A switch landing between pulses cannot distort a pulse; the host and chip clocks drift, so an occasional pulse can be split. Owner: "better than before", not claimed perfectly smooth.

Command: `gt6816_ctl.py rainbow [--mode pulse|slice] [--seconds N] [--sweep S] [--period P] --execute`. It always ends with `73 01`, `11 01` (and restores the stock window in slice mode).

## 25. Sustained 1200 half-steps/s stalls — 2026-10-15

With the scan firmware patched to about 1200 half-steps/s (`load --jog-rate 1200`, reload value `F2FB`), a counted move of 6,000 steps in command `14` (direction `b`) ran for the expected 5.0 s according to the status polls, but the owner reported the motor **stuttered / stalled**. This disagrees with section 20, where 1000 and 1200 half-steps/s were reported smooth for 1,500-step (1.25 s) moves. Possible reasons, none tested: the longer run (5 s versus 1.25 s: heating, resonance, or lost steps accumulating), a different scanner (a second unit of the model was swapped in and out during the session, so the motor may differ), or the rate being marginal. Practical conclusion: without an acceleration ramp, do not rely on 1200 half-steps/s; the tested-safe range is up to about 800 half-steps/s for 800-step moves and up to 1000 for 1.5 s. The firmware's counted move gives a constant rate only, so a higher sustained speed needs a ramp (the custom `motor_step` program supports one, at the cost of USB recovery, see section 19). Direction naming (which of `14`/`15` is the paper-feed direction) is still unconfirmed. The scanner was reloaded with the stock-rate firmware afterwards.

## 26. The power LED is GPIO0 and can be blinked — 2026-10-15

**Result:** with a two-byte firmware patch, the power LED is switched by normal commands `50 01` (on) and `51 01` (off) and can be blinked at any rate (`gt6816_ctl.py blink`). Owner-observed: off during `51`, on during `50`, and a clean ~2 Hz blink; baseline with no commands is steady on.

**How it works (firmware analysis plus live tests):**
- The LED is on GPIO0 (`GPIODR` `FF95` bit 0, direction `GPIOCR` `FF94` bit 0), high = on. Commands `50`/`51` set/clear that bit (`52`/`53` also set the hidden `FFFF` bit 6). The datasheet's 44-pin table does not list GPIO0 as bonded out, yet it clearly drives this LED, so the package or pin table differs from the datasheet.
- The Timer 0 interrupt (vector `0x0B`, about 12 ms per tick) forces GPIO0 high whenever the scanner is idle (no counted move `2Ah.2`, no scan blink `27h.3`, and no paper on the GPIO5 sensor): in the interrupt at `0x0E82..0x0E9F` and in `sub_0D1C` (idle branch at `0x0D3C..0x0D45`, about every 3 s). That is why the LED is steady on, and why holding `51` every 50 ms only dimmed/flickered it (the interrupt re-set it every 12 ms).
- The firmware's own blink is `27h.3`: `sub_0D1C` then toggles GPIO0 every 21 ticks (about 250 ms). `27h.3` is set by command `35` (data read start, `0x11C4`) and cleared at scan end (`sub_18E5`). Sending `35 01` alone produced only a single flicker (the flag is cleared almost at once, presumably because there is no data transfer), so this is not a usable blink by itself.
- **Patch:** NOP the two `SETB ACC.0` instructions at `0x0E9A` and `0x0D40` of the uploaded copy of `cism603.fw` (bytes `E0 D2 E0 90` become `E0 00 00 90`; checked before patching). The interrupt then rewrites GPIODR unchanged, and the host owns GPIO0. `gt6816_ctl.py load --free-led --execute` applies this in memory; the vendor file is untouched. Side effect: the idle branch no longer forces the LED on, so the LED stays wherever the host leaves it until the stock firmware is reloaded.
- **Alternative without a patch (inferred, not tested):** while paper holds the GPIO5 sensor active (or a counted move is running), the interrupt skips its forcing code, so `50`/`51` should work directly.

Commands: `gt6816_ctl.py load --free-led --execute`, then `gt6816_ctl.py blink --hz 2 --seconds 10 --end on --execute`, or single `normal 0x50 0x01` / `normal 0x51 0x01 --execute`. Reload with plain `load --execute` to restore the stock behaviour (LED steady on). The scanner was left on the stock firmware.

## 27. Single steps and holding torque — 2026-10-25

**Single steps.** A counted move with count 1 works: `14 01 01 00` is one half-step (8-entry table), `82 01 01 00` is one full step (4-entry table, command `82` clears the half-step flag). Both were accepted and the status returned to idle within 0.3 s. The owner's feel of them was not recorded. The firmware keeps the phase index in RAM (`4Fh`), so successive moves continue from where the last one stopped; the index starts at 0 after a firmware load and the half-step table index runs mod 8 (full-step: mod 4).

**Holding torque.** The stock firmware always switches the coils off (`PPHDR` = 0, i.e. phase lines PD0..PD3 low) at the end of a counted move, in the idle interrupt, and in a few other places, so the shaft turns freely between moves. 29 places in `cism603.fw` write zero to `PPHDR` (pattern `90 FF A2 74 00 F0`). Patching the `MOVX @DPTR,A` (`F0` -> `00`, NOP) at six of them (`0x0E79` idle interrupt, `0x1D42` and `0x1DB6` uncounted stops, `0x1EBB` end of a counted move, `0x1EE9` zero-count move, `0x1EF4` start of a counted move) leaves the last phase energised. The explicit release commands (`12 01` sets `PPHDR` = 0, also `83 01`, `24`, `30`) are untouched, so `normal 0x12 0x01` releases the motor. `gt6816_ctl.py load --hold --execute` applies the patch in memory; the vendor file is untouched.

**Result.** After `load --hold` and `14 01 02 00` (two half-steps, ending on the full-step phase `0E` with both bridges on), the owner reported the roller **holds firmly**. Choosing an even number of half-steps matters: odd positions use a table entry with only one bridge enabled, which gives a weaker hold. Before the first move after a load the phase lines stay at the init value `0xF8` (only bit 3 set), so holding is only meaningful after a move.

**Cautions.** Holding keeps current flowing through the motor and the LB1940 for as long as it is on, from the bus-powered 5 V; no measurement of the current or temperature was made. Release it when not needed (`normal 0x12 0x01 --execute`, or reload the stock firmware, whose idle interrupt switches the coils off). The scanner was left holding at the end of this test.

## 28. Low running torque: full-step does not help — 2026-10-25

The owner found the motor easy to stop by gently holding the roller at 61 and 100 half-steps/s (running torque), although the standstill hold (section 27) is firm. Hypothesis: half-step mode lowers torque because every second table entry energises only one coil (half table `0F 03 0B 08 0A 02 0E 0C`: bit 3 or bit 1 low in the odd entries). Test: `gt6816_ctl.py load --full-step --jog-rate 61.1 --execute` NOPs the `SETB 26h.1` (half-step flag) in the handlers of commands 14 and 15 (`0x0EE5`, `0x0EF2`; bytes verified `D2 31`), so those moves use the full-step table `0F 0B 0A 0E` with both bridges always enabled (twice the angle per step, so twice the shaft speed at the same step rate). A 305-step, 5 s run at 61 steps/s completed in the expected time. **Owner: torque the same as before.** Conclusion: the running torque is limited by something other than the phase pattern, most likely the driver's current limit and the bus-powered 5 V supply (neither can be changed from software: the LB1940 has only direction and enable inputs from this chip, and no voltage or current was measured). The step rate cannot go below ~61/s in the firmware's own timer, and stepper torque is already near its maximum at these low speeds, so slower does not help either.

Untested ideas: power the scanner through a powered USB hub or a different port (a sagging bus voltage under motor load would reduce current and torque), and measuring the supply voltage at the LB1940 and its motor current. The scanner was reloaded with the stock firmware afterwards.

## 29. Full steps are now the default; 200 steps/s run — 2026-10-25

At the owner's request `gt6816_ctl.py load` now applies the full-step patch (section 28) by default; `--half-step` keeps the stock half-step moves. A 1,000-step run at ~200 full steps/s (reload `B1E0`, 20,000 counts) in direction `b` completed in the expected 5.0 s according to the status polls. The owner's verdict on smoothness and torque at this rate was not given yet. At the same step rate a full step turns the shaft twice as far as a half-step, so this is about 400 half-step-equivalents per second.

## 30. Direction mapping — 2026-10-25

Owner-observed (two 3 s moves of 240 full steps at ~80 steps/s, direction `a` first, then `b`): **direction `b` = command `14` turns the roller clockwise** as seen from the owner's viewing side, so direction `a` = command `15` is anticlockwise. (SANE uses command `82`, the same phase direction as `14`, to feed a document in, which suggests clockwise from that side is also the feed-in direction; the owner did not confirm that.) The earlier 1 s identification moves were too short to judge. A clockwise 3 s run at ~80 steps/s (240 steps, command `14`) completed in the expected time per the status polls.

## 31. Motor lock after every rotation is now the default — 2026-10-25

At the owner's request `gt6816_ctl.py load` applies the hold patch of section 27 by default (`--no-hold` restores the stock coils-off behaviour), together with the default full-step patch of section 29. After `load --jog-rate 100` and a 4-step anticlockwise move (command `15`) the owner reported the roller **locked firmly**. The firmware loses its phase index on every reload (RAM is cleared), so the lock after a reload is established by a small move and can sit up to a couple of steps from where the previous rotation ended. In full-step mode every table entry (`0F 0B 0A 0E`) energises both coils, so any step count gives a full-strength hold (the even-count caution of section 27 applies to half-step mode only). The coils stay energised until released with `normal 0x12 0x01 --execute` or until the firmware is reloaded without a move. No current or temperature was measured; do not leave the motor locked unattended for long on bus power.

## 32. Motor console — 2026-10-25

`scripts/motor_console.py` is an interactive console for the motor. It waits for the scanner, loads the patched `cism603.fw` (full steps, motor locked after moves; no RAM backup file is written per load), then loops asking for speed (61-1500 steps/s; warning above 500, where earlier tests stalled), direction (`cw` = command `14`, `ccw` = command `15`) and step count (1-65535). It shows the expected duration, waits for Enter, runs the move while polling the status, and reports the actual time. Changing the speed reloads the firmware (about 3 s) because the rate is patched into the uploaded copy. `r` releases the coils, `q` quits and offers to release the motor (default yes); Ctrl+C during a move sends the stop command `83 01`. Tested with scripted input: 20 steps cw at 100/s, then 8 steps ccw at 80/s (reload), release on exit.

## 33. Torque under load, the LB1940 driver, and slow starts — 2026-10-25

**Report.** With 200 g hung on each side of a rubber belt over the motor shaft, continuous runs only jerked in place ("not enough torque").

**Driver facts** (ON Semiconductor LB1940 datasheet, `lb1940.pdf` fetched from the link in the readme, not saved in the repo): a 2-channel H-bridge **constant-current** driver; absolute maximum output current 400 mA per channel; the coil current is set by an analog reference `VC` (built-in `Vref` = 0.9 V through a divider) and a sense resistor `RFB` at the `RFG` pins (`I = VC / RFB`, e.g. 100 mA at VC = 0.2 V, RFB = 2 ohm in the datasheet's example); `ENA1/ENA2` and `IN1/IN2` are the only logic inputs. **The torque is therefore set by board components (divider and sense resistor), not by anything this chip's firmware can write**; the board's actual current setting is unknown (not measured). A constant-current driver already delivers its set current at low speed, which is why full-step (section 28) and slower continuous rates did not raise the torque.

**What does help: a slow start.** The firmware's own continuous stepping cannot run below ~61 steps/s. Host-timed single-step moves can (`14 01 01 00` per step, with the coils kept on by the hold patch). With the 400 g belt load on, 50 single steps at **10 steps/s** (clockwise) made the shaft turn, "a bit jerky" (owner), where the continuous runs only jerked. `scripts/motor_console.py` now has a **slow-start ramp**: a start speed below the speed makes the first N and last N steps host-timed single steps with the rate rising (then falling) linearly from the start speed (capped at 80% of the loaded rate), and the steps in between one continuous move at the full speed. Tested with scripted input (100 steps, start 10, ramp 20, speed 100): ramp up, cruise and ramp down, 1.7 s as predicted. Whether a heavier load can then be accelerated to 61-100 steps/s was not tested.

**Options if more torque is needed (hardware, not done):** gear or pulley reduction on the shaft; a better 5 V source (powered hub); raising the coil current by changing the board's `VC` divider or `RFB` (up to the driver's 400 mA absolute maximum; risks overheating the motor and driver and exceeding the 500 mA USB budget, and needs a meter). For a proper torque figure hang one weight on a thread wound on the shaft (torque = m * g * r); equal weights on both sides give almost no net torque, and add 400 g of side load on the shaft bearing.

## 34. Slow-rate tests with the 400 g belt load — 2026-10-25

Host-timed single full steps (`14 01 01 00` each, coils kept on), clockwise, with the 200 g + 200 g belt load on the shaft, owner-observed: **2 steps/s (20 steps): jerked in place**; **10 steps/s (50 steps): turned, a bit jerky** (first attempt: no verdict, second attempt: turned); **20 steps/s (40 steps) and 40 steps/s (80 steps): neither turned**. The results are not monotonic in speed, which means the load sits at the edge of what the motor can do (a load right at the pull-out torque: whether it advances depends on friction, belt position and momentum, not on the rate). Slower is not better (static torque must beat the load at every step) and there is no clear sweet spot. Conclusion: the 400 g belt load is about the limit of this motor and driver setting; reduce the load (for example 100 g, or one-sided on a thread wound on the shaft to get a torque figure) or add gearing / raise the driver current (section 33). The scanner was left with the coils locked (hold patch).

## 35. Repeat of the slow rates under load — 2026-10-26

Same setup as section 34 (200 g + 200 g belt load, host-timed single full steps, clockwise, coils kept on). **5 steps/s (50 steps, 10 s): turned, a bit jerky. 10 steps/s (100 steps, 10 s), run twice in total across sessions: turned, a bit jerky each time.** Together with section 34 (2, 20 and 40 steps/s did not turn it), the loaded shaft turns reproducibly at 5-10 steps/s and not at 2, 20 or 40, so there is a narrow usable window; the motion is uneven at every rate. One attempt on 2026-10-26 did not run because the scanner had dropped off the bus overnight (re-plugged, firmware reloaded, then the run completed in the expected 10.0 s).

## 36. A second, different scanner: Mustek ScanExpress A3 USB (055f:0210) — 2026-10-26

On 2026-10-26 the owner connected "another scanner" that turned out not to be an S400: `055f:0210`, Mustek ScanExpress A3 USB (`bcdUSB 1.10`, `bcdDevice 1.00`, product string "USB Scanner", one vendor-specific interface, bulk IN `0x81` and OUT `0x02` of 64 bytes, **self-powered** per `bmAttributes 0xE0`). SANE's `gt68xx_devices.c` lists it as `mustek_a3usb_model`: **same GT6816 command set** as the S400 (`mustek_gt6816_command_set`: RAM read/write `0x200C`/`0x200B`, commands via `0x2010`/`0x2011`, small commands `0x2012`/`0x2013`), firmware file `A32fw.usb` (not available here), an A3 flatbed (scan area 297 x 433 mm), CIS sensor with a lamp that needs warming (`GT68XX_FLAG_CIS_LAMP`), 600 dpi motor.

**Read-only identification** (no writes): `70 01` -> `00 70 00` (no firmware loaded), `81 01` -> device type `0` (the S400 answers 3), code RAM at power-on is noise like the S400's (`captures/ram/mustek_a3usb_m1_poweron.bin`, SHA-256 starts `1862ea77…`).

**Motor test.** With the owner's confirmation (adapter connected, nothing blocking the carriage, any transport lock unlocked) the minimal stepper program `firmware/motor_step.bin` (enables `PPDSR` DATA_OE and walks the 4-entry full-step table on `PPHDR` bits 3..0 = PD0..PD3; nothing else) was uploaded to its code RAM (2,112 bytes, verified block by block; RAM backup `captures/ram/mustek_a3usb_m1_pre_stepper.bin`) and booted with `69 01 00 20`: 20 steps at 10 steps/s. The program ran (completion marker `MOTR` + 20 steps arrived after 2.02 s, which also shows the same 4 MHz timer clock), but the owner saw and heard **nothing**. **Conclusion: on this scanner PD0..PD3 do not drive the motor** (or the motor needs power or enable lines I have not driven). Its motor and lamp wiring are different from the S400's and cannot be guessed safely; the S400's `cism603.fw` was deliberately not loaded on it.

**Next step.** Obtain the Mustek's own firmware `A32fw.usb` (from Mustek's ScanExpress A3 USB driver package) and disassemble it with `scripts/gt6816_disasm.py`, as was done for the S400, to find the registers/pins the motor and lamp use. A blind alternative (sweeping GPIO0..7 and the 8051 port 1 groups with a custom program while listening) would take many runs and a re-plug after each.

## 37. The S400 firmware drives the Mustek's motor — 2026-10-26

After a re-plug (the earlier test program had left the Mustek unresponsive, `70 01`/RAM reads timing out), the owner asked to load the Plustek S400 firmware on the Mustek ScanExpress A3 USB (`055f:0210`). `cism603.fw` with the full-step and ~100 steps/s patches (no motor-lock patch) was uploaded to its code RAM (8,192 bytes, verified, RAM backup `captures/ram/gt6816_m1_pre_load_064653.bin`), booted with `69 01 00 20` and the result stage read (`00 69`). Result: `70 01` -> `00 70 FF CE` (firmware running), `17 01` answers. A clockwise move (`14 01 64 00`, 100 steps, ~1 s) was accepted and **the owner reported the carriage moved / ticked**. No lamp or sensor commands were sent. The direction the carriage moved was not recorded.

**Why the earlier minimal program did not move it (section 36):** that program only enabled `PPDSR` DATA_OE and drove PPHDR bits 3..0. The S400 firmware's full startup (boot result stage, `sub_1470`/`sub_0909`) additionally sets `GPIOCR` = `0x0F` and `GPIODR` = `0xFF` (GPIO0..3 outputs high), writes port 1 (`P1` = `0xFF`), initialises the timing generator, AFE and USB, and the idle interrupt forces GPIO0 high. At least one of those additional outputs is evidently needed by the Mustek's motor driver (an enable or power line); which one was not isolated. This is an untested hypothesis.

`scripts/motor_console.py --mustek` points the console at the Mustek (add `--no-hold` to let the coils switch off after each move). Cautions: the S400 firmware also sets other outputs on a board it was not written for, so keep moves short; the Mustek has a lamp (CCFL-like, needs warming) and the S400 lamp commands (`10 01`, `70`..`72`) were not sent and should not be sent without checking what they drive there.

## 38. Mustek there-and-back run — 2026-10-26

With the S400 firmware running on the Mustek ScanExpress A3 USB (section 37; full steps, ~100 steps/s, no motor-lock patch): a clockwise move of 1,000 steps (command `14`, 10.1 s per the status polls) followed, after 2 s, by an anticlockwise move of 1,000 steps (command `15`, 10.1 s). The owner reported **smooth, there and back**; no end stop was reached. The physical direction of the carriage for "clockwise" and the distance travelled were not recorded. The motor-lock patch was not used, so the coils switched off after each move.

## 39. Erratum: the "Mustek ScanExpress A3 USB" was an S400 board without its EEPROM — 2026-10-26

**Correction to sections 36-38.** The owner reports that the board that enumerated as `055f:0210` ("USB Scanner", `bcdDevice 1.00`) was an S400 board **from which its EEPROM had been removed** (first reported as a 24C04; the owner then corrected this to a **24LC16B**, the same part as in section 15). After the EEPROM was soldered back, the same board enumerated at 07:50:51 as `07b3:0465`, "600dpi USB Scanner", `bcdDevice 5.01` (kernel log), the S400's identity. So it was never a Mustek ScanExpress A3. Sections 36-38 call it one because I matched the USB ID to SANE's table; the facts recorded there (the read-only probe, the minimal-program test, the S400 firmware test) are accurate, but "Mustek", "A3 flatbed", "self-powered", "CCFL-like lamp" and the `A32fw.usb` plan were wrong. `055f:0210` is the GT6816's built-in ROM identity (Mustek is the chip's original OEM), which the chip presents when no EEPROM answers.

**What it shows.**
- At power-on the chip does consult the EEPROM, at least for its USB identity (VID/PID, strings, `bcdDevice`): with the 24LC16B present it is a Plustek S400, without it a ROM-default `055f:0210`. This matches the datasheet's statement that the chip searches for a serial EEPROM at power-on and uses its embedded code when none is found. It also means the EEPROM's descriptor table (section 16, offsets `0x00D2`..) is what the host sees.
- The S400 firmware downloads and runs identically on the EEPROM-less ROM identity (same GT6816 protocol), and drove the motor there.
- The earlier puzzle (section 36) is therefore about the same board with and without its EEPROM-supplied startup: the minimal PD0..PD3 program did not move the motor on the EEPROM-less board, the full S400 firmware did. The EEPROM's own startup (section 16: `GPIOCR` = `0x40`, `GPIODR` = `0x20`, `P1` = `0xFF`, `FFFF` = `0x20`, `FFFD` = `0`) and the S400 firmware's init set extra outputs that this board's motor driver may need; not isolated.
- This board's EEPROM is a 24LC16B, the same part (2 KB) as the one dumped in section 15; an earlier remark here that it was a 24C04 (and so a different board) came from a misreport and is withdrawn. Whether its contents equal the section 15 dump has not been checked (it has not been dumped).
- The M1 noise seen at power-on on every unit (EEPROM present or not) remains unexplained: if the EEPROM code runs, it is not visible through the `0x200C` RAM read.

The scanner is back as `07b3:0465` with the S400 firmware running (`70 01` -> `00 70 FF`), motor locked after the last move.
