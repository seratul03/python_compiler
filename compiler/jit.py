JIT_THRESHOLD = 10
class _Untranslatable(Exception):
    """Raised by PythonCodeGen when it encounters a node it cannot translate."""

class PythonCodeGen:
    def __init__(self):
        self._indent = 0
    def emit_function(self, func_def):
        self._indent = 1
        body_lines = []
        try:
            for stmt in func_def.body:
                body_lines.extend(self._stmt(stmt))
        except _Untranslatable:
            return None, False

        if not body_lines:
            body_lines = ["    pass"]

        params = ", ".join(func_def.params)
        header = f"def {func_def.name}({params}):"
        return header + "\n" + "\n".join(body_lines), True

    def _stmt(self, node):
        from compiler.ast_nodes import (
            Assignment, AugmentedAssignment, Return,
            IfStatement, WhileLoop, ForInLoop, ForLoop,
            Print, Break, Continue,
            FunctionCall, IndexAssignment, AttributeAssignment,
            AttributeAugAssignment, IndexAugAssignment,
        )
        t = type(node)

        if t is Assignment:
            return [self._ind(f"{node.name} = {self._expr(node.value)}")]

        if t is AugmentedAssignment:
            return [self._ind(f"{node.name} {node.operator}= {self._expr(node.value)}")]

        if t is AttributeAugAssignment:
            obj = node.obj if isinstance(node.obj, str) else self._expr(node.obj)
            return [self._ind(f"{obj}.{node.attr} {node.operator}= {self._expr(node.value)}")]

        if t is IndexAugAssignment:
            return [self._ind(
                f"{node.name}[{self._expr(node.index)}] "
                f"{node.operator}= {self._expr(node.value)}"
            )]

        if t is IndexAssignment:
            return [self._ind(
                f"{node.name}[{self._expr(node.index)}] = {self._expr(node.value)}"
            )]

        if t is AttributeAssignment:
            obj = node.obj if isinstance(node.obj, str) else self._expr(node.obj)
            return [self._ind(f"{obj}.{node.attr} = {self._expr(node.value)}")]

        if t is Return:
            val = self._expr(node.value) if node.value is not None else "None"
            return [self._ind(f"return {val}")]

        if t is Print:
            args_src = ", ".join(self._expr(v) for v in node.values)
            return [self._ind(f"__jit_print__({args_src})")]

        if t is Break:
            return [self._ind("break")]

        if t is Continue:
            return [self._ind("continue")]

        if t is IfStatement:
            return self._if_stmt(node)

        if t is WhileLoop:
            return self._while_stmt(node)

        if t is ForInLoop:
            return self._for_in_stmt(node)

        if t is ForLoop:
            return self._for_stmt(node)

        if t is FunctionCall:
            return [self._ind(self._expr(node))]

        raise _Untranslatable(f"Unsupported statement: {type(node).__name__}")

    def _if_stmt(self, node):
        lines = [self._ind(f"if {self._expr(node.condition)}:")]
        self._indent += 1
        for s in node.body:
            lines.extend(self._stmt(s))
        self._indent -= 1
        if node.else_body:
            lines.append(self._ind("else:"))
            self._indent += 1
            for s in node.else_body:
                lines.extend(self._stmt(s))
            self._indent -= 1
        return lines

    def _while_stmt(self, node):
        lines = [self._ind(f"while {self._expr(node.condition)}:")]
        self._indent += 1
        for s in node.body:
            lines.extend(self._stmt(s))
        self._indent -= 1
        return lines

    def _for_in_stmt(self, node):
        lines = [self._ind(f"for {node.var_name} in {self._expr(node.iterable)}:")]
        self._indent += 1
        for s in node.body:
            lines.extend(self._stmt(s))
        self._indent -= 1
        return lines

    def _for_stmt(self, node):
        start = self._expr(node.start)
        end   = self._expr(node.end)
        lines = [self._ind(f"for {node.var_name} in range({start}, {end}):")]
        self._indent += 1
        for s in node.body:
            lines.extend(self._stmt(s))
        self._indent -= 1
        return lines

    def _expr(self, node):
        from compiler.ast_nodes import (
            Number, Float, String, BoolLiteral, NoneLiteral,
            Variable, BinaryOp, UnaryOp, Compare, BoolOp,
            FunctionCall, ListLiteral, ListAccess,
            AttributeAccess, MethodCall, MethodCallExpr,
            RangeExpr, ListComprehension,
        )
        t = type(node)

        if t is Number:
            return str(node.value)
        if t is Float:
            return str(node.value)
        if t is String:
            return repr(node.value)
        if t is BoolLiteral:
            return "True" if node.value else "False"
        if t is NoneLiteral:
            return "None"

        if t is Variable:
            return node.name

        if t is BinaryOp:
            return f"({self._expr(node.left)} {node.operator} {self._expr(node.right)})"
        if t is UnaryOp:
            return f"({node.operator}{self._expr(node.operand)})"
        if t is Compare:
            return f"({self._expr(node.left)} {node.operator} {self._expr(node.right)})"
        if t is BoolOp:
            return f"({self._expr(node.left)} {node.operator} {self._expr(node.right)})"

        if t is FunctionCall:
            args = ", ".join(self._expr(a) for a in node.args)
            return f"{node.name}({args})"

        if t is ListLiteral:
            elems = ", ".join(self._expr(e) for e in node.elements)
            return f"[{elems}]"
        if t is ListAccess:
            return f"{node.name}[{self._expr(node.index)}]"

        if t is AttributeAccess:
            obj = node.obj if isinstance(node.obj, str) else self._expr(node.obj)
            return f"{obj}.{node.attr}"
        if t is MethodCall:
            obj  = node.obj if isinstance(node.obj, str) else self._expr(node.obj)
            args = ", ".join(self._expr(a) for a in node.args)
            return f"{obj}.{node.method}({args})"
        if t is MethodCallExpr:
            args = ", ".join(self._expr(a) for a in node.args)
            return f"{self._expr(node.obj_expr)}.{node.method}({args})"

        if t is RangeExpr:
            parts = [self._expr(node.start), self._expr(node.stop)]
            if node.step is not None:
                parts.append(self._expr(node.step))
            return f"range({', '.join(parts)})"

        if t is ListComprehension:
            expr_s = self._expr(node.expr)
            it_s   = self._expr(node.iterable)
            cond_s = f" if {self._expr(node.condition)}" if node.condition else ""
            return f"[{expr_s} for {node.var_name} in {it_s}{cond_s}]"

        raise _Untranslatable(f"Unsupported expression: {type(node).__name__}")

    def _ind(self, text):
        return "    " * self._indent + text

