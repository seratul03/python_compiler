import ast as _ast_mod
import dis as _dis_mod
import tokenize as _tokenize_mod
import token as _token_mod
import types as _types_mod
import sys
import io
import contextlib
import traceback
import builtins as _builtins_mod
import os
import time
import threading
import json
import uuid
import tempfile
import pathlib
import logging
import pprint
import inspect
import subprocess
import shutil
import io
import textwrap

from compiler.lexer import tokenize
from compiler.parser import Parser
from compiler.bytecode import BytecodeGenerator
from compiler.vm import VirtualMachine
from compiler.semantic import SemanticAnalyzer
from compiler.optimizer import Optimizer
from compiler.ir import IRGenerator
from compiler.ir_to_bytecode import IRToBytecodeConverter
from compiler.ast_visualizer import ASTVisualizer
from compiler.cfg import CFGBuilder
from compiler.disassembler import BytecodeDisassembler

active_processes = {}

SAFE_BUILTINS = {
    "print": print,
    "input": input,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sorted": sorted,
    "reversed": reversed,
    "map": map,
    "filter": filter,
    "zip": zip,
    "chr": chr,
    "ord": ord,
    "hex": hex,
    "oct": oct,
    "bin": bin,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "hasattr": hasattr,
    "getattr": getattr,
    "setattr": setattr,
    "delattr": delattr,
    "callable": callable,
    "type": type,
    "id": id,
    "hash": hash,
    "repr": repr,
    "format": format,
    "open": open,
    "iter": iter,
    "next": next,
    "object": object,
    "super": super,
    "property": property,
    "staticmethod": staticmethod,
    "classmethod": classmethod,
    "vars": vars,
    "dir": dir,
    "help": help,
    "NotImplemented": NotImplemented,
    "Ellipsis": ...,
    "__import__": __import__,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "NameError": NameError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,
    "ZeroDivisionError": ZeroDivisionError,
    "FileNotFoundError": FileNotFoundError,
    "IOError": IOError,
    "OSError": OSError,
    "ImportError": ImportError,
    "NotImplementedError": NotImplementedError,
    "AssertionError": AssertionError,
    "OverflowError": OverflowError,
    "RecursionError": RecursionError,
    "MemoryError": MemoryError,
    "PermissionError": PermissionError,
    "TimeoutError": TimeoutError,
    "UnicodeError": UnicodeError,
    "UnicodeDecodeError": UnicodeDecodeError,
    "UnicodeEncodeError": UnicodeEncodeError,
    "KeyboardInterrupt": KeyboardInterrupt,
    "SystemExit": SystemExit,
    "BaseException": BaseException,
    "ArithmeticError": ArithmeticError,
    "LookupError": LookupError,
    "ast": _ast_mod,
    "dis": _dis_mod,
    "tokenize": _tokenize_mod,
    "token": _token_mod,
    "types": _types_mod,
    "sys": sys,
    "io": io,
    "contextlib": contextlib,
    "traceback": traceback,
    "builtins": _builtins_mod,
    "os": os,
    "time": time,
    "threading": threading,
    "json": json,
    "uuid": uuid,
    "tempfile": tempfile,
    "pathlib": pathlib,
    "logging": logging,
    "pprint": pprint,
    "inspect": inspect,
    "subprocess": subprocess,
}

