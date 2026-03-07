from compiler.ast_nodes import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        raise Exception(
            f"Expected {token_type}, got {token.type if token else 'EOF'} "
            f"(value={token.value if token else None}, line={token.line if token else '?'})"
        )

    def parse(self):
        statements = []
        while self.current():
            if self.current().type == "NEWLINE":
                self.eat("NEWLINE")
                continue
            statements.append(self.statement())
        return Program(statements)

    def statement(self):
        token = self.current()

        if token.type == "PASS":
            self.eat("PASS")
            return Pass()

        if token.type == "STRING":
            self.eat("STRING")
            return Pass()

        if token.type == "FSTRING":
            self.eat("FSTRING")
            return Pass()

        if token.type == "BREAK":
            self.eat("BREAK")
            return Break()

        if token.type == "CONTINUE":
            self.eat("CONTINUE")
            return Continue()

        if token.type == "PRINT":
            self.eat("PRINT")
            self.eat("LPAREN")
            values = []
            if self.current() and self.current().type != "RPAREN":
                if not (self.current().type == "IDENT" and self.peek() and self.peek().type == "ASSIGN"):
                    values.append(self.bool_expr())
                while self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    if self.current() and self.current().type == "RPAREN":
                        break
                    if self.current().type == "IDENT" and self.peek() and self.peek().type == "ASSIGN":
                        self.eat("IDENT")
                        self.eat("ASSIGN")
                        self.bool_expr() 
                    else:
                        values.append(self.bool_expr())
            self.eat("RPAREN")
            return Print(values)

        if token.type == "DEF":
            self.eat("DEF")
            name = self.eat("IDENT").value
            self.eat("LPAREN")
            params = []
            if self.current().type != "RPAREN":
                param = self.eat("IDENT").value
                params.append(param)
                if self.current() and self.current().type == "ASSIGN":
                    self.eat("ASSIGN")
                    self.bool_expr()  
                while self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    if self.current() and self.current().type == "RPAREN":
                        break
                    param = self.eat("IDENT").value
                    params.append(param)
                    if self.current() and self.current().type == "ASSIGN":
                        self.eat("ASSIGN")
                        self.bool_expr()
            self.eat("RPAREN")
            self.eat("COLON")
            body = self.block()
            return FunctionDef(name, params, body)

        if token.type == "RETURN":
            self.eat("RETURN")
            if self.current() and self.current().type not in ("NEWLINE", "DEDENT"):
                value = self.bool_expr()
            else:
                value = NoneLiteral()
            return Return(value)

        if token.type == "IF":
            return self._parse_if()

        if token.type == "WHILE":
            self.eat("WHILE")
            condition = self.bool_expr()
            self.eat("COLON")
            body = self.block()
            return WhileLoop(condition, body)

        if token.type == "FOR":
            return self._parse_for()

        if token.type == "CLASS":
            self.eat("CLASS")
            name = self.eat("IDENT").value
            parent = None
            if self.current() and self.current().type == "LPAREN":
                self.eat("LPAREN")
                if self.current().type != "RPAREN":
                    parent = self.eat("IDENT").value
                self.eat("RPAREN")
            self.eat("COLON")
            body = self.block()
            return ClassDef(name, parent, body)

        if token.type == "IDENT":
            return self._parse_ident_statement()

        raise Exception(
            f"Invalid statement: token {token.type}={token.value!r} at line {token.line}"
        )

    def _parse_if(self):
        self.eat("IF")
        condition = self.bool_expr()
        self.eat("COLON")
        body = self.block()

        else_body = []

        while self.current() and self.current().type == "ELIF":
            self.eat("ELIF")
            elif_cond = self.bool_expr()
            self.eat("COLON")
            elif_body = self.block()
            elif_else = []
            if self.current() and self.current().type in ("ELIF", "ELSE"):
                elif_else = self._parse_elif_tail()
            else_body = [IfStatement(elif_cond, elif_body, elif_else)]
            break

        if not else_body and self.current() and self.current().type == "ELSE":
            self.eat("ELSE")
            self.eat("COLON")
            else_body = self.block()

        return IfStatement(condition, body, else_body)

    def _parse_elif_tail(self):
        if self.current() and self.current().type == "ELIF":
            self.eat("ELIF")
            cond = self.bool_expr()
            self.eat("COLON")
            body = self.block()
            inner_else = []
            if self.current() and self.current().type in ("ELIF", "ELSE"):
                inner_else = self._parse_elif_tail()
            return [IfStatement(cond, body, inner_else)]
        elif self.current() and self.current().type == "ELSE":
            self.eat("ELSE")
            self.eat("COLON")
            return self.block()
        return []

    def _parse_for(self):
        self.eat("FOR")
        first_var = self.eat("IDENT").value
        if self.current() and self.current().type == "COMMA":
            var_names = [first_var]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                var_names.append(self.eat("IDENT").value)
            var_name = var_names  
        else:
            var_name = first_var  
        self.eat("IN")

        if self.current() and self.current().type == "RANGE":
            self.eat("RANGE")
            self.eat("LPAREN")
            first = self.bool_expr()
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                second = self.bool_expr()
                if self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    third = self.bool_expr()
                    iterable = RangeExpr(first, second, third)
                else:
                    iterable = RangeExpr(first, second, None)
            else:
                iterable = RangeExpr(Number(0), first, None)
            self.eat("RPAREN")
        else:
            iterable = self.bool_expr()

        self.eat("COLON")
        body = self.block()
        return ForInLoop(var_name, iterable, body)

    _AUG_OPS = {
        "PLUS_ASSIGN":  "+",
        "MINUS_ASSIGN": "-",
        "MULT_ASSIGN":  "*",
        "DIV_ASSIGN":   "/",
        "MOD_ASSIGN":   "%",
        "POW_ASSIGN":   "**",
        "FLOORDIV_ASSIGN": "//",
    }

    def _parse_ident_statement(self):
        name = self.eat("IDENT").value

        if self.current() and self.current().type == "COMMA":
            names = [name]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                names.append(self.eat("IDENT").value)
            self.eat("ASSIGN")
            value = self.bool_expr()
            return UnpackAssignment(names, value)

        if self.current() and self.current().type == "DOT":
            self.eat("DOT")
            attr = self.eat("IDENT").value

            if self.current() and self.current().type == "DOT":
                acc_node = AttributeAccess(name, attr)
                self.eat("DOT")
                method2 = self.eat("IDENT").value
                self.eat("LPAREN")
                method_args = self._arg_list()
                self.eat("RPAREN")
                return ExprStatement(MethodCallExpr(acc_node, method2, method_args))

            if self.current() and self.current().type == "ASSIGN":
                self.eat("ASSIGN")
                value = self.bool_expr()
                return AttributeAssignment(name, attr, value)

            if self.current() and self.current().type in self._AUG_OPS:
                op = self._AUG_OPS[self.eat(self.current().type).type]
                value = self.bool_expr()
                return AttributeAugAssignment(name, attr, op, value)

            if self.current() and self.current().type == "LPAREN":
                self.eat("LPAREN")
                args = self._arg_list()
                self.eat("RPAREN")
                return ExprStatement(MethodCall(name, attr, args))
            raise Exception(f"Expected assignment or call after {name}.{attr}")

        if self.current() and self.current().type == "LBRACKET":
            self.eat("LBRACKET")
            indices = [self.bool_expr()]
            self.eat("RBRACKET")
            while self.current() and self.current().type == "LBRACKET":
                self.eat("LBRACKET")
                indices.append(self.bool_expr())
                self.eat("RBRACKET")
            if self.current() and self.current().type in self._AUG_OPS:
                op = self._AUG_OPS[self.eat(self.current().type).type]
                value = self.bool_expr()
                return IndexAugAssignment(name, indices[0], op, value)
            self.eat("ASSIGN")
            value = self.bool_expr()
            if len(indices) == 1:
                return IndexAssignment(name, indices[0], value)
            return ChainedIndexAssignment(name, indices, value)

        if self.current() and self.current().type in self._AUG_OPS:
            op = self._AUG_OPS[self.eat(self.current().type).type]
            value = self.bool_expr()
            return AugmentedAssignment(name, op, value)

        if self.current() and self.current().type == "ASSIGN":
            self.eat("ASSIGN")
            expr = self.bool_expr()
            return Assignment(name, expr)

        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")

            if name == "super":
                self.eat("DOT")
                method = self.eat("IDENT").value
                self.eat("LPAREN")
                method_args = self._arg_list()
                self.eat("RPAREN")
                explicit_class = None
                if args and hasattr(args[0], 'name'):
                    explicit_class = args[0].name
                return ExprStatement(SuperMethodCall(method, method_args, explicit_class))

            call = FunctionCall(name, args)
            if self.current() and self.current().type == "DOT":
                self.eat("DOT")
                method = self.eat("IDENT").value
                self.eat("LPAREN")
                method_args = self._arg_list()
                self.eat("RPAREN")
                return ExprStatement(MethodCallExpr(call, method, method_args))
            return ExprStatement(call)

        raise Exception(
            f"Unexpected token after identifier '{name}': "
            f"{self.current().type if self.current() else 'EOF'}"
        )

    def block(self):
        statements = []
        self.eat("NEWLINE")
        self.eat("INDENT")
        while self.current() and self.current().type != "DEDENT":
            if self.current().type == "NEWLINE":
                self.eat("NEWLINE")
                continue
            statements.append(self.statement())
        self.eat("DEDENT")
        return statements

    
    def bool_expr(self):
        left = self.comparison()
        while self.current() and self.current().type in ("AND", "OR"):
            op = self.eat(self.current().type).value
            right = self.comparison()
            left = BoolOp(op, left, right)
        return left

    def comparison(self):
        left = self.expression()
        if self.current() and self.current().type == "NOT":
            saved_pos = self.pos
            self.eat("NOT")
            if self.current() and self.current().type == "IN":
                self.eat("IN")
                right = self.expression()
                return Compare(left, "not in", right)
            self.pos = saved_pos
        if self.current() and self.current().type == "IS":
            self.eat("IS")
            if self.current() and self.current().type == "NOT":
                self.eat("NOT")
                right = self.expression()
                return Compare(left, "is not", right)
            right = self.expression()
            return Compare(left, "is", right)
        if self.current() and self.current().type in (
            "EQ", "NEQ", "LT", "GT", "LE", "GE", "IN"
        ):
            tok = self.eat(self.current().type)
            op = "in" if tok.type == "IN" else tok.value
            right = self.expression()
            return Compare(left, op, right)
        return left

    def expression(self):
        left = self.term()
        while self.current() and self.current().type in ("PLUS", "MINUS"):
            op = self.eat(self.current().type).value
            right = self.term()
            left = BinaryOp(left, op, right)
        return left

    def term(self):
        left = self.power()
        while self.current() and self.current().type in ("MULT", "DIV", "MOD", "FLOORDIV"):
            op = self.eat(self.current().type).value
            right = self.power()
            left = BinaryOp(left, op, right)
        return left

    def power(self):
        left = self.unary()
        if self.current() and self.current().type == "POW":
            self.eat("POW")
            right = self.unary()
            left = BinaryOp(left, "**", right)
        return left

    def unary(self):
        token = self.current()
        if token and token.type == "MINUS":
            self.eat("MINUS")
            return UnaryOp("-", self.unary())
        if token and token.type == "NOT":
            self.eat("NOT")
            return UnaryOp("not", self.bool_expr())
        return self.factor()

    def factor(self):
        node = self._primary()
        while self.current() and self.current().type in ("DOT", "LBRACKET"):
            if self.current().type == "DOT":
                node = self._parse_dot_chain(node)
            else:
                self.eat("LBRACKET")
                index = self.bool_expr()
                self.eat("RBRACKET")
                if isinstance(node, Variable):
                    node = ListAccess(node.name, index)
                else:
                    node = ExprSubscript(node, index)
        return node

    def _primary(self):
        token = self.current()

        if token is None:
            raise Exception("Unexpected end of input in expression")
        
        if token.type == "NUMBER":
            return Number(self.eat("NUMBER").value)

        if token.type == "FLOAT":
            return Float(self.eat("FLOAT").value)

        if token.type == "FSTRING":
            raw = self.eat("FSTRING").value
            return self._parse_fstring(raw)

        if token.type == "STRING":
            return String(self.eat("STRING").value)

        if token.type == "TRUE":
            self.eat("TRUE")
            return BoolLiteral(True)

        if token.type == "FALSE":
            self.eat("FALSE")
            return BoolLiteral(False)

        if token.type == "NONE":
            self.eat("NONE")
            return NoneLiteral()

        if token.type == "LPAREN":
            self.eat("LPAREN")
            if self.current() and self.current().type == "RPAREN":
                self.eat("RPAREN")
                return TupleLiteral([])
            first = self.bool_expr()
            if self.current() and self.current().type == "COMMA":
                elements = [first]
                while self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    if self.current() and self.current().type == "RPAREN":
                        break
                    elements.append(self.bool_expr())
                self.eat("RPAREN")
                return TupleLiteral(elements)
            self.eat("RPAREN")
            return first

        if token.type == "LBRACKET":
            return self._parse_list_or_comp()

        if token.type == "IDENT":
            return self._parse_ident_expr()

        raise Exception(
            f"Invalid expression token: {token.type}={token.value!r} at line {token.line}"
        )

    def _skip_newlines(self):
        while self.current() and self.current().type in ("NEWLINE", "INDENT", "DEDENT"):
            self.pos += 1

    def _parse_list_or_comp(self):
        self.eat("LBRACKET")
        self._skip_newlines()

        if self.current() and self.current().type == "RBRACKET":
            self.eat("RBRACKET")
            return ListLiteral([])

        first_expr = self.bool_expr()

        if self.current() and self.current().type == "FOR":
            self.eat("FOR")
            var_name = self.eat("IDENT").value
            self.eat("IN")
            iterable = self._parse_for_iterable()
            condition = None
            if self.current() and self.current().type == "IF":
                self.eat("IF")
                condition = self.bool_expr()
            self.eat("RBRACKET")
            return ListComprehension(first_expr, var_name, iterable, condition)

        elements = [first_expr]
        while self.current() and self.current().type == "COMMA":
            self.eat("COMMA")
            self._skip_newlines()
            if self.current() and self.current().type == "RBRACKET":
                break
            elements.append(self.bool_expr())
        self._skip_newlines()
        self.eat("RBRACKET")
        return ListLiteral(elements)

    def _parse_for_iterable(self):
        if self.current() and self.current().type == "RANGE":
            self.eat("RANGE")
            self.eat("LPAREN")
            first = self.bool_expr()
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                second = self.bool_expr()
                if self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    third = self.bool_expr()
                    expr = RangeExpr(first, second, third)
                else:
                    expr = RangeExpr(first, second, None)
            else:
                expr = RangeExpr(Number(0), first, None)
            self.eat("RPAREN")
            return expr
        return self.bool_expr()

    def _parse_ident_expr(self):
        name = self.eat("IDENT").value


        if name == "super" and self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            super_args = self._arg_list() 
            self.eat("RPAREN")
            self.eat("DOT")
            method = self.eat("IDENT").value
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")
            explicit_class = None
            if super_args and hasattr(super_args[0], 'name'):
                explicit_class = super_args[0].name
            return SuperMethodCall(method, args, explicit_class)

        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")
            node = FunctionCall(name, args)
            if self.current() and self.current().type == "DOT":
                return self._parse_dot_chain(node)
            return node
        
        if self.current() and self.current().type == "LBRACKET":
            self.eat("LBRACKET")
            index = self.bool_expr()
            self.eat("RBRACKET")
            return ListAccess(name, index)
        
        if self.current() and self.current().type == "DOT":
            return self._parse_dot_chain(Variable(name))

        return Variable(name)

    def _parse_dot_chain(self, obj_node):
        self.eat("DOT")
        attr = self.eat("IDENT").value

        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")
            if isinstance(obj_node, Variable):
                node = MethodCall(obj_node.name, attr, args)
            else:
                node = MethodCallExpr(obj_node, attr, args)
            return node

        if isinstance(obj_node, Variable):
            return AttributeAccess(obj_node.name, attr)
        return AttributeAccessExpr(obj_node, attr)

    def _arg_list(self):
        args = []
        if self.current() and self.current().type != "RPAREN":
            args.append(self.bool_expr())
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                if self.current() and self.current().type == "RPAREN":
                    break
                args.append(self.bool_expr())
        return args

    def _parse_fstring(self, raw_content):
        from compiler.lexer import tokenize as _lex

        def _unescape_segment(s):
            from compiler.lexer import _is_hex
            import unicodedata
            result = []
            j = 0
            while j < len(s):
                if s[j] == '\\' and j + 1 < len(s):
                    c = s[j + 1]
                    if   c == 'n':  result.append('\n'); j += 2
                    elif c == 't':  result.append('\t'); j += 2
                    elif c == 'r':  result.append('\r'); j += 2
                    elif c == '\\': result.append('\\'); j += 2
                    elif c == '"':  result.append('"');  j += 2
                    elif c == "'":  result.append("'");  j += 2
                    elif c == 'a':  result.append('\a'); j += 2
                    elif c == 'b':  result.append('\b'); j += 2
                    elif c == 'f':  result.append('\f'); j += 2
                    elif c == 'v':  result.append('\v'); j += 2
                    elif c == '0':  result.append('\0'); j += 2
                    elif c == 'x' and j + 3 < len(s) and _is_hex(s[j+2:j+4]):
                        result.append(chr(int(s[j+2:j+4], 16))); j += 4
                    elif c == 'u' and j + 5 < len(s) and _is_hex(s[j+2:j+6]):
                        result.append(chr(int(s[j+2:j+6], 16))); j += 6
                    elif c == 'U' and j + 9 < len(s) and _is_hex(s[j+2:j+10]):
                        result.append(chr(int(s[j+2:j+10], 16))); j += 10
                    elif c == 'N' and j + 2 < len(s) and s[j+2] == '{':
                        end = s.find('}', j + 3)
                        if end != -1:
                            try:
                                result.append(unicodedata.lookup(s[j+3:end]))
                                j = end + 1
                                continue
                            except KeyError:
                                pass
                        result.append(s[j]); j += 1
                    else:           result.append(s[j]); j += 1
                else:
                    result.append(s[j])
                    j += 1
            return ''.join(result)

        parts = []
        i = 0
        current_literal = ""

        while i < len(raw_content):
            ch = raw_content[i]
            if ch == '{':
                if i + 1 < len(raw_content) and raw_content[i + 1] == '{':
                    current_literal += '{'
                    i += 2
                    continue
                if current_literal:
                    parts.append(String(_unescape_segment(current_literal)))
                    current_literal = ""
                depth = 1
                j = i + 1
                while j < len(raw_content) and depth > 0:
                    if raw_content[j] == '{':
                        depth += 1
                    elif raw_content[j] == '}':
                        depth -= 1
                    j += 1
                expr_content = raw_content[i + 1: j - 1]
                fmt_spec = None
                colon_idx = expr_content.find(':')
                if colon_idx != -1:
                    fmt_spec = expr_content[colon_idx + 1:]
                    expr_str = expr_content[:colon_idx].strip()
                else:
                    expr_str = expr_content.strip()
                expr_tokens = _lex(expr_str)
                sub_parser = Parser(expr_tokens)
                expr_node = sub_parser.bool_expr()
                parts.append((expr_node, fmt_spec))
                i = j
            elif ch == '}' and i + 1 < len(raw_content) and raw_content[i + 1] == '}':
                current_literal += '}'
                i += 2
            else:
                current_literal += ch
                i += 1

        if current_literal:
            parts.append(String(_unescape_segment(current_literal)))

        return FStringExpr(parts)
