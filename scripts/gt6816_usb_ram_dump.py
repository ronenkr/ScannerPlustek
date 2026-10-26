#!/usr/bin/env python3
"""Read GT-6816 program RAM using the SANE Mustek-GT6816 vendor command.

This is NOT a direct EEPROM read. The copied bytes may (or may not) represent
code loaded from an external EEPROM at boot. Reads only; does not write memory.
"""
import argparse
import hashlib
import pathlib
import sys

import usb.core


ROOT = pathlib.Path(__file__).resolve().parent.parent


def hex_id(text):
    return int(text.removeprefix('0x'), 16)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('vid', type=hex_id, help='USB vendor ID, hex (e.g. 055f)')
    p.add_argument('pid', type=hex_id, help='USB product ID, hex (e.g. 021b)')
    p.add_argument('--size', type=int, choices=[2048, 8192], default=2048,
                   help='Bytes to read from program RAM (default: 2048)')
    p.add_argument('--output', default=str(ROOT / 'captures' / 'ram' / 'gt6816_ram.bin'))
    args = p.parse_args()

    dev = usb.core.find(idVendor=args.vid, idProduct=args.pid)
    if dev is None:
        sys.exit(f'USB device {args.vid:04x}:{args.pid:04x} not found')

    print(f'Reading {args.size} bytes of GT-6816 program RAM (read only)')
    contents = bytearray()
    for address in range(0, args.size, 64):
        try:
            block = dev.ctrl_transfer(0xC0, 0x01, 0x200C, address, 64,
                                      timeout=3000)
        except usb.core.USBError as exc:
            sys.exit(f'USB read failed at 0x{address:04X}: {exc}\n'
                     'The board may use a different command set, or its firmware '
                     'may not support this request.')
        if len(block) != 64:
            sys.exit(f'Short read at 0x{address:04X}: {len(block)} bytes')
        contents.extend(block)
    pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'wb') as out:
        out.write(contents)
    print(f'Saved {len(contents)} bytes to {args.output}')
    print('SHA-256:', hashlib.sha256(contents).hexdigest())
    print('First 64 bytes:', contents[:64].hex(' '))
    print('NOTE: This is RAM, not a verified 24LC16B EEPROM dump.')


if __name__ == '__main__':
    main()
