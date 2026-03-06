from compiler.ast_nodes import *


class Instruction:
    def __init__(self, opcode, argument=None):
        self.opcode = opcode
        self.argument = argument

    def __repr__(self):
        return f"{self.opcode}({self.argument!r})"


class BytecodeGenerator:
    def __init__(self):
        self.instructions = []
        # stacks of lists of instruction indices that need patching
        self.break_targets = []     # for BREAK inside loops
        self.continue_targets = []  # for CONTINUE inside loops
        self._counter = 0           # unique temp-variable counter

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def generate(self, node):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self._visit_unknown)
        return method(node)

    def _visit_unknown(self, node):
        raise NotImplementedError(
            f"BytecodeGenerator: no visitor for {type(node).__name__}"
        )

    def _fresh(self):
        self._counter += 1
        return self._counter

    # ------------------------------------------------------------------ #
    # Program
    # ------------------------------------------------------------------ #

    def visit_Program(self, node):
        for stmt in node.statements:
            self.generate(stmt)
        return self.instructions

    # ------------------------------------------------------------------ #
    # Literals
    # ------------------------------------------------------------------ #

    def visit_Number(self, node):
        self.instructions.append(Instruction("LOAD_CONST", node.value))

    def visit_Float(self, node):
        self.instructions.append(Instruction("LOAD_CONST", node.value))

    def visit_String(self, node):
        self.instructions.append(Instruction("LOAD_CONST", node.value))

    def visit_BoolLiteral(self, node):
        self.instructions.append(Instruction("LOAD_CONST", node.value))

    def visit_NoneLiteral(self, node):
        self.instructions.append(Instruction("LOAD_CONST", None))

    # ------------------------------------------------------------------ #
    # Variables
    # ------------------------------------------------------------------ #

    def visit_Variable(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.name))

    def visit_Assignment(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_VAR", node.name))

    def visit_AttributeAssignment(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_ATTR", node.attr))

    # ------------------------------------------------------------------ #
    # Operators
    # ------------------------------------------------------------------ #

    def visit_BinaryOp(self, node):
        self.generate(node.left)
        self.generate(node.right)
        op_map = {
            "+":  "ADD",
            "-":  "SUB",
            "*":  "MUL",
            "/":  "DIV",
            "%":  "MOD",
            "**": "POW",
            "//": "FLOORDIV",
        }
        self.instructions.append(Instruction(op_map[node.operator]))

    def visit_UnaryOp(self, node):
        self.generate(node.operand)
        if node.operator == "-":
            self.instructions.append(Instruction("UNARY_NEG"))
        elif node.operator == "not":
            self.instructions.append(Instruction("UNARY_NOT"))

    def visit_BoolOp(self, node):
        self.generate(node.left)
        self.generate(node.right)
        if node.operator == "and":
            self.instructions.append(Instruction("BINARY_AND"))
        else:
            self.instructions.append(Instruction("BINARY_OR"))

    def visit_Compare(self, node):
        self.generate(node.left)
        self.generate(node.right)
        self.instructions.append(Instruction("COMPARE", node.operator))

    # ------------------------------------------------------------------ #
    # Print
    # ------------------------------------------------------------------ #

    def visit_Print(self, node):
        for val in node.values:
            self.generate(val)
        self.instructions.append(Instruction("PRINT", len(node.values)))

    # ------------------------------------------------------------------ #
    # Control flow
    # ------------------------------------------------------------------ #

    def visit_IfStatement(self, node):
        self.generate(node.condition)

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        for stmt in node.body:
            self.generate(stmt)

        jump_end = len(self.instructions)
        self.instructions.append(Instruction("JUMP", None))

        self.instructions[jump_false].argument = len(self.instructions)

        for stmt in node.else_body:
            self.generate(stmt)

        self.instructions[jump_end].argument = len(self.instructions)

    def visit_WhileLoop(self, node):
        loop_start = len(self.instructions)

        self.generate(node.condition)

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        self.break_targets.append([])
        self.continue_targets.append([])

        for stmt in node.body:
            self.generate(stmt)

        # continue → jump back to condition re-check
        continue_target = len(self.instructions)
        for idx in self.continue_targets.pop():
            self.instructions[idx].argument = continue_target

        self.instructions.append(Instruction("JUMP", loop_start))
        self.instructions[jump_false].argument = len(self.instructions)

        for idx in self.break_targets.pop():
            self.instructions[idx].argument = len(self.instructions)

    def visit_Pass(self, node):
        pass  # no instructions needed

    def visit_Break(self, node):
        if not self.break_targets:
            raise SyntaxError("'break' outside loop")
        self.break_targets[-1].append(len(self.instructions))
        self.instructions.append(Instruction("JUMP", None))  # patched later

    def visit_Continue(self, node):
        if not self.continue_targets:
            raise SyntaxError("'continue' outside loop")
        self.continue_targets[-1].append(len(self.instructions))
        self.instructions.append(Instruction("JUMP", None))  # patched later

    # ------------------------------------------------------------------ #
    # Legacy range-only for loop (kept for backward compat)
    # ------------------------------------------------------------------ #

    def visit_ForLoop(self, node):
        self.generate(node.start)
        self.instructions.append(Instruction("STORE_VAR", node.var_name))

        loop_start = len(self.instructions)
        self.instructions.append(Instruction("LOAD_VAR", node.var_name))
        self.generate(node.end)
        self.instructions.append(Instruction("COMPARE", "<"))

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        self.break_targets.append([])
        self.continue_targets.append([])

        for stmt in node.body:
            self.generate(stmt)

        continue_target = len(self.instructions)
        for idx in self.continue_targets.pop():
            self.instructions[idx].argument = continue_target

        self.instructions.append(Instruction("LOAD_VAR", node.var_name))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", node.var_name))
        self.instructions.append(Instruction("JUMP", loop_start))

        self.instructions[jump_false].argument = len(self.instructions)
        for idx in self.break_targets.pop():
            self.instructions[idx].argument = len(self.instructions)

    # ------------------------------------------------------------------ #
    # ForInLoop  — for var in iterable / range
    # ------------------------------------------------------------------ #

    def visit_ForInLoop(self, node):
        uid = self._fresh()
        iter_var = f"__iter_{uid}__"
        idx_var  = f"__idx_{uid}__"

        if isinstance(node.iterable, RangeExpr):
            self._emit_range_for(node, iter_var, idx_var, uid)
        else:
            # General iterable: evaluate, store, iterate by index
            self.generate(node.iterable)
            self.instructions.append(Instruction("STORE_VAR", iter_var))
            self._emit_index_loop(node.var_name, iter_var, idx_var, node.body)

    def _emit_range_for(self, node, iter_var, idx_var, uid):
        """
        Compile  for var in range(start, stop[, step]):
        Into a step-based index loop using the range VM builtin.
        """
        r = node.iterable
        self.generate(r.start)
        self.generate(r.stop)
        if r.step is not None:
            self.generate(r.step)
            self.instructions.append(Instruction("CALL_FUNCTION", ("range", 3)))
        else:
            self.instructions.append(Instruction("CALL_FUNCTION", ("range", 2)))
        self.instructions.append(Instruction("STORE_VAR", iter_var))
        self._emit_index_loop(node.var_name, iter_var, idx_var, node.body)

    def _emit_index_loop(self, var_name, iter_var, idx_var, body):
        """
        Emit the while-index loop:
            idx = 0
            while idx < len(iter):
                var = iter[idx]   (or unpack if var_name is a list)
                <body>
                idx += 1
        """
        self.instructions.append(Instruction("LOAD_CONST", 0))
        self.instructions.append(Instruction("STORE_VAR", idx_var))

        loop_start = len(self.instructions)

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_VAR", iter_var))
        self.instructions.append(Instruction("CALL_FUNCTION", ("len", 1)))
        self.instructions.append(Instruction("COMPARE", "<"))

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        self.instructions.append(Instruction("LOAD_VAR", iter_var))
        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_INDEX"))

        if isinstance(var_name, list):
            # Tuple unpacking: e.g. for i, v in enumerate(...)
            self.instructions.append(Instruction("UNPACK_SEQUENCE", len(var_name)))
            for vn in var_name:
                self.instructions.append(Instruction("STORE_VAR", vn))
        else:
            self.instructions.append(Instruction("STORE_VAR", var_name))

        self.break_targets.append([])
        self.continue_targets.append([])

        for stmt in body:
            self.generate(stmt)

        continue_target = len(self.instructions)
        for idx in self.continue_targets.pop():
            self.instructions[idx].argument = continue_target

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", idx_var))
        self.instructions.append(Instruction("JUMP", loop_start))

        self.instructions[jump_false].argument = len(self.instructions)
        for idx in self.break_targets.pop():
            self.instructions[idx].argument = len(self.instructions)

    # ------------------------------------------------------------------ #
    # List comprehension
    # ------------------------------------------------------------------ #

    def visit_ListComprehension(self, node):
        uid = self._fresh()
        result_var = f"__comp_{uid}__"
        iter_var   = f"__citer_{uid}__"
        idx_var    = f"__cidx_{uid}__"

        # result = []
        self.instructions.append(Instruction("BUILD_LIST", 0))
        self.instructions.append(Instruction("STORE_VAR", result_var))

        # Evaluate iterable
        if isinstance(node.iterable, RangeExpr):
            r = node.iterable
            self.generate(r.start)
            self.generate(r.stop)
            if r.step is not None:
                self.generate(r.step)
                self.instructions.append(Instruction("CALL_FUNCTION", ("range", 3)))
            else:
                self.instructions.append(Instruction("CALL_FUNCTION", ("range", 2)))
        else:
            self.generate(node.iterable)
        self.instructions.append(Instruction("STORE_VAR", iter_var))

        # idx = 0
        self.instructions.append(Instruction("LOAD_CONST", 0))
        self.instructions.append(Instruction("STORE_VAR", idx_var))

        loop_start = len(self.instructions)

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_VAR", iter_var))
        self.instructions.append(Instruction("CALL_FUNCTION", ("len", 1)))
        self.instructions.append(Instruction("COMPARE", "<"))

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        # var = iter[idx]
        self.instructions.append(Instruction("LOAD_VAR", iter_var))
        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_INDEX"))
        self.instructions.append(Instruction("STORE_VAR", node.var_name))

        if node.condition is not None:
            self.generate(node.condition)
            skip_jump = len(self.instructions)
            self.instructions.append(Instruction("JUMP_IF_FALSE", None))

            # result.append(expr)
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("LIST_APPEND"))

            self.instructions[skip_jump].argument = len(self.instructions)
        else:
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("LIST_APPEND"))

        # idx += 1
        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", idx_var))
        self.instructions.append(Instruction("JUMP", loop_start))

        self.instructions[jump_false].argument = len(self.instructions)

        self.instructions.append(Instruction("LOAD_VAR", result_var))

    # ------------------------------------------------------------------ #
    # Functions
    # ------------------------------------------------------------------ #

    def visit_FunctionDef(self, node):
        self.instructions.append(Instruction("DEFINE_FUNCTION", node))

    def visit_FunctionCall(self, node):
        for arg in node.args:
            self.generate(arg)
        self.instructions.append(
            Instruction("CALL_FUNCTION", (node.name, len(node.args)))
        )

    def visit_Return(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("RETURN_VALUE"))

    # ------------------------------------------------------------------ #
    # Expression statement  (result is discarded)
    # ------------------------------------------------------------------ #

    def visit_ExprStatement(self, node):
        self.generate(node.expr)
        self.instructions.append(Instruction("POP_TOP"))

    # ------------------------------------------------------------------ #
    # Augmented assignments
    # ------------------------------------------------------------------ #

    _AUG_OP_MAP = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD", "**": "POW", "//": "FLOORDIV"}

    def visit_AugmentedAssignment(self, node):
        # name OP= value  →  name = name OP value
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.generate(node.value)
        self.instructions.append(Instruction(self._AUG_OP_MAP[node.operator]))
        self.instructions.append(Instruction("STORE_VAR", node.name))

    def visit_AttributeAugAssignment(self, node):
        # obj.attr OP= value  →  obj.attr = obj.attr OP value
        # STORE_ATTR pops: top=value, next=obj  → push obj first, then value
        uid = self._fresh()
        tmp_val = f"__augattr_{uid}__"
        # step 1: compute new value
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.instructions.append(Instruction("LOAD_ATTR", node.attr))
        self.generate(node.value)
        self.instructions.append(Instruction(self._AUG_OP_MAP[node.operator]))
        # step 2: save new value to temp (so we can push obj first)
        self.instructions.append(Instruction("STORE_VAR", tmp_val))
        # step 3: push obj, then value on top  (STORE_ATTR: pops value then obj)
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.instructions.append(Instruction("LOAD_VAR", tmp_val))
        self.instructions.append(Instruction("STORE_ATTR", node.attr))

    def visit_IndexAugAssignment(self, node):
        # name[index] OP= value  (uses temp vars to evaluate index once)
        uid = self._fresh()
        tmp_idx = f"__augidx_{uid}__"
        tmp_val = f"__augval_{uid}__"
        # compute and save the index
        self.generate(node.index)
        self.instructions.append(Instruction("STORE_VAR", tmp_idx))
        # load current element value
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.instructions.append(Instruction("LOAD_VAR", tmp_idx))
        self.instructions.append(Instruction("LOAD_INDEX"))
        # apply operator with rhs
        self.generate(node.value)
        self.instructions.append(Instruction(self._AUG_OP_MAP[node.operator]))
        # save new value to temp
        self.instructions.append(Instruction("STORE_VAR", tmp_val))
        # push obj, index, new_value in the order STORE_INDEX expects
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.instructions.append(Instruction("LOAD_VAR", tmp_idx))
        self.instructions.append(Instruction("LOAD_VAR", tmp_val))
        self.instructions.append(Instruction("STORE_INDEX"))

    # ------------------------------------------------------------------ #
    # Lists
    # ------------------------------------------------------------------ #

    def visit_ListLiteral(self, node):
        for element in node.elements:
            self.generate(element)
        self.instructions.append(Instruction("BUILD_LIST", len(node.elements)))

    def visit_ListAccess(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.generate(node.index)
        self.instructions.append(Instruction("LOAD_INDEX"))

    def visit_IndexAssignment(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.generate(node.index)
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_INDEX"))

    # ------------------------------------------------------------------ #
    # Classes and OOP
    # ------------------------------------------------------------------ #

    def visit_ClassDef(self, node):
        self.instructions.append(Instruction("DEFINE_CLASS", node))

    def visit_AttributeAccess(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.instructions.append(Instruction("LOAD_ATTR", node.attr))

    def visit_MethodCall(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        for arg in node.args:
            self.generate(arg)
        self.instructions.append(
            Instruction("CALL_METHOD", (node.method, len(node.args)))
        )

    def visit_SuperMethodCall(self, node):
        for arg in node.args:
            self.generate(arg)
        self.instructions.append(
            Instruction("CALL_SUPER_METHOD", (node.method, len(node.args)))
        )

    def visit_MethodCallExpr(self, node):
        """Method call on an arbitrary expression (string literal, call result, etc.)"""
        self.generate(node.obj_expr)   
        for arg in node.args:
            self.generate(arg)
        self.instructions.append(
            Instruction("CALL_METHOD", (node.method, len(node.args)))
        )

    def visit_AttributeAccessExpr(self, node):
        """Attribute access on an arbitrary expression."""
        self.generate(node.obj_expr)
        self.instructions.append(Instruction("LOAD_ATTR", node.attr))

    def visit_ExprSubscript(self, node):
        """Subscript on arbitrary expression: expr[index]  e.g. self.items[i]"""
        self.generate(node.obj_expr)
        self.generate(node.index)
        self.instructions.append(Instruction("LOAD_INDEX"))

    def visit_TupleLiteral(self, node):
        for elem in node.elements:
            self.generate(elem)
        self.instructions.append(Instruction("BUILD_TUPLE", len(node.elements)))

    def visit_UnpackAssignment(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("UNPACK_SEQUENCE", len(node.names)))
        for name in node.names:
            self.instructions.append(Instruction("STORE_VAR", name))

    def visit_ChainedIndexAssignment(self, node):
        # board[row][col] = v  →  load board, load row, LOAD_INDEX (gets row-list),
        # then load col, load v, STORE_INDEX  (mutates the row-list in place)
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        for idx in node.indices[:-1]:
            self.generate(idx)
            self.instructions.append(Instruction("LOAD_INDEX"))
        self.generate(node.indices[-1])
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_INDEX"))
