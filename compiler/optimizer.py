class Optimizer:
    def visit(self, node):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method:
            return method(node)
        return node

    def visit_Program(self, node):
        new_statements = []
        for stmt in node.statements:
            optimized = self.visit(stmt)
            if optimized is None:
                continue
            if isinstance(optimized, list):
                new_statements.extend(optimized)
            else:
                new_statements.append(optimized)
        node.statements = new_statements
        return node

    def visit_Assignment(self, node):
        node.value = self.visit(node.value)
        return node

    def visit_BinaryOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)

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

        if type(node.right).__name__ == "Number":
            if node.operator == "+" and node.right.value == 0:
                return node.left
            if node.operator == "*" and node.right.value == 1:
                return node.left

        if type(node.left).__name__ == "Number":
            if node.operator == "+" and node.left.value == 0:
                return node.right
            if node.operator == "*" and node.left.value == 1:
                return node.right

        return node

    def visit_Compare(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        return node

    def visit_IfStatement(self, node):
        node.condition = self.visit(node.condition)

        if type(node.condition).__name__ == "Number":
            if node.condition.value:
                return [self.visit(stmt) for stmt in node.body]
            else:
                return [self.visit(stmt) for stmt in node.else_body]

        node.body = [self.visit(stmt) for stmt in node.body if stmt is not None]
        node.else_body = [self.visit(stmt) for stmt in node.else_body if stmt is not None]

        return node

    def visit_WhileLoop(self, node):
        node.condition = self.visit(node.condition)
        node.body = [self.visit(stmt) for stmt in node.body if stmt is not None]
        return node

    def visit_FunctionDef(self, node):
        new_body = []
        for stmt in node.body:
            optimized = self.visit(stmt)
            if optimized is None:
                continue

            if isinstance(optimized, list):
                new_body.extend(optimized)
            else:
                new_body.append(optimized)

            if type(stmt).__name__ == "Return":
                break

        node.body = new_body
        return node

    def visit_TupleLiteral(self, node):
        node.elements = [self.visit(e) for e in node.elements]
        return node

    def visit_UnpackAssignment(self, node):
        node.value = self.visit(node.value)
        return node

    def visit_ChainedIndexAssignment(self, node):
        node.indices = [self.visit(idx) for idx in node.indices]
        node.value = self.visit(node.value)
        return node