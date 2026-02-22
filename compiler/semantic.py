class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]  # stack of dictionaries
        self.functions = {}
        self.classes = {}
        self.current_function = None

    # ---------------- Scope Handling ---------------- #

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

    # ---------------- Visit Dispatcher ---------------- #

    def visit(self, node):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method:
            return method(node)

    # ---------------- Program ---------------- #

    def visit_Program(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    # ---------------- Assignment ---------------- #

    def visit_Assignment(self, node):
        self.visit(node.value)
        self.declare(node.name)

    # ---------------- Variable ---------------- #

    def visit_Variable(self, node):
        if not self.is_declared(node.name):
            raise SemanticError(f"Variable '{node.name}' not defined")

    # ---------------- Print ---------------- #

    def visit_Print(self, node):
        self.visit(node.value)

    # ---------------- BinaryOp ---------------- #

    def visit_BinaryOp(self, node):
        self.visit(node.left)
        self.visit(node.right)

    # ---------------- Compare ---------------- #

    def visit_Compare(self, node):
        self.visit(node.left)
        self.visit(node.right)

    # ---------------- If ---------------- #

    def visit_IfStatement(self, node):
        self.visit(node.condition)

        self.enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self.exit_scope()

        self.enter_scope()
        for stmt in node.else_body:
            self.visit(stmt)
        self.exit_scope()

    # ---------------- While ---------------- #

    def visit_WhileLoop(self, node):
        self.visit(node.condition)

        self.enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self.exit_scope()

    # ---------------- Function Definition ---------------- #

    def visit_FunctionDef(self, node):
        if node.name in self.functions:
            raise SemanticError(f"Function '{node.name}' already defined")

        self.functions[node.name] = len(node.params)

        self.enter_scope()
        self.current_function = node.name

        for param in node.params:
            self.declare(param)

        for stmt in node.body:
            self.visit(stmt)

        self.current_function = None
        self.exit_scope()

    # ---------------- Function Call ---------------- #

    def visit_FunctionCall(self, node):
        if node.name == "len":
            if len(node.args) != 1:
                raise SemanticError("len() takes exactly one argument")
        else:
            if node.name not in self.functions:
                raise SemanticError(f"Function '{node.name}' not defined")

            expected = self.functions[node.name]
            if len(node.args) != expected:
                raise SemanticError(
                    f"Function '{node.name}' expects {expected} args"
                )

        for arg in node.args:
            self.visit(arg)

    # ---------------- Return ---------------- #

    def visit_Return(self, node):
        if not self.current_function:
            raise SemanticError("Return outside function")

        self.visit(node.value)