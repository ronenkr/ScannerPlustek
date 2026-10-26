#!/usr/bin/env python3
"""Diagnostic for an external GT6816 SROM reload into M1.

The default mode is offline.  --execute performs only volatile M1 RAM writes,
the documented SROM re-download request, and EP1 reads.  It never writes the
external EEPROM and labels output as an SROM-loaded M1 candidate rather than
an EEPROM dump.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import pathlib
import struct
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK = 64
M1_SIZE = 8192
CAPTURE_OFFSET = 0x1000
CAPTURE_SIZE = 2048
CHUNK = 8
MAX_STAGE_SIZE = 0x1000
PRE_MARKER = bytes((0xC3 + i) & 0xFF for i in range(CHUNK))
POST_MARKER = bytes((0x3C + i) & 0xFF for i in range(CHUNK))
SENTINEL = bytes((0x5A ^ ((i * 3) & 0xFF)) for i in range(CAPTURE_SIZE))


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_hex(path: pathlib.Path) -> bytes:
    records: dict[int, int] = {}
    base = 0
    eof = False
    for line_no, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"{path}:{line_no}: expected Intel HEX record")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: malformed Intel HEX") from exc
        if len(record) < 5 or sum(record) & 0xFF:
            raise ValueError(f"{path}:{line_no}: bad checksum/length")
        count, address, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        payload = record[4:-1]
        if count != len(payload):
            raise ValueError(f"{path}:{line_no}: byte count mismatch")
        if kind == 0:
            for offset, value in enumerate(payload):
                records[base + address + offset] = value
        elif kind == 1:
            eof = True
            break
        elif kind == 2 and len(payload) == 2:
            base = int.from_bytes(payload, "big") << 4
        elif kind == 4 and len(payload) == 2:
            base = int.from_bytes(payload, "big") << 16
        elif kind not in (3, 5):
            raise ValueError(f"{path}:{line_no}: unsupported record type {kind:02x}")
    if not eof or not records:
        raise ValueError(f"{path}: missing EOF or data")
    image = bytearray(max(records) + 1)
    for address, value in records.items():
        image[address] = value
    return bytes(image)


def load_image(path: pathlib.Path) -> bytes:
    image = parse_hex(path) if path.suffix.lower() in (".hex", ".ihx") else path.read_bytes()
    if not image or len(image) > MAX_STAGE_SIZE:
        raise ValueError(f"firmware must contain 1..{MAX_STAGE_SIZE} bytes")
    return image


def padded(image: bytes) -> tuple[bytes, int]:
    size = (len(image) + BLOCK - 1) // BLOCK * BLOCK
    return image.ljust(size, b"\0"), size


def read_exact(device, offset: int, length: int, timeout: int) -> bytes:
    data = bytes(device.ctrl_in(0xC0, 0x01, 0x200C, offset, length, timeout))
    if len(data) != length:
        raise RuntimeError(f"short M1 read at 0x{offset:04x}: {len(data)}/{length}")
    return data


def read_ep1_once(device, length: int, timeout: int, label: str) -> bytes:
    try:
        data = bytes(device.bulk_in(0x81, length, timeout))
    except Exception as exc:
        raise RuntimeError(f"{label} unavailable: {exc}") from exc
    if len(data) != length:
        raise RuntimeError(f"short {label}: {len(data)}/{length}")
    return data


def read_ep1_retry(device, length: int, timeout: int, label: str, log: logging.Logger) -> bytes:
    """Retry transport errors that can follow the controller reset."""
    last = None
    for attempt in range(3):
        try:
            return read_ep1_once(device, length, timeout, label)
        except Exception as exc:
            last = exc
            log.warning("%s attempt %d/3 failed: %s", label, attempt + 1, exc)
            if hasattr(device, "reacquire"):
                try:
                    device.reacquire()
                except Exception as reacquire_exc:
                    last = reacquire_exc
                    log.warning("USB reacquire failed: %s", reacquire_exc)
            time.sleep(0.05)
    raise RuntimeError(f"{label} unavailable after 3 attempts: {last}")


def run_once(device, image: bytes, backup_path: pathlib.Path, output_path: pathlib.Path,
             log: logging.Logger, timeout: int) -> bytes | None:
    image, image_size = padded(image)
    backup = bytearray()
    for offset in range(0, M1_SIZE, BLOCK):
        backup.extend(read_exact(device, offset, BLOCK, timeout))
    if len(backup) != M1_SIZE:
        raise RuntimeError(f"incomplete M1 backup: {len(backup)}/{M1_SIZE}")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_bytes(backup)
    log.info("saved volatile 8 KiB M1 backup to %s", backup_path)

    for offset in range(0, CAPTURE_SIZE, BLOCK):
        address = CAPTURE_OFFSET + offset
        block = SENTINEL[offset:offset + BLOCK]
        sent = device.ctrl_out(0x40, 0x01, 0x200B, address, block, timeout)
        if sent not in (None, BLOCK):
            raise RuntimeError(f"short sentinel write at 0x{address:04x}: {sent}/{BLOCK}")
        if read_exact(device, address, BLOCK, timeout) != block:
            raise RuntimeError(f"sentinel readback mismatch at 0x{address:04x}")

    for offset in range(0, image_size, BLOCK):
        block = image[offset:offset + BLOCK]
        sent = device.ctrl_out(0x40, 0x01, 0x200B, offset, block, timeout)
        if sent not in (None, BLOCK):
            raise RuntimeError(f"short firmware write at 0x{offset:04x}: {sent}/{BLOCK}")
        if read_exact(device, offset, BLOCK, timeout) != block:
            raise RuntimeError(f"firmware readback mismatch at 0x{offset:04x}")

    # Confirm the sentinel region survived the stage upload before requesting
    # the reset-triggering SROM reload.
    for offset in range(0, CAPTURE_SIZE, BLOCK):
        address = CAPTURE_OFFSET + offset
        block = SENTINEL[offset:offset + BLOCK]
        if read_exact(device, address, BLOCK, timeout) != block:
            raise RuntimeError(f"sentinel changed during firmware upload at 0x{address:04x}")

    command = bytearray(BLOCK)
    command[:4] = b"\x69\x01" + struct.pack("<H", image_size)
    device.ctrl_out(0x40, 0x01, 0x2010, 0x3F40, bytes(command), timeout)
    log.info("requested stage boot; FF80.3 will request external SROM reload")
    pre = read_ep1_retry(device, CHUNK, timeout, "PRE marker", log)
    if pre != PRE_MARKER:
        raise RuntimeError(f"PRE marker mismatch: got {pre.hex(' ')}, expected {PRE_MARKER.hex(' ')}")
    log.info("PRE marker verified; stage reached EP1 before SROM reload")

    post = read_ep1_retry(device, CHUNK, timeout, "POST marker", log)
    if post == PRE_MARKER:
        raise RuntimeError("second EP1 marker was PRE; SROM reload did not reach post image")
    if post != POST_MARKER:
        raise RuntimeError(f"POST marker mismatch: got {post.hex(' ')}, expected {POST_MARKER.hex(' ')}")
    log.info("POST marker verified; streaming SROM-loaded M1 candidate")

    capture = bytearray()
    for chunk in range(0, CAPTURE_SIZE, CHUNK):
        # Once POST is verified, retrying could consume a packet then shift
        # the capture if the host reports an error after receiving it.
        capture.extend(read_ep1_once(device, CHUNK, timeout,
                                     f"capture chunk {chunk // CHUNK}"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(capture)
    log.info("saved SROM-loaded M1 candidate to %s (not verified EEPROM)", output_path)
    log.info("candidate SHA-256: %s", hashlib.sha256(capture).hexdigest())
    return bytes(capture)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=pathlib.Path)
    parser.add_argument("--vid", type=parse_int, default=0x07B3)
    parser.add_argument("--pid", type=parse_int, default=0x0465)
    parser.add_argument("--backup", type=pathlib.Path, default=ROOT / "captures" / "ram" / "gt6816_srom_m1_backup.bin")
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "captures" / "ram" / "gt6816_srom_m1_candidate.bin")
    parser.add_argument("--repeat", type=int, default=1, help="complete runs to attempt (default: 1)")
    parser.add_argument("--timeout", type=int, default=3000)
    parser.add_argument("--log", type=pathlib.Path, default=ROOT / "logs" / "gt6816_srom_capture.log")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(args.log), logging.StreamHandler()])
    log = logging.getLogger("gt6816_srom_capture")
    try:
        image = load_image(args.firmware)
        _, image_size = padded(image)
        if args.repeat != 1:
            raise ValueError("--repeat > 1 is unsupported; power-cycle between independent runs")
        if not args.execute:
            log.info("dry-run: image=%d bytes, transfer=%d, backup=%d, sentinel=%d, EP1 capture=%d",
                     len(image), image_size, M1_SIZE, CAPTURE_SIZE, CAPTURE_SIZE)
            log.info("would request FF80.3 only; no EEPROM write is planned")
            return 0
        try:
            import usb.core
        except ImportError as exc:
            raise RuntimeError("PyUSB is required only with --execute") from exc
        device = usb.core.find(idVendor=args.vid, idProduct=args.pid)
        if device is None:
            raise RuntimeError(f"USB device {args.vid:04x}:{args.pid:04x} not found")
        class LiveDevice:
            def __init__(self, current):
                self.device = current
            def reacquire(self):
                current = usb.core.find(idVendor=args.vid, idProduct=args.pid)
                if current is None:
                    raise RuntimeError("USB device disappeared during reset")
                self.device = current
            def ctrl_in(self, typ, req, val, idx, length, timeout):
                return self.device.ctrl_transfer(typ, req, val, idx, length, timeout=timeout)
            def ctrl_out(self, typ, req, val, idx, data, timeout):
                return self.device.ctrl_transfer(typ, req, val, idx, data, timeout=timeout)
            def bulk_in(self, endpoint, length, timeout):
                return self.device.read(endpoint, length, timeout=timeout)
        capture = run_once(LiveDevice(device), image, args.backup, args.output, log, args.timeout)
        if capture is None:
            raise RuntimeError("no SROM-loaded M1 candidate was captured")
        log.info("candidate SHA-256: %s", hashlib.sha256(capture).hexdigest())
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        log.error("FAILED: %s", exc)
        log.error("Recovery: unplug/replug to restore the ROM USB bootstrap; use the saved M1 backup only for a separately verified RAM restore")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
