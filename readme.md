# PyFlux Compiler + Web IDE

PyFlux is a Python-like language compiler with a browser IDE. It lexes and parses source, runs semantic checks and AST optimizations, emits custom bytecode, and executes on a stack-based VM with a threshold-based JIT for hot functions. The web UI (Monaco Editor) lets you run code and inspect AST, CFG, and bytecode in one place.

## Highlights

- Multi-stage compiler: lexer, parser, semantic checks, optimizer, bytecode generator, VM
- Optional JIT: hot functions compile to native Python after a call threshold (default 10)
- Web IDE: Monaco editor, AST tree, CFG view, and disassembled bytecode
- Async execution: /start + /output polling with inline input() support
- Optional AI mode: pre-run and post-run checks via Groq API

## Compilation pipeline

```
Source
   -> Lexer (token stream)
   -> Parser (AST)
   -> Semantic analyzer (scopes, undefined names, loop rules)
   -> AST optimizer (constant folding, dead code removal)
   -> Bytecode generator (stack machine)
   -> Virtual machine
   -> JIT compiler (hot functions only)

Analysis outputs (parallel to execution):
   - AST visualizer
   - CFG builder
   - Bytecode disassembler
```

## Web IDE and API

The Flask app exposes a small API used by the UI:

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | / | Web IDE |
| POST | /run | Compile and run (sync). Returns output + AST/CFG/bytecode. |
| POST | /start | Start async run. Returns PID + debug info. |
| GET | /output/<pid> | Poll output for async run. |
| POST | /input/<pid> | Send a line of input to a running process. |
| POST | /stop/<pid> | Stop a running process. |

## AI mode (optional)

AI checks are optional and used only when the UI toggle is enabled. The backend calls Groq for:

- Pre-run checks (basic fixes before execution)
- Post-run analysis when a runtime error occurs
- Chat-based help about code, errors, and improvements

Set GROQ_API_KEY and GROQ_MODEL in a .env file to enable AI mode. Without them, the UI still works and the compiler runs normally.

## Language support (Python-like)

The parser and VM implement a wide slice of Python syntax, including:

- Types: int, float, string, bool, None, list, tuple, dict, set
- Expressions: arithmetic, comparison, boolean, bitwise, unary, ternary (x if c else y)
- Control flow: if/elif/else, while, for and for ... in, break, continue, pass
- Functions: def, return, default args, *args, **kwargs, keyword args
- Lambdas, decorators, super() calls
- List/dict/set comprehensions and generator expressions
- Indexing and slicing (a[0], a[1:3]), attribute access, and method calls
- Exceptions: try/except/else/finally, raise, assert
- Imports: import and from ... import ...
- F-strings (parsed and emitted as AST nodes)

## Running locally

### Prerequisites

- Python 3.10+
- pip

### Install

```bash
pip install flask requests python-dotenv
```

### Configure (optional)

Create a .env file if you want AI mode:

```
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### Run

```bash
python app.py
```

Open http://localhost:5000.

## Security notes

Execution safety is intentionally minimal and meant for local, trusted use:

- The async runner executes user code in a subprocess with only a small pattern check.
- safe_exec falls back to a permissive builtins map to keep the IDE usable.
- Treat this as a learning tool, not a hardened sandbox.

## Project structure

```
app.py                  # Flask server and API routes
ai/
   ai_checker.py         # Groq pre/post checks
   groq_client.py        # Groq API client
compiler/
   lexer.py              # Tokenizer
   parser.py             # AST builder
   ast_nodes.py          # AST node definitions
   semantic.py           # Semantic checks (scopes, loop rules)
   semantic_analyzer.py  # Legacy semantic pass (unused)
   optimizer.py          # AST-level optimizations
   ir.py                 # Intermediate representation (IR)
   ir_to_bytecode.py     # IR -> bytecode converter
   bytecode.py           # Bytecode emitter
   disassembler.py       # Bytecode disassembler
   vm.py                 # Stack-based VM
   jit.py                # JIT compiler
   cfg.py                # Control flow graph builder
   ast_visualizer.py     # AST -> text/JSON
execution/
   runner.py             # Compiler orchestration and async process handling
   sandbox.py            # Placeholder (unused)
static/
   script.js             # Frontend logic
   style.css             # UI styles
templates/
   index.html            # Web IDE
```
