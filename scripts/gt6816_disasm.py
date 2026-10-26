#!/usr/bin/env python3
"""Recursive-descent 8051 disassembler for GT-6816 code images.

Reads a raw image (e.g. the 24LC16B dump, which starts with an 8051 vector
table), follows jumps/calls from the reset and interrupt vectors, and writes
a listing with labels, GT-6816 register names (from gt6816_regs.py) and
cross-references.  Bytes not reached by the trace are shown as data.
Indirect jumps (JMP @A+DPTR) and RET-based dispatch are flagged, not followed.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gt6816_regs import REGISTERS  # noqa: E402

VECTORS = (0x00, 0x03, 0x0B, 0x13, 0x1B, 0x23, 0x2B)
SFR_NAMES = {
    0x80: "P0", 0x81: "SP", 0x82: "DPL", 0x83: "DPH", 0x87: "PCON", 0x88: "TCON", 0x89: "TMOD",
    0x8A: "TL0", 0x8B: "TL1", 0x8C: "TH0", 0x8D: "TH1", 0x90: "P1", 0x98: "SCON", 0x99: "SBUF",
    0xA0: "P2", 0xA8: "IE", 0xB0: "P3", 0xB8: "IP", 0xD0: "PSW", 0xE0: "ACC", 0xF0: "B",
}
ILLEGAL = 0xA5


def direct(addr: int) -> str:
    if addr >= 0x80:
        if addr in SFR_NAMES:
            return SFR_NAMES[addr]
        if addr in REGISTERS:
            return REGISTERS[addr][0]
        return f"SFR_{addr:02X}h"
    return f"{addr:02X}h"


def bit(addr: int) -> str:
    if addr < 0x80:
        return f"{0x20 + (addr >> 3):02X}h.{addr & 7}"
    return f"{direct(addr & 0xF8)}.{addr & 7}"


def rel_target(pc: int, length: int, off: int) -> int:
    return (pc + length + (off - 256 if off >= 128 else off)) & 0xFFFF


def decode(code: bytes, pc: int):
    """Return (length, text, kind, target); kind in {seq, jmp, cjmp, call, ret, ijmp, bad}."""
    op = code[pc]
    b = lambda n: code[pc + n] if pc + n < len(code) else 0
    lo, hi = op & 0x0F, op >> 4
    r = lo & 7
    ri = lo & 1
    # ---- fixed single-opcode forms --------------------------------------------------
    if op == 0x00: return 1, "NOP", "seq", None
    if op == ILLEGAL: return 1, "DB 0A5h  ; reserved opcode", "bad", None
    if lo == 1:  # AJMP / ACALL
        target = ((pc + 2) & 0xF800) | ((op >> 5) << 8) | b(1)
        return 2, f"{'ACALL' if hi & 1 else 'AJMP'} {{L:{target:04X}}}", "call" if hi & 1 else "jmp", target
    simple = {
        0x02: (3, "LJMP", "jmp"), 0x12: (3, "LCALL", "call"),
    }
    if op in simple:
        n, mn, kind = simple[op]
        target = (b(1) << 8) | b(2)
        return n, f"{mn} {{L:{target:04X}}}", kind, target
    if op == 0x22: return 1, "RET", "ret", None
    if op == 0x32: return 1, "RETI", "ret", None
    if op == 0x73: return 1, "JMP @A+DPTR", "ijmp", None
    if op == 0x80:
        t = rel_target(pc, 2, b(1)); return 2, f"SJMP {{L:{t:04X}}}", "jmp", t
    rel1 = {0x40: "JC", 0x50: "JNC", 0x60: "JZ", 0x70: "JNZ"}
    if op in rel1:
        t = rel_target(pc, 2, b(1)); return 2, f"{rel1[op]} {{L:{t:04X}}}", "cjmp", t
    bitrel = {0x10: "JBC", 0x20: "JB", 0x30: "JNB"}
    if op in bitrel:
        t = rel_target(pc, 3, b(2)); return 3, f"{bitrel[op]} {bit(b(1))},{{L:{t:04X}}}", "cjmp", t
    if op == 0x90:
        v = (b(1) << 8) | b(2)
        name = REGISTERS.get(v, (None,))[0]
        return 3, f"MOV DPTR,#{v:04X}h" + (f"  ; {name}" if name else ""), "seq", None
    two = {
        0x05: ("INC", None), 0x15: ("DEC", None),
    }
    if op in (0x05, 0x15):
        return 2, f"{'INC' if op == 0x05 else 'DEC'} {direct(b(1))}", "seq", None
    if op == 0x75: return 3, f"MOV {direct(b(1))},#{b(2):02X}h", "seq", None
    if op == 0x85: return 3, f"MOV {direct(b(2))},{direct(b(1))}", "seq", None
    if op == 0xF5: return 2, f"MOV {direct(b(1))},A", "seq", None
    if op == 0xE5: return 2, f"MOV A,{direct(b(1))}", "seq", None
    if op == 0xC0: return 2, f"PUSH {direct(b(1))}", "seq", None
    if op == 0xD0: return 2, f"POP {direct(b(1))}", "seq", None
    if op == 0xE0: return 1, "MOVX A,@DPTR", "seq", None
    if op == 0xF0: return 1, "MOVX @DPTR,A", "seq", None
    if op in (0xE2, 0xE3): return 1, f"MOVX A,@R{op & 1}", "seq", None
    if op in (0xF2, 0xF3): return 1, f"MOVX @R{op & 1},A", "seq", None
    if op == 0x83: return 1, "MOVC A,@A+PC", "seq", None
    if op == 0x93: return 1, "MOVC A,@A+DPTR", "seq", None
    if op == 0xA3: return 1, "INC DPTR", "seq", None
    one = {
        0x03: "RR A", 0x13: "RRC A", 0x23: "RL A", 0x33: "RLC A", 0x04: "INC A", 0x14: "DEC A",
        0x84: "DIV AB", 0xA4: "MUL AB", 0xC4: "SWAP A", 0xD4: "DA A", 0xE4: "CLR A", 0xF4: "CPL A",
        0xB3: "CPL C", 0xC3: "CLR C", 0xD3: "SETB C",
    }
    if op in one: return 1, one[op], "seq", None
    # direct,A / direct,#imm logic forms
    if op in (0x42, 0x52, 0x62):
        return 2, f"{ {0x42:'ORL',0x52:'ANL',0x62:'XRL'}[op] } {direct(b(1))},A", "seq", None
    if op in (0x43, 0x53, 0x63):
        return 3, f"{ {0x43:'ORL',0x53:'ANL',0x63:'XRL'}[op] } {direct(b(1))},#{b(2):02X}h", "seq", None
    # carry/bit ops
    bitops = {0x72: "ORL C,", 0x82: "ANL C,", 0xA0: "ORL C,/", 0xB0: "ANL C,/", 0xA2: "MOV C,",
              0xB2: "CPL ", 0xC2: "CLR ", 0xD2: "SETB "}
    if op in bitops: return 2, f"{bitops[op]}{bit(b(1))}", "seq", None
    if op == 0x92: return 2, f"MOV {bit(b(1))},C", "seq", None
    # CJNE / DJNZ
    if op == 0xB4:
        t = rel_target(pc, 3, b(2)); return 3, f"CJNE A,#{b(1):02X}h,{{L:{t:04X}}}", "cjmp", t
    if op == 0xB5:
        t = rel_target(pc, 3, b(2)); return 3, f"CJNE A,{direct(b(1))},{{L:{t:04X}}}", "cjmp", t
    if op in (0xB6, 0xB7):
        t = rel_target(pc, 3, b(2)); return 3, f"CJNE @R{ri},#{b(1):02X}h,{{L:{t:04X}}}", "cjmp", t
    if 0xB8 <= op <= 0xBF:
        t = rel_target(pc, 3, b(2)); return 3, f"CJNE R{r},#{b(1):02X}h,{{L:{t:04X}}}", "cjmp", t
    if op == 0xD5:
        t = rel_target(pc, 3, b(2)); return 3, f"DJNZ {direct(b(1))},{{L:{t:04X}}}", "cjmp", t
    if 0xD8 <= op <= 0xDF:
        t = rel_target(pc, 2, b(1)); return 2, f"DJNZ R{r},{{L:{t:04X}}}", "cjmp", t
    # ---- regular arithmetic/move columns --------------------------------------------
    names = {0x2: "ADD A,", 0x3: "ADDC A,", 0x4: "ORL A,", 0x5: "ANL A,", 0x6: "XRL A,", 0x9: "SUBB A,"}
    if hi in names and lo >= 4:
        mn = names[hi]
        if lo == 4: return 2, f"{mn}#{b(1):02X}h", "seq", None
        if lo == 5: return 2, f"{mn}{direct(b(1))}", "seq", None
        if lo in (6, 7): return 1, f"{mn}@R{ri}", "seq", None
        return 1, f"{mn}R{r}", "seq", None
    if hi == 0x7 and lo >= 4:
        if lo == 4: return 2, f"MOV A,#{b(1):02X}h", "seq", None
        if lo in (6, 7): return 2, f"MOV @R{ri},#{b(1):02X}h", "seq", None
        if lo >= 8: return 2, f"MOV R{r},#{b(1):02X}h", "seq", None
    if hi == 0x0 and lo >= 6: return 1, f"INC {'@R%d' % ri if lo < 8 else 'R%d' % r}", "seq", None
    if hi == 0x1 and lo >= 6: return 1, f"DEC {'@R%d' % ri if lo < 8 else 'R%d' % r}", "seq", None
    if hi == 0x8 and lo >= 6:
        src = f"@R{ri}" if lo < 8 else f"R{r}"
        return 2, f"MOV {direct(b(1))},{src}", "seq", None
    if hi == 0xA and lo >= 6:
        dst = f"@R{ri}" if lo < 8 else f"R{r}"
        return 2, f"MOV {dst},{direct(b(1))}", "seq", None
    if hi == 0xC and lo >= 5:
        return (2, f"XCH A,{direct(b(1))}", "seq", None) if lo == 5 else (
            1, f"XCH A,{'@R%d' % ri if lo < 8 else 'R%d' % r}", "seq", None)
    if hi == 0xD and lo in (6, 7): return 1, f"XCHD A,@R{ri}", "seq", None
    if hi == 0xE and lo >= 6: return 1, f"MOV A,{'@R%d' % ri if lo < 8 else 'R%d' % r}", "seq", None
    if hi == 0xF and lo >= 6: return 1, f"MOV {'@R%d' % ri if lo < 8 else 'R%d' % r},A", "seq", None
    return 1, f"DB {op:02X}h  ; undecoded", "bad", None


def trace(code: bytes, entries):
    """Return (instructions: {pc: (len, text, kind, target)}, call_targets, jump_targets)."""
    insts, calls, jumps = {}, set(), set()
    work = list(entries)
    seen_entry = set()
    while work:
        pc = work.pop()
        while 0 <= pc < len(code) and pc not in insts:
            n, text, kind, target = decode(code, pc)
            if pc + n > len(code):
                break
            insts[pc] = (n, text, kind, target)
            if kind == "call":
                calls.add(target); work.append(target)
            elif kind in ("jmp", "cjmp"):
                jumps.add(target); work.append(target)
            if kind in ("jmp", "ret", "ijmp", "bad"):
                break
            pc += n
        seen_entry.add(pc)
    return insts, calls, jumps


def render(code: bytes, insts, calls, jumps, entries) -> str:
    labels = {}
    for t in sorted(calls):
        labels[t] = f"sub_{t:04X}"
    for t in sorted(jumps):
        labels.setdefault(t, f"loc_{t:04X}")
    for v in entries:
        labels.setdefault(v, f"vec_{v:04X}")
    xrefs: dict[int, list[int]] = {}
    for pc, (_, _, kind, target) in insts.items():
        if target is not None:
            xrefs.setdefault(target, []).append(pc)

    lines = []
    pc = 0
    while pc < len(code):
        if pc in labels:
            refs = ", ".join(f"{x:04X}" for x in sorted(xrefs.get(pc, []))[:8])
            lines.append(f"\n{labels[pc]}:" + (f"    ; xref {refs}" if refs else ""))
        if pc in insts:
            n, text, kind, target = insts[pc]
            text = text.replace("{L:%04X}" % target, labels.get(target, f"{target:04X}h")) if target is not None else text
            raw = " ".join(f"{code[pc + i]:02X}" for i in range(n))
            note = "   ; indirect jump" if kind == "ijmp" else ""
            lines.append(f"  {pc:04X}  {raw:<9} {text}{note}")
            pc += n
        else:
            end = pc
            while end < len(code) and end not in insts and (end == pc or end not in labels):
                end += 1
            run = code[pc:end]
            tag = "padding FF" if set(run) == {0xFF} else "data/unreached"
            for off in range(0, len(run), 16):
                chunk = run[off:off + 16]
                lines.append(f"  {pc + off:04X}  DB " + ",".join(f"{x:02X}h" for x in chunk) + f"   ; {tag}")
            pc = end
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument("-o", "--output", type=pathlib.Path)
    parser.add_argument("--entry", action="append", type=lambda s: int(s, 0), default=[],
                        help="extra entry point (repeatable)")
    args = parser.parse_args()
    code = args.image.read_bytes()
    entries = list(VECTORS) + args.entry
    insts, calls, jumps = trace(code, entries)
    text = render(code, insts, calls, jumps, entries)
    covered = sum(n for n, *_ in insts.values())
    header = (f"; {args.image.name}  {len(code)} bytes, base 0x0000\n"
              f"; traced {len(insts)} instructions covering {covered} bytes; "
              f"{len(calls)} call targets\n")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(header + text)
        print(f"wrote {args.output}: {header.strip()}")
    else:
        sys.stdout.write(header + text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
