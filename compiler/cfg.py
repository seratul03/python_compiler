class CFGNode:
    def __init__(self, label, scope="main"):
        self.label = label
        self.edges = []
        self.scope = scope

class CFGBuilder:
    def __init__(self):
        self.nodes = []
        self.counter = 0

    def new_node(self, label, scope="main"):
        node = CFGNode(f"{self.counter}:{label}", scope=scope)
        self.counter += 1
        self.nodes.append(node)
        return node

    def build(self, ast):
        start = self.new_node("START", scope="main")
        end = self.new_node("END", scope="main")

        last_nodes = self._build_block(ast.statements, [start], scope="main")
        for n in last_nodes:
            n.edges.append(end)

        return self.nodes

    def _build_block(self, statements, prev_nodes, scope="main"):
        current_prevs = prev_nodes
        for stmt in statements:
            stmt_type = type(stmt).__name__
            stmt_name = getattr(stmt, "name", None)
            display = f"{stmt_type}({stmt_name})" if stmt_name and stmt_type in ("FunctionDef", "ClassDef") else stmt_type
            node = self.new_node(display, scope=scope)

            for p in current_prevs:
                p.edges.append(node)

            if stmt_type == "IfStatement":
                body_ends = self._build_block(stmt.body, [node], scope=scope)
                else_ends = self._build_block(stmt.else_body, [node], scope=scope) if getattr(stmt, "else_body", None) else [node]
                current_prevs = body_ends + else_ends

            elif stmt_type in ("WhileLoop", "ForLoop"):
                body_ends = self._build_block(stmt.body, [node], scope=scope)
                for b_n in body_ends:
                    b_n.edges.append(node)
                current_prevs = [node]

            elif stmt_type == "ForInLoop":
                body_ends = self._build_block(stmt.body, [node], scope=scope)
                for b_n in body_ends:
                    b_n.edges.append(node)
                current_prevs = [node]

            elif stmt_type == "FunctionDef":
                fn_scope = f"fn:{stmt_name or '?'}"
                self._build_block(stmt.body, [node], scope=fn_scope)
                current_prevs = [node]

            elif stmt_type == "ClassDef":
                cls_scope = f"class:{stmt_name or '?'}"
                self._build_block(stmt.body, [node], scope=cls_scope)
                current_prevs = [node]

            elif stmt_type == "TryExcept":
                try_ends = self._build_block(getattr(stmt, "body", []), [node], scope=scope)
                handler_ends = []
                for handler in (getattr(stmt, "handlers", None) or []):
                    handler_ends += self._build_block(getattr(handler, "body", []), [node], scope=scope)
                else_ends = self._build_block(getattr(stmt, "else_body", None) or [], try_ends, scope=scope)
                finally_ends = self._build_block(getattr(stmt, "finally_body", None) or [], try_ends + handler_ends + else_ends, scope=scope)
                current_prevs = finally_ends if finally_ends else (try_ends + handler_ends)

            elif stmt_type == "WithStatement":
                body_ends = self._build_block(stmt.body, [node], scope=scope)
                current_prevs = body_ends

            elif stmt_type == "Decorated":
                inner = getattr(stmt, "node", None)
                if inner:
                    inner_name = getattr(inner, "name", "?")
                    inner_body = getattr(inner, "body", [])
                    if inner_body:
                        self._build_block(inner_body, [node], scope=f"fn:{inner_name}")
                current_prevs = [node]

            else:
                current_prevs = [node]

        return current_prevs

    def render(self, nodes):
        from collections import defaultdict, OrderedDict
        scope_edges = OrderedDict()

        for node in nodes:
            s = node.scope
            if s not in scope_edges:
                scope_edges[s] = []
            for edge in node.edges:
                scope_edges[s].append(f"{node.label} -> {edge.label}")

        lines = []
        for scope, edges in scope_edges.items():
            if scope == "main":
                lines.append("=== Main Program Flow ===")
            elif scope.startswith("fn:"):
                lines.append(f"\n=== Function: {scope[3:]} ===")
            elif scope.startswith("class:"):
                lines.append(f"\n=== Class: {scope[6:]} ===")
            else:
                lines.append(f"\n=== {scope} ===")
            lines.extend(edges)

        return "\n".join(lines)