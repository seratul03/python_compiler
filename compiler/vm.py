class Frame:
    def __init__(self):
        self.variables = {}


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


_BUILTIN_CALLABLES = {
    "int":   int,
    "float": float,
    "str":   str,
    "bool":  bool,
    "abs":   abs,
    "round": round,
    "type":  lambda x: type(x).__name__,
}

_ALLOWED_MODULES = {
    "ast", "dis", "tokenize", "token", "symtable", "types", "codeop",
    "sys", "io", "contextlib", "traceback", "builtins",
    "os", "os.path", "signal", "subprocess", "time", "threading",
    "json", "uuid", "tempfile", "pathlib", "logging", "pprint",
    "graphviz", "inspect", "resource", "math", "re", "copy",
    "functools", "itertools", "collections", "string", "textwrap",
    "operator", "struct", "array", "heapq", "bisect", "queue",
    "random", "statistics", "decimal", "fractions", "numbers",
    "datetime", "calendar", "hashlib", "hmac", "secrets", "base64",
    "urllib", "urllib.parse", "urllib.request", "http", "http.client",
    "email", "csv", "configparser", "argparse", "shutil", "glob",
    "fnmatch", "linecache", "pickle", "shelve", "sqlite3", "xml",
    "html", "html.parser", "enum", "dataclasses", "abc", "weakref",
    "gc", "platform", "socket", "ssl", "select", "errno", "ctypes",
}

_ALLOWED_PREFIXES = {
    "numpy",
    "pandas",
    "matplotlib",
    "sklearn",
}


def _import_module(name: str):
    """Import a module by name if it is in the allowed list."""
    if name not in _ALLOWED_MODULES:
        allowed_by_prefix = any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in _ALLOWED_PREFIXES
        )
        if not allowed_by_prefix:
            raise ImportError(
                f"Module '{name}' is not in the list of allowed imports."
            )
    import importlib
    return importlib.import_module(name)




