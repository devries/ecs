#!/usr/bin/env python
import sys
import time
import threading
import Queue

STDIO_MEM = 24576

def main(argv):
    if len(argv)!=2:
        print "Usage: %s <ROM>"%(argv[0])
        sys.exit(1)

    cpu = HackCpu()

    fin = open(argv[1])
    program = [int(l,2)&0xffff for l in fin]
    cpu.loadRom(program)
    fin.close()
    i = 0

    for pc in cpu:
        sp = cpu.peek(0)
        instruction = cpu.rom[pc]
        i+=1

        #print "{:7d} -> {:5d}: {:016b}, A={:04x}, D={:04x}, SP={:5d}".format(i,pc,instruction,cpu.a,cpu.d,sp)
        #time.sleep(0.01)

class HackCpu(object):
    def __init__(self):
        self.rom = [0]*2**15
        self.ram = [0]*2**15
        self.a = 0
        self.d = 0
        self.pc = 0
        self.input_manager = InputManager()
        self.input_manager.start()

    def loadRom(self,rom_array):
        if(len(rom_array)>2**15):
            raise MemoryError('The ROM is limited to 32K')
        else:
            self.rom[:len(rom_array)] = rom_array

    def __iter__(self):
        return self

    def next(self):
        if self.pc>=2**15-1:
            raise StopIteration
        else:
            oldpc = self.pc
            instruction = self.rom[self.pc]

            if instruction&0x8000==0:
                # A-instruction
                self.a = instruction
                self.pc+=1

            else:
                # C instruction
                a_segment = (instruction&0x1000)>>12
                c_segment = (instruction&0x0fc0)>>6
                d_segment = (instruction&0x0038)>>3
                j_segment = (instruction&0x0007)
                
                if a_segment:
                    a_val = self.peek(self.a)
                else:
                    a_val = self.a

                if c_segment==0b101010:
                    retval = 0
                elif c_segment==0b111111:
                    retval = 1
                elif c_segment==0b111010:
                    retval = -1&0xffff
                elif c_segment==0b001100:
                    retval = self.d
                elif c_segment==0b110000:
                    retval = a_val
                elif c_segment==0b001101:
                    retval = ~self.d&0xffff
                elif c_segment==0b110001:
                    retval = ~a_val&0xffff
                elif c_segment==0b001111:
                    retval = -self.d&0xffff
                elif c_segment==0b110011:
                    retval = -a_val&0xffff
                elif c_segment==0b011111:
                    retval = (self.d+1)&0xffff
                elif c_segment==0b110111:
                    retval = (a_val+1)&0xffff
                elif c_segment==0b001110:
                    retval = (self.d-1)&0xffff
                elif c_segment==0b110010:
                    retval = (a_val-1)&0xffff
                elif c_segment==0b000010:
                    retval = (self.d+a_val)&0xffff
                elif c_segment==0b010011:
                    retval = (self.d-a_val)&0xffff
                elif c_segment==0b000111:
                    retval = (a_val-self.d)&0xffff
                elif c_segment==0b000000:
                    retval = self.d&a_val
                elif c_segment==0b010101:
                    retval = self.d|a_val
                else:
                    print "Invalid command C computation: %s"%(bin(c_segment))
                    sys.exit(1)

                if d_segment&0b001>0:
                    self.poke(self.a, retval)
                if d_segment&0b010>0:
                    self.d=retval
                if d_segment&0b100>0:
                    self.a=retval

                eq,gt,lt = False, False, False
                if retval==0:
                    eq = True
                elif retval>0 and retval<0x8000:
                    gt = True
                else:
                    lt = True

                self.pc+=1
                
                if j_segment&0b001>0:
                    if gt:
                        self.pc = self.a
                if j_segment&0b010>0:
                    if eq:
                        self.pc = self.a
                if j_segment&0b100>0:
                    if lt:
                        self.pc = self.a

        return oldpc

    def peek(self,i):
        if i==STDIO_MEM:
            # read from stdin
            v = self.input_manager.getCharacter()
            return v 
        elif i>=0 and i<2**15:
            return self.ram[i]
        else:
            raise IndexError('RAM addresses are between 0 and 2**15')

    def poke(self,i,val):
        if i==STDIO_MEM:
            # write to stdout
            sys.stdout.write(unichr(val))
        if i>=0 and i<2**15:
            self.ram[i]=val&0xffff
        else:
            raise IndexError('RAM addresses are between 0 and 2**15')

class InputManager(object):
    def __init__(self):
        self.input_queue = Queue.Queue()
        self.keepRunning = True
        self.inputThread = None

    def process_input(self):
        while self.keepRunning:
            inputchar = sys.stdin.read(1)
            if inputchar!='':
                self.input_queue.put(inputchar)

        return

    def getCharacter(self):
        try:
            retval = ord(self.input_queue.get(block=False))&0xffff
        except Queue.Empty:
            retval = 0

        return retval

    def start(self):
        self.keepRunning = True
        self.inputThread = threading.Thread(target=self.process_input)
        self.inputThread.daemon=True
        self.inputThread.start()

    def stop(self):
        self.keepRunning=False
        sys.stdin.close()
        self.inputThread.join()

if __name__ == '__main__':
    main(sys.argv)
