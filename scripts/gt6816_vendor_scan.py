#!/usr/bin/env python3
"""Read-only scan of GT6816 EP0 vendor IN requests.

Every probe is a device-to-host control transfer (bmRequestType 0xC0), so no
payload is ever sent to the device.  Phases:

  1. bRequest 0x00..0xFF with wValue=0, wIndex=0
  2. for bRequest in --requests: wValue = <high><low> for low 0x00..0xFF
     (default high byte 0x20, matching the known SANE wValue values) for
     each wIndex in --indexes

After any failure other than a plain STALL the tool re-reads M1 offset 0 (the
known-good request) to confirm the device still answers, and attempts a USB
reset before stopping if it does not.  M1 is captured before and after.  The
default mode is an offline dry run; --execute opens the device.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK = 64
M1_SIZE = 8192
IN_VENDOR_DEVICE = 0xC0
KNOWN = {
    (0x01, 0x200C): "M1 read (SANE memory_read)",
    (0x01, 0x2011): "normal result (SANE recv_res)",
    (0x01, 0x2013): "small result (SANE recv_small_res)",
}


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_list(text: str) -> list[int]:
    return [parse_int(item) for item in text.split(",") if item]


def read_m1(dev, timeout: int) -> bytes:
    out = bytearray()
    for off in range(0, M1_SIZE, BLOCK):
        out += bytes(dev.ctrl_transfer(IN_VENDOR_DEVICE, 0x01, 0x200C, off, BLOCK, timeout))
    return bytes(out)


def alive(dev, timeout: int) -> bool:
    try:
        return len(dev.ctrl_transfer(IN_VENDOR_DEVICE, 0x01, 0x200C, 0, BLOCK, timeout)) == BLOCK
    except Exception:
        return False


def probe(dev, usb, request: int, value: int, index: int, timeout: int) -> dict:
    row = {"request": request, "value": value, "index": index}
    try:
        data = bytes(dev.ctrl_transfer(IN_VENDOR_DEVICE, request, value, index, BLOCK, timeout))
        row.update(status="data", length=len(data), data=data.hex())
    except usb.core.USBTimeoutError:
        row.update(status="timeout")
    except usb.core.USBError as exc:
        # errno 32 = EPIPE: the device STALLed an unsupported request.
        row.update(status="stall" if exc.errno == 32 else "error", detail=str(exc))
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vid", type=parse_int, default=0x07B3)
    parser.add_argument("--pid", type=parse_int, default=0x0465)
    parser.add_argument("--requests", type=parse_list, default=[0x01, 0x04],
                        help="bRequest values for the wValue sweep (default: 0x01,0x04)")
    parser.add_argument("--value-high", type=parse_int, default=0x20,
                        help="high byte of wValue for the sweep (default: 0x20)")
    parser.add_argument("--indexes", type=parse_list, default=[0x0000, 0x3F00],
                        help="wIndex values for the wValue sweep (default: 0x0000,0x3F00)")
    parser.add_argument("--skip-phase1", action="store_true")
    parser.add_argument("--timeout", type=int, default=500)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "logs" / "gt6816_vendor_scan.json")
    parser.add_argument("--m1-before", type=pathlib.Path, default=ROOT / "captures" / "ram" / "gt6816_m1_pre_vendor_scan.bin")
    parser.add_argument("--m1-after", type=pathlib.Path, default=ROOT / "captures" / "ram" / "gt6816_m1_post_vendor_scan.bin")
    parser.add_argument("--execute", action="store_true", help="perform live USB IN transfers")
    args = parser.parse_args()

    plan = [] if args.skip_phase1 else [(r, 0, 0) for r in range(256)]
    for request in args.requests:
        for index in args.indexes:
            plan += [(request, (args.value_high << 8) | low, index) for low in range(256)]
    print(f"{len(plan)} IN-only probes planned (bmRequestType 0xC0, wLength {BLOCK})")
    if not args.execute:
        print("Dry run: no device opened.  Re-run with --execute.")
        return 0

    import usb.core

    dev = usb.core.find(idVendor=args.vid, idProduct=args.pid)
    if dev is None:
        raise SystemExit("device not found")
    if not alive(dev, 3000):
        raise SystemExit("baseline M1 read failed; refusing to scan")
    before = read_m1(dev, 3000)
    for target in (args.m1_before, args.m1_after, args.out):
        target.parent.mkdir(parents=True, exist_ok=True)
    args.m1_before.write_bytes(before)
    print("M1 before:", hashlib.sha256(before).hexdigest())

    results, stopped = [], None
    started = time.time()
    for request, value, index in plan:
        row = probe(dev, usb, request, value, index, args.timeout)
        label = KNOWN.get((request, value))
        if label:
            row["known"] = label
        results.append(row)
        if row["status"] == "data":
            print(f"DATA  req=0x{request:02x} value=0x{value:04x} index=0x{index:04x} "
                  f"len={row['length']} {row['data'][:48]}")
        if row["status"] in ("timeout", "error") and not alive(dev, 3000):
            try:
                dev.reset()
            except usb.core.USBError:
                pass
            time.sleep(1.0)
            if not alive(dev, 3000):
                stopped = row
                print("device stopped answering after", row)
                break
            row["recovered_by_reset"] = True

    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("data", "stall", "timeout", "error")}
    print("summary:", summary, f"in {time.time() - started:.1f}s")

    if stopped is None:
        after = read_m1(dev, 3000)
        args.m1_after.write_bytes(after)
        print("M1 after: ", hashlib.sha256(after).hexdigest(),
              "(unchanged)" if after == before else "(CHANGED)")
    args.out.write_text(json.dumps({"summary": summary, "stopped_at": stopped, "results": results}, indent=1))
    print("wrote", args.out)
    return 0 if stopped is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
