from flask import Flask, request, jsonify, render_template
import subprocess
import tempfile
import os
from execution.runner import cleanup
from execution.runner import start_process, send_input, read_output


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run():
    code = request.json.get("code")
    pid = start_process(code)
    return jsonify({"pid": pid})


@app.route("/input", methods=["POST"])
def input_to_process():
    pid = request.json.get("pid")
    user_input = request.json.get("input")
    return jsonify(send_input(pid, user_input))

@app.route("/output", methods=["POST"])
def get_output():
    pid = request.json.get("pid")
    return jsonify(read_output(pid))

@app.route("/reset", methods=["POST"])
def reset():
    pid = request.json.get("pid")
    cleanup(pid)
    return jsonify({"status": "terminated"})

# Duplicate code is here. REMOVED - DO NOT ADD THIS AGAIN YOU IDIOT
# def run_code():
#     code = request.json.get("code")
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp:
#         temp.write(code.encode())
#         temp_path = temp.name

#     try:
#         result = subprocess.run(
#             ["python", temp_path],
#             capture_output=True,
#             text=True,
#             timeout=5
#         )

#         output = result.stdout
#         error = result.stderr

#         return jsonify({
#             "output": output,
#             "error": error
#         })

#     except subprocess.TimeoutExpired:
#         return jsonify({"error": "Execution timed out."})

#     finally:
#         os.remove(temp_path)

if __name__ == "__main__":
    app.run(debug=True)