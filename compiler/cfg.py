class CFGNode:
    def __init__(self, label):
        self.label = label
        self.edges = []

class CFGBuilder:
    def __init__(self):
        self.nodes = []
        self.counter = 0

    def new_node(self, label):
        node = CFGNode(f"{self.counter}:{label}")
        self.counter += 1
        self.nodes.append(node)
        return node

    def build(self, ast):
        start = self.new_node("START")
        end = self.new_node("END")

        last_nodes = self._build_block(ast.statements, [start])
        for n in last_nodes:
            n.edges.append(end)

        return self.nodes

    def _build_block(self, statements, prev_nodes):
        current_prevs = prev_nodes
        for stmt in statements:
            stmt_type = type(stmt).__name__
            node = self.new_node(stmt_type)

            for p in current_prevs:
                p.edges.append(node)

            if stmt_type == "IfStatement":
                body_ends = self._build_block(stmt.body, [node])
                else_ends = self._build_block(stmt.else_body, [node]) if getattr(stmt, "else_body", None) else [node]
                current_prevs = body_ends + else_ends

            elif stmt_type in ("WhileLoop", "ForLoop"):
                body_ends = self._build_block(stmt.body, [node])
                for b_n in body_ends:
                    b_n.edges.append(node)
                current_prevs = [node]

            else:
                current_prevs = [node]

        return current_prevs

    def render(self, nodes):
        lines = []
        for node in nodes:
            for edge in node.edges:
                lines.append(f"{node.label} -> {edge.label}")
        return "\n".join(lines)