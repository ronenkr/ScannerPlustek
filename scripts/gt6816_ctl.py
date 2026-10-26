#!/usr/bin/env python3
"""Control a GT-6816 Plustek scanner (07b3:0465) over USB: query, load firmware, buttons, motor.

Protocol (SANE gt68xx GT6816 command set, matched by Plustek's Windows scanapi.dll):
  normal command  OUT 0x40/0x01 wValue 0x2010 wIndex 0x3F40, 64 bytes; result IN 0xC0/0x01 0x2011 / 0x3F00
  small command   OUT wValue 0x2012 wIndex 0x3F40, 8-byte command repeated 8x; result IN 0x2013 / 0x3F00
  RAM write/read  wValue 0x200B / 0x200C, wIndex = M1 offset, 64 bytes
  boot            normal command 69 01 <size LE>

Only volatile code RAM and the motor/GPIO pins are ever touched; nothing writes the EEPROM.
Subcommands that act on the device require --execute (otherwise they print what they would send).
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
FW_DEFAULT = ROOT / "vendor/windows_s400/extracted/Data/74RU/cism603.fw"
VID = 0x07B3
PIDS = (0x0465, 0x0412)
BLOCK, M1_SIZE = 64, 8192
MAX_STEPS_DEFAULT = 200


def parse_int(text: str) -> int:
    return int(text, 0)


def hexs(data: bytes, n: int = 16) -> str:
    return data[:n].hex(" ") + (" ..." if len(data) > n else "")


class Scanner:
    def __init__(self, timeout: int = 3000):
        import usb.core
        self.usb = usb.core
        self.timeout = timeout
        self.dev = None
        self.find()

    def find(self, wait: float = 0.0):
        end = time.time() + wait
        while True:
            for pid in PIDS:
                dev = self.usb.find(idVendor=VID, idProduct=pid)
                if dev is not None:
                    self.dev = dev
                    return dev
            if time.time() >= end:
                raise SystemExit("scanner (07b3:0465 / 07b3:0412) not found")
            time.sleep(0.2)

    @property
    def ident(self) -> str:
        return f"{self.dev.idVendor:04x}:{self.dev.idProduct:04x} bus {self.dev.bus} addr {self.dev.address}"

    def out(self, value: int, index: int, data: bytes):
        return self.dev.ctrl_transfer(0x40, 0x01, value, index, data, self.timeout)

    def inn(self, value: int, index: int, length: int) -> bytes:
        return bytes(self.dev.ctrl_transfer(0xC0, 0x01, value, index, length, self.timeout))

    def normal(self, packet: bytes, reply: int = 64) -> bytes:
        assert len(packet) <= 64
        self.out(0x2010, 0x3F40, packet.ljust(64, b"\0"))
        return self.inn(0x2011, 0x3F00, reply)

    def small(self, cmd: bytes) -> bytes:
        cmd8 = cmd.ljust(8, b"\0")
        self.out(0x2012, 0x3F40, cmd8 * 8)
        try:
            return self.inn(0x2013, 0x3F00, 8)
        except self.usb.USBError:
            # without scan firmware the ROM replies with 64 bytes (SANE note)
            return self.inn(0x2013, 0x3F00, 64)

    def recover(self):
        """Custom code can leave the ROM EP0 RAM commands dead; a USB bus reset restores them."""
        try:
            self.inn(0x200C, 0, BLOCK)
            return
        except self.usb.USBError:
            pass
        try:
            self.dev.reset()
        except self.usb.USBError:
            pass
        time.sleep(1.0)
        self.find(wait=8)
        self.inn(0x200C, 0, BLOCK)  # raises if still dead

    def read_m1(self, size: int = M1_SIZE) -> bytes:
        return b"".join(self.inn(0x200C, off, BLOCK) for off in range(0, size, BLOCK))


def need_exec(args, what: str) -> bool:
    if not args.execute:
        print(f"[dry run] would {what}; re-run with --execute")
        return False
    return True


def cmd_info(args):
    sc = Scanner()
    print("device:", sc.ident)
    for name, cmd in (("70 01 firmware-loaded", b"\x70\x01"), ("81 01 device-type", b"\x81\x01"),
                      ("85 01 GPIO5", b"\x85\x01"), ("74 01 button", b"\x74\x01")):
        if args.skip_button and cmd[0] == 0x74:
            continue
        try:
            print(f"small {name}: {hexs(sc.small(cmd), 12)}")
        except Exception as exc:  # keep going; show what answers
            print(f"small {name}: ERROR {exc}")


def upload_and_boot(sc: "Scanner", fw: bytes, label: str, backup: bool = False):
    """Back up M1, write `fw` in verified 64-byte blocks, then send 69 01 00 20 (boot)."""
    if len(fw) > M1_SIZE:
        raise SystemExit("firmware larger than 8 KiB")
    sc.recover()
    image = fw.ljust(-(-len(fw) // BLOCK) * BLOCK, b"\0")
    if backup:
        m1 = sc.read_m1()
        bpath = ROOT / f"captures/ram/gt6816_m1_pre_load_{time.strftime('%H%M%S')}.bin"
        bpath.parent.mkdir(parents=True, exist_ok=True)
        bpath.write_bytes(m1)
        print(f"{label}: M1 backup -> {bpath.relative_to(ROOT)} {hashlib.sha256(m1).hexdigest()[:16]}")
    for off in range(0, len(image), BLOCK):
        blk = image[off:off + BLOCK]
        sc.out(0x200B, off, blk)
        if sc.inn(0x200C, off, BLOCK) != blk:
            raise SystemExit(f"readback mismatch at 0x{off:04x}; NOT booting")
    print(f"{label}: upload of {len(image)} bytes verified")
    started = time.time()
    try:
        sc.out(0x2010, 0x3F40, bytes((0x69, 0x01, 0x00, 0x20)).ljust(64, b"\0"))  # Windows driver always passes 0x2000
    except Exception as exc:
        print("boot command error (may be expected as the CPU restarts):", exc)
    # Like the Windows driver (scanapi.dll 0x10005e70 -> 0x100059e0), also read the command result (wValue 0x2011).
    # The scan firmware handles command 0x69 in two stages; the result stage runs its full hardware init
    # (sub_1470), including DATA_OE on the PD0..PD3 motor lines.  Without this read the motor lines stay disabled.
    for attempt in range(20):
        time.sleep(0.2)
        try:
            res = sc.inn(0x2011, 0x3F00, 64)
            print(f"{label}: boot result stage read after {0.2 * (attempt + 1):.1f}s: {hexs(res, 8)}")
            break
        except Exception as exc:
            last = exc
    else:
        print(f"{label}: boot result read failed ({last}); hardware init may not have run")
    return started


JOG_RELOAD_AT = 0x1F7F  # cism603.fw: MOV TH1,#D3h (operand at 0x1F7F) / MOV TL1,#59h (operand at 0x1F82) -> reload for the factory jog
JOG_STOCK = (0xD3, 0x59)
TIMER1_HZ = 4_000_000  # Timer clock measured with run-motor --calibrate (48 MHz / 12)


def patch_jog(fw: bytes, rate: float) -> bytes:
    """Return a copy of cism603.fw whose counted-move step rate (commands 14/15/82) is `rate` steps/s."""
    if (fw[JOG_RELOAD_AT], fw[JOG_RELOAD_AT + 3]) != JOG_STOCK or len(fw) != M1_SIZE:
        raise SystemExit("--jog-rate only applies to the stock cism603.fw (bytes at 0x1F7F/0x1F82 differ)")
    counts = int(round(TIMER1_HZ / rate))
    if not 1 <= counts <= 0xFFFF:
        raise SystemExit(f"--jog-rate {rate} out of range: {TIMER1_HZ / 0xFFFF:.1f} .. {TIMER1_HZ:.0f} steps/s")
    reload = 0x10000 - counts
    out = bytearray(fw)
    out[JOG_RELOAD_AT], out[JOG_RELOAD_AT + 3] = reload >> 8, reload & 0xFF
    print(f"patched jog reload {JOG_STOCK[0]:02x}..{JOG_STOCK[1]:02x} -> {out[JOG_RELOAD_AT]:02x}..{out[JOG_RELOAD_AT + 3]:02x} "
          f"({counts} counts, ~{TIMER1_HZ / counts:.0f} steps/s; stock is ~350/s)")
    return bytes(out)


LED_FREE_PATCH = ((0x0E99, bytes.fromhex("e0d2e090")), (0x0D3F, bytes.fromhex("e0d2e090")))  # MOVX A,@DPTR; SETB ACC.0; MOV DPTR..


def patch_led_free(fw: bytes) -> bytes:
    """NOP the two `SETB ACC.0` instructions with which the timer interrupt forces GPIO0 (the power LED) high every
    tick when idle, so only the host commands 50/51 change it.  Applies to the stock cism603.fw only."""
    out = bytearray(fw)
    for off, expect in LED_FREE_PATCH:
        if bytes(out[off:off + 4]) != expect:
            raise SystemExit(f"--free-led only applies to the stock cism603.fw (bytes at 0x{off:04X} differ)")
        out[off + 1:off + 3] = b"\x00\x00"
    print("patched: GPIO0 idle forcing removed (NOPs at 0x0E9A and 0x0D40)")
    return bytes(out)


HOLD_SITES = (0x0E79, 0x1D42, 0x1DB6, 0x1EBB, 0x1EE9, 0x1EF4)  # idle ISR; uncounted stops; counted-move end/zero-count/start
ZERO_PPHDR = bytes.fromhex("90ffa27400f0")  # MOV DPTR,#FFA2h ; MOV A,#00h ; MOVX @DPTR,A  (phase lines low = coils off)


def patch_hold(fw: bytes) -> bytes:
    """Make the motor hold its last phase: NOP the `MOVX @DPTR,A` of the autonomous PPHDR=0 writes (idle interrupt,
    end/start of counted moves, uncounted stops).  Explicit release commands (12 01, 83 01, ...) are left intact."""
    out = bytearray(fw)
    for off in HOLD_SITES:
        if bytes(out[off:off + 6]) != ZERO_PPHDR:
            raise SystemExit(f"--hold only applies to the stock cism603.fw (bytes at 0x{off:04X} differ)")
        out[off + 5] = 0x00
    print(f"patched: coils stay energised after moves (NOP at {', '.join(f'0x{o + 5:04X}' for o in HOLD_SITES)}); release with: normal 0x12 0x01")
    return bytes(out)


FULLSTEP_SITES = (0x0EE5, 0x0EF2)  # `SETB 26h.1` (half-step flag) in the handlers of commands 14 and 15


def patch_fullstep(fw: bytes) -> bytes:
    """Make counted moves 14/15 use the 4-entry full-step table (both coils always on, more torque) by NOPing the
    `SETB 26h.1` that selects the half-step table.  One step is then twice as large (twice the shaft speed per step/s)."""
    out = bytearray(fw)
    for off in FULLSTEP_SITES:
        if bytes(out[off:off + 2]) != b"\xd2\x31":
            raise SystemExit(f"--full-step only applies to the stock cism603.fw (bytes at 0x{off:04X} differ)")
        out[off:off + 2] = b"\x00\x00"
    print("patched: commands 14/15 use full steps (NOP at 0x0EE5, 0x0EF2); a step is twice as large as a half-step")
    return bytes(out)


def cmd_load(args):
    fw = pathlib.Path(args.firmware).read_bytes()
    if args.jog_rate:
        fw = patch_jog(fw, args.jog_rate)
    if not args.half_step:  # full steps are the default (owner's request); --half-step restores the stock half-step moves
        try:
            fw = patch_fullstep(fw)
        except SystemExit as exc:
            print(f"note: full-step patch skipped ({exc})")
    if not args.no_hold:  # motor lock after a move is the default (owner's request); --no-hold restores the stock coils-off behaviour
        try:
            fw = patch_hold(fw)
        except SystemExit as exc:
            print(f"note: hold patch skipped ({exc})")
    if args.free_led:
        fw = patch_led_free(fw)
    print(f"firmware {args.firmware}: {len(fw)} bytes, sha256 {hashlib.sha256(fw).hexdigest()}")
    if not need_exec(args, "back up M1, write the image in 64-byte blocks (verified), boot with 69 01 00 20"):
        return
    sc = Scanner()
    print("device:", sc.ident)
    upload_and_boot(sc, fw, "load", backup=args.backup)
    time.sleep(1.5)
    sc.find(wait=8)
    print("device after boot:", sc.ident)


CLOCK_FILE = ROOT / "logs/gt6816_timer_clock.txt"
MOTOR_BIN = ROOT / "firmware/motor_step.bin"
PARAMS_AT = 0x800
LEAD_IN_COUNTS = 0xFFFF


def timer_clock() -> float:
    try:
        return float(CLOCK_FILE.read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return 14.3e6  # rough estimate from the factory firmware's jog rate; calibrate with --calibrate


def cmd_run_motor(args):
    clock = timer_clock()
    if args.calibrate:
        steps, start, run, ramp = 40, 400000, 400000, 0
    else:
        steps = args.steps
        if steps > args.max_steps:
            raise SystemExit(f"{steps} steps exceeds --max-steps {args.max_steps}")
        run = int(round(clock / args.rate))
        start = int(round(clock / args.start_rate)) if args.start_rate else run
        ramp = args.ramp
        if not (1 <= run <= 0x7FFFFFFF and 1 <= start <= 0x7FFFFFFF) or run > start:
            raise SystemExit(f"bad rates: run={run} counts must be 1..2^31 and not larger than start={start} "
                             "(start rate must be <= cruise rate)")
    mode = 1 if args.mode == "half" else 0
    direction = 1 if args.direction == "rev" else 0
    img = bytearray(MOTOR_BIN.read_bytes())
    img[PARAMS_AT:PARAMS_AT + 14] = (bytes((mode, direction, steps & 255, steps >> 8))
                                     + start.to_bytes(4, "little") + run.to_bytes(4, "little")
                                     + ramp.to_bytes(2, "little"))
    est = (LEAD_IN_COUNTS + sum(max(run, start - (start - run) * min(i, steps - 1 - i, ramp) // max(ramp, 1))
                                for i in range(steps))) / clock
    print(f"{args.mode} step, {args.direction}, {steps} steps, run {run} counts (~{clock / run:.0f} steps/s), "
          f"start {start} counts (~{clock / start:.0f}/s), ramp {ramp}; clock {clock / 1e6:.2f} MHz; est {est:.2f}s")
    if not need_exec(args, "upload motor_step and run it"):
        return
    sc = Scanner()
    print("device:", sc.ident)
    started = upload_and_boot(sc, bytes(img), "motor")
    marker = None
    try:
        marker = bytes(sc.dev.read(0x81, 64, int((est + 5) * 1000)))
    except sc.usb.USBError as exc:
        print("no completion marker:", exc)
    elapsed = time.time() - started
    if marker:
        print(f"marker {marker.hex(' ')} after {elapsed:.2f}s (est {est:.2f}s)")
        if args.calibrate and marker[:4] == b"MOTR":
            total = LEAD_IN_COUNTS + steps * run
            measured = total / elapsed
            CLOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            CLOCK_FILE.write_text(f"{measured:.0f} timer counts/s (from {steps} steps x {run} counts in {elapsed:.2f}s)\n")
            print(f"timer clock ~{measured / 1e6:.2f} MHz -> saved {CLOCK_FILE.relative_to(ROOT)}")
    # The idle program leaves the ROM EP0 commands dead; upload_and_boot() -> recover() bus-resets and retries.
    time.sleep(0.3)
    if args.no_restore:
        return
    upload_and_boot(sc, FW_DEFAULT.read_bytes(), "restore")
    time.sleep(1.5)
    sc.find(wait=8)
    print("scan firmware restored:", sc.ident, hexs(sc.small(b"\x70\x01"), 4))


def cmd_small(args):
    if not need_exec(args, f"send small command {args.bytes}"):
        return
    sc = Scanner()
    print(hexs(sc.small(bytes(args.bytes)), 16))


def cmd_normal(args):
    if not need_exec(args, f"send normal command {args.bytes}"):
        return
    sc = Scanner()
    print(hexs(sc.normal(bytes(args.bytes)), 16))


def cmd_status(args):
    sc = Scanner()
    print("device:", sc.ident)
    for name, pkt in (("17 01 motion/sensor", b"\x17\x01"), ("59 01 GPIO5", b"\x59\x01"),
                      ("3F 01 flags", b"\x3f\x01")):
        print(f"normal {name}: {hexs(sc.normal(pkt), 12)}")


BUTTON_NAMES = {0x88: "regular button A (code 0x88)", 0x02: "regular button B (code 0x02)"}


def cmd_buttons(args):
    """Report presses of the two regular buttons (latched codes via small command 74) and the optical button
    (live level of GPIO5: small command 85 byte 2 = 1 while active)."""
    sc = Scanner()
    print(f"watching buttons for {args.seconds}s: regular A=0x88, regular B=0x02 (latched), optical = GPIO5 level")
    end = time.time() + args.seconds
    optical = 0
    while time.time() < end:
        r74 = sc.small(b"\x74\x01")
        code = r74[2] if len(r74) > 2 else 0
        if code:
            print(f"{time.strftime('%H:%M:%S')} {BUTTON_NAMES.get(code, f'unknown code 0x{code:02x}')}")
        r85 = sc.small(b"\x85\x01")
        level = r85[2] if len(r85) > 2 else 0
        if level != optical:
            print(f"{time.strftime('%H:%M:%S')} optical button {'ACTIVE' if level else 'released'}")
            optical = level
        time.sleep(0.03)
    print("done")


LED_CMD = {"r": 0x70, "g": 0x71, "b": 0x72}


def cmd_lamp(args):
    """Light the CIS LED: `10 01` (SHRRR=0x80: parks the SHR pin at a constant level = LED power enable)
    plus `70`/`71`/`72` (LEDCR: red/green/blue channel).  Off: `73 01` then `11 01`."""
    plan = "turn the lamp off (73 01, 11 01)" if args.color == "off" else (
        f"send 10 01 then {LED_CMD[args.color]:02x} 01 ({args.color.upper()}) for {args.seconds}s, then switch off")
    if not need_exec(args, plan):
        return
    sc = Scanner()
    send = lambda *b: sc.normal(bytes(b))
    if args.color == "off":
        send(0x73, 1); send(0x11, 1)
        print("lamp off")
        return
    send(0x10, 1)
    send(LED_CMD[args.color], 1)
    print(f"lamp {args.color.upper()} on for {args.seconds}s")
    try:
        time.sleep(args.seconds)
    finally:
        send(0x73, 1); send(0x11, 1)
        print("lamp off")


def hue_weights(h: float) -> tuple[float, float, float]:
    """Fully saturated HSV colour for hue h in [0,1) as (r, g, b) weights."""
    h6 = (h % 1.0) * 6
    i, f = int(h6), h6 - int(h6)
    return [(1, f, 0), (1 - f, 1, 0), (0, 1, f), (0, 1 - f, 1), (f, 0, 1), (1, 0, 1 - f)][i]


def cmd_rainbow(args):
    """Rainbow show: the firmware can light only one LED channel at a time (70/71/72), so mixed colours
    are made by time-slicing the channels at ~1/period Hz (each switch costs ~0.4 ms)."""
    if not need_exec(args, f"run a rainbow for {args.seconds}s ({args.sweep}s per hue sweep, {1 / args.period:.0f} Hz slicing)"):
        return
    sc = Scanner()
    send = lambda *b: sc.normal(bytes(b))
    min_slot = 0.00045
    word = lambda v: bytes((v & 255, v >> 8))

    def set_window(rise: int, fall: int):
        # command 76: three (rise, fall) LED windows R,G,B as little-endian words at packet bytes 2..13
        pkt = bytearray(64)
        pkt[0], pkt[1] = 0x76, 0x01
        pkt[2:14] = (word(rise) + word(fall)) * 3
        sc.normal(bytes(pkt))

    send(0x10, 1)
    if args.mode == "slice" and args.window:
        set_window(0x0010, args.window)  # line period is 0x157B counts; stock window is 0x0008..0x012C (~5%)
    start = time.perf_counter()
    cycles = 0
    acc = [0.0, 0.0, 0.0]
    next_t = start
    try:
        while True:
            now = time.perf_counter() - start
            if now >= args.seconds:
                break
            w = hue_weights(now / args.sweep)
            total = sum(w)
            if args.mode == "pulse":
                # one colour per LED pulse (one pulse per line period); sigma-delta keeps the long-run mix at the target hue
                for i in range(3):
                    acc[i] += w[i] / total
                k = max(range(3), key=lambda i: acc[i])
                acc[k] -= 1.0
                send((0x70, 0x71, 0x72)[k], 1)
                next_t += args.period
                while time.perf_counter() < next_t:
                    pass
            else:
                slots = [(cmd, wi / total * args.period) for cmd, wi in zip((0x70, 0x71, 0x72), w) if wi / total * args.period >= min_slot]
                for cmd, dur in slots:
                    end = time.perf_counter() + dur
                    send(cmd, 1)
                    while time.perf_counter() < end:
                        pass
            cycles += 1
    finally:
        send(0x73, 1); send(0x11, 1)
        if args.mode == "slice" and args.window:
            set_window(0x0008, 0x012C)  # restore the stock LED window
    print(f"rainbow done: {cycles} slicing cycles in {args.seconds}s; lamp off")


def cmd_blink(args):
    """Blink the power LED (GPIO0) by alternating commands 50 (high) and 51 (low).  Needs `load --free-led`."""
    if not need_exec(args, f"blink GPIO0 at {args.hz} Hz for {args.seconds}s (50/51), ending {args.end}"):
        return
    sc = Scanner()
    half = 0.5 / args.hz
    end = time.perf_counter() + args.seconds
    state = 1
    next_t = time.perf_counter()
    try:
        while time.perf_counter() < end:
            sc.normal(bytes((0x50 if state else 0x51, 1)))
            state ^= 1
            next_t += half
            while time.perf_counter() < next_t:
                pass
    finally:
        sc.normal(bytes((0x50 if args.end == "on" else 0x51, 1)))
    print("blink done")


def cmd_watch(args):
    """Poll every input the firmware exposes and print each change: button latch (74), GPIO5 (85, 59), motion status (17)."""
    sc = Scanner()
    print(f"watching for {args.seconds}s (columns: 74 latched code | 85 GPIO5 | 59 GPIO5 | 17 status b2,b3)")
    end = time.time() + args.seconds
    prev = None
    t0 = time.time()
    while time.time() < end:
        r74 = sc.small(b"\x74\x01")
        r85 = sc.small(b"\x85\x01")
        r59 = sc.normal(b"\x59\x01")
        r17 = sc.normal(b"\x17\x01")
        cur = (r74[2], r85[2], r59[2], r17[2], r17[3])
        if cur != prev:
            print(f"{time.time() - t0:7.2f}s  74={cur[0]:02x}  85={cur[1]:02x}  59={cur[2]:02x}  17={cur[3]:02x},{cur[4]:02x}")
            prev = cur
        time.sleep(args.interval)
    print("done")


def cmd_motor(args):
    steps = args.steps
    if steps > args.max_steps:
        raise SystemExit(f"{steps} steps exceeds --max-steps {args.max_steps}")
    cmd = 0x15 if args.direction == "a" else 0x14
    packet = bytes((cmd, 0x01, steps & 0xFF, (steps >> 8) & 0xFF))
    if not need_exec(args, f"send {packet.hex(' ')} ({steps} steps, direction {args.direction}), then poll 17 01"):
        return
    sc = Scanner()
    print("before:", hexs(sc.normal(b"\x17\x01"), 8))
    print("move reply:", hexs(sc.normal(packet), 8))
    end = time.time() + args.watch
    while time.time() < end:
        st = sc.normal(b"\x17\x01")
        print(f"{time.time() - end + args.watch:5.2f}s status {hexs(st, 6)}")
        time.sleep(0.1)
    if args.stop:
        print("stop (83 01):", hexs(sc.normal(b"\x83\x01"), 8))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="read-only small-command queries (70/81/85/74)")
    p.add_argument("--skip-button", action="store_true", help="do not send 74 (it clears the latched button)")
    p.set_defaults(fn=cmd_info)
    p = sub.add_parser("load", help="load scan firmware into code RAM and boot it (volatile)")
    p.add_argument("--firmware", default=str(FW_DEFAULT))
    p.add_argument("--jog-rate", type=float, default=0.0,
                   help="patch a copy of cism603.fw so counted moves (14/15/82) step at this many steps/s (stock ~350)")
    p.add_argument("--backup", action="store_true",
                   help="first save the current code RAM to captures/ram/gt6816_m1_pre_load_<time>.bin (off by default)")
    p.add_argument("--full-step", action="store_true", help="(default, kept for compatibility) moves 14/15 use full steps")
    p.add_argument("--half-step", action="store_true",
                   help="keep the stock half-step table for moves 14/15 instead of the default full steps")
    p.add_argument("--hold", action="store_true", help="(default, kept for compatibility) coils stay energised after a move")
    p.add_argument("--no-hold", action="store_true",
                   help="do not apply the hold patch: the motor coils switch off after a move, as in the stock firmware")
    p.add_argument("--free-led", action="store_true",
                   help="patch the copy so the idle interrupt no longer forces the power LED (GPIO0) high; then 50/51 control it")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_load)
    p = sub.add_parser("status", help="normal commands 17/59/3F (read-only)")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("buttons", help="poll the button code (small command 74)")
    p.add_argument("--seconds", type=float, default=15)
    p.set_defaults(fn=cmd_buttons)
    p = sub.add_parser("lamp", help="light the CIS LED in one colour (needs the scan firmware loaded)")
    p.add_argument("color", choices=("r", "g", "b", "off"))
    p.add_argument("--seconds", type=float, default=5.0, help="how long to keep it on before switching off (default 5)")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_lamp)
    p = sub.add_parser("rainbow", help="rainbow light show (time-sliced colour mixing)")
    p.add_argument("--seconds", type=float, default=24.0)
    p.add_argument("--sweep", type=float, default=6.0, help="seconds per full hue cycle")
    p.add_argument("--mode", choices=("pulse", "slice"), default="pulse",
                   help="pulse: one colour per LED pulse (one per line period, sigma-delta); slice: time-slice at --period")
    p.add_argument("--period", type=float, default=0.0027495,
                   help="seconds per step: default is the TG line period 0x157B counts / 2 MHz = 2.7495 ms (pulse mode)")
    p.add_argument("--window", type=lambda s: int(s, 0), default=0x1200,
                   help="slice mode only: LED fall time in line-counter counts (0 keeps the stock ~5%% window)")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_rainbow)
    p = sub.add_parser("blink", help="blink the power LED (GPIO0); needs the firmware loaded with --free-led")
    p.add_argument("--hz", type=float, default=2.0)
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--end", choices=("on", "off"), default="on", help="LED state to leave it in")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_blink)
    p = sub.add_parser("watch", help="print every change of the button latch and sensor inputs")
    p.add_argument("--seconds", type=float, default=15)
    p.add_argument("--interval", type=float, default=0.03)
    p.set_defaults(fn=cmd_watch)
    p = sub.add_parser("motor", help="step the motor a limited number of steps")
    p.add_argument("--steps", type=parse_int, default=20)
    p.add_argument("--direction", choices=("a", "b"), default="a", help="a=command 15, b=command 14")
    p.add_argument("--max-steps", type=parse_int, default=MAX_STEPS_DEFAULT)
    p.add_argument("--watch", type=float, default=2.0, help="seconds to poll status afterwards")
    p.add_argument("--stop", action="store_true", help="send stop (83 01) at the end")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_motor)
    p = sub.add_parser("run-motor", help="run the custom stepper program (slow, controlled steps)")
    p.add_argument("--steps", type=parse_int, default=48)
    p.add_argument("--rate", type=float, default=20.0, help="cruise rate in steps/s (default 20)")
    p.add_argument("--start-rate", type=float, default=0.0, help="starting rate in steps/s for the ramp (default = --rate)")
    p.add_argument("--ramp", type=parse_int, default=0, help="steps spent accelerating and decelerating")
    p.add_argument("--mode", choices=("full", "half"), default="full")
    p.add_argument("--direction", choices=("fwd", "rev"), default="fwd")
    p.add_argument("--max-steps", type=parse_int, default=2000)
    p.add_argument("--no-restore", action="store_true", help="skip reloading the scan firmware after the watchdog reset")
    p.add_argument("--calibrate", action="store_true", help="run 40 slow steps at a fixed count and measure the timer clock")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_run_motor)
    p = sub.add_parser("small", help="send a raw small command (hex bytes)")
    p.add_argument("bytes", nargs="+", type=parse_int)
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_small)
    p = sub.add_parser("normal", help="send a raw normal command (hex bytes)")
    p.add_argument("bytes", nargs="+", type=parse_int)
    p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_normal)

    args = ap.parse_args()
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
