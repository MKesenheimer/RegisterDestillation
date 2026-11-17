#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# Commands:
# - Read from address with custom vendor command:
#   openocd -f interface/cmsis-dap.cfg -c "adapter serial E66368254F1C3532" -c "transport select swd" -f target/stm32g0x.cfg -c "init" -c "cmsis-dap cmd 0x80 0x00 0x00 0x08 0x00 0x00 0x00" -c "shutdown"
# - Read registers:
#   openocd -f interface/cmsis-dap.cfg -c "adapter serial E66368254F1C3532" -c "transport select swd" -f target/stm32g0x.cfg -c "init" -c "halt" -c "get_reg {r0}" -c "shutdown"
# - Programming the Pico Glitcher with debugprobe firmware:
#   openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter serial E6616407E3879F29" -c "adapter speed 5000" -c "program debugprobe.elf verify exit"
#   openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter serial E6616407E3879F29" -c "adapter speed 5000" -c "init" -c "reset" -c "shutdown"
# - 


import argparse
import logging
import random
import sys
import time
import subprocess
import re

# import custom libraries
from findus import Database
from findus import DebugInterface
from findus import Glitcher

elf_image = "toggle-led-stm32l051.elf"
#elf_image = "toggle-led-stm32g030.elf"

def hex_type(value:str) -> int:
    """
    Converts a hexadecimal string (with or without '0x' prefix) to an integer.
    """
    try:
        return int(value, 16)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid hexadecimal value: {value}")

def generate_register_args(reg_dict:dict[str, str], reg_keys:list[str]) -> list[str]:
    """
    Extract values from a dictionary given by a list of keys.
    """
    args = []
    for key in reg_keys:
        if key in reg_dict:
            args.append(DebugInterface.format_bytes(reg_dict[key]))
        else:
            args.append(DebugInterface.format_bytes('0x00'))
    return args

class Helper(Glitcher):
    pass

