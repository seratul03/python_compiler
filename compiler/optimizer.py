class Optimizer:
    def visit(self, node):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method:
            return method(node)
        return node

    # ---------------- Program ---------------- #

    def visit_Program(self, node):
        new_statements = []
        for stmt in node.statements:
            optimized = self.visit(stmt)
            if optimized is not None:
                new_statements.append(optimized)
        node.statements = new_statements
        return node

    # ---------------- Assignment ---------------- #

    def visit_Assignment(self, node):
        node.value = self.visit(node.value)
        return node

    # ---------------- BinaryOp (Constant Folding) ---------------- #

    def visit_BinaryOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)

        # If both sides are constants, compute at compile time
        if type(node.left).__name__ == "Number" and type(node.right).__name__ == "Number":
            left = node.left.value
            right = node.right.value

            if node.operator == "+":
                return type(node.left)(left + right)
            elif node.operator == "-":
                return type(node.left)(left - right)
            elif node.operator == "*":
                return type(node.left)(left * right)
            elif node.operator == "/":
                return type(node.left)(left / right)

        return node

    # ---------------- Compare ---------------- #

    def visit_Compare(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        return node

    # ---------------- If (Dead Code Elimination) ---------------- #

    def visit_IfStatement(self, node):
        node.condition = self.visit(node.condition)

        # If condition is constant
        if type(node.condition).__name__ == "Number":
            if node.condition.value:
                return node.body
            else:
                return node.else_body

        node.body = [self.visit(stmt) for stmt in node.body]
        node.else_body = [self.visit(stmt) for stmt in node.else_body]

        return node

    # ---------------- While ---------------- #

    def visit_WhileLoop(self, node):
        node.condition = self.visit(node.condition)
        node.body = [self.visit(stmt) for stmt in node.body]
        return node

    # ---------------- Function ---------------- #

    def visit_FunctionDef(self, node):
        new_body = []
        for stmt in node.body:
            optimized = self.visit(stmt)
            if optimized is None:
                continue
            new_body.append(optimized)

            # Remove unreachable after return
            if type(stmt).__name__ == "Return":
                break

        node.body = new_body
        return node