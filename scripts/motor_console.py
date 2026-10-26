#!/usr/bin/env python3
"""Interactive console for the scanner's stepper motor.

On start it looks for the scanner (07b3:0465), loads our patched scan firmware (volatile code RAM only:
full steps, motor locked after each move) and then asks, in a loop, for

    speed (steps per second), direction (cw / ccw), number of steps, and an optional slow-start ramp,

shows the expected duration and runs the move after you confirm.  Changing the speed reloads the firmware
(about 3 s) because the cruise rate is patched into the uploaded copy.  The motor stays locked (coils energised)
after each move; "r" releases it and leaving the program offers to release it.

Slow-start ramp (for loads that make the motor jerk in place when started fast): if the start speed is lower than
the speed, the first N steps and the last N steps are sent from the PC as single-step moves, host-timed, with
the rate rising linearly from the start speed to the speed (and falling again at the end); the steps in between
run as one continuous move at the full speed.  The firmware's own continuous stepping cannot go below ~61 steps/s,
host-timed steps can.

Run from anywhere:  python3 scripts/motor_console.py [--mustek] [--no-hold]
  --mustek   drive the Mustek ScanExpress A3 USB (055f:0210) instead of the Plustek S400
  --no-hold  let the coils switch off after each move instead of locking the motor
"""

from __future__ import annotations

import contextlib
import io
import sys
import time
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gt6816_ctl as c  # noqa: E402

CW, CCW = 0x14, 0x15          # clockwise = command 14, anticlockwise = command 15 (owner-observed)
MIN_RATE = c.TIMER1_HZ / 0xFFFF   # ~61 steps/s: longest step interval of the 16-bit timer
SOFT_MAX = 500                # stalled at >=1200 half-steps/s (= 600 full steps/s) sustained; warn above this
HARD_MAX = 1500
MAX_STEPS = 65535
HOST_FRACTION = 0.8           # a host-timed single step takes one firmware timer period; stay below this share of it


