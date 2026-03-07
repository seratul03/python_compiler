class SemanticError(Exception):
    pass


BUILTIN_NAMES = {
    "len", "input", "int", "float", "str", "bool", "abs", "round",
    "range", "list", "tuple", "set", "dict", "map", "enumerate",
    "zip", "sum", "min", "max", "sorted", "reversed", "print",
    "isinstance", "hasattr", "getattr", "setattr", "type", "format",
    "True", "False", "None", "self", "super",
    "NotImplemented", "Ellipsis", "__name__",
}


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [dict.fromkeys(BUILTIN_NAMES, True)]
        self.functions = {}
        self.classes   = {}
        self._current_class = None
        self.current_function = None
        self._in_loop = 0

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def declare(self, name):
        self.scopes[-1][name] = True

    def is_declared(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return True
        return False

    def visit(self, node):
        if node is None:
            return
        method = getattr(self, f"visit_{type(node).__name__}", self._visit_noop)
        return method(node)

    def _visit_noop(self, node):
        pass

    def visit_Program(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_Number(self, node):      pass
    def visit_Float(self, node):       pass
    def visit_String(self, node):      pass
    def visit_BoolLiteral(self, node): pass
    def visit_NoneLiteral(self, node): pass
    def visit_Pass(self, node):        pass

    def visit_Variable(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' is not defined")

    def visit_Assignment(self, node):
        self.visit(node.value)
        self.declare(node.name)

    def visit_AttributeAssignment(self, node):
        self.visit(node.value)

    def visit_BinaryOp(self, node):
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node):
        self.visit(node.operand)

    def visit_BoolOp(self, node):
        self.visit(node.left)
        self.visit(node.right)

    def visit_Compare(self, node):
        self.visit(node.left)
        self.visit(node.right)

    def visit_Print(self, node):
        for v in node.values:
            self.visit(v)

    def visit_IfStatement(self, node):
        self.visit(node.condition)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.else_body:
            self.visit(stmt)

    def visit_WhileLoop(self, node):
        self.visit(node.condition)
        self._in_loop += 1
        self.enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self.exit_scope()
        self._in_loop -= 1

    def visit_Break(self, node):
        if not self._in_loop:
            raise SemanticError("'break' outside loop")

    def visit_Continue(self, node):
        if not self._in_loop:
            raise SemanticError("'continue' outside loop")

    def visit_ForLoop(self, node):
        self.visit(node.start)
        self.visit(node.end)
        self.declare(node.var_name)
        self._in_loop += 1
        self.enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self.exit_scope()
        self._in_loop -= 1

    def visit_ForInLoop(self, node):
        self.visit(node.iterable)
        if isinstance(node.var_name, list):
            for vn in node.var_name:
                self.declare(vn)
        else:
            self.declare(node.var_name)
        self._in_loop += 1
        self.enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self.exit_scope()
        self._in_loop -= 1

    def visit_RangeExpr(self, node):
        self.visit(node.start)
        self.visit(node.stop)
        if node.step:
            self.visit(node.step)

    def visit_ListLiteral(self, node):
        for e in node.elements:
            self.visit(e)

    def visit_ListAccess(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' is not defined")
        self.visit(node.index)

    def visit_IndexAssignment(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' is not defined")
        self.visit(node.index)
        self.visit(node.value)

    def visit_ListComprehension(self, node):
        self.visit(node.iterable)
        self.enter_scope()
        self.declare(node.var_name)
        self.visit(node.expr)
        if node.condition:
            self.visit(node.condition)
        self.exit_scope()

    def visit_AugmentedAssignment(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' is not defined")
        self.visit(node.value)

    def visit_AttributeAugAssignment(self, node):
        self.visit(node.value)

    def visit_IndexAugAssignment(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' is not defined")
        self.visit(node.index)
        self.visit(node.value)

    def visit_ExprStatement(self, node):
        self.visit(node.expr)

    def visit_FunctionDef(self, node):
        self.functions[node.name] = len(node.params)
        self.declare(node.name)
        self.enter_scope()
        prev = self.current_function
        self.current_function = node.name
        for param in node.params:
            self.declare(param)
        for stmt in node.body:
            self.visit(stmt)
        self.current_function = prev
        self.exit_scope()

    def visit_FunctionCall(self, node):
        if node.name not in BUILTIN_NAMES and node.name not in self.classes:
            if node.name not in self.functions and not self.is_declared(node.name):
                raise SemanticError(f"Function or class '{node.name}' is not defined")
        for arg in node.args:
            self.visit(arg)

    def visit_Return(self, node):
        self.visit(node.value)

    def visit_ClassDef(self, node):
        self.classes[node.name] = node
        self.declare(node.name)
        prev_class = self._current_class
        self._current_class = node.name
        self.enter_scope()
        self.declare("self")
        for stmt in node.body:
            self.visit(stmt)
        self.exit_scope()
        self._current_class = prev_class

    def visit_AttributeAccess(self, node):
        if not self.is_declared(node.obj):
            raise SemanticError(f"Variable '{node.obj}' is not defined")

    def visit_MethodCall(self, node):
        if not self.is_declared(node.obj):
            raise SemanticError(f"Variable '{node.obj}' is not defined")
        for arg in node.args:
            self.visit(arg)

    def visit_SuperMethodCall(self, node):
        if node.explicit_class is not None:
            cls_node = self.classes.get(node.explicit_class)
            if cls_node is None:
                raise SemanticError(f"super(): '{node.explicit_class}' is not a defined class")
            if cls_node.parent is None:
                raise SemanticError(
                    f"super(): class '{node.explicit_class}' has no parent class"
                )
        elif self._current_class is not None:
            cls_node = self.classes.get(self._current_class)
            if cls_node is not None and cls_node.parent is None:
                raise SemanticError(
                    f"super(): class '{self._current_class}' has no parent class"
                )
        for arg in node.args:
            self.visit(arg)

    def visit_MethodCallExpr(self, node):
        self.visit(node.obj_expr)
        for arg in node.args:
            self.visit(arg)

    def visit_AttributeAccessExpr(self, node):
        self.visit(node.obj_expr)

    def visit_ExprSubscript(self, node):
        self.visit(node.obj_expr)
        self.visit(node.index)

    def visit_TupleLiteral(self, node):
        for e in node.elements:
            self.visit(e)

    def visit_UnpackAssignment(self, node):
        self.visit(node.value)
        for name in node.names:
            self.declare(name)

    def visit_ChainedIndexAssignment(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' is not defined")
        for idx in node.indices:
            self.visit(idx)
        self.visit(node.value)
