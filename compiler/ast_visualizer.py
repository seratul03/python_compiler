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