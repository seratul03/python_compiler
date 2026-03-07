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
        self.break_targets = []     
        self.continue_targets = []  
        self._counter = 0           


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

    def visit_Program(self, node):
        for stmt in node.statements:
            self.generate(stmt)
        return self.instructions

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

    def visit_Variable(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.name))

    def visit_Assignment(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_VAR", node.name))

    def visit_AttributeAssignment(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_ATTR", node.attr))

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

    def visit_Print(self, node):
        for val in node.values:
            self.generate(val)
        self.instructions.append(Instruction("PRINT", len(node.values)))

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


        continue_target = len(self.instructions)
        for idx in self.continue_targets.pop():
            self.instructions[idx].argument = continue_target

        self.instructions.append(Instruction("JUMP", loop_start))
        self.instructions[jump_false].argument = len(self.instructions)

        for idx in self.break_targets.pop():
            self.instructions[idx].argument = len(self.instructions)

    def visit_Pass(self, node):
        pass  

    def visit_Break(self, node):
        if not self.break_targets:
            raise SyntaxError("'break' outside loop")
        self.break_targets[-1].append(len(self.instructions))
        self.instructions.append(Instruction("JUMP", None))  

    def visit_Continue(self, node):
        if not self.continue_targets:
            raise SyntaxError("'continue' outside loop")
        self.continue_targets[-1].append(len(self.instructions))
        self.instructions.append(Instruction("JUMP", None))  

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

    def visit_ForInLoop(self, node):
        uid = self._fresh()
        iter_var = f"__iter_{uid}__"
        idx_var  = f"__idx_{uid}__"

        if isinstance(node.iterable, RangeExpr):
            self._emit_range_for(node, iter_var, idx_var, uid)
        else:
            self.generate(node.iterable)
            self.instructions.append(Instruction("STORE_VAR", iter_var))
            self._emit_index_loop(node.var_name, iter_var, idx_var, node.body)

    def _emit_range_for(self, node, iter_var, idx_var, uid):
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

    def visit_ListComprehension(self, node):
        uid = self._fresh()
        result_var = f"__comp_{uid}__"
        iter_var   = f"__citer_{uid}__"
        idx_var    = f"__cidx_{uid}__"

        self.instructions.append(Instruction("BUILD_LIST", 0))
        self.instructions.append(Instruction("STORE_VAR", result_var))

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
        self.instructions.append(Instruction("STORE_VAR", node.var_name))

        if node.condition is not None:
            self.generate(node.condition)
            skip_jump = len(self.instructions)
            self.instructions.append(Instruction("JUMP_IF_FALSE", None))

            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("LIST_APPEND"))

            self.instructions[skip_jump].argument = len(self.instructions)
        else:
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("LIST_APPEND"))

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", idx_var))
        self.instructions.append(Instruction("JUMP", loop_start))

        self.instructions[jump_false].argument = len(self.instructions)

        self.instructions.append(Instruction("LOAD_VAR", result_var))

    def visit_FunctionDef(self, node):
        self.instructions.append(Instruction("DEFINE_FUNCTION", node))

    def visit_FunctionCall(self, node):
        has_special = any(
            type(a).__name__ in ("KeywordArg", "Starred", "DoubleStarred")
            for a in node.args
        )
        if has_special:
            self._emit_call_ex(node.name, node.args)
        else:
            for arg in node.args:
                self.generate(arg)
            self.instructions.append(
                Instruction("CALL_FUNCTION", (node.name, len(node.args)))
            )

    def _emit_call_ex(self, name, args):
        """Emit a function call that may contain keyword/starred args."""
        pos_parts = []
        kw_parts = []
        star_parts = []
        dstar_parts = []
        for a in args:
            t = type(a).__name__
            if t == "KeywordArg":
                kw_parts.append(a)
            elif t == "Starred":
                star_parts.append(a)
            elif t == "DoubleStarred":
                dstar_parts.append(a)
            else:
                pos_parts.append(a)
        for a in pos_parts:
            self.generate(a)
        for s in star_parts:
            self.generate(s.value)
            self.instructions.append(Instruction("UNPACK_STARRED"))
        for a in dstar_parts:
            self.generate(a.value)
        for kw in kw_parts:
            self.instructions.append(Instruction("LOAD_CONST", kw.name))
            self.generate(kw.value)
        n_kw = len(kw_parts) + len(dstar_parts)
        self.instructions.append(
            Instruction("CALL_FUNCTION_KW", (name, len(pos_parts) + len(star_parts), n_kw))
        )

    def visit_FStringExpr(self, node):
        if not node.parts:
            self.instructions.append(Instruction("LOAD_CONST", ""))
            return

        def _emit_part(part):
            if isinstance(part, String):
                self.instructions.append(Instruction("LOAD_CONST", part.value))
            else:
                expr_node, fmt_spec = part
                self.generate(expr_node)
                if fmt_spec:
                    self.instructions.append(Instruction("LOAD_CONST", fmt_spec))
                    self.instructions.append(Instruction("CALL_FUNCTION", ("format", 2)))
                else:
                    self.instructions.append(Instruction("CALL_FUNCTION", ("str", 1)))

        _emit_part(node.parts[0])
        for part in node.parts[1:]:
            _emit_part(part)
            self.instructions.append(Instruction("ADD"))

    def visit_Return(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("RETURN_VALUE"))

    def visit_ExprStatement(self, node):
        self.generate(node.expr)
        self.instructions.append(Instruction("POP_TOP"))

    _AUG_OP_MAP = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD", "**": "POW", "//": "FLOORDIV"}

    def visit_AugmentedAssignment(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.generate(node.value)
        self.instructions.append(Instruction(self._AUG_OP_MAP[node.operator]))
        self.instructions.append(Instruction("STORE_VAR", node.name))

    def visit_AttributeAugAssignment(self, node):
        uid = self._fresh()
        tmp_val = f"__augattr_{uid}__"
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.instructions.append(Instruction("LOAD_ATTR", node.attr))
        self.generate(node.value)
        self.instructions.append(Instruction(self._AUG_OP_MAP[node.operator]))
        self.instructions.append(Instruction("STORE_VAR", tmp_val))
        self.instructions.append(Instruction("LOAD_VAR", node.obj))
        self.instructions.append(Instruction("LOAD_VAR", tmp_val))
        self.instructions.append(Instruction("STORE_ATTR", node.attr))

    def visit_IndexAugAssignment(self, node):
        uid = self._fresh()
        tmp_idx = f"__augidx_{uid}__"
        tmp_val = f"__augval_{uid}__"
        self.generate(node.index)
        self.instructions.append(Instruction("STORE_VAR", tmp_idx))
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.instructions.append(Instruction("LOAD_VAR", tmp_idx))
        self.instructions.append(Instruction("LOAD_INDEX"))
        self.generate(node.value)
        self.instructions.append(Instruction(self._AUG_OP_MAP[node.operator]))
        self.instructions.append(Instruction("STORE_VAR", tmp_val))
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        self.instructions.append(Instruction("LOAD_VAR", tmp_idx))
        self.instructions.append(Instruction("LOAD_VAR", tmp_val))
        self.instructions.append(Instruction("STORE_INDEX"))

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
            Instruction("CALL_SUPER_METHOD", (node.method, len(node.args), getattr(node, 'explicit_class', None)))
        )

    def visit_MethodCallExpr(self, node):
        self.generate(node.obj_expr)   
        for arg in node.args:
            self.generate(arg)
        self.instructions.append(
            Instruction("CALL_METHOD", (node.method, len(node.args)))
        )

    def visit_AttributeAccessExpr(self, node):
        self.generate(node.obj_expr)
        self.instructions.append(Instruction("LOAD_ATTR", node.attr))

    def visit_ExprSubscript(self, node):
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
        self.instructions.append(Instruction("LOAD_VAR", node.name))
        for idx in node.indices[:-1]:
            self.generate(idx)
            self.instructions.append(Instruction("LOAD_INDEX"))
        self.generate(node.indices[-1])
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_INDEX"))

    _AUG_OP_MAP_BITWISE = {
        "&": "BITWISE_AND", "|": "BITWISE_OR", "^": "BITWISE_XOR",
        "<<": "BITWISE_LSHIFT", ">>": "BITWISE_RSHIFT",
    }

    def visit_BitwiseOp(self, node):
        self.generate(node.left)
        self.generate(node.right)
        op_map = {
            "&":  "BITWISE_AND",
            "|":  "BITWISE_OR",
            "^":  "BITWISE_XOR",
            "<<": "BITWISE_LSHIFT",
            ">>": "BITWISE_RSHIFT",
        }
        self.instructions.append(Instruction(op_map[node.operator]))

    def visit_UnaryBitNot(self, node):
        self.generate(node.operand)
        self.instructions.append(Instruction("UNARY_BITNOT"))

    def visit_EllipsisNode(self, node):
        self.instructions.append(Instruction("LOAD_CONST", ...))

    def visit_WalrusExpr(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("DUP_TOP"))
        self.instructions.append(Instruction("STORE_VAR", node.name))

    def visit_IfExpr(self, node):
        self.generate(node.condition)
        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))
        self.generate(node.body)
        jump_end = len(self.instructions)
        self.instructions.append(Instruction("JUMP", None))
        self.instructions[jump_false].argument = len(self.instructions)
        self.generate(node.orelse)
        self.instructions[jump_end].argument = len(self.instructions)

    def visit_Import(self, node):
        self.instructions.append(Instruction("IMPORT_MODULE", node.names))

    def visit_ImportFrom(self, node):
        self.instructions.append(Instruction("IMPORT_FROM", (node.module, node.names)))

    def visit_GlobalStatement(self, node):
        self.instructions.append(Instruction("DECLARE_GLOBAL", node.names))

    def visit_NonlocalStatement(self, node):
        self.instructions.append(Instruction("DECLARE_NONLOCAL", node.names))

    def visit_DeleteStatement(self, node):
        for target in node.targets:
            if hasattr(target, 'name') and not hasattr(target, 'index'):
                self.instructions.append(Instruction("DELETE_VAR", target.name))
            else:
                pass

    def visit_RaiseStatement(self, node):
        if node.exc is not None:
            self.generate(node.exc)
        else:
            self.instructions.append(Instruction("LOAD_CONST", None))
        self.instructions.append(Instruction("RAISE_EXCEPTION"))

    def visit_Assert(self, node):
        self.generate(node.condition)
        jump_ok = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_TRUE", None))
        if node.message is not None:
            self.generate(node.message)
        else:
            self.instructions.append(Instruction("LOAD_CONST", "AssertionError"))
        self.instructions.append(Instruction("RAISE_ASSERTION"))
        self.instructions[jump_ok].argument = len(self.instructions)

    def visit_TryExcept(self, node):
        self.instructions.append(Instruction("EXEC_TRY", node))

    def visit_WithStatement(self, node):
        self.instructions.append(Instruction("EXEC_WITH", node))

    def visit_YieldExpr(self, node):
        if node.value is not None:
            self.generate(node.value)
        else:
            self.instructions.append(Instruction("LOAD_CONST", None))
        self.instructions.append(Instruction("YIELD_VALUE"))

    def visit_LambdaExpr(self, node):
        self.instructions.append(Instruction("MAKE_LAMBDA", node))

    def visit_Decorated(self, node):
        self.generate(node.node)
        for dec in reversed(node.decorators):
            self.generate(dec)
            self.instructions.append(Instruction("APPLY_DECORATOR"))

    def visit_DictLiteral(self, node):
        for k, v in zip(node.keys, node.values):
            if k is None:
                self.generate(v.value)  
                self.instructions.append(Instruction("DICT_SPREAD"))
            else:
                self.generate(k)
                self.generate(v)
        self.instructions.append(Instruction("BUILD_DICT", len(node.keys)))

    def visit_SetLiteral(self, node):
        for elem in node.elements:
            self.generate(elem)
        self.instructions.append(Instruction("BUILD_SET", len(node.elements)))

    def visit_Slice(self, node):
        if node.start is not None:
            self.generate(node.start)
        else:
            self.instructions.append(Instruction("LOAD_CONST", None))
        if node.stop is not None:
            self.generate(node.stop)
        else:
            self.instructions.append(Instruction("LOAD_CONST", None))
        if node.step is not None:
            self.generate(node.step)
        else:
            self.instructions.append(Instruction("LOAD_CONST", None))
        self.instructions.append(Instruction("BUILD_SLICE"))

    def visit_Starred(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("UNPACK_STARRED"))

    def visit_DoubleStarred(self, node):
        self.generate(node.value)

    def visit_KeywordArg(self, node):
        self.generate(node.value)

    def visit_DictComprehension(self, node):
        uid = self._fresh()
        result_var = f"__dcomp_{uid}__"
        iter_var   = f"__dciter_{uid}__"
        idx_var    = f"__dcidx_{uid}__"

        self.instructions.append(Instruction("BUILD_DICT", 0))
        self.instructions.append(Instruction("STORE_VAR", result_var))

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
        self.instructions.append(Instruction("STORE_VAR", node.var_name))

        if node.condition is not None:
            self.generate(node.condition)
            skip = len(self.instructions)
            self.instructions.append(Instruction("JUMP_IF_FALSE", None))
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.key_expr)
            self.generate(node.val_expr)
            self.instructions.append(Instruction("DICT_SET_ITEM"))
            self.instructions[skip].argument = len(self.instructions)
        else:
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.key_expr)
            self.generate(node.val_expr)
            self.instructions.append(Instruction("DICT_SET_ITEM"))

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", idx_var))
        self.instructions.append(Instruction("JUMP", loop_start))
        self.instructions[jump_false].argument = len(self.instructions)
        self.instructions.append(Instruction("LOAD_VAR", result_var))

    def visit_SetComprehension(self, node):
        uid = self._fresh()
        result_var = f"__scomp_{uid}__"
        iter_var   = f"__sciter_{uid}__"
        idx_var    = f"__scidx_{uid}__"

        self.instructions.append(Instruction("BUILD_SET", 0))
        self.instructions.append(Instruction("STORE_VAR", result_var))

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
        self.instructions.append(Instruction("STORE_VAR", node.var_name))

        if node.condition is not None:
            self.generate(node.condition)
            skip = len(self.instructions)
            self.instructions.append(Instruction("JUMP_IF_FALSE", None))
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("SET_ADD"))
            self.instructions[skip].argument = len(self.instructions)
        else:
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("SET_ADD"))

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", idx_var))
        self.instructions.append(Instruction("JUMP", loop_start))
        self.instructions[jump_false].argument = len(self.instructions)
        self.instructions.append(Instruction("LOAD_VAR", result_var))

    def visit_GeneratorExpr(self, node):
        uid = self._fresh()
        result_var = f"__gexpr_{uid}__"
        iter_var   = f"__giter_{uid}__"
        idx_var    = f"__gidx_{uid}__"

        self.instructions.append(Instruction("BUILD_LIST", 0))
        self.instructions.append(Instruction("STORE_VAR", result_var))

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
        self.instructions.append(Instruction("STORE_VAR", node.var_name))

        if node.condition is not None:
            self.generate(node.condition)
            skip = len(self.instructions)
            self.instructions.append(Instruction("JUMP_IF_FALSE", None))
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("LIST_APPEND"))
            self.instructions[skip].argument = len(self.instructions)
        else:
            self.instructions.append(Instruction("LOAD_VAR", result_var))
            self.generate(node.expr)
            self.instructions.append(Instruction("LIST_APPEND"))

        self.instructions.append(Instruction("LOAD_VAR", idx_var))
        self.instructions.append(Instruction("LOAD_CONST", 1))
        self.instructions.append(Instruction("ADD"))
        self.instructions.append(Instruction("STORE_VAR", idx_var))
        self.instructions.append(Instruction("JUMP", loop_start))
        self.instructions[jump_false].argument = len(self.instructions)
        self.instructions.append(Instruction("LOAD_VAR", result_var))



