from compiler.ast_nodes import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Top level
    # ------------------------------------------------------------------ #

    def parse(self):
        statements = []
        while self.current():
            if self.current().type == "NEWLINE":
                self.eat("NEWLINE")
                continue
            statements.append(self.statement())
        return Program(statements)

    # ------------------------------------------------------------------ #
    # Statements
    # ------------------------------------------------------------------ #

    def statement(self):
        token = self.current()

        # pass
        if token.type == "PASS":
            self.eat("PASS")
            return Pass()

        # break
        if token.type == "BREAK":
            self.eat("BREAK")
            return Break()

        # continue
        if token.type == "CONTINUE":
            self.eat("CONTINUE")
            return Continue()

        # print(a, b, ...)
        if token.type == "PRINT":
            self.eat("PRINT")
            self.eat("LPAREN")
            values = []
            if self.current().type != "RPAREN":
                values.append(self.bool_expr())
                while self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    values.append(self.bool_expr())
            self.eat("RPAREN")
            return Print(values)

        # def
        if token.type == "DEF":
            self.eat("DEF")
            name = self.eat("IDENT").value
            self.eat("LPAREN")
            params = []
            if self.current().type != "RPAREN":
                param = self.eat("IDENT").value
                params.append(param)
                while self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                    params.append(self.eat("IDENT").value)
            self.eat("RPAREN")
            self.eat("COLON")
            body = self.block()
            return FunctionDef(name, params, body)

        # return
        if token.type == "RETURN":
            self.eat("RETURN")
            # allow bare return (no value)
            if self.current() and self.current().type not in ("NEWLINE", "DEDENT"):
                value = self.bool_expr()
            else:
                value = NoneLiteral()
            return Return(value)

        # if / elif
        if token.type == "IF":
            return self._parse_if()

        # while
        if token.type == "WHILE":
            self.eat("WHILE")
            condition = self.bool_expr()
            self.eat("COLON")
            body = self.block()
            return WhileLoop(condition, body)

        # for
        if token.type == "FOR":
            return self._parse_for()

        # class
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

        # IDENT-led statements: assignment, index-assign, attr-assign, bare call
        if token.type == "IDENT":
            return self._parse_ident_statement()

        raise Exception(
            f"Invalid statement: token {token.type}={token.value!r} at line {token.line}"
        )

    # ------------------------------------------------------------------ #
    # if / elif / else
    # ------------------------------------------------------------------ #

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
            # build nested else_body tail
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

    # ------------------------------------------------------------------ #
    # for loop  — supports range(n), range(s,e), range(s,e,st), iterables
    # ------------------------------------------------------------------ #

    def _parse_for(self):
        self.eat("FOR")
        # Support single var or tuple unpacking:  for i in ...   or  for i, v in ...
        first_var = self.eat("IDENT").value
        if self.current() and self.current().type == "COMMA":
            var_names = [first_var]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                var_names.append(self.eat("IDENT").value)
            var_name = var_names   # list signals unpacking
        else:
            var_name = first_var   # plain string = single variable
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

    # ------------------------------------------------------------------ #
    # IDENT-led statements
    # ------------------------------------------------------------------ #

    # Mapping from augmented-assignment token types to their operators
    _AUG_OPS = {
        "PLUS_ASSIGN":  "+",
        "MINUS_ASSIGN": "-",
        "MULT_ASSIGN":  "*",
        "DIV_ASSIGN":   "/",
        "MOD_ASSIGN":   "%",
        "POW_ASSIGN":   "**",
    }

    def _parse_ident_statement(self):
        name = self.eat("IDENT").value

        # obj.attr = value  (attribute assignment)  or  obj.method(args)
        if self.current() and self.current().type == "DOT":
            self.eat("DOT")
            attr = self.eat("IDENT").value

            # Further chaining: obj.attr.method(...)  e.g. self.items.append(x)
            if self.current() and self.current().type == "DOT":
                acc_node = AttributeAccess(name, attr)
                self.eat("DOT")
                method2 = self.eat("IDENT").value
                self.eat("LPAREN")
                method_args = self._arg_list()
                self.eat("RPAREN")
                return ExprStatement(MethodCallExpr(acc_node, method2, method_args))

            # obj.attr = value  (plain attribute assignment)
            if self.current() and self.current().type == "ASSIGN":
                self.eat("ASSIGN")
                value = self.bool_expr()
                return AttributeAssignment(name, attr, value)

            # obj.attr OP= value  (augmented attribute assignment)
            if self.current() and self.current().type in self._AUG_OPS:
                op = self._AUG_OPS[self.eat(self.current().type).type]
                value = self.bool_expr()
                return AttributeAugAssignment(name, attr, op, value)

            # method call used as a statement: obj.method(...)
            if self.current() and self.current().type == "LPAREN":
                self.eat("LPAREN")
                args = self._arg_list()
                self.eat("RPAREN")
                return ExprStatement(MethodCall(name, attr, args))
            raise Exception(f"Expected assignment or call after {name}.{attr}")

        # name[index] OP= value  or  name[index] = value
        if self.current() and self.current().type == "LBRACKET":
            self.eat("LBRACKET")
            index = self.bool_expr()
            self.eat("RBRACKET")
            if self.current() and self.current().type in self._AUG_OPS:
                op = self._AUG_OPS[self.eat(self.current().type).type]
                value = self.bool_expr()
                return IndexAugAssignment(name, index, op, value)
            self.eat("ASSIGN")
            value = self.bool_expr()
            return IndexAssignment(name, index, value)

        # name OP= value  (augmented variable assignment)
        if self.current() and self.current().type in self._AUG_OPS:
            op = self._AUG_OPS[self.eat(self.current().type).type]
            value = self.bool_expr()
            return AugmentedAssignment(name, op, value)

        # name = value
        if self.current() and self.current().type == "ASSIGN":
            self.eat("ASSIGN")
            expr = self.bool_expr()
            return Assignment(name, expr)

        # bare function call used as a statement: func(...)
        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")

            # super().method(args) pattern
            if name == "super":
                self.eat("DOT")
                method = self.eat("IDENT").value
                self.eat("LPAREN")
                method_args = self._arg_list()
                self.eat("RPAREN")
                return ExprStatement(SuperMethodCall(method, method_args))

            call = FunctionCall(name, args)
            # Allow chaining: call().method(...)
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

    # ------------------------------------------------------------------ #
    # Block
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Expressions — precedence ladder (low → high)
    #   bool_expr  :  comparison (and|or comparison)*
    #   comparison :  expression (op expression)?
    #   expression :  term ((+|-) term)*
    #   term       :  power ((*|/|%) power)*
    #   power      :  unary (** unary)*
    #   unary      :  (- | not) unary  |  factor
    #   factor     :  NUMBER | FLOAT | STRING | TRUE | FALSE | NONE |
    #                 LPAREN expr RPAREN | list | list-comp | call | attr | var
    # ------------------------------------------------------------------ #

    def bool_expr(self):
        left = self.comparison()
        while self.current() and self.current().type in ("AND", "OR"):
            op = self.eat(self.current().type).value
            right = self.comparison()
            left = BoolOp(op, left, right)
        return left

    def comparison(self):
        left = self.expression()
        # Handle 'not in' compound operator
        if self.current() and self.current().type == "NOT":
            saved_pos = self.pos
            self.eat("NOT")
            if self.current() and self.current().type == "IN":
                self.eat("IN")
                right = self.expression()
                return Compare(left, "not in", right)
            # Not 'not in' — restore position and fall through
            self.pos = saved_pos
        # Handle 'is not' compound operator
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
        while self.current() and self.current().type in ("MULT", "DIV", "MOD"):
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
        """Parse a primary expression and handle any trailing DOT-chains or subscripts."""
        node = self._primary()
        # Post-factor chaining: DOT or LBRACKET after any expression
        while self.current() and self.current().type in ("DOT", "LBRACKET"):
            if self.current().type == "DOT":
                node = self._parse_dot_chain(node)
            else:  # LBRACKET
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

        # --- literals ---
        if token.type == "NUMBER":
            return Number(self.eat("NUMBER").value)

        if token.type == "FLOAT":
            return Float(self.eat("FLOAT").value)

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

        # --- parenthesised expression ---
        if token.type == "LPAREN":
            self.eat("LPAREN")
            expr = self.bool_expr()
            self.eat("RPAREN")
            return expr

        # --- list literal / list comprehension ---
        if token.type == "LBRACKET":
            return self._parse_list_or_comp()

        # --- IDENT-led expressions ---
        if token.type == "IDENT":
            return self._parse_ident_expr()

        raise Exception(
            f"Invalid expression token: {token.type}={token.value!r} at line {token.line}"
        )

    # ------------------------------------------------------------------ #
    # List literal or list comprehension  [ ... ]
    # ------------------------------------------------------------------ #

    def _parse_list_or_comp(self):
        self.eat("LBRACKET")

        # empty list
        if self.current() and self.current().type == "RBRACKET":
            self.eat("RBRACKET")
            return ListLiteral([])

        first_expr = self.bool_expr()

        # list comprehension: [expr for var in iterable [if cond]]
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

        # regular list
        elements = [first_expr]
        while self.current() and self.current().type == "COMMA":
            self.eat("COMMA")
            if self.current() and self.current().type == "RBRACKET":
                break
            elements.append(self.bool_expr())
        self.eat("RBRACKET")
        return ListLiteral(elements)

    def _parse_for_iterable(self):
        """Parse the iterable in a for or comprehension — handles range(...)."""
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

    # ------------------------------------------------------------------ #
    # IDENT-led expressions  (variable, call, attr, method, subscript)
    # ------------------------------------------------------------------ #

    def _parse_ident_expr(self):
        name = self.eat("IDENT").value

        # super().method(args)
        if name == "super" and self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            self.eat("RPAREN")
            self.eat("DOT")
            method = self.eat("IDENT").value
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")
            return SuperMethodCall(method, args)

        # function call: name(args)
        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")
            node = FunctionCall(name, args)
            # allow chained call: func().method(...)
            if self.current() and self.current().type == "DOT":
                return self._parse_dot_chain(node)
            return node

        # subscript: name[index]
        if self.current() and self.current().type == "LBRACKET":
            self.eat("LBRACKET")
            index = self.bool_expr()
            self.eat("RBRACKET")
            return ListAccess(name, index)

        # attribute / method chain: name.attr  or  name.method(args)
        if self.current() and self.current().type == "DOT":
            return self._parse_dot_chain(Variable(name))

        return Variable(name)

    def _parse_dot_chain(self, obj_node):
        """
        Handles  obj.attr  and  obj.method(args).
        For a plain Variable receiver → MethodCall / AttributeAccess (keep string name).
        For any other expression → MethodCallExpr / AttributeAccessExpr (keep AST node).
        """
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

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

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