class DerivedDebugInterface(DebugInterface):
    def is_thumb16_opcode(self, hw):
        """
        Rough filter for valid Thumb-1 (Cortex-M0+) 16-bit opcodes.
        hw: 16-bit halfword (int)
        """
        # BX / BLX
        if (hw & 0xFF87) == 0x4700:
            print("bx")
            return True
        # POP {..., PC}
        if (hw & 0xFF00) == 0xBD00:
            print("pop")
            return True
        # PUSH
        if (hw & 0xFE00) == 0xB400:
            print("push")
            return True
        # Conditional branch
        if (hw & 0xF000) == 0xD000:
            print("cond branch")
            return True
        # Unconditional branch
        if (hw & 0xF800) == 0xE000:
            print("uncond branch")
            return True
        # LDR literal
        if (hw & 0xF800) == 0x4800:
            print("ldr")
            return True
        
    def contains_interesting_opcode(self, word):
        # debug
        #word = 0x1e034770 # xx BX LR
        #word = 0x1e034770 # SUBS R3 R0 #0 xx
        #word = 0x68013004 # xx ADDS R0
        #word = 0x3010e01d # ADDS R0 xx
        #word = 0x320c0002 # xx MOVS R2 R0
        #word = 0x320c0002 # ADDS R2 #0xC xx
        hw_lo = word & 0xFFFF
        hw_hi = (word >> 16) & 0xFFFF
        for hw in (hw_lo, hw_hi):
            return self.is_thumb16_opcode(hw)

    def overview_characterize(self, response:str, mem:list[str], ram:list[str]) -> list[tuple[bytes, str]]:
        flash_address_found = False
        ram_address_found = False
        interesting_ram_content_found = False

        for m in mem:
            mi = hex_type(m)
            if mi >= 0x08000000 and mi < 0x0c000000:
                flash_address_found = True
            elif mi >= 0x20000000 and mi < 0x20800000:
                ram_address_found = True
        for r in ram:
            ri = hex_type(r)
            if ri != 0xe5e5e5e5:
                interesting_ram_content_found = True
                
        if flash_address_found:
            return [(b'success: Flash memory address found in dump', 'R')]
        elif interesting_ram_content_found:
            return [(b'success: Interesting values in RAM found', 'M')]
        elif ram_address_found:
            return [(b'success: RAM memory address found in dump', 'O')]
        elif len(mem) != 0 and len(ram) != 0:
            return [(b'expected: memory read successful', 'G')]
        # no response
        return [(b'error: no response', 'Y')]

    def detailed_characterize(self, response:str, mem:list[str], ram:list[str]) -> list[tuple[bytes, str]]:
        flash_addresses_found = 0
        ram_addresses_found = 0
        interesting_ram_addresses_found = 0
        potential_opcode_found = 0
        potential_ram_opcode_found = 0

        for m in mem:
            mi = hex_type(m)
            if mi >= 0x08000000 and mi < 0x0c000000:
                flash_addresses_found += 1
            if mi >= 0x20000000 and mi < 0x20800000:
                ram_addresses_found += 1
            if mi != 0xe5e5e5e5 and mi != 0x00 and mi != 0xffffffff and self.contains_interesting_opcode(mi):
                potential_opcode_found += 1
            
        for r in ram:
            ri = hex_type(r)
            if ri != 0xe5e5e5e5:
                interesting_ram_addresses_found += 1
            if ri != 0xe5e5e5e5 and ri != 0x00 and ri != 0xffffffff and self.contains_interesting_opcode(ri):
                potential_ram_opcode_found += 1

        #self.contains_interesting_opcode(0x00)
        #sys.exit(1)

        character = []
        if flash_addresses_found >= 3:
            character.append((b'success: At least three flash addresses found', 'R'))
        if flash_addresses_found >= 2:
            character.append((b'success: At least two flash addresses found', 'M'))
        if flash_addresses_found >= 1:
            character.append((b'success: At least one flash address found', 'O'))
        if ram_addresses_found >= 5:
            character.append((b'success: At least five RAM addresses found', 'B'))
        #if ram_addresses_found >= 2:
        #    character.append((b'success: At least two RAM addresses found', 'C'))
        #if ram_addresses_found >= 1:
        #    character.append((b'success: At least one RAM address found', 'Z'))
        if potential_ram_opcode_found >= 1:
            character.append((b'success: Potential opcode found in RAM', 'C'))
        if potential_opcode_found >= 1:
            character.append((b'success: Potential opcode found', 'G'))

        if (flash_addresses_found == 0 
            and ram_addresses_found == 0 
            and interesting_ram_addresses_found == 0 
            and potential_opcode_found == 0 
            and potential_ram_opcode_found):
            character.append((b'error: no response', 'Y'))
        
        if len(character) == 0:
            character.append((b'error: No fitting characterization found', 'Y'))
        
        return character

    def create_fault(self, trace_delay:int, reg_name_list:list[str], start_address:int, width:int = 32, count:int = 256, verbose:bool = False):
        """
        Attaches to the OpenOCD server.

        Parameters:
            delay: Delay in seconds before checking if OpenOCD is running.
        """
        delay24_31 = (trace_delay & 0xff000000) >> 24
        delay16_23 = (trace_delay & 0x00ff0000) >> 16
        delay08_15 = (trace_delay & 0x0000ff00) >> 8
        delay00_07 = (trace_delay & 0x000000ff) >> 0
        reg_string = ' '.join(reg_name_list)
        # check if there is a dangling process that would interfere with openocd
        self.kill_process(self.gdb_port)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', 'init',
            '-c', f"cmsis-dap cmd 0x80 0x{delay24_31:02x} 0x{delay16_23:02x} 0x{delay08_15:02x} 0x{delay00_07:02x} 0x08 0x00 0x00 0x00",
            '-c', f"halt; get_reg {{{reg_string}}}",
            '-c', f"read_memory 0x{start_address:08x} {width} {count}",
            '-c', 'shutdown'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        response = result.stdout + result.stderr
        if verbose:
            print(response)

        registers = self.telnet_parse_registers(response)
        registers = generate_register_args(registers, reg_name_list)

        memory = re.findall(r'0x[0-9a-fA-F]+', response)
        if len(memory) != count:
            memory += ["0x00"] * (count - len(memory))
        memory = [self.format_bytes(h) for h in memory[-count:]]
        if verbose:
            print(registers)
            print(memory)
        return registers, memory, response

