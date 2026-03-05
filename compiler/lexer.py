import re

TOKEN_SPEC = [
    ("SKIP",         r"[ \t]+"),
    ("FLOAT",        r"\d+\.\d+"),          # must be before NUMBER
    ("NUMBER",       r"\d+"),
    ("STRING",       r'"[^"]*"|\'[^\']*\''), # single or double quotes
    ("EQ",           r"=="),
    ("NEQ",          r"!="),
    ("LE",           r"<="),
    ("GE",           r">="),
    ("POW_ASSIGN",   r"\*\*="),             # **= before ** and *=
    ("POW",          r"\*\*"),              # must be before MULT
    ("MULT_ASSIGN",  r"\*="),               # *= before *
    ("LT",           r"<"),
    ("GT",           r">"),
    ("IDENT",        r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("PLUS_ASSIGN",  r"\+="),               # += before +
    ("PLUS",         r"\+"),
    ("MINUS_ASSIGN", r"-="),                # -= before -
    ("MINUS",        r"-"),
    ("MULT",         r"\*"),
    ("DIV_ASSIGN",   r"/="),                # /= before /
    ("DIV",          r"/"),
    ("MOD_ASSIGN",   r"%="),                # %= before %
    ("MOD",          r"%"),
    ("ASSIGN",       r"="),
    ("LPAREN",       r"\("),
    ("RPAREN",       r"\)"),
    ("COLON",        r":"),
    ("COMMA",        r","),
    ("LBRACKET",     r"\["),
    ("RBRACKET",     r"\]"),
    ("DOT",          r"\.")
]

TOKEN_REGEX = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)

KEYWORDS = {
    "if":       "IF",
    "elif":     "ELIF",
    "else":     "ELSE",
    "while":    "WHILE",
    "for":      "FOR",
    "in":       "IN",
    "range":    "RANGE",
    "def":      "DEF",
    "return":   "RETURN",
    "class":    "CLASS",
    "print":    "PRINT",
    "break":    "BREAK",
    "continue": "CONTINUE",
    "pass":     "PASS",
    "True":     "TRUE",
    "False":    "FALSE",
    "None":     "NONE",
    "and":      "AND",
    "or":       "OR",
    "not":      "NOT",
    "is":       "IS",
    "lambda":   "LAMBDA",
    "import":   "IMPORT",
    "from":     "FROM",
    "as":       "AS",
    "with":     "WITH",
    "try":      "TRY",
    "except":   "EXCEPT",
    "finally":  "FINALLY",
    "raise":    "RAISE",
    "del":      "DEL",
    "global":   "GLOBAL",
    "nonlocal": "NONLOCAL",
    "yield":    "YIELD",
    "assert":   "ASSERT",
}


class Token:
    def __init__(self, type_, value=None, line=0, column=0):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"{self.type}:{self.value}"


def tokenize(code):
    tokens = []
    indent_stack = [0]
    code = code.replace("\r", "")
    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):

        # strip inline comments
        if "#" in line:
            in_string = False
            quote_char = None
            for ci, ch in enumerate(line):
                if in_string:
                    if ch == quote_char:
                        in_string = False
                elif ch in ('"', "'"):
                    in_string = True
                    quote_char = ch
                elif ch == "#":
                    line = line[:ci]
                    break

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")

        if indent > indent_stack[-1]:
            indent_stack.append(indent)
            tokens.append(Token("INDENT", line=line_num))

        while indent < indent_stack[-1]:
            indent_stack.pop()
            tokens.append(Token("DEDENT", line=line_num))

        pos = 0

        while pos < len(stripped):

            match = re.match(TOKEN_REGEX, stripped[pos:])

            if not match:
                raise SyntaxError(
                    f"Unexpected character '{stripped[pos]}' at line {line_num} column {pos}"
                )

            kind = match.lastgroup
            value = match.group()

            if kind == "SKIP":
                pos += len(value)
                continue

            elif kind == "FLOAT":
                tokens.append(Token("FLOAT", float(value), line_num, pos))

            elif kind == "NUMBER":
                tokens.append(Token("NUMBER", int(value), line_num, pos))

            elif kind == "STRING":
                # strip surrounding quotes (handles both ' and ")
                tokens.append(Token("STRING", value[1:-1], line_num, pos))

            elif kind == "IDENT" and value in KEYWORDS:
                tokens.append(Token(KEYWORDS[value], value, line_num, pos))

            elif kind == "IDENT":
                tokens.append(Token("IDENT", value, line_num, pos))

            else:
                tokens.append(Token(kind, value, line_num, pos))

            pos += len(value)

        tokens.append(Token("NEWLINE", line=line_num))

    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token("DEDENT"))

    return tokens