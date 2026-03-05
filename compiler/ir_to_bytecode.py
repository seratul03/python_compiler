from compiler.bytecode import Instruction


class IRToBytecodeConverter:
    def __init__(self, ir_code):
        self.ir_code = ir_code
        self.bytecode = []
        self.labels = {}

    def first_pass(self):
        """Count the actual number of bytecode instructions emitted per IR
        instruction so that label targets resolve to the correct positions."""
        position = 0
        for instr in self.ir_code:
            if instr.op == "LABEL":
                self.labels[instr.arg1] = position
            elif instr.op == "CONST":
                position += 2  
            elif instr.op == "ASSIGN":
                position += 2 
            elif instr.op in ("+", "-", "*", "/"):
                position += 4  
            elif instr.op in ("<", ">", "==", "!=", "<=", ">="):
                position += 4  
            elif instr.op == "PRINT":
                position += 2   
            elif instr.op == "JUMP":
                position += 1
            elif instr.op == "JUMP_IF_FALSE":
                position += 2  
            elif instr.op == "RETURN":
                position += 2   
            elif instr.op == "CALL":
                n_args = len(instr.arg2) if isinstance(instr.arg2, list) else 0
                position += n_args + 2
            elif instr.op == "LIST":
                n_elems = len(instr.arg1) if isinstance(instr.arg1, list) else 0
                position += n_elems + 2
            elif instr.op == "INDEX":
                position += 4  
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

            elif instr.op in ("<", ">", "==", "!=", "<=", ">="):
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg1)
                )
                self.bytecode.append(
                    Instruction("LOAD_VAR", instr.arg2)
                )
                self.bytecode.append(
                    Instruction("COMPARE", instr.op)
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

            elif instr.op == "DEFINE_FUNCTION":
                # Pass the AST node so the VM can inline the body when called.
                self.bytecode.append(
                    Instruction("DEFINE_FUNCTION", instr.arg2)
                )

            elif instr.op == "CALL":
                arg_list = instr.arg2 if isinstance(instr.arg2, list) else []
                for arg_var in arg_list:
                    self.bytecode.append(Instruction("LOAD_VAR", arg_var))
                self.bytecode.append(
                    Instruction("CALL_FUNCTION", (instr.arg1, len(arg_list)))
                )
                self.bytecode.append(
                    Instruction("STORE_VAR", instr.result)
                )

            elif instr.op == "RETURN":
                self.bytecode.append(Instruction("LOAD_VAR", instr.arg1))
                self.bytecode.append(Instruction("RETURN_VALUE"))

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