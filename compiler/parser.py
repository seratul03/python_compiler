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

        while token and token.type == "SEMICOLON":
            self.eat("SEMICOLON")
            token = self.current()
        if not token:
            return Pass()

        if token.type == "PASS":
            self.eat("PASS")
            return Pass()

        if token.type == "STRING":
            val = self.eat("STRING").value
            return ExprStatement(String(val))

        if token.type == "FSTRING":
            self.eat("FSTRING")
            return Pass()

        if token.type == "BREAK":
            self.eat("BREAK")
            return Break()

        if token.type == "CONTINUE":
            self.eat("CONTINUE")
            return Continue()

        if token.type == "AT":
            return self._parse_decorated()

        if token.type == "ASSERT":
            self.eat("ASSERT")
            condition = self.bool_expr()
            message = None
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                message = self.bool_expr()
            return Assert(condition, message)

        if token.type == "RAISE":
            self.eat("RAISE")
            exc = None
            cause = None
            if self.current() and self.current().type not in ("NEWLINE", "DEDENT"):
                exc = self.bool_expr()
                if self.current() and self.current().type == "IDENT" and self.current().value == "from":
                    self.eat("IDENT")
                    cause = self.bool_expr()
            return RaiseStatement(exc, cause)

        if token.type == "DEL":
            self.eat("DEL")
            targets = [self.bool_expr()]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                targets.append(self.bool_expr())
            return DeleteStatement(targets)

        if token.type == "GLOBAL":
            self.eat("GLOBAL")
            names = [self.eat("IDENT").value]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                names.append(self.eat("IDENT").value)
            return GlobalStatement(names)

        if token.type == "NONLOCAL":
            self.eat("NONLOCAL")
            names = [self.eat("IDENT").value]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                names.append(self.eat("IDENT").value)
            return NonlocalStatement(names)

        if token.type == "YIELD":
            self.eat("YIELD")
            value = None
            if self.current() and self.current().type not in ("NEWLINE", "DEDENT"):
                value = self.bool_expr()
            return ExprStatement(YieldExpr(value))

        if token.type == "IMPORT":
            self.eat("IMPORT")
            names = []
            name = self._parse_dotted_name()
            alias = None
            if self.current() and self.current().type == "AS":
                self.eat("AS")
                alias = self.eat("IDENT").value
            names.append((name, alias))
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                name = self._parse_dotted_name()
                alias = None
                if self.current() and self.current().type == "AS":
                    self.eat("AS")
                    alias = self.eat("IDENT").value
                names.append((name, alias))
            return Import(names)

        if token.type == "FROM":
            self.eat("FROM")
            module = self._parse_dotted_name()
            self.eat("IMPORT")
            if self.current() and self.current().type == "MULT":
                self.eat("MULT")
                return ImportFrom(module, [("*", None)])
            if self.current() and self.current().type == "LPAREN":
                self.eat("LPAREN")
                names = self._parse_import_names()
                self.eat("RPAREN")
            else:
                names = self._parse_import_names()
            return ImportFrom(module, names)

        if token.type == "TRY":
            return self._parse_try()

        if token.type == "WITH":
            return self._parse_with()

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
            return self._parse_funcdef()

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
            return self._parse_classdef()

        if token.type == "ASYNC":
            self.eat("ASYNC")
            return self.statement()

        if token.type == "AWAIT":
            self.eat("AWAIT")
            expr = self.bool_expr()
            return ExprStatement(expr)

        if token.type == "IDENT":
            return self._parse_ident_statement()

        try:
            expr = self.bool_expr()
            return ExprStatement(expr)
        except Exception:
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

    def _parse_decorated(self):
        decorators = []
        while self.current() and self.current().type == "AT":
            self.eat("AT")
            dec_expr = self._parse_decorator_expr()
            decorators.append(dec_expr)
            while self.current() and self.current().type == "NEWLINE":
                self.eat("NEWLINE")
        if self.current() and self.current().type == "DEF":
            node = self._parse_funcdef()
        elif self.current() and self.current().type == "CLASS":
            node = self._parse_classdef()
        else:
            node = self.statement()
        if decorators:
            if isinstance(node, FunctionDef):
                node.decorators = decorators + node.decorators
            return Decorated(decorators, node)
        return node

    def _parse_decorator_expr(self):
        name = self.eat("IDENT").value
        node = Variable(name)
        while self.current() and self.current().type == "DOT":
            self.eat("DOT")
            attr = self.eat("IDENT").value
            node = AttributeAccessExpr(node, attr)
        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            args = self._arg_list()
            self.eat("RPAREN")
            if isinstance(node, Variable):
                node = FunctionCall(node.name, args)
            else:
                node = MethodCallExpr(node, "__call__", args)
        return node

    def _parse_funcdef(self):
        self.eat("DEF")
        name = self.eat("IDENT").value
        self.eat("LPAREN")
        params, defaults, vararg, kwarg, kwonly = self._parse_param_list()
        self.eat("RPAREN")
        if self.current() and self.current().type == "ARROW":
            self.eat("ARROW")
            self.bool_expr()
        self.eat("COLON")
        body = self.block()
        return FunctionDef(name, params, body, defaults=defaults,
                           vararg=vararg, kwarg=kwarg, kwonly_params=kwonly)

    def _parse_param_list(self):
        """Parse function parameters.  Returns (params, defaults, vararg, kwarg, kwonly_params)."""
        params = []
        defaults = {}
        vararg = None
        kwarg = None
        kwonly = []
        seen_star = False

        while self.current() and self.current().type != "RPAREN":
            tok = self.current()

            if tok.type == "MULT":
                self.eat("MULT")
                if self.current() and self.current().type == "IDENT":
                    vararg = self.eat("IDENT").value
                seen_star = True
            elif tok.type == "POW":
                self.eat("POW")
                kwarg = self.eat("IDENT").value
            elif tok.type == "IDENT":
                pname = self.eat("IDENT").value
                if self.current() and self.current().type == "COLON":
                    self.eat("COLON")
                    self.bool_expr()
                if self.current() and self.current().type == "ASSIGN":
                    self.eat("ASSIGN")
                    defaults[pname] = self.bool_expr()
                if seen_star:
                    kwonly.append(pname)
                else:
                    params.append(pname)
            else:
                break

            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
            else:
                break

        return params, defaults, vararg, kwarg, kwonly

    def _parse_classdef(self):
        self.eat("CLASS")
        name = self.eat("IDENT").value
        bases = []
        if self.current() and self.current().type == "LPAREN":
            self.eat("LPAREN")
            while self.current() and self.current().type != "RPAREN":
                if self.current().type == "IDENT":
                    b = self.eat("IDENT").value
                    while self.current() and self.current().type == "DOT":
                        self.eat("DOT")
                        b += "." + self.eat("IDENT").value
                    bases.append(b)
                if self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                else:
                    break
            self.eat("RPAREN")
        self.eat("COLON")
        body = self.block()
        parent = bases[0] if bases else None
        return ClassDef(name, parent, body, bases=bases)

    def _parse_dotted_name(self):
        name = self.eat("IDENT").value
        while self.current() and self.current().type == "DOT":
            self.eat("DOT")
            if self.current() and self.current().type == "IDENT":
                name += "." + self.eat("IDENT").value
            else:
                break
        return name

    def _parse_import_names(self):
        names = []
        while True:
            if self.current() and self.current().type == "IDENT":
                name = self.eat("IDENT").value
                alias = None
                if self.current() and self.current().type == "AS":
                    self.eat("AS")
                    alias = self.eat("IDENT").value
                names.append((name, alias))
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                if self.current() and self.current().type in ("RPAREN", "NEWLINE", "DEDENT"):
                    break
            else:
                break
        return names

    def _parse_try(self):
        self.eat("TRY")
        self.eat("COLON")
        body = self.block()
        handlers = []
        else_body = []
        finally_body = []

        while self.current() and self.current().type == "EXCEPT":
            self.eat("EXCEPT")
            exc_type = None
            var_name = None
            if self.current() and self.current().type not in ("COLON", "NEWLINE"):
                exc_type = self._parse_dotted_name()
                if self.current() and self.current().type == "AS":
                    self.eat("AS")
                    var_name = self.eat("IDENT").value
            self.eat("COLON")
            handler_body = self.block()
            handlers.append(ExceptHandler(exc_type, var_name, handler_body))

        if self.current() and self.current().type == "ELSE":
            self.eat("ELSE")
            self.eat("COLON")
            else_body = self.block()

        if self.current() and self.current().type == "FINALLY":
            self.eat("FINALLY")
            self.eat("COLON")
            finally_body = self.block()

        return TryExcept(body, handlers, else_body, finally_body)

    def _parse_with(self):
        self.eat("WITH")
        items = []
        ctx = self.bool_expr()
        var_name = None
        if self.current() and self.current().type == "AS":
            self.eat("AS")
            var_name = self.eat("IDENT").value
        items.append((ctx, var_name))
        while self.current() and self.current().type == "COMMA":
            self.eat("COMMA")
            ctx2 = self.bool_expr()
            vn2 = None
            if self.current() and self.current().type == "AS":
                self.eat("AS")
                vn2 = self.eat("IDENT").value
            items.append((ctx2, vn2))
        self.eat("COLON")
        body = self.block()
        return WithStatement(items, body)

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
        "PLUS_ASSIGN":     "+",
        "MINUS_ASSIGN":    "-",
        "MULT_ASSIGN":     "*",
        "DIV_ASSIGN":      "/",
        "MOD_ASSIGN":      "%",
        "POW_ASSIGN":      "**",
        "FLOORDIV_ASSIGN": "//",
        "AND_ASSIGN":      "&",
        "OR_ASSIGN":       "|",
        "XOR_ASSIGN":      "^",
        "LSHIFT_ASSIGN":   "<<",
        "RSHIFT_ASSIGN":   ">>",
        "AT_ASSIGN":       "@",
    }

    def _parse_ident_statement(self):
        name = self.eat("IDENT").value

        if self.current() and self.current().type == "WALRUS":
            self.eat("WALRUS")
            value = self.bool_expr()
            return ExprStatement(WalrusExpr(name, value))

        if self.current() and self.current().type == "COMMA":
            names = [name]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                if self.current() and self.current().type in ("NEWLINE", "DEDENT", None.__class__):
                    break
                if self.current() and self.current().type == "IDENT":
                    names.append(self.eat("IDENT").value)
                else:
                    break
            self.eat("ASSIGN")
            value = self.bool_expr()
            return UnpackAssignment(names, value)

        if self.current() and self.current().type == "DOT":
            self.eat("DOT")
            attr = self.eat("IDENT").value

            if self.current() and self.current().type == "DOT":
                acc_node = AttributeAccess(name, attr)
                return ExprStatement(self._parse_dot_chain(acc_node))

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
                call_node = MethodCall(name, attr, args)
                if self.current() and self.current().type in ("DOT", "LBRACKET"):
                    result = self.factor.__func__(self)   
                return ExprStatement(call_node)

            if self.current() and self.current().type == "LBRACKET":
                acc = AttributeAccess(name, attr)
                return ExprStatement(self._parse_dot_chain(acc))

            raise Exception(f"Expected assignment or call after {name}.{attr}")

        if self.current() and self.current().type == "LBRACKET":
            self.eat("LBRACKET")
            first_idx = self._parse_subscript_index()
            indices = [first_idx]
            while self.current() and self.current().type == "LBRACKET":
                self.eat("LBRACKET")
                indices.append(self._parse_subscript_index())
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
                return ExprStatement(self._parse_dot_chain(call))
            return ExprStatement(call)

        raise Exception(
            f"Unexpected token after identifier '{name}': "
            f"{self.current().type if self.current() else 'EOF'}"
        )

    def _parse_subscript_index(self):
        """Parse the content between [ and ] including possible slices."""
        if self.current() and self.current().type == "COLON":
            start = None
        else:
            start = self.bool_expr()
        if self.current() and self.current().type == "COLON":
            self.eat("COLON")
            stop = None
            if self.current() and self.current().type not in ("RBRACKET", "COLON"):
                stop = self.bool_expr()
            step = None
            if self.current() and self.current().type == "COLON":
                self.eat("COLON")
                if self.current() and self.current().type != "RBRACKET":
                    step = self.bool_expr()
            self.eat("RBRACKET")
            return Slice(start, stop, step)
        self.eat("RBRACKET")
        return start

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
        """or / and / ternary — top-level expression."""
        left = self._and_expr()
        while self.current() and self.current().type == "OR":
            self.eat("OR")
            right = self._and_expr()
            left = BoolOp("or", left, right)
        if self.current() and self.current().type == "IF":
            saved = self.pos
            self.eat("IF")
            condition = self._and_expr()
            if self.current() and self.current().type == "ELSE":
                self.eat("ELSE")
                orelse = self.bool_expr()
                return IfExpr(condition, left, orelse)
            else:
                self.pos = saved
        return left

    def _and_expr(self):
        left = self._not_expr()
        while self.current() and self.current().type == "AND":
            self.eat("AND")
            right = self._not_expr()
            left = BoolOp("and", left, right)
        return left

    def _not_expr(self):
        if self.current() and self.current().type == "NOT":
            self.eat("NOT")
            operand = self._not_expr()
            return UnaryOp("not", operand)
        return self.comparison()

    def comparison(self):
        left = self.bitor()
        if self.current() and self.current().type == "NOT":
            saved_pos = self.pos
            self.eat("NOT")
            if self.current() and self.current().type == "IN":
                self.eat("IN")
                right = self.bitor()
                return Compare(left, "not in", right)
            self.pos = saved_pos
        if self.current() and self.current().type == "IS":
            self.eat("IS")
            if self.current() and self.current().type == "NOT":
                self.eat("NOT")
                right = self.bitor()
                return Compare(left, "is not", right)
            right = self.bitor()
            return Compare(left, "is", right)
        if self.current() and self.current().type in (
            "EQ", "NEQ", "LT", "GT", "LE", "GE", "IN"
        ):
            tok = self.eat(self.current().type)
            op = "in" if tok.type == "IN" else tok.value
            right = self.bitor()
            return Compare(left, op, right)
        return left

    def bitor(self):
        left = self.bitxor()
        while self.current() and self.current().type == "BITOR":
            self.eat("BITOR")
            right = self.bitxor()
            left = BitwiseOp(left, "|", right)
        return left

    def bitxor(self):
        left = self.bitand()
        while self.current() and self.current().type == "BITXOR":
            self.eat("BITXOR")
            right = self.bitand()
            left = BitwiseOp(left, "^", right)
        return left

    def bitand(self):
        left = self.shift()
        while self.current() and self.current().type == "BITAND":
            self.eat("BITAND")
            right = self.shift()
            left = BitwiseOp(left, "&", right)
        return left

    def shift(self):
        left = self.expression()
        while self.current() and self.current().type in ("LSHIFT", "RSHIFT"):
            op = self.eat(self.current().type).type
            right = self.expression()
            left = BitwiseOp(left, "<<" if op == "LSHIFT" else ">>", right)
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
        if token and token.type == "BITNOT":
            self.eat("BITNOT")
            return UnaryBitNot(self.unary())
        if token and token.type == "NOT":
            self.eat("NOT")
            return UnaryOp("not", self.bool_expr())
        if token and token.type == "PLUS":
            self.eat("PLUS")
            return self.unary()  
        return self.factor()

    def factor(self):
        node = self._primary()
        while self.current() and self.current().type in ("DOT", "LBRACKET"):
            if self.current().type == "DOT":
                node = self._parse_dot_chain(node)
            else:
                self.eat("LBRACKET")
                node = self._parse_subscript(node)
        return node

    def _parse_subscript(self, obj_node):
        """Parse [index] or [start:stop:step] after an expression."""
        start = None
        stop = None
        step = None

        if self.current() and self.current().type == "COLON":
            pass
        else:
            start = self.bool_expr()

        if self.current() and self.current().type == "COLON":
            self.eat("COLON")
            if self.current() and self.current().type not in ("RBRACKET", "COLON"):
                stop = self.bool_expr()
            if self.current() and self.current().type == "COLON":
                self.eat("COLON")
                if self.current() and self.current().type != "RBRACKET":
                    step = self.bool_expr()
            self.eat("RBRACKET")
            index = Slice(start, stop, step)
        else:
            index = start
            self.eat("RBRACKET")

        if isinstance(obj_node, Variable):
            return ListAccess(obj_node.name, index)
        return ExprSubscript(obj_node, index)

    def _primary(self):
        token = self.current()

        if token is None:
            raise Exception("Unexpected end of input in expression")

        if token.type == "LAMBDA":
            return self._parse_lambda()

        if token.type == "AWAIT":
            self.eat("AWAIT")
            return self._primary()

        if token.type == "NUMBER":
            return Number(self.eat("NUMBER").value)

        if token.type == "FLOAT":
            return Float(self.eat("FLOAT").value)

        if token.type == "FSTRING":
            raw = self.eat("FSTRING").value
            return self._parse_fstring(raw)

        if token.type == "STRING":
            val = self.eat("STRING").value
            while self.current() and self.current().type == "STRING":
                val += self.eat("STRING").value
            return String(val)

        if token.type == "TRUE":
            self.eat("TRUE")
            return BoolLiteral(True)

        if token.type == "FALSE":
            self.eat("FALSE")
            return BoolLiteral(False)

        if token.type == "NONE":
            self.eat("NONE")
            return NoneLiteral()

        if token.type == "ELLIPSIS":
            self.eat("ELLIPSIS")
            return EllipsisNode()

        if token.type == "LPAREN":
            self.eat("LPAREN")
            if self.current() and self.current().type == "RPAREN":
                self.eat("RPAREN")
                return TupleLiteral([])
            first = self.bool_expr()
            if self.current() and self.current().type == "FOR":
                self.eat("FOR")
                var_name = self.eat("IDENT").value
                self.eat("IN")
                iterable = self._parse_for_iterable()
                condition = None
                if self.current() and self.current().type == "IF":
                    self.eat("IF")
                    condition = self.bool_expr()
                self.eat("RPAREN")
                return GeneratorExpr(first, var_name, iterable, condition)
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

        if token.type == "LBRACE":
            return self._parse_dict_or_set()

        if token.type == "IDENT":
            return self._parse_ident_expr()

        raise Exception(
            f"Invalid expression token: {token.type}={token.value!r} at line {token.line}"
        )
    
    def _parse_lambda(self):
        self.eat("LAMBDA")
        params = []
        defaults = {}
        vararg = None
        kwarg = None
        if self.current() and self.current().type != "COLON":
            while self.current() and self.current().type != "COLON":
                tok = self.current()
                if tok.type == "MULT":
                    self.eat("MULT")
                    if self.current() and self.current().type == "IDENT":
                        vararg = self.eat("IDENT").value
                elif tok.type == "POW":
                    self.eat("POW")
                    kwarg = self.eat("IDENT").value
                elif tok.type == "IDENT":
                    pname = self.eat("IDENT").value
                    if self.current() and self.current().type == "ASSIGN":
                        self.eat("ASSIGN")
                        defaults[pname] = self.bool_expr()
                    params.append(pname)
                if self.current() and self.current().type == "COMMA":
                    self.eat("COMMA")
                else:
                    break
        self.eat("COLON")
        body = self.bool_expr()
        return LambdaExpr(params, body, defaults=defaults, vararg=vararg, kwarg=kwarg)

    def _parse_dict_or_set(self):
        self.eat("LBRACE")
        self._skip_newlines()
        if self.current() and self.current().type == "RBRACE":
            self.eat("RBRACE")
            return DictLiteral([], [])  

        if self.current() and self.current().type == "POW":
            self.eat("POW")
            val = self.bool_expr()
            keys = [None]
            values = [DoubleStarred(val)]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                self._skip_newlines()
                if self.current() and self.current().type == "RBRACE":
                    break
                if self.current() and self.current().type == "POW":
                    self.eat("POW")
                    v = self.bool_expr()
                    keys.append(None)
                    values.append(DoubleStarred(v))
                else:
                    k = self.bool_expr()
                    self.eat("COLON")
                    v = self.bool_expr()
                    keys.append(k)
                    values.append(v)
            self.eat("RBRACE")
            return DictLiteral(keys, values)

        first = self.bool_expr()

        if self.current() and self.current().type == "COLON":
            self.eat("COLON")
            first_val = self.bool_expr()
            if self.current() and self.current().type == "FOR":
                self.eat("FOR")
                var_name = self.eat("IDENT").value
                self.eat("IN")
                iterable = self._parse_for_iterable()
                condition = None
                if self.current() and self.current().type == "IF":
                    self.eat("IF")
                    condition = self.bool_expr()
                self.eat("RBRACE")
                return DictComprehension(first, first_val, var_name, iterable, condition)
            keys = [first]
            values = [first_val]
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                self._skip_newlines()
                if self.current() and self.current().type == "RBRACE":
                    break
                if self.current() and self.current().type == "POW":
                    self.eat("POW")
                    v = self.bool_expr()
                    keys.append(None)
                    values.append(DoubleStarred(v))
                else:
                    k = self.bool_expr()
                    self.eat("COLON")
                    v = self.bool_expr()
                    keys.append(k)
                    values.append(v)
            self.eat("RBRACE")
            return DictLiteral(keys, values)

        if self.current() and self.current().type == "FOR":
            self.eat("FOR")
            var_name = self.eat("IDENT").value
            self.eat("IN")
            iterable = self._parse_for_iterable()
            condition = None
            if self.current() and self.current().type == "IF":
                self.eat("IF")
                condition = self.bool_expr()
            self.eat("RBRACE")
            return SetComprehension(first, var_name, iterable, condition)

        elements = [first]
        while self.current() and self.current().type == "COMMA":
            self.eat("COMMA")
            self._skip_newlines()
            if self.current() and self.current().type == "RBRACE":
                break
            elements.append(self.bool_expr())
        self.eat("RBRACE")
        return SetLiteral(elements)

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

        if self.current() and self.current().type == "WALRUS":
            self.eat("WALRUS")
            value = self.bool_expr()
            return WalrusExpr(name, value)

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
            node = self._parse_subscript(Variable(name))
            return node

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
        """Parse function call arguments, supporting positional, keyword, *args, **kwargs."""
        args = []
        if self.current() and self.current().type != "RPAREN":
            args.append(self._parse_one_arg())
            while self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
                if self.current() and self.current().type == "RPAREN":
                    break
                args.append(self._parse_one_arg())
        return args

    def _parse_one_arg(self):
        """Parse a single argument (positional / keyword / starred / double-starred)."""
        tok = self.current()
        if tok and tok.type == "POW":
            self.eat("POW")
            return DoubleStarred(self.bool_expr())
        if tok and tok.type == "MULT":
            self.eat("MULT")
            return Starred(self.bool_expr())
        expr = self.bool_expr()
        if (isinstance(expr, Variable) and
                self.current() and self.current().type == "ASSIGN"):
            self.eat("ASSIGN")
            value = self.bool_expr()
            return KeywordArg(expr.name, value)
        return expr

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
