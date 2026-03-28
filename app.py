from flask import Flask, request, jsonify, render_template
import time
from ai.ai_checker import check_code, analyze_output, chat_with_ai, review_success
from execution.runner import (
    run_with_compiler,
    get_debug_info,
    start_process,
    read_output,
    send_input,
    cleanup,
)

app = Flask(__name__)
app.json.ensure_ascii = False 

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run():

    data = request.json
    code = data.get("code", "")
    ai_mode = bool(data.get("ai_mode"))
    ai_precheck = check_code(code) if ai_mode else None

    try:
        start_time = time.perf_counter()
        result = run_with_compiler(code, True)
        runtime_seconds = time.perf_counter() - start_time
        result["runtime_seconds"] = runtime_seconds
        if ai_precheck is not None:
            result["ai_precheck"] = ai_precheck

        if ai_mode and "error" in result:
            error = result.get("error")
            if isinstance(error, dict):
                error_text = error.get("message") or error.get("formatted") or ""
            else:
                error_text = str(error)

            if error_text:
                result["ai_postcheck"] = analyze_output(code, result.get("output", ""), error_text)
        elif ai_mode:
            result["ai_postcheck"] = review_success(
                code,
                result.get("output", ""),
                runtime_seconds,
            )
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/start", methods=["POST"])
def start():
    data = request.json
    code = data.get("code", "")
    try:
        ai_mode = bool(data.get("ai_mode"))
        ai_precheck = check_code(code) if ai_mode else None
        debug_info = get_debug_info(code)
        pid = start_process(code, ai_mode=ai_mode)
        response = {"pid": pid, **debug_info}
        if ai_precheck is not None:
            response["ai_precheck"] = ai_precheck
        return jsonify(response)
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


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    code = data.get("code", "")
    error = data.get("error", "")
    history = data.get("history") or []

    response = chat_with_ai(message, code=code, error=error, history=history)
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)