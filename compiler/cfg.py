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

            elif stmt_type == "ForInLoop":
                body_ends = self._build_block(stmt.body, [node])
                for b_n in body_ends:
                    b_n.edges.append(node)
                current_prevs = [node]

            elif stmt_type == "FunctionDef":
                self._build_block(stmt.body, [node])
                current_prevs = [node]

            elif stmt_type == "ClassDef":
                self._build_block(stmt.body, [node])
                current_prevs = [node]

            elif stmt_type == "TryExcept":
                try_ends = self._build_block(getattr(stmt, "body", []), [node])
                handler_ends = []
                for handler in (getattr(stmt, "handlers", None) or []):
                    handler_ends += self._build_block(getattr(handler, "body", []), [node])
                else_ends = self._build_block(getattr(stmt, "else_body", None) or [], try_ends)
                finally_ends = self._build_block(getattr(stmt, "finally_body", None) or [], try_ends + handler_ends + else_ends)
                current_prevs = finally_ends if finally_ends else (try_ends + handler_ends)

            elif stmt_type == "WithStatement":
                body_ends = self._build_block(stmt.body, [node])
                current_prevs = body_ends

            elif stmt_type == "Decorated":
                inner = getattr(stmt, "node", None)
                if inner:
                    inner_body = getattr(inner, "body", [])
                    if inner_body:
                        self._build_block(inner_body, [node])
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