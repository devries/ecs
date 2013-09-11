#!/usr/bin/env python
import sys
import string

A_COMMAND = 1
C_COMMAND = 2
L_COMMAND = 3

def main(argv):
    if len(argv)!=2:
        print "Usage: %s <program>"%(argv[0])
        sys.exit(1)

    fout_name = argv[1]
    extension = fout_name.rfind('.asm')
    if extension>=0:
        fout_name = fout_name[:extension]

    fout_name = fout_name+'.hack'
    fout = open(fout_name,'w')


    symbol_table = {'SP':0,
            'LCL':1,
            'ARG':2,
            'THIS':3,
            'THAT':4,
            'SCREEN':16384,
            'KBD':24576,
            # I added the following symbols for special areas
            'STDIO':24576,
            }
    for i in range(16):
        symbol_table['R%d'%i]=i

    # Pass 1
    psr = Parser(argv[1])
    rom = 0

    while psr.hasMoreCommands():
        psr.advance()
        if psr.commandType()==L_COMMAND:
            symbol_table[psr.symbol()]=rom
        else:
            rom = rom+1

    psr = Parser(argv[1])
    cdr = Code()
    ram = 16

    while psr.hasMoreCommands():
        psr.advance()
        if psr.commandType()==A_COMMAND:
            symbol = psr.symbol()
            if symbol[0] in string.digits:
                # It's a number
                fout.write('0%s\n'%symbol)
            else:
                # It's a symbol
                if symbol_table.has_key(symbol):
                    fout.write('0%s\n'%integerToBinary(symbol_table[symbol]))
                else:
                    symbol_table[symbol]=ram
                    fout.write('0%s\n'%integerToBinary(ram))
                    ram+=1
        elif psr.commandType()==C_COMMAND:
            fout.write('111%s%s%s\n'%(cdr.comp(psr.comp()),cdr.dest(psr.dest()),cdr.jump(psr.jump())))

    fout.close()

class Parser(object):
    def __init__(self,fname):
        self.fstream = open(fname,'r')
        self.getNextCommand()

    def getNextCommand(self):
        next_line = self.fstream.readline()
        if next_line == '':
            self.next_command = ''
            self.fstream.close()
        else:
            self.next_command = self.reduceToCommand(next_line)
            if self.next_command == '':
                self.getNextCommand()

    def reduceToCommand(self,line):
        retval = line
        commentstart = retval.find('//')
        if commentstart>=0:
            retval = line[:commentstart]

        for c in string.whitespace:
            retval = retval.replace(c,'')

        return retval

    def hasMoreCommands(self):
        retval = True
        if self.next_command == '':
            retval = False

        return retval

    def advance(self):
        # Parse stuff right here
        if self.next_command.startswith('@'):
            self.command_type = A_COMMAND
            argument = self.next_command[1:]
            if argument[0] in string.digits:
                self.command_symbol = integerToBinary(int(argument))
            else:
                self.command_symbol = argument
        elif self.next_command.startswith('('):
            self.command_type = L_COMMAND
            endbrace = self.next_command.find(')')
            self.command_symbol = self.next_command[1:endbrace]
        else:
            self.command_type = C_COMMAND
            equal_position = self.next_command.find('=')
            semicolon_position = self.next_command.find(';')
            if equal_position>=0:
                self.command_dest = self.next_command[0:equal_position]
            else:
                self.command_dest = 'null'
            
            if semicolon_position>=0:
                self.command_comp = self.next_command[equal_position+1:semicolon_position]
                self.command_jump = self.next_command[semicolon_position+1:]
            else:
                self.command_comp = self.next_command[equal_position+1:]
                self.command_jump = 'null'

        self.getNextCommand()

    def commandType(self):
        return self.command_type
        
    def symbol(self):
        return self.command_symbol

    def dest(self):
        return self.command_dest

    def comp(self):
        return self.command_comp

    def jump(self):
        return self.command_jump

class Code(object):
    def __init__(self):
        self.dest_table = {'null':'000',
                'M':'001',
                'D':'010',
                'MD':'011',
                'A':'100',
                'AM':'101',
                'AD':'110',
                'AMD':'111'}
        self.jump_table = {'null':'000',
                'JGT':'001',
                'JEQ':'010',
                'JGE':'011',
                'JLT':'100',
                'JNE':'101',
                'JLE':'110',
                'JMP':'111'}
        self.comp_table = {'0':'0101010',
                '1':'0111111',
                '-1':'0111010',
                'D':'0001100',
                'A':'0110000',
                'M':'1110000',
                '!D':'0001101',
                '!A':'0110001',
                '!M':'1110001',
                '-D':'0001111',
                '-A':'0110011',
                '-M':'1110011',
                'D+1':'0011111',
                'A+1':'0110111',
                'M+1':'1110111',
                'D-1':'0001110',
                'A-1':'0110010',
                'M-1':'1110010',
                'D+A':'0000010',
                'D+M':'1000010',
                'D-A':'0010011',
                'D-M':'1010011',
                'A-D':'0000111',
                'M-D':'1000111',
                'D&A':'0000000',
                'D&M':'1000000',
                'D|A':'0010101',
                'D|M':'1010101'}

    def dest(self,mnemonic):
        retval = self.dest_table[mnemonic]
        return retval

    def comp(self,mnemonic):
        retval = self.comp_table[mnemonic]
        return retval

    def jump(self,mnemonic):
        retval = self.jump_table[mnemonic]
        return retval

# Note: I didn't end up using this
class SymbolTable(object):
    def __init__(self):
        self.table = {'SP':0,
                'LCL':1,
                'ARG':2,
                'THIS':3,
                'THAT':4,
                'SCREEN':16384,
                'KBD':24576}
        for i in range(16):
            self.table['R%d'%i]=i

    def addEntry(self,symbol,value):
        self.table[symbol]=value

    def contains(self,symbol):
        return self.table.has_key(symbol)

    def getAddress(self,symbol):
        return self.table[symbol]


def integerToBinary(val):
    if val>(2**15-1):
        raise OverflowError('Value is greater than 15 bits.')
    accum = ''
    radix = 2**14
    while radix>=1:
        if val>=radix:
            accum = accum+'1'
            val = val-radix
        else:
            accum = accum+'0'

        radix = radix/2

    return accum

if __name__ == '__main__':
    main(sys.argv)
