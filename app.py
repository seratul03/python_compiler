from flask import Flask, request, jsonify, render_template
from execution.runner import (
    run_with_compiler,
    get_debug_info,
    start_process,
    read_output,
    send_input,
    cleanup,
)

app = Flask(__name__)
app.json.ensure_ascii = False  # preserve Unicode characters (e.g. ₹) in JSON responses


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run():

    data = request.json
    code = data.get("code")

    try:
        result = run_with_compiler(code, True)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/start", methods=["POST"])
def start():
    data = request.json
    code = data.get("code", "")
    try:
        debug_info = get_debug_info(code)
        pid = start_process(code)
        return jsonify({"pid": pid, **debug_info})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/output/<pid>", methods=["GET"])
def get_output(pid):
    return jsonify(read_output(pid))


@app.route("/input/<pid>", methods=["POST"])
def give_input(pid):
    data = request.json
    user_input = data.get("input", "")
    return jsonify(send_input(pid, user_input))


@app.route("/stop/<pid>", methods=["POST"])
def stop(pid):
    cleanup(pid)
    return jsonify({"status": "stopped"})


if __name__ == "__main__":
    app.run(debug=True)