class Main():
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # STLink Debugger
        #self.debugger = DerivedDebugInterface(interface="stlink", target="stm32l0", transport="hla_swd", gdb_exec="gdb-multiarch")
        #self.debugger = DerivedDebugInterface(interface_config="interface/stlink.cfg", target="stm32l0", transport="hla_swd")
        self.debugger = DerivedDebugInterface(interface_config="interface/cmsis-dap.cfg", target="stm32l0", transport="swd")
        #self.debugger = DerivedDebugInterface(interface_config="interface/cmsis-dap.cfg", target="stm32g0x", transport="swd")

        # programming the target
        if args.test and args.program_target is not None:
            print("[+] Programming target.")
            #self.debugger.program_target(elf_image=elf_image, unlock=True, rdp_level=args.program_target, overwrite_target_name="stm32g0x", verbose=True)
            self.debugger.program_target(elf_image=elf_image, unlock=True, rdp_level=args.program_target, verbose=True)

        # set up the database
        column_names = ["delay", "dummy"]
        self.debugger.attach()
        time.sleep(0.1)
        if args.extract_reg_names:
            self.reg_keys = self.debugger.telnet_read_register_names()
            print(f"[+] Extracted column names from target response: {column_names}")
        else:
            self.reg_keys = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12', 'sp', 'lr', 'pc', 'xpsr', 'msp', 'psp', 'primask', 'control', 'dwt_ctrl', 'dwt_cyccnt', 'dwt_0_comp', 'dwt_0_mask', 'dwt_0_function', 'dwt_1_comp', 'dwt_1_mask', 'dwt_1_function']
        self.ram_count = 32
        self.ram_keys = [f"ram{i}" for i in range(0, self.ram_count)]
        column_names += self.reg_keys
        column_names += self.ram_keys
        print(column_names)
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=column_names)
        self.start_time = int(time.time())
        self.debugger.detach()

    def cleanup(self):
        print("[+] Cleaning up.")
        self.debugger.detach()

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))
        experiment_base_id = self.database.get_base_experiments_count()

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        s_dummy = 0
        e_dummy = 100

        experiment_id = 0
        response = ""
        reg = []
        ram = []
        while True:
            print("[+] Starting new attempt.")
            delay = random.randint(s_delay, e_delay)
            dummy = random.randint(s_dummy, e_dummy)
            
            # create hard fault and read registers
            reg, ram, response = self.debugger.create_fault(
                trace_delay=delay,
                reg_name_list=self.reg_keys,
                start_address=0x20000000,
                #start_address=0x20000a70,
                width=32,
                count=32,
                verbose=False)

            # classify state
            #state, color = self.debugger.overview_characterize(response=response, mem=reg, ram=ram)
            character = self.debugger.detailed_characterize(response=response, mem=reg, ram=ram)

            for state, color in character:
                # add to database
                state_str = b"state = " + state
                if b'success' not in state:
                    state_str += b", response = " + response.encode("utf-8")
                self.database.insert(experiment_id, delay, dummy, *reg, *ram, color, state_str)

                # monitor
                speed = Helper.get_speed(self.start_time, experiment_id)
                reg_string = ' '
                columns = 8
                for i in range(0, len(reg)):
                    if i % columns == 0:
                        reg_string += '\n\t' + reg[i]
                    else:
                        reg_string += ' ' + reg[i]
                for i in range(0, len(ram)):
                    if i % columns == 0:
                        reg_string += '\n\t' + ram[i]
                    else:
                        reg_string += ' ' + ram[i]
                print(Helper.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{dummy}\t{color}\t{state}{reg_string}", color))

                # increase experiment id
                experiment_id += 1

                # DEBUG: add only one characterization to the database
                break
            
            # attack finished
            if self.args.number_of_experiments is not None and experiment_base_id + experiment_id + 1 >= self.args.number_of_experiments:
                break
                


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=True, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end in microseconds", type=int)
    parser.add_argument("--address-range", required=False, nargs=2, help="address range to dump in hexadecimal", type=hex_type)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    parser.add_argument("--program-target", required=False, metavar="RDP_LEVEL", type=int, default=None, help="Reprogram the target before glitching and set the RDP level (for research only).")
    parser.add_argument("--test", required=False, action='store_true', help="Collect data on a test device. If this option is not supplied, all functions that could reset the targets flash are deactivated.")
    parser.add_argument("--number-of-experiments", required=False, default=None, help="Carry out only this many glitching attempts, then stop.", type=int)
    parser.add_argument("--extract-reg-names", required=False, action='store_true', help="Whether to extract the register names directly from the target. If not, predefined register names are used.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        main.cleanup()
        sys.exit(1)
