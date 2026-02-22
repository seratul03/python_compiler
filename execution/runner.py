import subprocess
import tempfile
import os
import shutil
import sys
import uuid
import threading
from compiler.lexer import tokenize
from compiler.parser import Parser
from compiler.bytecode import BytecodeGenerator
from compiler.vm import VirtualMachine
from compiler.semantic import SemanticAnalyzer
from compiler.optimizer import Optimizer
from compiler.ir import IRGenerator
from compiler.ir_to_bytecode import IRToBytecodeConverter

active_processes = {}

def start_process(user_code):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "main.py")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(user_code)

    process = subprocess.Popen(
        [sys.executable, "-u", file_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=temp_dir,
        bufsize=1
    )

    pid = str(uuid.uuid4())

    active_processes[pid] = {
        "process": process,
        "temp_dir": temp_dir,
        "buffer": ""
    }

    # Background thread to continuously read output, including prompts without newlines
    def reader():
        while True:
            chunk = process.stdout.read(1)
            if chunk == "":
                break
            if pid in active_processes:
                active_processes[pid]["buffer"] += chunk

    threading.Thread(target=reader, daemon=True).start()

    return pid


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

    if process.poll() is not None:
        cleanup(pid)
        return {"output": output, "finished": True}

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

def run_with_compiler(code):
    tokens = tokenize(code)
    parser = Parser(tokens)
    ast = parser.parse()

    analyzer = SemanticAnalyzer()
    analyzer.visit(ast)

    optimizer = Optimizer()
    ast = optimizer.visit(ast)

    # Generate IR
    ir_gen = IRGenerator()
    ir_code = ir_gen.generate(ast)

    # Convert IR → Bytecode
    converter = IRToBytecodeConverter(ir_code)
    instructions = converter.convert()

    vm = VirtualMachine(instructions)
    return vm.run()