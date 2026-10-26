#!/usr/bin/env python3
"""Upload and run the GT6816 stage-1 RAM marker probe.

The default mode is an offline dry-run: it parses the supplied Intel HEX or
binary image and prints the SANE USB operations without opening a device.
Use --execute only when a disposable, recoverable live USB test is intended.
This tool handles volatile program RAM only; it never claims to dump EEPROM.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import logging
import pathlib
import struct
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK = 64
RAM_SIZE = 8192
DEFAULT_TIMEOUT_MS = 3000
MARKER_SIZE = 8
MARKER = bytes((0xA5 ^ i) for i in range(MARKER_SIZE))


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_hex(path: pathlib.Path) -> bytes:
    """Parse Intel HEX records into a zero-based contiguous image."""
    data: dict[int, int] = {}
    base = 0
    eof = False
    for line_no, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"{path}:{line_no}: expected ':'")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: invalid HEX record") from exc
        if len(record) < 5 or (sum(record) & 0xFF):
            raise ValueError(f"{path}:{line_no}: bad record checksum/length")
        count, address, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        payload = record[4:-1]
        if count != len(payload):
            raise ValueError(f"{path}:{line_no}: byte count mismatch")
        if kind == 0x00:
            for offset, value in enumerate(payload):
                data[base + address + offset] = value
        elif kind == 0x01:
            eof = True
            break
        elif kind == 0x02 and len(payload) == 2:
            base = int.from_bytes(payload, "big") << 4
        elif kind == 0x04 and len(payload) == 2:
            base = int.from_bytes(payload, "big") << 16
        elif kind not in (0x03, 0x05):
            raise ValueError(f"{path}:{line_no}: unsupported record type {kind:02x}")
    if not eof:
        raise ValueError(f"{path}: missing EOF record")
    if not data:
        raise ValueError(f"{path}: HEX image has no data records")
    end = max(data) + 1
    image = bytearray([0x00] * end)
    for address, value in data.items():
        image[address] = value
    return bytes(image)


def load_image(path: pathlib.Path) -> bytes:
    if path.suffix.lower() in (".hex", ".ihx"):
        image = parse_hex(path)
    else:
        image = path.read_bytes()
    if not image:
        raise ValueError(f"{path}: image is empty")
    if len(image) > RAM_SIZE:
        raise ValueError(f"{path}: image is {len(image)} bytes, maximum is {RAM_SIZE}")
    return image


def padded_blocks(image: bytes) -> tuple[bytes, int]:
    size = ((len(image) + BLOCK - 1) // BLOCK) * BLOCK
    return image.ljust(size, b"\x00"), size


def expected_marker() -> bytes:
    return MARKER


def read_exact(device, request_type: int, request: int, value: int, index: int,
               length: int, what: str) -> bytes:
    """Issue a control read and reject short replies."""
    result = bytes(device.ctrl_in(request_type, request, value, index, length))
    if len(result) != length:
        raise RuntimeError(f"short {what}: expected {length} bytes, got {len(result)}")
    return result


class DryRunDevice:
    def __init__(self, log: logging.Logger):
        self.log = log

    def ctrl_out(self, request_type: int, request: int, value: int, index: int, data: bytes) -> None:
        self.log.info("CTRL OUT type=%02x req=%02x value=%04x index=%04x len=%d data=%s",
                      request_type, request, value, index, len(data), data[:8].hex(" "))

    def ctrl_in(self, request_type: int, request: int, value: int, index: int, length: int) -> bytes:
        self.log.info("CTRL IN  type=%02x req=%02x value=%04x index=%04x len=%d",
                      request_type, request, value, index, length)
        return bytes(length)

    def bulk_in(self, endpoint: int, length: int) -> bytes:
        self.log.info("BULK IN   endpoint=%02x len=%d", endpoint, length)
        return bytes(length)


def run(device, image: bytes, backup_path: pathlib.Path, log: logging.Logger, timeout: int) -> None:
    padded, transfer_size = padded_blocks(image)
    log.info("image=%d bytes transfer_size=%d sha256=%s", len(image), transfer_size,
             hashlib.sha256(image).hexdigest())

    backup = bytearray()
    for address in range(0, RAM_SIZE, BLOCK):
        backup.extend(read_exact(device, 0xC0, 0x01, 0x200C, address, BLOCK,
                                 f"M1 backup block 0x{address:04x}"))
    if len(backup) != RAM_SIZE:
        raise RuntimeError(f"incomplete M1 backup: expected {RAM_SIZE} bytes, got {len(backup)}")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_bytes(backup)
    log.info("saved volatile 8 KiB M1 RAM backup to %s", backup_path)
    log.info("recovery path: unplug/replug the scanner to restore the ROM USB bootstrap; "
             "the saved RAM image is available for a separate restore operation")

    for address in range(0, transfer_size, BLOCK):
        block = padded[address:address + BLOCK]
        device.ctrl_out(0x40, 0x01, 0x200B, address, block)
        readback = read_exact(device, 0xC0, 0x01, 0x200C, address, BLOCK,
                              f"RAM write readback block 0x{address:04x}")
        if readback != block:
            raise RuntimeError(f"RAM readback mismatch at 0x{address:04x}")

    command = bytearray(BLOCK)
    command[:4] = b"\x69\x01" + struct.pack("<H", transfer_size)
    device.ctrl_out(0x40, 0x01, 0x2010, 0x3F40, bytes(command))
    try:
        response = bytes(device.ctrl_in(0xC0, 0x01, 0x2011, 0x3F00, BLOCK))
        if len(response) == BLOCK:
            log.info("boot response: %s", response.hex(" "))
        else:
            log.warning("boot response was short (%d/%d bytes); continuing to EP1",
                        len(response), BLOCK)
    except Exception as exc:  # The custom image may take over EP0 immediately.
        log.warning("boot response unavailable (%s); continuing to EP1", exc)
    time.sleep(0.05)
    marker = bytes(device.bulk_in(0x81, MARKER_SIZE))
    if len(marker) != MARKER_SIZE:
        raise RuntimeError(f"short EP1 marker read: expected {MARKER_SIZE} bytes, got {len(marker)}")
    if marker == expected_marker():
        log.info("EP1 marker verified")
    else:
        raise RuntimeError(f"EP1 marker mismatch: got {marker[:16].hex(' ')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=pathlib.Path, help="SDCC .hex/.ihx or raw binary")
    parser.add_argument("--vid", type=parse_int, default=0x07B3)
    parser.add_argument("--pid", type=parse_int, default=0x0465)
    parser.add_argument("--backup", type=pathlib.Path, default=ROOT / "captures" / "ram" / "gt6816_m1_backup.bin")
    parser.add_argument("--log", type=pathlib.Path, default=ROOT / "logs" / "gt6816_ram_runner.log")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--execute", action="store_true", help="perform live USB operations")
    args = parser.parse_args(argv)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(args.log), logging.StreamHandler()])
    log = logging.getLogger("gt6816_ram_runner")
    try:
        image = load_image(args.firmware)
        padded, transfer_size = padded_blocks(image)
        log.info("dry-run" if not args.execute else "LIVE EXECUTION")
        log.info("parsed %s: %d bytes, %d transferred", args.firmware, len(image), transfer_size)
        if not args.execute:
            log.info("would back up %d bytes, upload %d bytes, boot with 69 01 %04x, then read EP1",
                     RAM_SIZE, transfer_size, transfer_size)
            return 0
        try:
            import usb.core
        except ImportError as exc:
            raise RuntimeError("PyUSB is required only with --execute") from exc
        device = usb.core.find(idVendor=args.vid, idProduct=args.pid)
        if device is None:
            raise RuntimeError(f"USB device {args.vid:04x}:{args.pid:04x} not found")
        class LiveDevice:
            def ctrl_out(self, *params):
                sent = device.ctrl_transfer(*params, timeout=args.timeout)
                expected = len(params[-1])
                if sent not in (None, expected):
                    raise RuntimeError(f"short control write: expected {expected} bytes, got {sent}")
            def ctrl_in(self, *params):
                return device.ctrl_transfer(*params, timeout=args.timeout)
            def bulk_in(self, endpoint, length):
                return device.read(endpoint, length, timeout=args.timeout)
        run(LiveDevice(), image, args.backup, log, args.timeout)
        return 0
    except (OSError, ValueError, RuntimeError, binascii.Error) as exc:
        log.error("FAILED: %s", exc)
        log.error("Recovery path: unplug/replug the scanner to return to the ROM USB bootstrap; "
                  "restore saved RAM only through a separately verified RAM upload")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