INPUT_MARKER = "__PYFLUX_INPUT__"
IMAGE_MARKER = "__PYFLUX_IMAGE__"
IMAGE_ERROR_MARKER = "__PYFLUX_IMAGE_ERROR__"
INPUT_BOOTSTRAP = textwrap.dedent(
    f"""\
import builtins as __builtins__
import sys as __sys__

__pyflux_input_marker = {INPUT_MARKER!r}
__pyflux_image_marker = {IMAGE_MARKER!r} + ":"
__pyflux_image_error_marker = {IMAGE_ERROR_MARKER!r} + ":"
__pyflux_original_input = __builtins__.input
__pyflux_original_import = __builtins__.__import__
__pyflux_patching = False

def __pyflux_input(prompt=""):
    if prompt:
        __sys__.stdout.write(str(prompt))
        __sys__.stdout.flush()
    __sys__.stdout.write(__pyflux_input_marker + "\\n")
    __sys__.stdout.flush()
    return __pyflux_original_input()

def __pyflux_patch_matplotlib():
    global __pyflux_patching
    if __pyflux_patching:
        return
    __pyflux_patching = True
    try:
        import matplotlib.pyplot as __plt__
    except Exception:
        __pyflux_patching = False
        return
    try:
        if getattr(__plt__, "__pyflux_patched__", False):
            return

        def __pyflux_show(*args, **kwargs):
            try:
                import io as __io__
                import base64 as __base64__
                buf = __io__.BytesIO()
                __plt__.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                payload = __base64__.b64encode(buf.read()).decode("ascii")
                __sys__.stdout.write(__pyflux_image_marker + payload + "\\n")
                __sys__.stdout.flush()
            except Exception as __e:
                __sys__.stdout.write(
                    __pyflux_image_error_marker + str(__e) + "\\n"
                )
                __sys__.stdout.flush()
            finally:
                try:
                    __plt__.close("all")
                except Exception:
                    pass

        __plt__.show = __pyflux_show
        __plt__.__pyflux_patched__ = True
    finally:
        __pyflux_patching = False

def __pyflux_import(name, globals=None, locals=None, fromlist=(), level=0):
    mod = __pyflux_original_import(name, globals, locals, fromlist, level)
    if isinstance(name, str) and name.startswith("matplotlib"):
        __pyflux_patch_matplotlib()
    return mod

__builtins__.input = __pyflux_input
__builtins__.__import__ = __pyflux_import
"""
)

import importlib as _importlib
for _mod_name in ("graphviz", "resource", "symtable", "codeop", "signal"):
    try:
        SAFE_BUILTINS[_mod_name] = _importlib.import_module(_mod_name)
    except ImportError:
        pass


def security_check(code):
    """Basic security check — blocks only truly dangerous operations."""
    _dangerous = [
        "__import__('os').system",
        "ctypes.cdll",
        "ctypes.CDLL",
    ]
    for pat in _dangerous:
        if pat in code:
            raise Exception(f"SecurityError: '{pat}' is not allowed.")


def format_error(e):
    name = type(e).__name__
    message = str(e)

    return {
        "type": name,
        "message": message,
        "formatted": f"{name}: {message}"
    }

def start_process(user_code, ai_mode=False):

    security_check(user_code)

    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "main.py")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(INPUT_BOOTSTRAP)
        f.write("\n")
        f.write(user_code)

    process = subprocess.Popen(
        [sys.executable, "-u", file_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        cwd=temp_dir,
        bufsize=1,
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "MPLBACKEND": "Agg",
        },
    )

    pid = str(uuid.uuid4())

    active_processes[pid] = {
        "process": process,
        "temp_dir": temp_dir,
        "buffer": "",
        "full_output": "",
        "ai_mode": ai_mode,
        "code": user_code,
        "ai_post_result": None,
        "start_time": time.perf_counter(),
    }

    def reader():
        try:
            while True:
                chunk = process.stdout.read(1)
                if chunk == "":
                    break

                if pid in active_processes:
                    active_processes[pid]["buffer"] += chunk
        except:
            pass

    threading.Thread(target=reader, daemon=True).start()

    return pid

def get_debug_info(code):
    """Compile code and return AST/CFG/bytecode debug info without executing."""
    try:
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        analyzer.visit(ast)

        optimizer = Optimizer()
        ast = optimizer.visit(ast)

        gen = BytecodeGenerator()
        instructions = gen.generate(ast)

        ast_vis = ASTVisualizer()
        ast_tree = ast_vis.render(ast)
        ast_json_data = ast_vis.render_json(ast)

        cfg_builder = CFGBuilder()
        cfg = cfg_builder.build(ast)
        cfg_text = cfg_builder.render(cfg)

        dis = BytecodeDisassembler()
        bytecode_text = dis.disassemble(instructions)

        return {"ast": ast_tree, "ast_json": ast_json_data, "cfg": cfg_text, "bytecode": bytecode_text}
    except Exception:
        return {"ast": "", "ast_json": None, "cfg": "", "bytecode": ""}


