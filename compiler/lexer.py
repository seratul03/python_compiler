import re


def _is_hex(s):
    return len(s) > 0 and all(c in '0123456789abcdefABCDEF' for c in s)


def _unescape_string(s):
    import unicodedata
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = s[i + 1]
            if   c == 'n':  result.append('\n'); i += 2
            elif c == 't':  result.append('\t'); i += 2
            elif c == 'r':  result.append('\r'); i += 2
            elif c == '\\': result.append('\\'); i += 2
            elif c == '"':  result.append('"');  i += 2
            elif c == "'":  result.append("'");  i += 2
            elif c == 'a':  result.append('\a'); i += 2
            elif c == 'b':  result.append('\b'); i += 2
            elif c == 'f':  result.append('\f'); i += 2
            elif c == 'v':  result.append('\v'); i += 2
            elif c == '0':  result.append('\0'); i += 2
            elif c == 'x' and i + 3 < len(s) and _is_hex(s[i+2:i+4]):
                result.append(chr(int(s[i+2:i+4], 16))); i += 4
            elif c == 'u' and i + 5 < len(s) and _is_hex(s[i+2:i+6]):
                result.append(chr(int(s[i+2:i+6], 16))); i += 6
            elif c == 'U' and i + 9 < len(s) and _is_hex(s[i+2:i+10]):
                result.append(chr(int(s[i+2:i+10], 16))); i += 10
            elif c == 'N' and i + 2 < len(s) and s[i+2] == '{':
                end = s.find('}', i + 3)
                if end != -1:
                    try:
                        result.append(unicodedata.lookup(s[i+3:end]))
                        i = end + 1
                        continue
                    except KeyError:
                        pass
                result.append(s[i]); i += 1
            else:           result.append(s[i]); i += 1
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


TOKEN_SPEC = [
    ("SKIP",         r"[ \t]+"),
    ("FLOAT",        r"\d+\.\d+"),         
    ("NUMBER",       r"\d+"),
    ("FSTRING",      r'f"[^"]*"|f\'[^\']*\''),
    ("STRING",       r'"[^"]*"|\'[^\']*\''), 
    ("EQ",           r"=="),
    ("NEQ",          r"!="),
    ("LE",           r"<="),
    ("GE",           r">="),
    ("POW_ASSIGN",   r"\*\*="),           
    ("POW",          r"\*\*"),            
    ("MULT_ASSIGN",  r"\*="),            
    ("LT",           r"<"),
    ("GT",           r">"),
    ("IDENT",        r"[^\W\d]\w*"),
    ("PLUS_ASSIGN",  r"\+="),
    ("PLUS",         r"\+"),
    ("MINUS_ASSIGN", r"-="),             
    ("MINUS",        r"-"),
    ("MULT",         r"\*"),
    ("FLOORDIV_ASSIGN", r"//="),
    ("FLOORDIV",     r"//"),
    ("DIV_ASSIGN",   r"/="),               
    ("DIV",          r"/"),
    ("MOD_ASSIGN",   r"%="),                
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

    def _replace_tq(m):
        newlines = m.group(0).count('\n')
        return '""' + '\n' * newlines
    code = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', _replace_tq, code)

    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):
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

            elif kind == "FSTRING":
                tokens.append(Token("FSTRING", value[2:-1], line_num, pos))

            elif kind == "STRING":
                tokens.append(Token("STRING", _unescape_string(value[1:-1]), line_num, pos))

            elif kind == "IDENT":
                end = pos + len(value)
                while end < len(stripped) and (value + stripped[end]).isidentifier():
                    value += stripped[end]
                    end += 1
                if value in KEYWORDS:
                    tokens.append(Token(KEYWORDS[value], value, line_num, pos))
                else:
                    tokens.append(Token("IDENT", value, line_num, pos))

            else:
                tokens.append(Token(kind, value, line_num, pos))

            pos += len(value)

        tokens.append(Token("NEWLINE", line=line_num))

    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token("DEDENT"))

    return tokens