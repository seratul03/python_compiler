# PyFlux

PyFlux is a custom Python-like compiler with a web-based IDE. It compiles source code to custom bytecode and executes it on a stack-based virtual machine. The UI includes AST, CFG, and bytecode views, plus optional AI guidance.

## Features

- Full compilation pipeline: lexer, parser, semantic analyzer, optimizer, bytecode generator, VM
- Debug panels for AST, CFG, and bytecode
- Interactive run mode with stdin support
- Optional AI precheck, post-run review, and chat

## Architecture (high level)

1. Lexer -> tokens
2. Parser -> AST
3. Semantic analysis -> scope and validation
4. Optimizer -> constant folding and dead code pruning
5. Bytecode generation -> custom instruction set
6. Virtual machine -> stack-based execution

## Requirements

- Python 3.9+
- See requirements.txt for Python packages

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Optional AI Mode (Groq)

AI mode is off by default. To enable it, create a .env file in the project root and set:

```env
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=your_model_id_here
```

## Project Structure

- app.py: Flask web server and API endpoints
- ai/: AI precheck, runtime analysis, and chat helpers
- compiler/: core compiler, optimizer, and VM
- execution/: execution runner and sandbox helpers
- templates/: web UI template
- static/: UI assets

## Notes

- The VM restricts imports to an allowlist and a few safe prefixes.
- Matplotlib output is captured and rendered in the UI when available.
