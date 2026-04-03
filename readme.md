# PyFlux

**PyFlux** is a Python-like compiler and execution engine with a web-based IDE. It features a full compilation pipeline, a custom stack-based virtual machine, and a hybrid execution model that enables both controlled experimentation and practical support for real-world code.

---

## Features

* End-to-end compilation pipeline:

  * Lexer → Parser → AST → Semantic Analysis → Optimization → Bytecode
* Custom stack-based virtual machine for execution
* Hybrid execution support for advanced Python features
* Interactive web IDE with:

  * AST visualization
  * CFG (Control Flow Graph)
  * Intermediate Representation (IR)
  * Bytecode inspection
* Interactive run mode with stdin support
* Optional AI assistance:

  * Pre-execution code analysis
  * Post-run review
  * Chat-based help

---

## Execution Model

PyFlux uses a **hybrid execution architecture**:

* **Custom VM Execution**
  Core language constructs (e.g., arithmetic, variables, control flow) are compiled into custom bytecode and executed on a stack-based virtual machine.

* **Python Runtime Delegation**
  For unsupported or advanced features (e.g., external libraries, complex runtime behavior, ML workloads), execution is delegated to the Python runtime.

This design allows PyFlux to balance:

* Low-level control and visibility into execution
* Practical compatibility with real-world Python code

---

## Architecture Overview

1. **Lexer** → Tokenizes source code
2. **Parser** → Builds Abstract Syntax Tree (AST)
3. **Semantic Analysis** → Scope resolution and validation
4. **Optimizer** → Constant folding, dead code elimination
5. **Bytecode Generator** → Custom instruction set
6. **Virtual Machine** → Stack-based execution engine

---

## Web IDE

The built-in web interface provides deep insight into program execution:

* AST visualization
* CFG (Control Flow Graph)
* IR inspection
* Bytecode view
* Runtime output console
* Matplotlib rendering support (when applicable)

---

## Requirements

* Python 3.9+
* Dependencies listed in `requirements.txt`

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run

```bash
python app.py
```

Then open:

```
http://127.0.0.1:5000
```

---

## Optional AI Mode (Groq)

AI features are disabled by default.

To enable, create a `.env` file in the project root:

```env
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=your_model_id_here
```

---

## Project Structure

```
app.py                # Flask server and API endpoints
ai/                   # AI precheck, analysis, and chat modules
compiler/             # Core compiler, optimizer, VM
execution/            # Execution runner and sandboxing
templates/            # Web UI templates
static/               # Frontend assets
```

---

## Security Notes

* Execution is sandboxed with restricted imports
* Only allowlisted modules and safe prefixes are permitted
* External code execution should be used cautiously in untrusted environments

---

## Limitations

* Not all Python features are supported in the custom VM
* Some advanced behaviors rely on Python runtime delegation
* Full Python compatibility is not guaranteed
* Performance may vary depending on execution path (VM vs Python runtime)

---

## Purpose

PyFlux is designed for:

* Learning and experimenting with compiler design
* Understanding execution pipelines (AST → IR → Bytecode → VM)
* Visualizing program structure and transformations
* Bridging theoretical concepts with practical execution

---

## Summary

PyFlux is not just a compiler—it is a **hybrid execution system** that combines:

* Custom VM-based execution
* Real-world Python interoperability
* Deep introspection via a web IDE
