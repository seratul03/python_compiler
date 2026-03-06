# PyFlux — Custom Compiler & Web IDE

A full, multi-stage compilation pipeline for a Python-like language, paired with a browser-based code editor. Write code, run it, and inspect every stage of compilation — AST, control flow graph, IR, and bytecode — all from one interface.

---

## Features

- **10-stage compiler pipeline** — Lexer → Parser → Semantic Analyzer → Optimizer → IR → Bytecode Generator → Virtual Machine + CFG & AST visualizers
- **Web IDE** — Monaco Editor (the same editor used in VS Code) served via Flask
- **Interactive debug visualizations** — collapsible, color-coded AST tree; CFG graph; disassembled bytecode
- **Intermediate Representation (IR)** — three-address code stage for further analysis and optimization
- **Interactive execution** — programs that call `input()` prompt an inline input dialog in the browser
- **AST optimizer** — constant folding, dead code elimination, branch simplification, algebraic rewrites
- **OOP support** — classes, inheritance, `super()`, instance methods, `__str__()`, augmented attribute/index assignment
- **Sandboxed execution** — code runs in isolated subprocesses with a restricted built-ins whitelist
- **Security hardening** — blocks dangerous patterns (`import`, `open`, `eval`, `exec`, `__import__`) before execution
- **Async process management** — long-running processes polled with thread-safe output buffering

---

## Compilation Pipeline

```
Source Code
    │
    ▼
 Lexer                →  Token stream (40+ token types, indentation handling)
    │
    ▼
 Parser               →  Abstract Syntax Tree (42+ node types)
    │
    ▼
 Semantic Analyzer    →  Scope checking, variable & function validation
    │
    ▼
 Optimizer            →  Constant folding, dead code elimination,
                          branch simplification, algebraic rewrites
    │
    ▼
 IR Generator         →  Three-address intermediate representation
    │
    ▼
 Bytecode Generator   →  Stack machine instructions (20+ opcodes)
    │
    ▼
 Virtual Machine      →  Frame-based execution; functions, classes,
                          built-ins, break/continue, __str__

 ─── Analysis stages (run in parallel) ───────────────────────────
 CFG Builder          →  Control Flow Graph (nodes + edges)
 AST Visualizer       →  JSON tree for interactive UI rendering
 Disassembler         →  Human-readable bytecode listing
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`

### Installation

```bash
git clone https://github.com/seratul03/python_compiler
cd compiler
pip install flask
```

### Running

```bash
python app.py
```

Open your browser and go to `http://localhost:5000`.

---

## Usage

1. Write code in the editor on the left.
2. Click **Run Code** or press **Ctrl + Enter**.
3. Use the tabs on the right to inspect results:

| Tab | Contents |
|-----|----------|
| **Output** | Standard output from the program |
| **AST** | Color-coded, collapsible Abstract Syntax Tree |
| **CFG** | Control Flow Graph — nodes and edges |
| **Bytecode** | Disassembled stack machine instructions |

4. If your program calls `input()`, an inline input bar appears automatically.
5. Click **Reset** to clear the editor and all output tabs.

---

## Language Reference

The language is a subset of Python. Supported constructs:

### Types & Literals

| Type | Examples |
|------|---------|
| Integer | `42`, `-7` |
| Float | `3.14`, `-0.5` |
| String | `"hello"`, `'world'` |
| Boolean | `True`, `False` |
| None | `None` |

### Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+`, `-`, `*`, `/`, `%`, `**` |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Boolean | `and`, `or`, `not` |
| Membership | `in`, `is` |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `**=` |

### Constructs

| Feature | Example |
|---------|---------|
| Variables & assignment | `x = 42` |
| Augmented assignment | `x += 1` |
| Conditionals | `if / elif / else` |
| While loops | `while x > 0:` |
| For loops | `for i in range(10):` |
| Break & continue | `break`, `continue` |
| Pass | `pass` |
| Functions | `def greet(name):` |
| Return | `return value` |
| Classes & inheritance | `class Dog(Animal):` |
| `super()` | `super().method()` |
| `__str__` | `def __str__(self):` |
| List literals | `[1, 2, 3]` |
| Index access / assignment | `arr[0]`, `arr[i] = x` |
| Augmented index assignment | `arr[i] += 1` |
| Augmented attribute assignment | `obj.x += 1` |
| List comprehensions | `[x * 2 for x in items]` |
| String & list methods | `.append()`, `.upper()`, etc. |
| Comments | `# this is a comment` |

### Built-in Functions

| Category | Functions |
|----------|-----------|
| I/O | `print()`, `input()` |
| Type conversion | `int()`, `float()`, `str()`, `bool()` |
| Collections | `list()`, `tuple()`, `dict()`, `set()` |
| Iteration | `range()`, `enumerate()`, `zip()`, `map()`, `filter()`, `reversed()`, `sorted()` |
| Math | `abs()`, `round()`, `sum()`, `min()`, `max()` |
| Utilities | `len()`, `type()`, `isinstance()`, `hasattr()`, `getattr()`, `setattr()` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the web IDE |
| `POST` | `/run` | Compile and run code; returns output + debug info (AST, CFG, bytecode) |
| `POST` | `/start` | Start an async process; returns PID + initial debug info |
| `GET` | `/output/<pid>` | Poll stdout of a running process; returns output + `finished` flag |
| `POST` | `/input/<pid>` | Send a line of input to a running process |
| `POST` | `/stop/<pid>` | Kill a running process and clean up temp files |

---

## Security

Code is executed in a sandboxed subprocess with:

- **Forbidden patterns** — `import os`, `import sys`, `import subprocess`, `__import__`, `open(`, `eval(`, `exec(` are blocked before execution
- **Restricted built-ins** — only a safe whitelist is available inside the sandbox (`print`, `input`, `len`, `range`, `int`, `float`, `str`, `bool`, `list`, `dict`, `set`, `tuple`, `sum`, `min`, `max`, `enumerate`)
- **Process isolation** — each run gets a unique UUID and a temporary directory that is cleaned up on exit
- **Thread-safe I/O** — output is buffered via background threads to prevent blocking

---

## Project Structure

```
compiler/
├── lexer.py              # Tokenizer
├── parser.py             # AST builder
├── ast_nodes.py          # 42+ AST node definitions
├── semantic.py           # Scope & variable validation
├── semantic_analyzer.py  # Visitor-based semantic checks
├── optimizer.py          # AST-level optimizations
├── ir.py                 # Intermediate representation
├── ir_to_bytecode.py     # IR → bytecode converter
├── bytecode.py           # Bytecode instruction emitter
├── disassembler.py       # Human-readable bytecode output
├── vm.py                 # Stack-based virtual machine
├── cfg.py                # Control flow graph builder
├── ast_visualizer.py     # AST → JSON for UI rendering
execution/
├── runner.py             # Compiler orchestration + process management
├── sandbox.py            # Safe execution environment
templates/
└── index.html            # Web IDE (Monaco Editor)
static/
├── style.css             # UI styles
└── script.js             # Frontend logic
app.py                    # Flask server & API routes
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `Flask` | Web server and REST API |
| `Monaco Editor` (CDN) | Browser-based code editor |
| `subprocess`, `threading`, `uuid`, `tempfile` | Sandboxed async process execution (stdlib only) |