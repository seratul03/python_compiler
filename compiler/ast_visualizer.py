class ASTVisualizer:
    def __init__(self):
        self.lines = []

    def visualize(self, node, indent=0):
        prefix = "  " * indent
        label = node.__class__.__name__

        if hasattr(node, "value") and not hasattr(node.value, "__dict__"):
            label += f"({node.value})"
        elif hasattr(node, "name"):
            label += f"({node.name})"

        self.lines.append(prefix + label)

        for attr in vars(node).values():
            if isinstance(attr, list):
                for item in attr:
                    if hasattr(item, "__dict__"):
                        self.visualize(item, indent + 1)

            elif hasattr(attr, "__dict__"):
                self.visualize(attr, indent + 1)

    def render(self, ast):
        self.lines = []
        self.visualize(ast)
        return "\n".join(self.lines)

    # ── JSON tree (used by the interactive browser tree view) ──────────

    def _node_label(self, node):
        """Return a concise human-readable label for a node."""
        base = node.__class__.__name__
        # Scalar value (Number, String, BoolLiteral, etc.)
        if hasattr(node, "value"):
            val = node.value
            if not hasattr(val, "__dict__") and not isinstance(val, list):
                return f"{base}({val})"
        # Named node (FunctionDef, Variable, FunctionCall, …)
        if hasattr(node, "name") and isinstance(getattr(node, "name"), str):
            return f"{base}({node.name})"
        # Iterator variable (ForLoop, ForInLoop, ListComprehension)
        if hasattr(node, "var_name") and isinstance(getattr(node, "var_name"), str):
            return f"{base}({node.var_name})"
        # Operator node (BinaryOp, UnaryOp, Compare, BoolOp, AugmentedAssignment)
        if hasattr(node, "operator") and isinstance(getattr(node, "operator"), str):
            return f"{base}({node.operator})"
        # Method call (MethodCall, MethodCallExpr, SuperMethodCall)
        if hasattr(node, "method") and isinstance(getattr(node, "method"), str):
            return f"{base}({node.method})"
        # Attribute access (AttributeAccess, AttributeAccessExpr)
        if hasattr(node, "attr") and isinstance(getattr(node, "attr"), str):
            return f"{base}({node.attr})"
        return base

    def _to_json(self, node):
        label = self._node_label(node)
        children = []
        for attr in vars(node).values():
            if isinstance(attr, list):
                for item in attr:
                    if hasattr(item, "__dict__"):
                        children.append(self._to_json(item))
            elif hasattr(attr, "__dict__"):
                children.append(self._to_json(attr))
        result = {"label": label}
        if children:
            result["children"] = children
        return result

    def render_json(self, ast):
        """Return a nested dict tree suitable for JSON serialisation."""
        return self._to_json(ast)