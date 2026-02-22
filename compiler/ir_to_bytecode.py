from compiler.bytecode import Instruction


class IRToBytecodeConverter:
    def __init__(self, ir_code):
        self.ir_code = ir_code
        self.bytecode = []
        self.labels = {}

    def first_pass(self):
        position = 0
        for instr in self.ir_code:
            if instr.op == "LABEL":
                self.labels[instr.arg1] = position
            else:
                position += 1

    def convert(self):
        self.first_pass()

        for instr in self.ir_code:

            if instr.op == "LABEL":
                continue

            elif instr.op == "CONST":
                self.bytecode.append(
                    Instruction("LOAD_CONST", instr.arg1)
                )
                self.bytecode.append(
                    Instruction("STORE_VAR", instr.result)
                )

            elif instr.op == "ASSIGN":
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg1)
                )
                self.bytecode.append(
                    Instruction("STORE_VAR", instr.result)
                )

            elif instr.op in ("+", "-", "*", "/"):
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg1)
                )
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg2)
                )

                op_map = {
                    "+": "ADD",
                    "-": "SUB",
                    "*": "MUL",
                    "/": "DIV"
                }

                self.bytecode.append(
                    Instruction(op_map[instr.op])
                )
                self.bytecode.append(
                    Instruction("STORE_VAR", instr.result)
                )

            elif instr.op == "COMPARE":
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg1)
                )
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg2)
                )
                self.bytecode.append(
                    Instruction("COMPARE", "<")  # adjust later for full support
                )
                self.bytecode.append(
                    Instruction("STORE_VAR", instr.result)
                )

            elif instr.op == "PRINT":
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg1)
                )
                self.bytecode.append(
                    Instruction("PRINT")
                )

            elif instr.op == "JUMP":
                self.bytecode.append(
                    Instruction("JUMP", self.labels[instr.arg1])
                )

            elif instr.op == "JUMP_IF_FALSE":
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg2)
                )
                self.bytecode.append(
                    Instruction("JUMP_IF_FALSE", self.labels[instr.arg1])
                )

        return self.bytecode