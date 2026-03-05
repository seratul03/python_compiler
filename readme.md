# Custom Compiler & Web IDE

A full compilation pipeline for a Python-like language, paired with a browser-based code editor. Write code, run it, and inspect every stage of compilation — tokens, AST, control flow graph, and bytecode — all from one interface.

---

## Features

- **Full compiler pipeline** — Lexer → Parser → Semantic Analyzer → Optimizer → Bytecode Generator → Virtual Machine
- **Web IDE** — Monaco Editor (the same editor used in VS Code) served via Flask
- **Debug visualizations** — view the AST, CFG, and disassembled bytecode for any program
- **Interactive execution** — programs that call `input()` prompt a dialog in the browser
- **AST optimizer** — constant folding, dead code elimination, branch simplification
- **OOP support** — classes, inheritance, instance methods, and `super()`
- **Security hardening** — blocks dangerous patterns (`import`, `open`, `eval`, `__import__`) before execution

---

## Compilation Pipeline

```
Source Code
    │
    ▼
 Lexer           →  Token stream
    │
    ▼
 Parser          →  Abstract Syntax Tree 
    │
    ▼
 Semantic        →  Scope checking, variable validation
 Analyzer
    │
    ▼
 Optimizer       →  Constant folding, dead code elimination
    │
    ▼
 Bytecode        →  Stack machine instructions
    │
    ▼
 Virtual         →  Executes bytecode; supports functions, classes,
 Machine            built-in callables, break/continue
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`

### Installation

```bash
git clone <repo-url>
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
| **AST** | Abstract Syntax Tree hierarchy |
| **CFG** | Control Flow Graph (nodes and edges) |
| **Bytecode** | Disassembled bytecode instructions |

4. If your program calls `input()`, an input dialog will appear automatically.
5. Click **Reset** to clear the editor and output.

---

## Language Reference

The language is a subset of Python. Supported constructs:

| Feature | Example |
|---------|---------|
| Variables & assignment | `x = 42` |
| Augmented assignment | `x += 1` |
| Arithmetic & comparison | `x * 2`, `x >= 10` |
| Conditionals | `if / elif / else` |
| While loops | `while x > 0:` |
| For loops | `for i in range(10):` |
| Break & continue | `break`, `continue` |
| Functions | `def greet(name):` |
| Classes & inheritance | `class Dog(Animal):` |
| List comprehensions | `[x * 2 for x in items]` |
| String & list methods | `.append()`, `.upper()`, etc. |
| Built-ins | `print()`, `input()`, `range()`, `len()`, `type()` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the web IDE |
| `POST` | `/run` | Compile and run code; returns output + debug info |
| `POST` | `/start` | Start a long-running process (returns PID) |
| `GET` | `/output/<pid>` | Poll stdout of a running process |
| `POST` | `/input/<pid>` | Send a line of input to a running process |
| `POST` | `/stop/<pid>` | Kill a running process |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `Flask` | Web server and API |
| `Monaco Editor` (CDN) | Browser code editor |