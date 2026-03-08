class ASTVisualizer:
    def __init__(self):
        self.lines = []

    def visualize(self, node, indent=0):
        prefix = "  " * indent
        label = self._node_label(node)

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


    def _node_label(self, node):
        base = node.__class__.__name__
        if hasattr(node, "value"):
            val = node.value
            if not hasattr(val, "__dict__") and not isinstance(val, list):
                return f"{base}({val})"
        if hasattr(node, "name") and isinstance(getattr(node, "name"), str):
            return f"{base}({node.name})"
        if hasattr(node, "var_name") and isinstance(getattr(node, "var_name"), str):
            return f"{base}({node.var_name})"
        if hasattr(node, "operator") and isinstance(getattr(node, "operator"), str):
            return f"{base}({node.operator})"
        if hasattr(node, "method") and isinstance(getattr(node, "method"), str):
            return f"{base}({node.method})"
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
        return self._to_json(ast)