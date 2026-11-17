#!/usr/bin/env python3
"""
Convert a memory dump hex file to binary format.

Input format (capture_*.hex):
  address  value
  Example:     0x08000000  0x20000768

The values are 32-bit little-endian words as written in the hex dump.
"""

import struct
import argparse
from pathlib import Path

def hex_to_binary(hex_file: str, output_file: str) -> None:
    """
    Convert hex dump file to raw binary.

    Each line in the hex file contains a 32-bit value at a given address.
    The output is a binary file with those values written at their addresses.
    """
    hex_path = Path(hex_file)
    output_path = Path(output_file)

    # Dictionary to store address -> value mappings
    memory = {}

    with open(hex_path, 'r') as f:
        for line in f:
            line = line.rstrip('\r\n')  # Handle both Windows and Unix line endings
            if not line:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            try:
                # Format: "line_number address value"
                addr = int(parts[0], 16)
                value = int(parts[1], 16)
                memory[addr] = value
            except ValueError:
                continue

    # Find min and max address
    if not memory:
        print("No valid data found in hex file")
        return

    min_addr = min(memory.keys())
    max_addr = max(memory.keys())

    # Calculate required size and align to 4 bytes
    size = ((max_addr - min_addr + 4) // 4) * 4

    # Create binary output
    with open(output_path, 'wb') as f:
        # Sort addresses and write values
        #for addr in sorted(memory.keys()):
        #    f.write(struct.pack('<I', memory[addr]))
        for a in range(min_addr, max_addr + 4, 4):
            try:
                f.write(struct.pack('<I', memory[a]))
            except:
                f.write(struct.pack('<I', 0xFFFFFFFF))

    print(f"Converted {len(memory)} memory words")
    print(f"Address range: 0x{min_addr:08x} - 0x{max_addr:08x}")
    print(f"Output: {output_path} ({size} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Convert STM32 memory dump hex file to binary")
    parser.add_argument('input', help='Input hex dump file (capture_*.hex)')
    parser.add_argument('-o', '--output', help='Output binary file (default: basename without .hex + .bin)', default=None)
    args = parser.parse_args()

    output = args.output
    if not output:
        base = Path(args.input).stem
        if args.flat:
            output = f"{base}.flat.bin"
        else:
            output = f"{base}.bin"

    hex_to_binary(args.input, output)


if __name__ == '__main__':
    main()