def quiet(fn, *args, **kwargs):
    """Call a ctl helper while swallowing its progress prints."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def ask(prompt: str, default=None):
    suffix = f" [{default}]" if default is not None else ""
    try:
        text = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        raise SystemExit("\ninput closed")
    return text if text else (str(default) if default is not None else "")


def wait_for_scanner() -> "c.Scanner":
    announced = False
    while True:
        try:
            return c.Scanner()
        except SystemExit:
            if not announced:
                print("Scanner (07b3:0465) not found. Plug in its USB cable... (Ctrl+C to quit)")
                announced = True
            time.sleep(1.0)
        except Exception as exc:  # e.g. permission problems
            raise SystemExit(f"cannot open the scanner: {exc}")


NO_HOLD = False   # set by --no-hold: let the coils switch off after each move (stock behaviour)


def load_firmware(sc: "c.Scanner", rate: float) -> float:
    """Upload our firmware with the given jog rate; returns the exact rate the timer reload gives."""
    counts = int(round(c.TIMER1_HZ / rate))
    fw = c.FW_DEFAULT.read_bytes()
    fw = quiet(c.patch_jog, fw, rate)
    fw = quiet(c.patch_fullstep, fw)
    if not NO_HOLD:
        fw = quiet(c.patch_hold, fw)
    print(f"Loading firmware for {c.TIMER1_HZ / counts:.1f} steps/s ... ", end="", flush=True)
    quiet(c.upload_and_boot, sc, fw, "console", False)
    time.sleep(1.5)
    sc.find(wait=8)
    state = sc.small(b"\x70\x01")
    if len(state) < 3 or state[2] != 0xFF:
        raise SystemExit("firmware did not report as loaded (70 01)")
    print("done.")
    return c.TIMER1_HZ / counts


def ramp_rates(n: int, r0: float, r1: float, cap: float):
    for i in range(n):
        yield min(cap, r0 + (r1 - r0) * (i / max(n - 1, 1)))


def host_steps(sc: "c.Scanner", cmd: int, rates, label: str):
    """Send one single-step move per rate, host-timed (1/rate seconds apart)."""
    packet = bytes((cmd, 1, 1, 0))
    nxt = time.perf_counter()
    total = 0
    for r in rates:
        sc.normal(packet)
        total += 1
        nxt += 1.0 / r
        while time.perf_counter() < nxt:
            pass
    return total


def plan_time(steps: int, rate: float, start: float, ramp: int, cap: float) -> float:
    if start >= rate or ramp <= 0:
        return steps / rate
    ramp = min(ramp, steps // 2)
    up = sum(1.0 / r for r in ramp_rates(ramp, start, rate, cap))
    return 2 * up + (steps - 2 * ramp) / rate


def run_move(sc: "c.Scanner", cmd: int, steps: int, rate: float, start: float, ramp: int):
    cap = HOST_FRACTION * rate
    ramp = min(ramp, steps // 2) if start < rate else 0
    expected = plan_time(steps, rate, start, ramp, cap)
    t0 = time.time()
    try:
        if ramp:
            print(f"  ramp up: {ramp} host-timed steps {start:g} -> {min(rate, cap):g} steps/s")
            host_steps(sc, cmd, ramp_rates(ramp, start, rate, cap), "up")
        cruise = steps - 2 * ramp
        if cruise > 0:
            sc.normal(bytes((cmd, 1, cruise & 0xFF, cruise >> 8)))
            t1 = time.time()
            cruise_expected = cruise / rate
            while True:
                moving = sc.normal(b"\x17\x01")[2]
                elapsed = time.time() - t1
                print(f"\r  cruise {cruise} steps at {rate:.1f}/s: {elapsed:5.1f} s / {cruise_expected:.1f} s", end="", flush=True)
                if not moving and elapsed > 0.05:
                    break
                if elapsed > cruise_expected + 5:
                    print("\n  timeout waiting for the move to finish")
                    break
                time.sleep(0.05)
            print()
        if ramp:
            print(f"  ramp down: {ramp} host-timed steps {min(rate, cap):g} -> {start:g} steps/s")
            host_steps(sc, cmd, ramp_rates(ramp, rate, start, cap), "down")
    except KeyboardInterrupt:
        sc.normal(b"\x83\x01")  # stop; this also releases the coils
        print("\n  interrupted: stop sent (motor released)")
        return
    print(f"  finished in {time.time() - t0:.1f} s (expected {expected:.1f} s); motor locked.")


def main() -> int:
    global NO_HOLD
    args = sys.argv[1:]
    if "--no-hold" in args:
        NO_HOLD = True
    if "--mustek" in args:   # Mustek ScanExpress A3 USB (055f:0210): the S400 firmware also drives its motor (section 37)
        c.VID, c.PIDS = 0x055F, (0x0210,)
    print("GT-6816 scanner motor console  (volatile firmware only; nothing is written to the EEPROM)")
    sc = wait_for_scanner()
    print(f"Scanner found: {sc.ident}")
    first = sc.small(b"\x70\x01")
    print(f"Firmware state before loading: {'loaded' if len(first) > 2 and first[2] == 0xFF else 'not loaded (ROM only)'}")
    rate = 100.0
    loaded_rate = load_firmware(sc, rate)
    print("\nEnter a move. Direction: cw = clockwise, ccw = anticlockwise.   Commands: r = release motor, q = quit")
    print("For a heavy load use a slow start speed (e.g. 10) with a ramp of 30-60 steps.\n")
    direction, steps, start, ramp_len = "cw", 100, None, 30
    while True:
        try:
            text = ask(f"Speed in steps/s ({MIN_RATE:.0f}-{HARD_MAX}), or r / q", f"{rate:g}")
            if text.lower() in ("q", "quit", "exit"):
                break
            if text.lower() in ("r", "release"):
                sc.normal(b"\x12\x01")
                print("  motor released (coils off).")
                continue
            new_rate = float(text)
            if not 61.0 <= new_rate <= HARD_MAX:
                print(f"  speed must be between 61 and {HARD_MAX} steps/s")
                continue
            new_rate = max(new_rate, MIN_RATE + 0.1)   # 61 means the slowest rate the 16-bit timer allows (~61.04)
            new_start = float(ask("Start speed for a slow-start ramp (= speed for no ramp)", f"{start if start else new_rate:g}"))
            if not 0.5 <= new_start <= new_rate:
                print(f"  start speed must be between 0.5 and the speed ({new_rate:g})")
                continue
            new_ramp = ramp_len
            if new_start < new_rate:
                new_ramp = int(ask("Ramp length in steps (up, and again down at the end)", ramp_len))
                if new_ramp < 1:
                    print("  ramp length must be at least 1")
                    continue
            d = ask("Direction (cw / ccw)", direction).lower()
            if d not in ("cw", "ccw", "c", "a"):
                print("  direction must be cw or ccw")
                continue
            d = "cw" if d in ("cw", "c") else "ccw"
            n = int(ask(f"Number of steps (1-{MAX_STEPS})", steps))
            if not 1 <= n <= MAX_STEPS:
                print(f"  steps must be between 1 and {MAX_STEPS}")
                continue
        except ValueError:
            print("  please enter a number")
            continue
        except KeyboardInterrupt:
            print()
            break

        if new_rate > SOFT_MAX:
            print(f"  warning: above ~{SOFT_MAX} steps/s the motor stalled in earlier tests")
        if abs(new_rate - loaded_rate) / loaded_rate > 0.01:
            loaded_rate = load_firmware(sc, new_rate)   # the cruise rate is part of the uploaded firmware
        rate, direction, steps, ramp_len = loaded_rate, d, n, new_ramp
        start = new_start if new_start < loaded_rate else None
        ramp = min(ramp_len, steps // 2) if start else 0
        total = plan_time(steps, loaded_rate, start or loaded_rate, ramp, HOST_FRACTION * loaded_rate)
        print(f"  {steps} steps {'clockwise' if d == 'cw' else 'anticlockwise'} at {loaded_rate:.1f} steps/s"
              + (f", ramp {start:g} -> {loaded_rate:.1f} over {ramp} steps" if start else "") + f" = about {total:.1f} s")
        if ask("  Press Enter to run, or n to cancel", "").lower() in ("n", "no"):
            continue
        try:
            run_move(sc, CW if d == "cw" else CCW, steps, loaded_rate, start or loaded_rate, ramp)
        except Exception as exc:
            print(f"\n  USB error: {exc}\n  The scanner may have been unplugged; reconnecting...")
            sc = wait_for_scanner()
            loaded_rate = load_firmware(sc, rate)

    answer = ask("Release the motor before exiting? (y = release, n = leave locked)", "y").lower()
    if answer not in ("n", "no"):
        try:
            sc.normal(b"\x12\x01")
            print("Motor released.")
        except Exception as exc:
            print(f"(could not release: {exc})")
    else:
        print("Motor left locked (current keeps flowing; release later with: gt6816_ctl.py normal 0x12 0x01 --execute).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nbye")