def safe_exec(code, input_data=""):

    old_stdout = sys.stdout
    old_stdin = sys.stdin

    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO(input_data)

    safe_globals = {"__builtins__": SAFE_BUILTINS, "__name__": "__main__"}

    try:
        exec(code, safe_globals)
        output = sys.stdout.getvalue()

        return {"output": output}

    except Exception as e:

        return {
            "error": {
                "type": type(e).__name__,
                "message": str(e)
            }
        }

    finally:
        sys.stdout = old_stdout
        sys.stdin = old_stdin


def send_input(pid, user_input):

    if pid not in active_processes:
        return {"error": "Process not found."}

    process = active_processes[pid]["process"]

    try:
        process.stdin.write(user_input + "\n")
        process.stdin.flush()
        return {"status": "sent"}
    except:
        return {"error": "Execution error."}


def read_output(pid):

    if pid not in active_processes:
        return {"error": "Process not found."}

    process_data = active_processes[pid]
    process = process_data["process"]

    output = process_data["buffer"]
    process_data["buffer"] = ""
    if output:
        process_data["full_output"] += output

    if process.poll() is not None:
        duration = time.perf_counter() - process_data.get("start_time", time.perf_counter())
        response = {"output": output, "finished": True, "runtime_seconds": duration}

        runtime_error = ""
        if process.returncode not in (0, None):
            runtime_error = process_data.get("full_output", "")
            response["runtime_error"] = runtime_error

        if process_data.get("ai_mode"):
            if process_data.get("ai_post_result") is None:
                if runtime_error:
                    from ai.ai_checker import analyze_output
                    response_ai = analyze_output(
                        process_data.get("code", ""),
                        process_data.get("full_output", ""),
                        runtime_error,
                    )
                else:
                    from ai.ai_checker import review_success
                    response_ai = review_success(
                        process_data.get("code", ""),
                        process_data.get("full_output", ""),
                        response.get("runtime_seconds", 0.0),
                    )
                process_data["ai_post_result"] = response_ai

            response["ai_postcheck"] = process_data.get("ai_post_result")

        cleanup(pid)
        return response

    return {"output": output}


def cleanup(pid):

    if pid in active_processes:

        process = active_processes[pid]["process"]
        temp_dir = active_processes[pid]["temp_dir"]

        try:
            process.kill()
        except:
            pass

        shutil.rmtree(temp_dir, ignore_errors=True)

        del active_processes[pid]


def reset_runtime():

    global active_processes

    for pid in list(active_processes.keys()):
        try:
            active_processes[pid]["process"].kill()
        except:
            pass

    active_processes = {}

def run_with_compiler(code, debug=False):

    try:
        tokens = tokenize(code)

        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        analyzer.visit(ast)

        optimizer = Optimizer()
        ast = optimizer.visit(ast)

        from compiler.bytecode import BytecodeGenerator
        gen = BytecodeGenerator()
        instructions = gen.generate(ast)
        original_instructions = list(instructions) 

        vm = VirtualMachine(instructions)
        inputs = code.split("__INPUT__")
        input_buffer = inputs[1].split("\n") if len(inputs) > 1 else []

        def fake_input(prompt=""):
            if input_buffer:
                return input_buffer.pop(0)
            return ""
        
        vm._input_provider = fake_input
        output = vm.run()

    except Exception as compiler_error:
        return safe_exec(code)

    if debug:

        ast_vis = ASTVisualizer()
        ast_tree = ast_vis.render(ast)

        cfg_builder = CFGBuilder()
        cfg = cfg_builder.build(ast)
        cfg_text = cfg_builder.render(cfg)

        dis = BytecodeDisassembler()
        bytecode_text = dis.disassemble(original_instructions)

        return {
            "ast": ast_tree,
            "cfg": cfg_text,
            "bytecode": bytecode_text,
            "output": output
        }

    return {"output": output}