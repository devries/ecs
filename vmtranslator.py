#!/usr/bin/env python
import sys
import string
import os
import glob
C_ARITHMETIC = 1
C_PUSH = 2
C_POP = 3
C_LABEL = 4
C_GOTO = 5
C_IF = 6
C_FUNCTION = 7
C_RETURN = 8
C_CALL = 9

arithmetic_commands = ['add','sub','neg','eq','gt','lt','and','or','not']
segments = ['argument','local','static','constant','this','that','pointer','temp']

stack_start = 256
heap_start = 2048
temp_start = 5
pointer_start = 3

def main(argv):
    if len(argv)!=2:
        print "Usage: %s <program|directory>"%(argv[0])
        sys.exit(1)

    files = []
    if os.path.isdir(argv[1]):
        files.extend(glob.glob('%s/*.vm'%argv[1]))
        sysinit=True
    else:
        files.append(argv[1])
        sysinit=False

    fout_name = argv[1]
    extension = fout_name.rfind('.vm')
    if extension>=0:
        fout_name = fout_name[:extension]

    fout_name = fout_name+'.asm'

    cdwr = CodeWriter(fout_name)

    cdwr.writeInit(sysinit)
    for fin_name in files:
        cdwr.setFileName(fin_name)
        psr = Parser(fin_name)
        while psr.hasMoreCommands():
            psr.advance()
            if psr.commandType()==C_ARITHMETIC:
                cdwr.writeArithmetic(psr.arg1())
            elif psr.commandType()==C_PUSH or psr.commandType()==C_POP:
                cdwr.writePushPop(psr.commandType(),psr.arg1(),int(psr.arg2()))
            elif psr.commandType()==C_LABEL:
                cdwr.writeLabel(psr.arg1())
            elif psr.commandType()==C_GOTO:
                cdwr.writeGoto(psr.arg1())
            elif psr.commandType()==C_IF:
                cdwr.writeIf(psr.arg1())
            elif psr.commandType()==C_FUNCTION:
                cdwr.writeFunction(psr.arg1(),int(psr.arg2()))
            elif psr.commandType()==C_CALL:
                cdwr.writeCall(psr.arg1(),int(psr.arg2()))
            elif psr.commandType()==C_RETURN:
                cdwr.writeReturn()
            else:
                raise Exception('Unrecognized command')

    cdwr.close()

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

        retval = retval.strip()
        return retval

    def hasMoreCommands(self):
        retval = True
        if self.next_command == '':
            retval = False

        return retval

    def advance(self):
        # Parse stuff right here
        components = self.next_command.split()
        command = components[0]
        if command == "push":
            self.command_type = C_PUSH
            self.command_arg1 = components[1]
            self.command_arg2 = components[2]
        elif command == 'pop':
            self.command_type = C_POP
            self.command_arg1 = components[1]
            self.command_arg2 = components[2]
        elif command in arithmetic_commands:
            self.command_type = C_ARITHMETIC
            self.command_arg1 = command
        elif command == 'label':
            self.command_type = C_LABEL
            self.command_arg1 = components[1]
        elif command == 'goto':
            self.command_type = C_GOTO
            self.command_arg1 = components[1]
        elif command == 'if-goto':
            self.command_type = C_IF
            self.command_arg1 = components[1]
        elif command == 'call':
            self.command_type = C_CALL
            self.command_arg1 = components[1]
            self.command_arg2 = components[2]
        elif command == 'function':
            self.command_type = C_FUNCTION
            self.command_arg1 = components[1]
            self.command_arg2 = components[2]
        elif command == 'return':
            self.command_type = C_RETURN
        else:
            raise NotImplementedError("Command %s Not implemented"%command)
        self.getNextCommand()

    def commandType(self):
        return self.command_type
        
    def arg1(self):
        return self.command_arg1

    def arg2(self):
        return self.command_arg2

