from flask import Flask, request, jsonify, render_template
import subprocess
import tempfile
import os
from execution.runner import run_code


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def execute():
    data = request.json
    code = data.get("code", "")
    user_input = data.get("input", "")

    result = run_code(code, user_input)
    return jsonify(result)

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