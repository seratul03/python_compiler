class Frame:
    def __init__(self):
        self.variables = {}


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


# ---------------------------------------------------------------------------
# Built-in functions available inside the VM
# ---------------------------------------------------------------------------

_BUILTIN_CALLABLES = {
    "int":   int,
    "float": float,
    "str":   str,
    "bool":  bool,
    "abs":   abs,
    "round": round,
    "type":  lambda x: type(x).__name__,
}


class VirtualMachine:
    def __init__(self, instructions):
        self.instructions = instructions
        self.stack = []
        self.frames = [Frame()]
        self.functions = {}       # name → {"params": [...], "instructions": [...]}
        self.classes   = {}       # name → ClassDef node
        self.output    = []
        self.call_stack = []      # [(saved_instructions, return_ip), ...]
        self._input_provider = input  # can be overridden for testing

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def current_frame(self):
        return self.frames[-1]

    def _load_var(self, name):
        """Look up variable: current frame → outer frames → builtins."""
        for frame in reversed(self.frames):
            if name in frame.variables:
                return frame.variables[name]
        # built-in callables / constants
        if name in _BUILTIN_CALLABLES:
            return _BUILTIN_CALLABLES[name]
        if name == "True":
            return True
        if name == "False":
            return False
        if name == "None":
            return None
        # user-defined function reference (for map / higher-order use)
        if name in self.functions:
            return name   # return function name as a string handle
        if name in self.classes:
            return name
        return 0   # default (matches old behaviour)

    def _compile_body(self, stmts):
        """Compile a list of AST statements to instructions."""
        from compiler.bytecode import BytecodeGenerator
        from compiler.ast_nodes import Program
        gen = BytecodeGenerator()
        instrs = gen.generate(Program(stmts))
        # Ensure there is always an implicit return None at the end
        if not instrs or instrs[-1].opcode != "RETURN_VALUE":
            from compiler.bytecode import Instruction
            instrs.append(Instruction("LOAD_CONST", None))
            instrs.append(Instruction("RETURN_VALUE"))
        return instrs

    def _find_method(self, class_name, method_name):
        """Walk the inheritance chain to find a method definition."""
        visited = set()
        while class_name and class_name not in visited:
            visited.add(class_name)
            cn = self.classes.get(class_name)
            if cn is None:
                break
            for stmt in cn.body:
                if hasattr(stmt, "name") and stmt.name == method_name:
                    return stmt, class_name
            class_name = getattr(cn, "parent", None)
        return None, None

    def _fmt(self, v):
        """Format a value for output, honouring __str__ on class instances."""
        if isinstance(v, bool):
            return "True" if v else "False"
        if v is None:
            return "None"
        if isinstance(v, dict) and "__class__" in v:
            s = self._instance_str(v)
            return s if s is not None else repr(v)
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)

    def _instance_str(self, obj):
        """
        Call __str__ on a class instance if the method is defined.
        Returns the string result, or a default '<ClassName object>' if not defined.
        """
        if not (isinstance(obj, dict) and "__class__" in obj):
            return None
        method_node, _ = self._find_method(obj["__class__"], "__str__")
        if method_node is None:
            class_name = obj.get("__class__", "object")
            return f"<{class_name} object>"
        method_instructions = self._compile_body(method_node.body)
        new_frame = Frame()
        new_frame.variables["self"] = obj
        new_frame.variables["__current_class__"] = obj.get("__class__", "")
        sub_vm = VirtualMachine(method_instructions)
        sub_vm.frames    = [new_frame]
        sub_vm.functions = self.functions
        sub_vm.classes   = self.classes
        sub_vm._input_provider = self._input_provider
        sub_vm.run()
        result = sub_vm.stack[-1] if sub_vm.stack else ""
        return str(result)

    def _call_method_node(self, method_node, obj, args, ip):
        """Switch instruction stream to execute a class method."""
        method_instructions = self._compile_body(method_node.body)
        new_frame = Frame()
        new_frame.variables["self"] = obj
        new_frame.variables["__current_class__"] = obj.get("__class__", "")
        for param, val in zip(method_node.params[1:], args):
            new_frame.variables[param] = val
        self.frames.append(new_frame)
        self.call_stack.append((self.instructions, ip + 1))
        self.instructions = method_instructions
        return -1  # ip → 0 after ip += 1

    def _call_function(self, func_name, args, ip):
        func = self.functions[func_name]
        new_frame = Frame()
        for param, val in zip(func["params"], args):
            new_frame.variables[param] = val
        self.frames.append(new_frame)
        self.call_stack.append((self.instructions, ip + 1))
        self.instructions = func["instructions"]
        return -1  # ip → 0 after ip += 1

    # ------------------------------------------------------------------ #
    # Main run loop
    # ------------------------------------------------------------------ #

    def run(self):
        ip = 0

        while ip < len(self.instructions):
            instr = self.instructions[ip]
            op    = instr.opcode

            # -------- LOAD / STORE -------- #

            if op == "LOAD_CONST":
                self.stack.append(instr.argument)

            elif op == "LOAD_VAR":
                self.stack.append(self._load_var(instr.argument))

            elif op == "STORE_VAR":
                self.current_frame().variables[instr.argument] = self.stack.pop()

            # -------- LISTS -------- #

            elif op == "BUILD_LIST":
                count = instr.argument
                elems = [self.stack.pop() for _ in range(count)]
                elems.reverse()
                self.stack.append(elems)

            elif op == "UNPACK_SEQUENCE":
                n   = instr.argument
                seq = self.stack.pop()
                items = list(seq)
                if len(items) != n:
                    raise ValueError(
                        f"not enough values to unpack (expected {n}, got {len(items)})"
                    )
                # Push in reverse so first STORE_VAR gets first element
                for item in reversed(items):
                    self.stack.append(item)

            elif op == "LIST_APPEND":
                value = self.stack.pop()
                lst   = self.stack.pop()
                lst.append(value)
                # list lives by reference — no need to push back

            elif op == "LOAD_INDEX":
                index = self.stack.pop()
                lst   = self.stack.pop()
                self.stack.append(lst[index])

            elif op == "STORE_INDEX":
                value = self.stack.pop()
                index = self.stack.pop()
                lst   = self.stack.pop()
                lst[index] = value

            elif op == "POP_TOP":
                if self.stack:
                    self.stack.pop()

            # -------- PRINT -------- #

            elif op == "PRINT":
                count  = instr.argument if instr.argument is not None else 1
                values = [self.stack.pop() for _ in range(count)]
                values.reverse()
                self.output.append(" ".join(self._fmt(v) for v in values))

            # -------- ARITHMETIC -------- #

            elif op in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW"):
                b = self.stack.pop()
                a = self.stack.pop()
                if op == "ADD":
                    result = a + b
                elif op == "SUB":
                    result = a - b
                elif op == "MUL":
                    result = a * b
                elif op == "DIV":
                    result = a / b
                elif op == "MOD":
                    result = a % b
                else:
                    result = a ** b
                self.stack.append(result)

            # -------- UNARY -------- #

            elif op == "UNARY_NEG":
                self.stack.append(-self.stack.pop())

            elif op == "UNARY_NOT":
                self.stack.append(not self.stack.pop())

            elif op == "BINARY_AND":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a and b)

            elif op == "BINARY_OR":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a or b)

            # -------- COMPARISON -------- #

            elif op == "COMPARE":
                b = self.stack.pop()
                a = self.stack.pop()
                cmp = instr.argument
                if cmp == "==":
                    self.stack.append(a == b)
                elif cmp == "!=":
                    self.stack.append(a != b)
                elif cmp == "<":
                    self.stack.append(a < b)
                elif cmp == ">":
                    self.stack.append(a > b)
                elif cmp == "<=":
                    self.stack.append(a <= b)
                elif cmp == ">=":
                    self.stack.append(a >= b)
                elif cmp == "is":
                    self.stack.append(a is b)
                elif cmp == "is not":
                    self.stack.append(a is not b)
                elif cmp == "in":
                    self.stack.append(a in b)
                elif cmp == "not in":
                    self.stack.append(a not in b)
                else:
                    self.stack.append(False)

            # -------- CONTROL FLOW -------- #

            elif op == "JUMP_IF_FALSE":
                if not self.stack.pop():
                    ip = instr.argument
                    continue

            elif op == "JUMP":
                ip = instr.argument
                continue

            # -------- FUNCTION DEFINITION -------- #

            elif op == "DEFINE_FUNCTION":
                func_node = instr.argument
                self.functions[func_node.name] = {
                    "params":       func_node.params,
                    "instructions": self._compile_body(func_node.body),
                }

            # -------- FUNCTION CALL -------- #

            elif op == "CALL_FUNCTION":
                name, arg_count = instr.argument
                args = [self.stack.pop() for _ in range(arg_count)]
                args.reverse()
                ip = self._dispatch_call(name, args, ip)
                if ip == -1:
                    ip = 0
                    continue
                # ip was set to a real value → skip the ip += 1 below
                else:
                    ip += 1
                    continue

            # -------- RETURN -------- #

            elif op == "RETURN_VALUE":
                return_value = self.stack.pop() if self.stack else None
                self.frames.pop()
                if self.call_stack:
                    self.instructions, ip = self.call_stack.pop()
                    ip -= 1   # ip += 1 at end of loop moves it right
                else:
                    # top-level return — end execution
                    self.stack.append(return_value)
                    break
                self.stack.append(return_value)

            # -------- CLASS DEFINITION -------- #

            elif op == "DEFINE_CLASS":
                class_node = instr.argument
                self.classes[class_node.name] = class_node

            # -------- ATTRIBUTE ACCESS -------- #

            elif op == "LOAD_ATTR":
                attr = instr.argument
                obj  = self.stack.pop()
                if isinstance(obj, dict) and "__attributes__" in obj:
                    self.stack.append(obj["__attributes__"].get(attr))
                else:
                    # strings, lists, or Python objects
                    self.stack.append(getattr(obj, attr, None))

            elif op == "STORE_ATTR":
                attr  = instr.argument
                value = self.stack.pop()
                obj   = self.stack.pop()
                if isinstance(obj, dict) and "__attributes__" in obj:
                    obj["__attributes__"][attr] = value
                else:
                    setattr(obj, attr, value)

            # -------- METHOD CALL -------- #

            elif op == "CALL_METHOD":
                method_name, arg_count = instr.argument
                args = [self.stack.pop() for _ in range(arg_count)]
                args.reverse()
                obj  = self.stack.pop()

                # --- built-in string methods ---
                if isinstance(obj, str):
                    m = getattr(str, method_name, None)
                    if m is None:
                        raise AttributeError(f"str has no method '{method_name}'")
                    result = getattr(obj, method_name)(*args)
                    self.stack.append(result if result is not None else obj)
                    ip += 1
                    continue

                # --- built-in list methods ---
                if isinstance(obj, list):
                    m = getattr(list, method_name, None)
                    if m is None:
                        raise AttributeError(f"list has no method '{method_name}'")
                    result = getattr(obj, method_name)(*args)
                    # methods like append/sort/reverse return None but mutate
                    self.stack.append(result if result is not None else None)
                    ip += 1
                    continue

                # --- class instance method ---
                if not (isinstance(obj, dict) and "__class__" in obj):
                    raise TypeError(
                        f"Cannot call method '{method_name}' on {type(obj).__name__}"
                    )
                method_node, _ = self._find_method(obj["__class__"], method_name)
                if method_node is None:
                    raise AttributeError(
                        f"Class '{obj['__class__']}' has no method '{method_name}'"
                    )
                ip = self._call_method_node(method_node, obj, args, ip)
                ip = 0
                continue

            # -------- SUPER METHOD CALL -------- #

            elif op == "CALL_SUPER_METHOD":
                method_name, arg_count = instr.argument
                args = [self.stack.pop() for _ in range(arg_count)]
                args.reverse()
                self_obj = self.current_frame().variables.get("self")
                current_class = self.current_frame().variables.get(
                    "__current_class__", self_obj.get("__class__", "") if self_obj else ""
                )
                parent_name = getattr(self.classes.get(current_class), "parent", None)
                if not parent_name:
                    raise Exception(f"Class '{current_class}' has no parent for super()")
                method_node, _ = self._find_method(parent_name, method_name)
                if method_node is None:
                    raise AttributeError(
                        f"Parent class '{parent_name}' has no method '{method_name}'"
                    )
                ip = self._call_method_node(method_node, self_obj, args, ip)
                ip = 0
                continue

            ip += 1

        return "\n".join(str(x) for x in self.output)

    # ------------------------------------------------------------------ #
    # Built-in dispatch
    # ------------------------------------------------------------------ #

    def _dispatch_call(self, name, args, ip):
        """
        Handle all built-in functions.
        Returns ip=-1 if control was handed to user-defined code (the caller
        must then start the new instruction stream at ip=0).
        Otherwise returns the next ip to continue at (caller should ip+=1 skip).
        This method pushes a result onto self.stack in the built-in case.
        """

        # --- simple type coercions ---
        if name == "str":
            # Honour __str__ on class instances
            obj = args[0] if args else ""
            if isinstance(obj, dict) and "__class__" in obj:
                self.stack.append(self._instance_str(obj) or str(obj))
            else:
                self.stack.append(str(obj))
            return ip

        if name in ("int", "float", "bool", "abs", "round"):
            fn = _BUILTIN_CALLABLES[name]
            self.stack.append(fn(*args))
            return ip   # caller does ip += 1

        if name == "len":
            self.stack.append(len(args[0]))
            return ip

        if name == "input":
            prompt = str(args[0]) if args else ""
            try:
                result = self._input_provider(prompt)
            except EOFError:
                result = ""
            self.stack.append(result)
            return ip

        if name == "range":
            if len(args) == 1:
                self.stack.append(list(range(int(args[0]))))
            elif len(args) == 2:
                self.stack.append(list(range(int(args[0]), int(args[1]))))
            else:
                self.stack.append(
                    list(range(int(args[0]), int(args[1]), int(args[2])))
                )
            return ip

        if name == "list":
            self.stack.append(list(args[0]))
            return ip

        if name == "tuple":
            self.stack.append(tuple(args[0]))
            return ip

        if name == "set":
            self.stack.append(set(args[0]) if args else set())
            return ip

        if name == "dict":
            self.stack.append(dict(*args))
            return ip

        if name == "sorted":
            self.stack.append(sorted(args[0]))
            return ip

        if name == "reversed":
            self.stack.append(list(reversed(args[0])))
            return ip

        if name == "enumerate":
            start = int(args[1]) if len(args) > 1 else 0
            self.stack.append(
                [[i + start, item] for i, item in enumerate(args[0])]
            )
            return ip

        if name == "map":
            fn_ref  = args[0]
            iterable = args[1]
            result  = []
            for item in iterable:
                if callable(fn_ref):
                    result.append(fn_ref(item))
                elif isinstance(fn_ref, str) and fn_ref in self.functions:
                    # user-defined function name
                    func = self.functions[fn_ref]
                    tmp_frame = Frame()
                    for param, val in zip(func["params"], [item]):
                        tmp_frame.variables[param] = val
                    sub_vm = VirtualMachine(func["instructions"])
                    sub_vm.frames = [tmp_frame]
                    sub_vm.functions = self.functions
                    sub_vm.classes   = self.classes
                    sub_vm.run()
                    result.append(sub_vm.stack[-1] if sub_vm.stack else None)
                else:
                    result.append(fn_ref)
            self.stack.append(result)
            return ip

        if name == "zip":
            self.stack.append([list(row) for row in zip(*args)])
            return ip

        if name == "sum":
            self.stack.append(sum(args[0]))
            return ip

        if name == "min":
            if len(args) == 1:
                self.stack.append(min(args[0]))
            else:
                self.stack.append(min(args))
            return ip

        if name == "max":
            if len(args) == 1:
                self.stack.append(max(args[0]))
            else:
                self.stack.append(max(args))
            return ip

        if name == "print":
            self.output.append(" ".join(self._fmt(v) for v in args))
            self.stack.append(None)
            return ip

        if name == "isinstance":
            obj, typ = args[0], args[1]
            if isinstance(typ, str):
                result = (
                    isinstance(obj, dict) and obj.get("__class__") == typ
                ) or isinstance(obj, {
                    "int": int, "float": float, "str": str,
                    "list": list, "bool": bool,
                }.get(typ, type(None)))
            else:
                result = isinstance(obj, typ)
            self.stack.append(result)
            return ip

        if name == "hasattr":
            obj, attr = args[0], args[1]
            if isinstance(obj, dict) and "__attributes__" in obj:
                result = attr in obj["__attributes__"]
            else:
                result = hasattr(obj, attr)
            self.stack.append(result)
            return ip

        if name == "getattr":
            obj = args[0]; attr = args[1]
            default = args[2] if len(args) > 2 else None
            if isinstance(obj, dict) and "__attributes__" in obj:
                result = obj["__attributes__"].get(attr, default)
            else:
                result = getattr(obj, attr, default)
            self.stack.append(result)
            return ip

        if name == "setattr":
            obj, attr, val = args
            if isinstance(obj, dict) and "__attributes__" in obj:
                obj["__attributes__"][attr] = val
            else:
                setattr(obj, attr, val)
            self.stack.append(None)
            return ip

        # --- class constructor ---
        if name in self.classes:
            instance = {"__class__": name, "__attributes__": {}}
            init_node, _ = self._find_method(name, "__init__")
            if init_node:
                init_instrs = self._compile_body(init_node.body)
                new_frame   = Frame()
                new_frame.variables["self"] = instance
                new_frame.variables["__current_class__"] = name
                for param, val in zip(init_node.params[1:], args):
                    new_frame.variables[param] = val
                # Run __init__ with a sub-VM (constructor always returns self)
                sub_vm = VirtualMachine(init_instrs)
                sub_vm.frames   = [new_frame]
                sub_vm.functions = self.functions
                sub_vm.classes   = self.classes
                sub_vm._input_provider = self._input_provider
                sub_vm.run()
                self.output.extend(sub_vm.output)
            self.stack.append(instance)
            return ip

        # --- user-defined function (instruction-switch) ---
        if name in self.functions:
            ip = self._call_function(name, args, ip)
            return ip   # -1  → caller handles

        raise NameError(f"Unknown function or class: '{name}'")
