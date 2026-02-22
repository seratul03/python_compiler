import re

TOKEN_SPEC = [
    ("EQ",       r'=='),
    ("NEQ",      r'!='),
    ("LE",       r'<='),
    ("GE",       r'>='),
    ("LT",       r'<'),
    ("GT",       r'>'),
    ("NUMBER",   r'\d+'),
    ("IDENT",    r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ("PLUS",     r'\+'),
    ("MINUS",    r'-'),
    ("MULT",     r'\*'),
    ("DIV",      r'/'),
    ("ASSIGN",   r'='),
    ("LPAREN",   r'\('),
    ("RPAREN",   r'\)'),
    ("COLON",    r':'),
    ("LBRACKET", r'\['),
    ("RBRACKET", r'\]'),
    ("DOT", r'\.'),
]

TOKEN_REGEX = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC)

class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"{self.type}:{self.value}"


def tokenize(code):
    tokens = []
    indent_stack = [0]
    lines = code.split("\n")

    for line in lines:
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")

        if indent > indent_stack[-1]:
            indent_stack.append(indent)
            tokens.append(Token("INDENT"))
        while indent < indent_stack[-1]:
            indent_stack.pop()
            tokens.append(Token("DEDENT"))

        for match in re.finditer(TOKEN_REGEX, stripped):
            kind = match.lastgroup
            value = match.group()

            if kind == "NUMBER":
                tokens.append(Token("NUMBER", int(value)))
            elif kind == "IDENT":
                tokens.append(Token("IDENT", value))
            else:
                tokens.append(Token(kind, value))

        tokens.append(Token("NEWLINE"))

    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token("DEDENT"))

    return tokens