class JITCompiler:
    def __init__(self, threshold=JIT_THRESHOLD):
        self.threshold   = threshold
        self._call_counts = {}
        self._cache       = {} 

        self._codegen = PythonCodeGen()

        self.stats = {
            "compiled": [],  
            "failed":   [],  
            "counts":   {},  
        }

    def record_call(self, func_name):
        n = self._call_counts.get(func_name, 0) + 1
        self._call_counts[func_name] = n
        return n

    def should_compile(self, func_name):
        return (
            self._call_counts.get(func_name, 0) >= self.threshold
            and func_name not in self._cache
        )

    def try_compile(self, func_name, func_def_node, builtins_ns):
        source, ok = self._codegen.emit_function(func_def_node)
        if not ok:
            self._mark_failed(func_name)
            return None

        try:
            code_obj = compile(source, f"<jit:{func_name}>", "exec")
        except SyntaxError:
            self._mark_failed(func_name)
            return None

        ns = dict(builtins_ns)
        try:
            exec(code_obj, ns)
        except Exception:
            self._mark_failed(func_name)
            return None

        fn = ns.get(func_name)
        if not callable(fn):
            self._mark_failed(func_name)
            return None

        self._cache[func_name] = fn
        self.stats["compiled"].append(func_name)
        self.stats["counts"][func_name] = self._call_counts[func_name]
        return fn

    def _mark_failed(self, func_name):
        self._cache[func_name] = False 
        self.stats["failed"].append(func_name)


    def try_get_compiled(self, func_name):
        result = self._cache.get(func_name)
        return result if callable(result) else None

    def get_call_count(self, func_name):
        return self._call_counts.get(func_name, 0)