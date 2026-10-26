#!/usr/bin/env python3
"""Read-only 24LC16B dump through a CH341A (1a86:5512) in I2C mode.

Speaks the CH341 I2C stream protocol with PyUSB (no kernel driver exists for
this adapter).  Only two kinds of bus transaction are ever built:
  * random read:    START, control(W), byte address, START, control(R), n x IN, STOP
No data byte is ever sent in write direction after the byte address, so the
EEPROM cannot be programmed by this tool.  Default mode is an offline dry run.

24LC16B: 8 blocks of 256 bytes at 7-bit addresses 0x50..0x57
(control bytes 0xA0|blk<<1 write, 0xA1|blk<<1 read).
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
VID, PID = 0x1A86, 0x5512
EP_OUT, EP_IN = 0x02, 0x82
CMD_I2C_STREAM = 0xAA
STM_STA, STM_STO, STM_OUT, STM_IN, STM_SET, STM_END = 0x74, 0x75, 0x80, 0xC0, 0x60, 0x00
SPEEDS = {0: "20 kHz", 1: "100 kHz", 2: "400 kHz", 3: "750 kHz"}
BLOCKS, BLOCK_SIZE, CHUNK = 8, 256, 32


def set_speed_frame(speed: int) -> bytes:
    return bytes((CMD_I2C_STREAM, STM_SET | speed, STM_END))


def probe_frame(block: int) -> bytes:
    return bytes((CMD_I2C_STREAM, STM_STA, STM_OUT | 1, 0xA0 | (block << 1), STM_STO, STM_END))


def read_frame(block: int, offset: int, count: int) -> bytes:
    assert 1 <= count <= CHUNK and 0 <= offset < BLOCK_SIZE and 0 <= block < BLOCKS
    assert offset + count <= BLOCK_SIZE
    frame = bytearray((CMD_I2C_STREAM, STM_STA, STM_OUT | 2, 0xA0 | (block << 1), offset,
                       STM_STA, STM_OUT | 1, 0xA1 | (block << 1)))
    if count > 1:
        frame.append(STM_IN | (count - 1))  # ACKed bytes
    frame.append(STM_IN)  # final byte, NACKed
    frame += bytes((STM_STO, STM_END))
    return bytes(frame)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--speed", type=int, choices=SPEEDS, default=0,
                        help="bus speed: 0=20 kHz (default, safest), 1=100 kHz, 2=400 kHz")
    parser.add_argument("--passes", type=int, default=2, help="independent full reads (default: 2)")
    parser.add_argument("--prefix", default=str(ROOT / "captures" / "eeprom" / "gt6816_24lc16b"),
                        help="output file prefix (default: captures/eeprom/gt6816_24lc16b)")
    parser.add_argument("--timeout", type=int, default=2000)
    parser.add_argument("--execute", action="store_true", help="drive the I2C bus")
    args = parser.parse_args()

    print("set speed :", set_speed_frame(args.speed).hex(" "), SPEEDS[args.speed])
    print("probe  0x50:", probe_frame(0).hex(" "))
    print("read blk0@0:", read_frame(0, 0, CHUNK).hex(" "))
    if not args.execute:
        print("Dry run: no device opened.  Re-run with --execute after wiring is verified.")
        return 0

    import usb.core
    import usb.util

    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise SystemExit("CH341A (1a86:5512) not found")
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except (usb.core.USBError, NotImplementedError):
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)

    def xfer(frame: bytes, expect: int) -> bytes:
        dev.write(EP_OUT, frame, args.timeout)
        return bytes(dev.read(EP_IN, max(expect, 1) + 8, args.timeout))

    xfer_nr = lambda f: dev.write(EP_OUT, f, args.timeout)
    xfer_nr(set_speed_frame(args.speed))

    # This adapter returns no ACK status bytes, so presence cannot be probed
    # per block.  Require both lines idle-high instead, and later reject a
    # read of a nonexistent address that looks like a real one.
    dev.write(EP_OUT, bytes((0xA0,)), args.timeout)
    pins = bytes(dev.read(EP_IN, 16, args.timeout))
    sda, scl = (pins[2] >> 7) & 1, (pins[2] >> 6) & 1
    print(f"idle pins: status {pins.hex(' ')}  SDA={sda} SCL={scl}")
    if not (sda and scl):
        raise SystemExit("SDA and/or SCL idle LOW: the bus is held down or unpowered (check EEPROM VCC "
                         "with a meter, clip contact/orientation, and back-feeding of the board). "
                         "Refusing to read; any data would be meaningless.")

    pathlib.Path(args.prefix).parent.mkdir(parents=True, exist_ok=True)
    images = []
    for number in range(1, args.passes + 1):
        image = bytearray()
        for block in range(BLOCKS):
            for offset in range(0, BLOCK_SIZE, CHUNK):
                frame = read_frame(block, offset, CHUNK)
                reply = xfer(frame, CHUNK + 3)
                if len(reply) != CHUNK:
                    raise SystemExit(f"unexpected reply length {len(reply)} at block {block} offset {offset}")
                image += reply
        path = pathlib.Path(f"{args.prefix}_read{number}.bin")
        path.write_bytes(image)
        digest = hashlib.sha256(image).hexdigest()
        print(f"pass {number}: {len(image)} bytes -> {path}  sha256 {digest}")
        images.append(bytes(image))

    if len(images) > 1 and all(i == images[0] for i in images):
        img = images[0]
        flags = []
        if len(set(img)) == 1:
            flags.append(f"every byte is 0x{img[0]:02x}: NOT a valid dump (blank EEPROM reads 0xFF; "
                         "0x00 means a held-low bus or no device)")
        print(f"All {len(images)} passes are identical.", "; ".join(flags) or "Contents are non-uniform.")
        pathlib.Path(f"{args.prefix}_dump.bin").write_bytes(img)
        print(f"wrote {args.prefix}_dump.bin  (sha256 {hashlib.sha256(img).hexdigest()})")
        return 0
    print("Passes DIFFER: do not trust any of these files.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