class CodeWriter(object):
    def __init__(self,outputfilename):
        self.fout = open(outputfilename,'w')
        self.heap = heap_start
        self.eqcount = 0
        self.gtcount = 0
        self.ltcount = 0
        self.current_function = 'VMROOT'
        self.return_address_count = 0

    def writeInit(self,sysinit=False):
        # initialize the stack pointer
        self.writecommand('@%d'%stack_start)
        self.writecommand('D=A')
        self.writecommand('@SP')
        self.writecommand('M=D')

        # Call Sys.init function
        if sysinit:
            self.writeCall('Sys.init',0)
            #self.writecommand('@Sys.init')
            #self.writecommand('0;JMP')

    def setFileName(self,filename):
        extension = filename.rfind('.vm')
        lastslash = filename.rfind('/')

        if extension>=0:
            self.current_fileroot = filename[:extension]
        else:
            self.current_fileroot = filename

        if lastslash>=0:
            self.current_fileroot = self.current_fileroot[lastslash+1:]
            
        self.current_filename = filename

    def writeArithmetic(self,command):
        if command == 'add':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('M=D+M')
        elif command == 'sub':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('M=M-D')
        elif command == 'neg':
            self.writecommand('@SP')
            self.writecommand('A=M-1')
            self.writecommand('M=-M')
        elif command == 'eq':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('D=M-D')
            self.writecommand('M=0') # 0 is false
            self.writecommand('@END_EQ%d'%self.eqcount)
            self.writecommand('D;JNE')
            self.writecommand('@SP')
            self.writecommand('A=M-1')
            self.writecommand('M=-1') # -1 is true
            self.writecommand('(END_EQ%d)'%self.eqcount)
            self.eqcount+=1
        elif command == 'gt':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('D=M-D')
            self.writecommand('M=0') # 0 is false
            self.writecommand('@END_GT%d'%self.gtcount)
            self.writecommand('D;JLE')
            self.writecommand('@SP')
            self.writecommand('A=M-1')
            self.writecommand('M=-1') # -1 is true
            self.writecommand('(END_GT%d)'%self.gtcount)
            self.gtcount+=1
        elif command == 'lt':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('D=M-D')
            self.writecommand('M=0') # 0 is false
            self.writecommand('@END_LT%d'%self.ltcount)
            self.writecommand('D;JGE')
            self.writecommand('@SP')
            self.writecommand('A=M-1')
            self.writecommand('M=-1') # -1 is true
            self.writecommand('(END_LT%d)'%self.ltcount)
            self.ltcount+=1
        elif command == 'and':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('M=D&M')
        elif command == 'or':
            self.writecommand('@SP')
            self.writecommand('AM=M-1')
            self.writecommand('D=M')
            self.writecommand('A=A-1')
            self.writecommand('M=D|M')
        elif command=='not':
            self.writecommand('@SP')
            self.writecommand('A=M-1')
            self.writecommand('M=!M')
        else:
            raise Exception("Unrecognized arithmatic command: %s"%command)

    def writePushPop(self,command,segment,index):
        if segment=='constant':
            self.writecommand('@%d'%index)
            self.writecommand('D=A')
        elif segment=='local':
            self.writecommand('@LCL')
            self.writecommand('D=M')
            self.writecommand('@%d'%index)
            self.writecommand('A=D+A')
        elif segment=='argument':
            self.writecommand('@ARG')
            self.writecommand('D=M')
            self.writecommand('@%d'%index)
            self.writecommand('A=D+A')
        elif segment=='this':
            self.writecommand('@THIS')
            self.writecommand('D=M')
            self.writecommand('@%d'%index)
            self.writecommand('A=D+A')
        elif segment=='that':
            self.writecommand('@THAT')
            self.writecommand('D=M')
            self.writecommand('@%d'%index)
            self.writecommand('A=D+A')
        elif segment=='temp':
            rampos = temp_start+index
            self.writecommand('@%d'%rampos)
        elif segment=='pointer':
            rampos = pointer_start+index
            self.writecommand('@%d'%rampos)
        elif segment=='static':
            self.writecommand('@%s.%d'%(self.current_fileroot,index))
        else:
            raise NotImplementedError("Segment %s is not implemented"%segment)

        if command==C_PUSH:
            if segment!='constant':
                self.writecommand('D=M')
            self.push_d_to_stack()
        else: # pop
            if segment=='constant':
                raise Exception("Unable to pop to constant segment.")
            self.pop_from_stack_to_m()

    def writeLabel(self,label):
        self.writecommand('(%s$%s)'%(self.current_function,label))

    def writeGoto(self,label):
        self.writecommand('@%s$%s'%(self.current_function,label))
        self.writecommand('0;JMP')

    def writeIf(self,label):
        self.writecommand('@SP')
        self.writecommand('AM=M-1')
        self.writecommand('D=M')
        self.writecommand('@%s$%s'%(self.current_function,label))
        self.writecommand('D;JNE')

    def writeFunction(self,function_label,local_variables):
        self.writecommand('(%s)'%function_label)
        self.current_function = function_label
        for i in range(local_variables):
            self.writePushPop(C_PUSH,'constant',0)

    def writeCall(self,function_label,nargs):
        # Push return address on stack
        self.writecommand('@RETURN%d'%self.return_address_count)
        self.writecommand('D=A')
        self.push_d_to_stack()
        
        # Push local of calling function to stack
        self.writecommand('@LCL')
        self.writecommand('D=M')
        self.push_d_to_stack()

        # Push ARG of the calling function to stack
        self.writecommand('@ARG')
        self.writecommand('D=M')
        self.push_d_to_stack()

        # Push THIS of the calling function to stack
        self.writecommand('@THIS')
        self.writecommand('D=M')
        self.push_d_to_stack()

        # Push THAT of the calling function to stack
        self.writecommand('@THAT')
        self.writecommand('D=M')
        self.push_d_to_stack()

        # Reposition ARG to SP-nargs-5
        self.writecommand('@%d'%(nargs+5))
        self.writecommand('D=A')
        self.writecommand('@SP')
        self.writecommand('D=M-D')
        self.writecommand('@ARG')
        self.writecommand('M=D')

        # Reposition LCL to SP
        self.writecommand('@SP')
        self.writecommand('D=M')
        self.writecommand('@LCL')
        self.writecommand('M=D')

        # Goto the return fumction
        self.writecommand('@%s'%(function_label))
        self.writecommand('0;JMP')

        # Write return label
        self.writecommand('(RETURN%d)'%(self.return_address_count))

        # Increment return address counter
        self.return_address_count+=1

    def writeReturn(self):
        # Create temporary frame variable = LCL (frame is R13)
        self.writecommand('@LCL')
        self.writecommand('D=M')
        self.writecommand('@R13')
        self.writecommand('M=D')

        # Create temporary RET variable = *(FRAME-5) (RET is R14)
        self.writecommand('@5')
        self.writecommand('D=A')
        self.writecommand('@R13')
        self.writecommand('A=M-D')
        self.writecommand('D=M')
        self.writecommand('@R14')
        self.writecommand('M=D')

        # Pop return value off the stack
        self.writecommand('@ARG')
        self.writecommand('A=M')
        self.pop_from_stack_to_m()

        # Move stack pointer to ARG+1
        self.writecommand('@ARG')
        self.writecommand('D=M+1')
        self.writecommand('@SP')
        self.writecommand('M=D')

        # Set that to *(FRAME-1)
        self.writecommand('@R13')
        self.writecommand('AM=M-1')
        self.writecommand('D=M')
        self.writecommand('@THAT')
        self.writecommand('M=D')

        # Set this to *(FRAME-2)
        self.writecommand('@R13')
        self.writecommand('AM=M-1')
        self.writecommand('D=M')
        self.writecommand('@THIS')
        self.writecommand('M=D')

        # Set arg to *(FRAME-3)
        self.writecommand('@R13')
        self.writecommand('AM=M-1')
        self.writecommand('D=M')
        self.writecommand('@ARG')
        self.writecommand('M=D')

        # Set LCL to *(FRAME-4)
        self.writecommand('@R13')
        self.writecommand('AM=M-1')
        self.writecommand('D=M')
        self.writecommand('@LCL')
        self.writecommand('M=D')

        # Load return value into D register
        # This is not part of the spec, but fun if D will serve as a display
        self.writecommand('@SP')
        self.writecommand('A=M-1')
        self.writecommand('D=M')

        # goto RET
        self.writecommand('@R14')
        self.writecommand('A=M')
        self.writecommand('0;JMP')

    def push_d_to_stack(self):
        self.writecommand('@SP')
        self.writecommand('AM=M+1')
        self.writecommand('A=A-1')
        self.writecommand('M=D')

    def pop_from_stack_to_m(self):
        self.writecommand('D=A')
        self.writecommand('@R15')
        self.writecommand('M=D')
        self.writecommand('@SP')
        self.writecommand('AM=M-1')
        self.writecommand('D=M')
        self.writecommand('@R15')
        self.writecommand('A=M')
        self.writecommand('M=D')

    def writecommand(self,cmdline):
        self.fout.write("%s\n"%cmdline)

    def close(self):
        self.fout.close()

if __name__ == '__main__':
    main(sys.argv)
