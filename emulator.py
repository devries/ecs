#!/usr/bin/env python
import sys

def main(argv):
    if len(argv)!=2:
        print "Usage: %s <ROM>"%(argv[0])
        sys.exit(1)

    cpu = HackCpu()

    fin = open(argv[1])
    program = [int(l,2)&0xffff for l in fin]
    cpu.loadRom(program)
    fin.close()

    for pc in cpu:
        sp = cpu.peek(0)
        instruction = cpu.rom[pc]

        print "%d: %s, A=%s, D=%s, SP=%d"%(pc,bin(instruction),int(cpu.a),int(cpu.d),sp)

class HackCpu(object):
    def __init__(self):
        self.rom = [0]*2**15
        self.ram = [0]*2**15
        self.a = 0
        self.d = 0
        self.pc = 0

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
                    a_val = self.ram[self.a]
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
                    self.ram[self.a]=retval
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
        if i>=0 and i<2**15:
            return self.ram[i]
        else:
            raise IndexError('RAM addresses are between 0 and 2**15')

    def poke(self,i,val):
        if i>=0 and i<2**15:
            self.ram[i]=val&0xffff
        else:
            raise IndexError('RAM addresses are between 0 and 2**15')

if __name__ == '__main__':
    main(sys.argv)
