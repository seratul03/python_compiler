from compiler.symbol_table import SymbolTable

class SemanticError(Exception):
    pass

BUILTIN_NAMES = {
    "len", "input", "int", "float", "str", "bool", "abs", "round",
    "range", "list", "tuple", "set", "dict", "map", "filter",
    "enumerate", "zip", "sum", "min", "max", "sorted", "reversed",
    "print", "isinstance", "hasattr", "getattr", "setattr", "type",
    "True", "False", "None", "self", "super",
    "NotImplemented", "Ellipsis",
}

class SemanticAnalyzer:
    """
    Milestone 3 — Semantic Analyzer.
    Traverses the AST using the visitor pattern, tracks variable
    declarations in a SymbolTable, and raises SemanticError for
    undefined variables.
    """

    def __init__(self):
        self.symbol_table = SymbolTable()
        for name in BUILTIN_NAMES:
            self.symbol_table.define(name, "builtin")

        self._scopes = [set(BUILTIN_NAMES)]

        self._current_function = None
        self._loop_depth = 0
        self._functions = {}
        self._classes = {}

    def _enter_scope(self):
        self._scopes.append(set())

    def _exit_scope(self):
        self._scopes.pop()

    def _declare(self, name, value_type="unknown"):
        self._scopes[-1].add(name)
        self.symbol_table.define(name, value_type)

    def _is_declared(self, name):
        return any(name in scope for scope in reversed(self._scopes))

    def visit(self, node):
        """Dispatch to visit_<ClassName> or silently skip unknown nodes."""
        if node is None:
            return None
        method = getattr(self, f"visit_{type(node).__name__}", self._generic_visit)
        return method(node)

    def _generic_visit(self, node):
        pass

    def visit_Program(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_Number(self, node):
        return "int"

    def visit_Float(self, node):
        return "float"

    def visit_String(self, node):
        return "str"

    def visit_BoolLiteral(self, node):
        return "bool"

    def visit_NoneLiteral(self, node):
        return "None"

    def visit_Pass(self, node):
        pass

    def visit_Variable(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        return self.symbol_table.lookup(node.name)

    def visit_Identifier(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        return self.symbol_table.lookup(node.name)

    def visit_Assignment(self, node):
        value_type = self.visit(node.value) or "unknown"
        self._declare(node.name, value_type)
        return value_type

    def visit_AttributeAssignment(self, node):
        self.visit(node.value)

    def visit_AugmentedAssignment(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        self.visit(node.value)

    def visit_AttributeAugAssignment(self, node):
        self.visit(node.value)

    def visit_IndexAugAssignment(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        self.visit(node.index)
        self.visit(node.value)

    def visit_IndexAssignment(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        self.visit(node.index)
        self.visit(node.value)

    def visit_BinaryOp(self, node):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        return left_type or right_type

    def visit_UnaryOp(self, node):
        return self.visit(node.operand)

    def visit_BoolOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        return "bool"

    def visit_Compare(self, node):
        self.visit(node.left)
        self.visit(node.right)
        return "bool"

    def visit_ExprStatement(self, node):
        self.visit(node.expr)

    def visit_Print(self, node):
        for value in node.values:
            self.visit(value)

    def visit_IfStatement(self, node):
        self.visit(node.condition)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.else_body:
            self.visit(stmt)

    def visit_WhileLoop(self, node):
        self.visit(node.condition)
        self._loop_depth += 1
        self._enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()
        self._loop_depth -= 1

    def visit_Break(self, node):
        if not self._loop_depth:
            raise SemanticError("'break' outside loop")

    def visit_Continue(self, node):
        if not self._loop_depth:
            raise SemanticError("'continue' outside loop")

    def visit_ForLoop(self, node):
        self.visit(node.start)
        self.visit(node.end)
        self._declare(node.var_name, "int")
        self._loop_depth += 1
        self._enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()
        self._loop_depth -= 1

    def visit_ForInLoop(self, node):
        self.visit(node.iterable)
        if isinstance(node.var_name, list):
            for vn in node.var_name:
                self._declare(vn, "unknown")
        else:
            self._declare(node.var_name, "unknown")
        self._loop_depth += 1
        self._enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()
        self._loop_depth -= 1

    def visit_RangeExpr(self, node):
        self.visit(node.start)
        self.visit(node.stop)
        if node.step:
            self.visit(node.step)

    def visit_ListLiteral(self, node):
        for element in node.elements:
            self.visit(element)
        return "list"

    def visit_ListAccess(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        self.visit(node.index)

    def visit_ListComprehension(self, node):
        self._enter_scope()
        self._declare(node.var_name, "unknown")
        self.visit(node.iterable)
        if node.condition:
            self.visit(node.condition)
        self.visit(node.expr)
        self._exit_scope()
        return "list"
    
    def visit_FunctionDef(self, node):
        self._functions[node.name] = len(node.params)
        self._declare(node.name, "function")
        prev_function = self._current_function
        self._current_function = node.name
        self._enter_scope()
        self._declare("self", "instance")
        for param in node.params:
            self._declare(param, "unknown")
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()
        self._current_function = prev_function

    def visit_Return(self, node):
        if node.value is not None:
            self.visit(node.value)

    def visit_FunctionCall(self, node):
        if (node.name not in BUILTIN_NAMES
                and node.name not in self._classes
                and node.name not in self._functions
                and not self._is_declared(node.name)):
            raise SemanticError(f"variable '{node.name}' not defined")
        for arg in node.args:
            self.visit(arg)

    def visit_ClassDef(self, node):
        self._classes[node.name] = node
        self._declare(node.name, "class")
        self._enter_scope()
        self._declare("self", "instance")
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()

    def visit_AttributeAccess(self, node):
        if not self._is_declared(node.obj):
            raise SemanticError(f"variable '{node.obj}' not defined")

    def visit_MethodCall(self, node):
        if not self._is_declared(node.obj):
            raise SemanticError(f"variable '{node.obj}' not defined")
        for arg in node.args:
            self.visit(arg)

    def visit_SuperMethodCall(self, node):
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
        return "tuple"

    def visit_UnpackAssignment(self, node):
        self.visit(node.value)
        for name in node.names:
            self._declare(name, "unknown")

    def visit_ChainedIndexAssignment(self, node):
        if not self._is_declared(node.name):
            raise SemanticError(f"variable '{node.name}' not defined")
        for idx in node.indices:
            self.visit(idx)
        self.visit(node.value)