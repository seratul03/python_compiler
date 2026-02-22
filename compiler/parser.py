from compiler.ast_nodes import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---------------- UTIL ---------------- #

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        raise Exception(
            f"Expected {token_type}, got {token.type if token else None}"
        )

    # ---------------- ENTRY ---------------- #

    def parse(self):
        statements = []

        while self.current():
            if self.current().type == "NEWLINE":
                self.eat("NEWLINE")
                continue

            statements.append(self.statement())

        return Program(statements)

    # ---------------- STATEMENTS ---------------- #

    def statement(self):
        token = self.current()

        # print
        if token.type == "IDENT" and token.value == "print":
            self.eat("IDENT")
            self.eat("LPAREN")
            expr = self.comparison()
            self.eat("RPAREN")
            return Print(expr)

        # def
        elif token.type == "IDENT" and token.value == "def":
            self.eat("IDENT")
            name = self.eat("IDENT").value
            self.eat("LPAREN")

            params = []
            if self.current().type != "RPAREN":
                params.append(self.eat("IDENT").value)
                while self.current().type == "COMMA":
                    self.eat("COMMA")
                    params.append(self.eat("IDENT").value)

            self.eat("RPAREN")
            self.eat("COLON")
            body = self.block()

            return FunctionDef(name, params, body)

        # return
        elif token.type == "IDENT" and token.value == "return":
            self.eat("IDENT")
            value = self.comparison()
            return Return(value)

        # if
        elif token.type == "IDENT" and token.value == "if":
            self.eat("IDENT")
            condition = self.comparison()
            self.eat("COLON")
            body = self.block()

            else_body = []
            if (
                self.current()
                and self.current().type == "IDENT"
                and self.current().value == "else"
            ):
                self.eat("IDENT")
                self.eat("COLON")
                else_body = self.block()

            return IfStatement(condition, body, else_body)

        # while
        elif token.type == "IDENT" and token.value == "while":
            self.eat("IDENT")
            condition = self.comparison()
            self.eat("COLON")
            body = self.block()
            return WhileLoop(condition, body)
        
        #for
        elif token.type == "IDENT" and token.value == "for":
            self.eat("IDENT")
            var_name = self.eat("IDENT").value
            self.eat("IDENT")  # in
            self.eat("IDENT")  # range
            self.eat("LPAREN")

            start = Number(0)
            end = self.comparison()

            self.eat("RPAREN")
            self.eat("COLON")
            body = self.block()

            return ForLoop(var_name, start, end, body)

        # assignment
        elif token.type == "IDENT":
            name = self.eat("IDENT").value

            if self.current() and self.current().type == "LBRACKET":
                self.eat("LBRACKET")
                index = self.comparison()
                self.eat("RBRACKET")
                self.eat("ASSIGN")
                value = self.comparison()
                return IndexAssignment(name, index, value)
            self.eat("ASSIGN")
            expr = self.comparison()
            return Assignment(name, expr)

        elif token.type == "IDENT" and token.value == "class":
            self.eat("IDENT")
            name = self.eat("IDENT").value
            self.eat("COLON")
            body = self.block()
            return ClassDef(name, body)
        else:
            raise Exception("Invalid statement")
        
    

    # ---------------- BLOCK ---------------- #

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

    # ---------------- EXPRESSIONS ---------------- #

    def comparison(self):
        left = self.expression()

        if self.current() and self.current().type in (
            "EQ", "NEQ", "LT", "GT", "LE", "GE"
        ):
            op = self.eat(self.current().type).value
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
        left = self.factor()

        while self.current() and self.current().type in ("MULT", "DIV"):
            op = self.eat(self.current().type).value
            right = self.factor()
            left = BinaryOp(left, op, right)

        return left

    def factor(self):
        token = self.current()

        # number
        if token.type == "NUMBER":
            return Number(self.eat("NUMBER").value)

        if name == "len":
            self.eat("LPAREN")
            arg = self.comparison()
            self.eat("RPAREN")
            return FunctionCall("len", [arg])
        
        # list literal
        elif token.type == "LBRACKET":
            self.eat("LBRACKET")
            elements = []

            if self.current().type != "RBRACKET":
                elements.append(self.comparison())
                while self.current().type == "COMMA":
                    self.eat("COMMA")
                    elements.append(self.comparison())

            self.eat("RBRACKET")
            return ListLiteral(elements)

        # identifier
        elif token.type == "IDENT":
            name = self.eat("IDENT").value

            # Function call
            if self.current() and self.current().type == "LPAREN":
                self.eat("LPAREN")
                args = []

                if self.current().type != "RPAREN":
                    args.append(self.comparison())
                    while self.current().type == "COMMA":
                        self.eat("COMMA")
                        args.append(self.comparison())

                self.eat("RPAREN")
                return FunctionCall(name, args)

            # List indexing
            if self.current() and self.current().type == "LBRACKET":
                self.eat("LBRACKET")
                index = self.comparison()
                self.eat("RBRACKET")
                return ListAccess(name, index)

            # Attribute access or method call
            if self.current() and self.current().type == "DOT":
                self.eat("DOT")
                attr = self.eat("IDENT").value

                # Method call
                if self.current() and self.current().type == "LPAREN":
                    self.eat("LPAREN")
                    args = []

                    if self.current().type != "RPAREN":
                        args.append(self.comparison())
                        while self.current().type == "COMMA":
                            self.eat("COMMA")
                            args.append(self.comparison())

                    self.eat("RPAREN")
                    return MethodCall(name, attr, args)

                # Just attribute access
                return AttributeAccess(name, attr)

            return Variable(name)

            # function call
            if self.current() and self.current().type == "LPAREN":
                self.eat("LPAREN")
                args = []

                if self.current().type != "RPAREN":
                    args.append(self.comparison())
                    while self.current().type == "COMMA":
                        self.eat("COMMA")
                        args.append(self.comparison())

                self.eat("RPAREN")
                return FunctionCall(name, args)

            # list indexing
            if self.current() and self.current().type == "LBRACKET":
                self.eat("LBRACKET")
                index = self.comparison()
                self.eat("RBRACKET")
                return ListAccess(name, index)

            return Variable(name)

        # parenthesis
        elif token.type == "LPAREN":
            self.eat("LPAREN")
            expr = self.comparison()
            self.eat("RPAREN")
            return expr

        else:
            raise Exception("Invalid expression")