class VirtualMachine:
    def __init__(self, instructions):
        self.instructions = instructions
        self.stack = []
        self.frames = [Frame()]
        self.functions = {}       
        self.classes   = {}       
        self.output    = []
        self.call_stack = []    
        self._input_provider = input  

        from compiler.jit import JITCompiler
        self.jit = JITCompiler(threshold=10)
        self._jit_builtins = {
            "range":    lambda *a: list(range(*[int(x) for x in a])),
            "len":      len,
            "str":      str,
            "int":      int,
            "float":    float,
            "bool":     bool,
            "abs":      abs,
            "round":    round,
            "sorted":   sorted,
            "reversed": lambda x: list(reversed(x)),
            "sum":      sum,
            "min":      min,
            "max":      max,
            "zip":      lambda *a: [list(r) for r in zip(*a)],
            "enumerate": enumerate,
            "list":     list,
            "tuple":    tuple,
            "type":     lambda x: type(x).__name__,
            "__jit_print__": self._jit_print,
        }


    def current_frame(self):
        return self.frames[-1]

    def _load_var(self, name):
        """Look up variable: current frame → outer frames → builtins."""
        for frame in reversed(self.frames):
            if name in frame.variables:
                return frame.variables[name]
        if name in _BUILTIN_CALLABLES:
            return _BUILTIN_CALLABLES[name]
        if name == "True":
            return True
        if name == "False":
            return False
        if name == "None":
            return None
        if name == "__name__":
            return "__main__"
        if name in self.functions:
            return name 
        if name in self.classes:
            return name
        return 0  

    def _compile_body(self, stmts):
        from compiler.bytecode import BytecodeGenerator
        from compiler.ast_nodes import Program
        gen = BytecodeGenerator()
        instrs = gen.generate(Program(stmts))
        if not instrs or instrs[-1].opcode != "RETURN_VALUE":
            from compiler.bytecode import Instruction
            instrs.append(Instruction("LOAD_CONST", None))
            instrs.append(Instruction("RETURN_VALUE"))
        return instrs

    def _find_method(self, class_name, method_name):
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
        if not (isinstance(obj, dict) and "__class__" in obj):
            return None
        method_node, found_class = self._find_method(obj["__class__"], "__str__")
        if method_node is None:
            class_name = obj.get("__class__", "object")
            return f"<{class_name} object>"
        method_instructions = self._compile_body(method_node.body)
        new_frame = Frame()
        new_frame.variables["self"] = obj
        new_frame.variables["__current_class__"] = found_class or obj.get("__class__", "")
        sub_vm = VirtualMachine(method_instructions)
        sub_vm.frames    = [new_frame]
        sub_vm.functions = self.functions
        sub_vm.classes   = self.classes
        sub_vm._input_provider = self._input_provider
        sub_vm.run()
        result = sub_vm.stack[-1] if sub_vm.stack else ""
        return str(result)

    def _call_method_node(self, method_node, obj, args, ip, class_name=None):
        method_instructions = self._compile_body(method_node.body)
        new_frame = Frame()
        new_frame.variables["self"] = obj
        new_frame.variables["__current_class__"] = (
            class_name if class_name is not None else obj.get("__class__", "")
        )
        for param, val in zip(method_node.params[1:], args):
            new_frame.variables[param] = val
        self.frames.append(new_frame)
        self.call_stack.append((self.instructions, ip + 1))
        self.instructions = method_instructions
        return -1

    def _jit_print(self, *args):
        self.output.append(" ".join(self._fmt(v) for v in args))

    def _call_function(self, func_name, args, ip):
        self.jit.record_call(func_name)
        cached_fn = self.jit.try_get_compiled(func_name)
        if cached_fn is None and self.jit.should_compile(func_name):
            func_entry   = self.functions.get(func_name, {})
            func_def_node = func_entry.get("node")
            if func_def_node:
                ns = dict(self._jit_builtins)
                for fname, fn in self.jit._cache.items():
                    if callable(fn):
                        ns[fname] = fn
                cached_fn = self.jit.try_compile(func_name, func_def_node, ns)
        if cached_fn is not None:
            try:
                result = cached_fn(*args)
                self.stack.append(result)
                return ip
            except Exception:
                pass

        func = self.functions[func_name]
        new_frame = Frame()
        for param, val in zip(func["params"], args):
            new_frame.variables[param] = val
        self.frames.append(new_frame)
        self.call_stack.append((self.instructions, ip + 1))
        self.instructions = func["instructions"]
        return -1

    def run(self):
        ip = 0

        while ip < len(self.instructions):
            instr = self.instructions[ip]
            op    = instr.opcode

            if op == "LOAD_CONST":
                self.stack.append(instr.argument)

            elif op == "LOAD_VAR":
                self.stack.append(self._load_var(instr.argument))

            elif op == "STORE_VAR":
                name = instr.argument
                globals_set = self.current_frame().variables.get("__globals__")
                if isinstance(globals_set, set) and name in globals_set:
                    self.frames[0].variables[name] = self.stack.pop()
                else:
                    self.current_frame().variables[name] = self.stack.pop()

            elif op == "BUILD_LIST":
                count = instr.argument
                elems = [self.stack.pop() for _ in range(count)]
                elems.reverse()
                self.stack.append(elems)

            elif op == "BUILD_TUPLE":
                count = instr.argument
                elems = [self.stack.pop() for _ in range(count)]
                elems.reverse()
                self.stack.append(tuple(elems))

            elif op == "UNPACK_SEQUENCE":
                n   = instr.argument
                seq = self.stack.pop()
                items = list(seq)
                if len(items) != n:
                    raise ValueError(
                        f"not enough values to unpack (expected {n}, got {len(items)})"
                    )
                for item in reversed(items):
                    self.stack.append(item)

            elif op == "LIST_APPEND":
                value = self.stack.pop()
                lst   = self.stack.pop()
                lst.append(value)
               
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

            elif op == "PRINT":
                count  = instr.argument if instr.argument is not None else 1
                values = [self.stack.pop() for _ in range(count)]
                values.reverse()
                self.output.append(" ".join(self._fmt(v) for v in values))

            elif op in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW", "FLOORDIV"):
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
                elif op == "FLOORDIV":
                    result = a // b
                else:
                    result = a ** b
                self.stack.append(result)

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
            elif op == "JUMP_IF_FALSE":
                if not self.stack.pop():
                    ip = instr.argument
                    continue

            elif op == "JUMP":
                ip = instr.argument
                continue
            elif op == "DEFINE_FUNCTION":
                func_node = instr.argument
                self.functions[func_node.name] = {
                    "params":       func_node.params,
                    "instructions": self._compile_body(func_node.body),
                    "node":         func_node,  
                }
            elif op == "CALL_FUNCTION":
                name, arg_count = instr.argument
                args = [self.stack.pop() for _ in range(arg_count)]
                args.reverse()
                ip = self._dispatch_call(name, args, ip)
                if ip == -1:
                    ip = 0
                    continue
                else:
                    ip += 1
                    continue
            elif op == "RETURN_VALUE":
                return_value = self.stack.pop() if self.stack else None
                self.frames.pop()
                if self.call_stack:
                    self.instructions, ip = self.call_stack.pop()
                    ip -= 1  
                else:
                    self.stack.append(return_value)
                    break
                self.stack.append(return_value)
            elif op == "DEFINE_CLASS":
                class_node = instr.argument
                self.classes[class_node.name] = class_node
            elif op == "LOAD_ATTR":
                attr = instr.argument
                obj  = self.stack.pop()
                if isinstance(obj, dict) and "__attributes__" in obj:
                    self.stack.append(obj["__attributes__"].get(attr))
                else:
                    self.stack.append(getattr(obj, attr, None))

            elif op == "STORE_ATTR":
                attr  = instr.argument
                value = self.stack.pop()
                obj   = self.stack.pop()
                if isinstance(obj, dict) and "__attributes__" in obj:
                    obj["__attributes__"][attr] = value
                else:
                    setattr(obj, attr, value)
            elif op == "CALL_METHOD":
                method_name, arg_count = instr.argument
                args = [self.stack.pop() for _ in range(arg_count)]
                args.reverse()
                obj  = self.stack.pop()

                if isinstance(obj, str):
                    m = getattr(str, method_name, None)
                    if m is None:
                        raise AttributeError(f"str has no method '{method_name}'")
                    result = getattr(obj, method_name)(*args)
                    self.stack.append(result if result is not None else obj)
                    ip += 1
                    continue

                if isinstance(obj, list):
                    m = getattr(list, method_name, None)
                    if m is None:
                        raise AttributeError(f"list has no method '{method_name}'")
                    result = getattr(obj, method_name)(*args)
                    self.stack.append(result if result is not None else None)
                    ip += 1
                    continue

                if not (isinstance(obj, dict) and "__class__" in obj):
                    method = getattr(obj, method_name, None)
                    if method is None:
                        raise AttributeError(
                            f"'{type(obj).__name__}' has no attribute '{method_name}'"
                        )
                    result = method(*args)
                    self.stack.append(result)
                    ip += 1
                    continue
                method_node, found_class = self._find_method(obj["__class__"], method_name)
                if method_node is None:
                    raise AttributeError(
                        f"Class '{obj['__class__']}' has no method '{method_name}'"
                    )
                ip = self._call_method_node(method_node, obj, args, ip, class_name=found_class)
                ip = 0
                continue
            elif op == "CALL_SUPER_METHOD":
                instr_arg = instr.argument
                if len(instr_arg) == 3:
                    method_name, arg_count, explicit_class = instr_arg
                else:
                    method_name, arg_count = instr_arg
                    explicit_class = None
                args = [self.stack.pop() for _ in range(arg_count)]
                args.reverse()
                self_obj = self.current_frame().variables.get("self")
                current_class = self.current_frame().variables.get(
                    "__current_class__", self_obj.get("__class__", "") if self_obj else ""
                )
                lookup_root = explicit_class if explicit_class else current_class
                parent_name = getattr(self.classes.get(lookup_root), "parent", None)
                if not parent_name:
                    raise Exception(f"Class '{lookup_root}' has no parent for super()")
                method_node, found_class = self._find_method(parent_name, method_name)
                if method_node is None:
                    raise AttributeError(
                        f"Parent class '{parent_name}' has no method '{method_name}'"
                    )
                ip = self._call_method_node(method_node, self_obj, args, ip, class_name=found_class)
                ip = 0
                continue

            elif op == "JUMP_IF_TRUE":
                if self.stack.pop():
                    ip = instr.argument
                    continue

            elif op == "DUP_TOP":
                self.stack.append(self.stack[-1])

            elif op in ("BITWISE_AND", "BITWISE_OR", "BITWISE_XOR",
                        "BITWISE_LSHIFT", "BITWISE_RSHIFT"):
                b = self.stack.pop()
                a = self.stack.pop()
                if op == "BITWISE_AND":
                    self.stack.append(int(a) & int(b))
                elif op == "BITWISE_OR":
                    self.stack.append(int(a) | int(b))
                elif op == "BITWISE_XOR":
                    self.stack.append(int(a) ^ int(b))
                elif op == "BITWISE_LSHIFT":
                    self.stack.append(int(a) << int(b))
                else:
                    self.stack.append(int(a) >> int(b))

            elif op == "UNARY_BITNOT":
                self.stack.append(~int(self.stack.pop()))

            elif op == "BUILD_DICT":
                count = instr.argument
                d = {}
                pairs = [self.stack.pop() for _ in range(count * 2)]
                pairs.reverse()
                for i in range(0, len(pairs), 2):
                    k, v = pairs[i], pairs[i + 1]
                    d[k] = v
                self.stack.append(d)

            elif op == "DICT_SPREAD":
                spread = self.stack.pop()
                if self.stack and isinstance(self.stack[-1], dict):
                    self.stack[-1].update(spread)
                else:
                    self.stack.append(dict(spread))

            elif op == "DICT_SET_ITEM":
                value = self.stack.pop()
                key   = self.stack.pop()
                d     = self.stack[-1]
                d[key] = value

            elif op == "BUILD_SET":
                count = instr.argument
                elems = [self.stack.pop() for _ in range(count)]
                self.stack.append(set(elems))

            elif op == "SET_ADD":
                elem = self.stack.pop()
                s    = self.stack[-1]
                s.add(elem)

            elif op == "BUILD_SLICE":
                step  = self.stack.pop()
                stop  = self.stack.pop()
                start = self.stack.pop()
                self.stack.append(slice(start, stop, step))

            elif op == "UNPACK_STARRED":
                val = self.stack.pop()
                if isinstance(val, (list, tuple)):
                    for item in val:
                        self.stack.append(item)
                else:
                    self.stack.append(val)

            elif op == "IMPORT_MODULE":
                names = instr.argument   # list of (name, alias) tuples
                for name, alias in names:
                    mod = _import_module(name)
                    store_as = alias if alias else name.split(".")[0]
                    self.current_frame().variables[store_as] = mod

            elif op == "IMPORT_FROM":
                module_name, names = instr.argument   # names: list of (attr, alias)
                mod = _import_module(module_name)
                for attr, alias in names:
                    store_as = alias if alias else attr
                    if attr == "*":
                        pub = getattr(mod, "__all__", None)
                        attrs = pub if pub else [a for a in dir(mod) if not a.startswith("_")]
                        for a in attrs:
                            self.current_frame().variables[a] = getattr(mod, a)
                    else:
                        self.current_frame().variables[store_as] = getattr(mod, attr)

            elif op == "DECLARE_GLOBAL":
                for name in instr.argument:
                    self.current_frame().variables.setdefault("__globals__", set())
                    if isinstance(self.current_frame().variables.get("__globals__"), set):
                        self.current_frame().variables["__globals__"].add(name)

            elif op == "DECLARE_NONLOCAL":
                pass

            elif op == "DELETE_VAR":
                name = instr.argument
                for frame in reversed(self.frames):
                    if name in frame.variables:
                        del frame.variables[name]
                        break

            elif op == "RAISE_EXCEPTION":
                exc = self.stack.pop()
                if exc is None:
                    raise RuntimeError("re-raise with no active exception")
                if isinstance(exc, type):
                    raise exc()
                if isinstance(exc, Exception):
                    raise exc
                raise RuntimeError(str(exc))

            elif op == "RAISE_ASSERTION":
                msg = self.stack.pop()
                raise AssertionError(str(msg) if msg is not None else "")

            elif op == "EXEC_TRY":
                node = instr.argument
                try:
                    sub = self._run_sub(node.body)
                    self.output.extend(sub.output)
                except Exception as caught:
                    handled = False
                    for handler in (node.handlers or []):
                        if handler.exc_type is None or isinstance(
                            caught,
                            self._resolve_exception_type(handler.exc_type)
                        ):
                            sub = self._run_sub(handler.body, extra_vars={
                                handler.var_name: caught
                            } if handler.var_name else {})
                            self.output.extend(sub.output)
                            handled = True
                            break
                    if not handled:
                        raise
                else:
                    if node.else_body:
                        sub = self._run_sub(node.else_body)
                        self.output.extend(sub.output)
                finally:
                    if node.finally_body:
                        sub = self._run_sub(node.finally_body)
                        self.output.extend(sub.output)

            elif op == "EXEC_WITH":
                node = instr.argument
                ctx_expr, var_name = node.items[0]
                ctx_instrs = self._compile_body([ctx_expr]
                    if not isinstance(ctx_expr, list) else ctx_expr)
                ctx_sub = VirtualMachine(ctx_instrs)
                ctx_sub.frames    = [self.frames[-1]]
                ctx_sub.functions = self.functions
                ctx_sub.classes   = self.classes
                ctx_sub._input_provider = self._input_provider
                ctx_sub.run()
                mgr = ctx_sub.stack[-1] if ctx_sub.stack else None
                if hasattr(mgr, '__enter__'):
                    val = mgr.__enter__()
                else:
                    val = mgr
                if var_name:
                    self.current_frame().variables[var_name] = val
                try:
                    sub = self._run_sub(node.body)
                    self.output.extend(sub.output)
                except Exception as e:
                    if hasattr(mgr, '__exit__'):
                        mgr.__exit__(type(e), e, None)
                    raise
                else:
                    if hasattr(mgr, '__exit__'):
                        mgr.__exit__(None, None, None)

            elif op == "YIELD_VALUE":
                val = self.stack.pop()
                self.output.append(self._fmt(val))

            elif op == "MAKE_LAMBDA":
                node = instr.argument
                captured = dict(self.current_frame().variables)
                vm_ref = self

                def _make_lambda(n, cap):
                    def _fn(*call_args):
                        new_frame = Frame()
                        new_frame.variables.update(cap)
                        for param, val in zip(n.params, call_args):
                            new_frame.variables[param] = val
                        for i, param in enumerate(n.params):
                            if param not in new_frame.variables and i in n.defaults:
                                dflt_instrs = vm_ref._compile_body([n.defaults[i]])
                                dflt_sub = VirtualMachine(dflt_instrs)
                                dflt_sub.frames = [Frame()]
                                dflt_sub.functions = vm_ref.functions
                                dflt_sub.classes   = vm_ref.classes
                                dflt_sub.run()
                                new_frame.variables[param] = (
                                    dflt_sub.stack[-1] if dflt_sub.stack else None
                                )
                        from compiler.bytecode import BytecodeGenerator, Instruction
                        from compiler.ast_nodes import Program, Return
                        body_stmts = [Return(n.body)] if not isinstance(n.body, list) else n.body
                        instrs = vm_ref._compile_body(body_stmts)
                        sub = VirtualMachine(instrs)
                        sub.frames = [new_frame]
                        sub.functions = vm_ref.functions
                        sub.classes   = vm_ref.classes
                        sub._input_provider = vm_ref._input_provider
                        sub.run()
                        return sub.stack[-1] if sub.stack else None
                    return _fn

                self.stack.append(_make_lambda(node, captured))

            elif op == "APPLY_DECORATOR":
                dec = self.stack.pop()
                fn  = self.stack.pop()
                if callable(dec):
                    self.stack.append(dec(fn))
                else:
                    self.stack.append(fn)

            elif op == "CALL_FUNCTION_KW":
                name, pos_count, kw_count = instr.argument
                kw_values = [self.stack.pop() for _ in range(kw_count)]
                kw_keys   = [self.stack.pop() for _ in range(kw_count)]
                pos_args  = [self.stack.pop() for _ in range(pos_count)]
                pos_args.reverse()
                kw_keys.reverse()
                kw_values.reverse()
                kwargs = dict(zip(kw_keys, kw_values))
                all_args = pos_args
                if name in self.functions:
                    func = self.functions[name]
                    params = func["params"]
                    new_frame = Frame()
                    for i, (param, val) in enumerate(zip(params, pos_args)):
                        new_frame.variables[param] = val
                    for param in params[len(pos_args):]:
                        if param in kwargs:
                            new_frame.variables[param] = kwargs[param]
                    self.frames.append(new_frame)
                    self.call_stack.append((self.instructions, ip + 1))
                    self.instructions = func["instructions"]
                    ip = 0
                    continue
                else:
                    ip = self._dispatch_call(name, pos_args, ip)
                    if ip == -1:
                        ip = 0
                    else:
                        ip += 1
                    continue

            ip += 1

        return "\n".join(str(x) for x in self.output)

    def _run_sub(self, stmts, extra_vars=None):
        """Execute a list of AST statements in a fresh sub-VM sharing state."""
        instrs = self._compile_body(stmts)
        sub = VirtualMachine(instrs)
        sub.frames    = [Frame()]
        if extra_vars:
            sub.frames[0].variables.update(extra_vars)
        for frame in self.frames:
            sub.frames[0].variables.update(frame.variables)
        sub.functions = self.functions
        sub.classes   = self.classes
        sub._input_provider = self._input_provider
        sub.run()
        return sub

    def _resolve_exception_type(self, exc_type_name):
        _exc_map = {
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "AttributeError": AttributeError,
            "NameError": NameError,
            "RuntimeError": RuntimeError,
            "StopIteration": StopIteration,
            "ZeroDivisionError": ZeroDivisionError,
            "FileNotFoundError": FileNotFoundError,
            "IOError": IOError,
            "OSError": OSError,
            "ImportError": ImportError,
            "NotImplementedError": NotImplementedError,
            "AssertionError": AssertionError,
            "OverflowError": OverflowError,
            "RecursionError": RecursionError,
            "MemoryError": MemoryError,
            "PermissionError": PermissionError,
            "TimeoutError": TimeoutError,
            "ArithmeticError": ArithmeticError,
            "LookupError": LookupError,
            "UnicodeError": UnicodeError,
            "UnicodeDecodeError": UnicodeDecodeError,
            "UnicodeEncodeError": UnicodeEncodeError,
            "SystemExit": SystemExit,
            "KeyboardInterrupt": KeyboardInterrupt,
            "GeneratorExit": GeneratorExit,
            "BaseException": BaseException,
        }
        if isinstance(exc_type_name, str):
            return _exc_map.get(exc_type_name, Exception)
        return Exception

    def _dispatch_call(self, name, args, ip):
        if name == "str":
            obj = args[0] if args else ""
            if isinstance(obj, dict) and "__class__" in obj:
                self.stack.append(self._instance_str(obj) or str(obj))
            else:
                self.stack.append(str(obj))
            return ip

        if name == "format":
            value = args[0]
            spec = args[1] if len(args) > 1 else ""
            self.stack.append(format(value, spec))
            return ip

        if name in ("int", "float", "bool", "abs", "round"):
            fn = _BUILTIN_CALLABLES[name]
            self.stack.append(fn(*args))
            return ip

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

        if name == "type":
            obj = args[0] if args else None
            if isinstance(obj, dict) and "__class__" in obj:
                self.stack.append(obj["__class__"])
            else:
                self.stack.append(type(obj))
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

        if name in self.classes:
            instance = {"__class__": name, "__attributes__": {}}
            init_node, init_class = self._find_method(name, "__init__")
            if init_node:
                init_instrs = self._compile_body(init_node.body)
                new_frame   = Frame()
                new_frame.variables["self"] = instance
                new_frame.variables["__current_class__"] = init_class or name
                for param, val in zip(init_node.params[1:], args):
                    new_frame.variables[param] = val
                sub_vm = VirtualMachine(init_instrs)
                sub_vm.frames   = [new_frame]
                sub_vm.functions = self.functions
                sub_vm.classes   = self.classes
                sub_vm._input_provider = self._input_provider
                sub_vm.run()
                self.output.extend(sub_vm.output)
            self.stack.append(instance)
            return ip

        if name in self.functions:
            ip = self._call_function(name, args, ip)
            return ip  

        var_val = None
        for frame in reversed(self.frames):
            if name in frame.variables:
                var_val = frame.variables[name]
                break
        if callable(var_val):
            try:
                self.stack.append(var_val(*args))
            except Exception as e:
                raise RuntimeError(f"Error calling '{name}': {e}") from e
            return ip

        if name in _BUILTIN_CALLABLES:
            self.stack.append(_BUILTIN_CALLABLES[name](*args))
            return ip

        import builtins as _builtins_ns
        _bi = getattr(_builtins_ns, name, None)
        if callable(_bi):
            self.stack.append(_bi(*args))
            return ip

        raise NameError(f"Unknown function or class: '{name}'")
