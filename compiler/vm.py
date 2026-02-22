class Frame:
    def __init__(self, return_ip=None):
        self.variables = {}
        self.return_ip = return_ip


class VirtualMachine:
    def __init__(self, instructions):
        self.instructions = instructions
        self.stack = []
        self.frames = [Frame()]
        self.functions = {}
        self.classes = {}
        self.output = []

    def current_frame(self):
        return self.frames[-1]

    def run(self):
        ip = 0

        while ip < len(self.instructions):
            instr = self.instructions[ip]

            # ---------------- LOAD / STORE ---------------- #

            if instr.opcode == "LOAD_CONST":
                self.stack.append(instr.argument)

            elif instr.opcode == "LOAD_VAR":
                value = self.current_frame().variables.get(instr.argument, 0)
                self.stack.append(value)

            elif instr.opcode == "STORE_VAR":
                self.current_frame().variables[instr.argument] = self.stack.pop()

            # ---------------- LISTS ---------------- #

            elif instr.opcode == "BUILD_LIST":
                count = instr.argument
                elements = []
                for _ in range(count):
                    elements.append(self.stack.pop())
                elements.reverse()
                self.stack.append(elements)

            elif instr.opcode == "LOAD_INDEX":
                index = self.stack.pop()
                lst = self.stack.pop()
                self.stack.append(lst[index])

            elif instr.opcode == "STORE_INDEX":
                value = self.stack.pop()
                index = self.stack.pop()
                lst = self.stack.pop()
                lst[index] = value

            # ---------------- PRINT ---------------- #

            elif instr.opcode == "PRINT":
                self.output.append(str(self.stack.pop()))

            # ---------------- ARITHMETIC ---------------- #

            elif instr.opcode in ("ADD", "SUB", "MUL", "DIV"):
                b = self.stack.pop()
                a = self.stack.pop()

                if instr.opcode == "ADD":
                    self.stack.append(a + b)
                elif instr.opcode == "SUB":
                    self.stack.append(a - b)
                elif instr.opcode == "MUL":
                    self.stack.append(a * b)
                elif instr.opcode == "DIV":
                    self.stack.append(a / b)

            # ---------------- COMPARISON ---------------- #

            elif instr.opcode == "COMPARE":
                b = self.stack.pop()
                a = self.stack.pop()

                op = instr.argument

                result = {
                    "==": a == b,
                    "!=": a != b,
                    "<": a < b,
                    ">": a > b,
                    "<=": a <= b,
                    ">=": a >= b,
                }[op]

                self.stack.append(result)

            # ---------------- CONTROL FLOW ---------------- #

            elif instr.opcode == "JUMP_IF_FALSE":
                condition = self.stack.pop()
                if not condition:
                    ip = instr.argument
                    continue

            elif instr.opcode == "JUMP":
                ip = instr.argument
                continue

            # ---------------- FUNCTIONS ---------------- #

            elif instr.opcode == "DEFINE_FUNCTION":
                func_node = instr.argument
                self.functions[func_node.name] = func_node

            elif instr.opcode == "CALL_FUNCTION":
                name, arg_count = instr.argument

                # Built-in len()
                if name == "len":
                    arg = self.stack.pop()
                    self.stack.append(len(arg))
                    ip += 1
                    continue

                # Class constructor
                if name in self.classes:
                    class_node = self.classes[name]

                    instance = {
                        "__class__": name,
                        "__attributes__": {}
                    }

                    # collect constructor args
                    args = []
                    for _ in range(arg_count):
                        args.append(self.stack.pop())
                    args.reverse()

                    # run __init__ if exists
                    for stmt in class_node.body:
                        if (
                            isinstance(stmt, type(class_node.body[0]))
                            and stmt.name == "__init__"
                        ):
                            new_frame = Frame(return_ip=None)
                            new_frame.variables["self"] = instance

                            for param, value in zip(stmt.params[1:], args):
                                new_frame.variables[param] = value

                            self.frames.append(new_frame)

                            from compiler.bytecode import BytecodeGenerator
                            from compiler.ast_nodes import Program

                            generator = BytecodeGenerator()
                            init_instructions = generator.generate(
                                Program(stmt.body)
                            )

                            temp_vm = VirtualMachine(init_instructions)
                            temp_vm.frames = self.frames
                            temp_vm.functions = self.functions
                            temp_vm.classes = self.classes
                            temp_vm.run()

                            self.frames.pop()

                    self.stack.append(instance)
                    ip += 1
                    continue

                # Normal function
                func = self.functions[name]

                args = []
                for _ in range(arg_count):
                    args.append(self.stack.pop())
                args.reverse()

                new_frame = Frame(return_ip=ip + 1)

                for param, value in zip(func.params, args):
                    new_frame.variables[param] = value

                self.frames.append(new_frame)

                from compiler.bytecode import BytecodeGenerator
                from compiler.ast_nodes import Program

                generator = BytecodeGenerator()
                func_instructions = generator.generate(
                    Program(func.body)
                )

                self.instructions[ip:ip + 1] = func_instructions
                ip -= 1

            elif instr.opcode == "RETURN_VALUE":
                return_value = self.stack.pop()
                frame = self.frames.pop()
                ip = frame.return_ip - 1
                self.stack.append(return_value)

            # ---------------- CLASSES ---------------- #

            elif instr.opcode == "DEFINE_CLASS":
                class_node = instr.argument
                self.classes[class_node.name] = class_node

            elif instr.opcode == "LOAD_ATTR":
                attr = instr.argument
                obj = self.stack.pop()
                self.stack.append(obj["__attributes__"].get(attr))

            elif instr.opcode == "STORE_ATTR":
                attr = instr.argument
                value = self.stack.pop()
                obj = self.stack.pop()
                obj["__attributes__"][attr] = value

            elif instr.opcode == "CALL_METHOD":
                method_name, arg_count = instr.argument

                args = []
                for _ in range(arg_count):
                    args.append(self.stack.pop())
                args.reverse()

                obj = self.stack.pop()
                class_node = self.classes[obj["__class__"]]

                for stmt in class_node.body:
                    if stmt.name == method_name:
                        new_frame = Frame(return_ip=ip + 1)
                        new_frame.variables["self"] = obj

                        for param, value in zip(stmt.params[1:], args):
                            new_frame.variables[param] = value

                        self.frames.append(new_frame)

                        from compiler.bytecode import BytecodeGenerator
                        from compiler.ast_nodes import Program

                        generator = BytecodeGenerator()
                        method_instructions = generator.generate(
                            Program(stmt.body)
                        )

                        self.instructions[ip:ip + 1] = method_instructions
                        ip -= 1
                        break

            ip += 1

        return "\n".join(self.output)