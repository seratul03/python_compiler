"""
JIT Compiler — Threshold-based method JIT for the custom VM.

Strategy
--------
1. The VM counts every call to each user-defined function.
2. Once a function reaches JIT_THRESHOLD calls, its stored FunctionDef AST
   node is transpiled to valid Python source by PythonCodeGen.
3. Python's built-in compile() + exec() turn that source into a real callable.
4. The callable is cached; future calls to that function skip the VM's
   interpreter dispatch loop entirely, running at CPython native speed.
5. If transpilation or runtime execution ever fails, the VM falls back to
   interpretation transparently.

Extension points (described at the bottom of this file):
  - Type-specialised recompilation (inline caches)
  - Back-edge tracing for hot loops
  - Exposing JIT stats in the web UI
"""

# ── tuneable ────────────────────────────────────────────────────────────────
JIT_THRESHOLD = 10   # calls before a function is JIT-compiled


# ============================================================================
# Internal sentinel
# ============================================================================

class _Untranslatable(Exception):
    """Raised by PythonCodeGen when it encounters a node it cannot translate."""


# ============================================================================
# PythonCodeGen  —  AST → Python source
# ============================================================================

class PythonCodeGen:
    """
    Walks the compiler's AST and emits syntactically-valid Python source.

    Only the nodes that appear inside function bodies are handled.  If an
    unsupported node is encountered (e.g. class instantiation, super() calls)
    _Untranslatable is raised and the JIT falls back to the interpreter.
    """

    def __init__(self):
        self._indent = 0          # current indentation level (1 = function body)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def emit_function(self, func_def):
        """
        Translate a FunctionDef AST node to Python source.

        Returns (source: str, ok: bool).
        ok=False means the function contains untranslatable nodes — the caller
        should fall back to the interpreter and NOT retry JIT compilation.
        """
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

    # ------------------------------------------------------------------ #
    # Statement translators  (return list[str] of indented lines)
    # ------------------------------------------------------------------ #

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
            # __jit_print__ is injected into the exec namespace by JITCompiler
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
            # expression-statement  (call result discarded)
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
        # Legacy range-based ForLoop node
        start = self._expr(node.start)
        end   = self._expr(node.end)
        lines = [self._ind(f"for {node.var_name} in range({start}, {end}):")]
        self._indent += 1
        for s in node.body:
            lines.extend(self._stmt(s))
        self._indent -= 1
        return lines

    # ------------------------------------------------------------------ #
    # Expression translators  (return inline str)
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _ind(self, text):
        return "    " * self._indent + text


# ============================================================================
# JITCompiler  —  profile, compile, cache
# ============================================================================

class JITCompiler:
    """
    Threshold-based method JIT.

    The VM must:
      1. Store the FunctionDef AST node in self.functions[name]["node"].
      2. Call jit.record_call(name) before every user-function invocation.
      3. Check jit.try_get_compiled(name) — if not None, call directly.
      4. Otherwise, if jit.should_compile(name), call jit.try_compile(...).

    See the bottom of this file for optional extensions.
    """

    def __init__(self, threshold=JIT_THRESHOLD):
        self.threshold   = threshold
        self._call_counts = {}   # func_name → int
        # _cache value is either a callable (success) or False (translation failed)
        self._cache       = {}   # func_name → callable | False

        self._codegen = PythonCodeGen()

        # Public stats — can be surfaced in the web UI
        self.stats = {
            "compiled": [],   # function names successfully JIT-compiled
            "failed":   [],   # function names that could not be compiled
            "counts":   {},   # func_name → call count at time of compilation
        }

    # ------------------------------------------------------------------ #
    # Profiling helpers
    # ------------------------------------------------------------------ #

    def record_call(self, func_name):
        """Increment and return the new call count for func_name."""
        n = self._call_counts.get(func_name, 0) + 1
        self._call_counts[func_name] = n
        return n

    def should_compile(self, func_name):
        """True when the threshold is reached and no cache entry exists yet."""
        return (
            self._call_counts.get(func_name, 0) >= self.threshold
            and func_name not in self._cache
        )

    # ------------------------------------------------------------------ #
    # Compilation
    # ------------------------------------------------------------------ #

    def try_compile(self, func_name, func_def_node, builtins_ns):
        """
        Attempt to JIT-compile func_def_node.

        builtins_ns  —  dict passed as the exec() global namespace.
                        Must include 'range', 'len', 'int', 'float', 'str',
                        'bool', 'abs', 'round', 'sorted', 'sum', 'min', 'max',
                        and '__jit_print__'.

        Returns the compiled callable on success, or None on any failure.
        On failure, marks the function so it is never retried.
        """
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
            exec(code_obj, ns)  # noqa: S102 — controlled namespace, no user input
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
        self._cache[func_name] = False   # sentinel: don't retry
        self.stats["failed"].append(func_name)

    # ------------------------------------------------------------------ #
    # Cache lookup
    # ------------------------------------------------------------------ #

    def try_get_compiled(self, func_name):
        """
        Returns the cached callable if JIT succeeded, otherwise None.
        (Also returns None when compilation previously failed — caller uses
        the interpreter without retrying JIT.)
        """
        result = self._cache.get(func_name)
        return result if callable(result) else None

    def get_call_count(self, func_name):
        return self._call_counts.get(func_name, 0)


# ============================================================================
# EXTENSION NOTES
# ============================================================================
#
# 1. TYPE-SPECIALISED RECOMPILATION
#    ─────────────────────────────
#    Track the Python type of each argument at every call site:
#
#        self._type_profile[func_name].append(tuple(type(a) for a in args))
#
#    After N calls, check if all observed argument tuples are the same type
#    signature.  If so, generate a specialised version with hardcoded type
#    annotations, letting CPython's optimiser eliminate dynamic dispatch.
#    Use a guard before calling:
#
#        if tuple(type(a) for a in args) != expected_sig:
#            deoptimize(func_name)   # fall back to interpreter, clear cache
#
# 2. BACK-EDGE TRACING (loop JIT)
#    ─────────────────────────────
#    In vm.py's run() loop, detect when a JUMP target is less than the
#    current ip  (a back-edge / loop):
#
#        if op == "JUMP" and instr.argument <= ip:
#            self._back_edge_counts[(instr.argument, ip)] += 1
#            if self._back_edge_counts[...] >= LOOP_THRESHOLD:
#                # record the bytecode slice [instr.argument .. ip]
#                # transpile it to a Python while-loop body
#                # compile and substitute
#
#    This "hot loop" detection is the classic tracing JIT approach used
#    by PyPy and LuaJIT.
#
# 3. INLINE CACHES
#    ─────────────
#    For LOAD_ATTR / CALL_METHOD, record which class name was seen at each
#    call site.  When the same class is always used, emit direct Python
#    attribute access instead of the generic VM lookup, eliminating the
#    inheritance-chain walk in _find_method().
#
# 4. EXPOSE STATS IN THE WEB UI
#    ───────────────────────────
#    In execution/runner.py, include vm.jit.stats in the JSON response
#    alongside the existing "ast", "bytecode", "cfg" debug information.
#    Then render it in templates/index.html as a "JIT" panel showing which
#    functions were compiled, how many times they were called, and which
#    fell back to interpretation.
