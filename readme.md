# 🐍 Small Python Compiler (local)

Hi — this repository contains a compact, local compiler/runtime project used to experiment with parsing, IR, bytecode, and a small VM for running Python-like code.

It’s purpose-built for learning and local experimentation rather than production use.

---

## What it is

- A tiny compiler toolchain that includes a lexer, parser, IR, optimizer, bytecode generator, and a simple VM.
- A lightweight web UI / runner for experimenting with code snippets (where present).

---

## Tech stack

- Python 3
- Standard library + small project modules (no heavy framework required to inspect core components)

---

## Project layout

```
.
├── app.py                # Optional web front-end (if present)
├── readme.md
├── compiler/             # Compiler implementation
│   ├── lexer.py
│   ├── parser.py
│   ├── ast_nodes.py
│   ├── ir.py
│   ├── ir_to_bytecode.py
│   ├── bytecode.py
│   ├── optimizer.py
│   ├── semantic.py
│   └── vm.py
├── execution/            # Runner / sandbox helpers
│   ├── runner.py
│   └── sandbox.py
├── templates/            # (Optional) HTML templates for the web UI
└── static/               # (Optional) client JS/CSS
```

Only files present in the repository are listed above — this README no longer references external or unrelated files.

---

## Quick start

Run a small example or inspect modules directly from Python.

1) From the project root, run a REPL or a simple script:

```powershell
python -c "import compiler.lexer as L; print('Lexer loaded', L)"
```

2) See there is an `app.py` web UI; start it locally:

```powershell
python app.py
# then open http://127.0.0.1:5000/ for accessing the UI
```

---

## Safety & scope

This project runs code locally and is intended for experimentation. Do not expose it as-is to untrusted users — it lacks robust sandboxing and hard execution limits.

---

## License
This is free to all project. You can absolutely take this code and add it in your project or anywhere. 