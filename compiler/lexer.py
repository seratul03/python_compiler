import re

# Token

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
    ("DOT",      r'\.'),
]

TOKEN_REGEX = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC)

# Keyword

KEYWORDS = {
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "print": "PRINT",
    "return": "RETURN",
}

# Token

class Token:
    def __init__(self, type_, value=None, line=0, column=0):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"{self.type}:{self.value}"

# Tokenizer

def tokenize(code):
    tokens = []
    indent_stack = [0]
    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")

        # Indent

        if indent > indent_stack[-1]:
            indent_stack.append(indent)
            tokens.append(Token("INDENT", line=line_num))

        while indent < indent_stack[-1]:
            indent_stack.pop()
            tokens.append(Token("DEDENT", line=line_num))

    #    Token match

        pos = 0
        while pos < len(stripped):

            match = re.match(TOKEN_REGEX, stripped[pos:])

            if not match:
                raise SyntaxError(
                    f"Unexpected character '{stripped[pos]}' "
                    f"at line {line_num} column {pos}"
                )

            kind = match.lastgroup
            value = match.group()

            # convert numbers
            if kind == "NUMBER":
                tokens.append(Token("NUMBER", int(value), line_num, pos))

            # check keywords
            elif kind == "IDENT" and value in KEYWORDS:
                tokens.append(Token(KEYWORDS[value], value, line_num, pos))

            elif kind == "IDENT":
                tokens.append(Token("IDENT", value, line_num, pos))

            else:
                tokens.append(Token(kind, value, line_num, pos))

            pos += len(value)

        tokens.append(Token("NEWLINE", line=line_num))

    # close remaining indents
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token("DEDENT"))

    return tokens