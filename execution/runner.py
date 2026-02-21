import subprocess
import tempfile
import os
import time
import shutil
import sys

TIME_LIMIT = 5


def run_code(user_code: str, user_input: str = ""):
    start_time = time.time()
    temp_dir = tempfile.mkdtemp()

    try:
        file_path = os.path.join(temp_dir, "main.py")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(user_code)

        process = subprocess.Popen(
            [sys.executable, file_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=temp_dir
        )

        try:
            stdout, stderr = process.communicate(
                input=user_input,
                timeout=TIME_LIMIT
            )

            execution_time = round(time.time() - start_time, 3)

            if process.returncode == 0:
                return {
                    "output": stdout,
                    "error": "",
                    "execution_time": execution_time,
                    "status": "success"
                }
            else:
                return {
                    "output": "",
                    "error": stderr,
                    "execution_time": execution_time,
                    "status": "error"
                }

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

            return {
                "output": "",
                "error": "Time Limit Exceeded",
                "execution_time": TIME_LIMIT,
                "status": "timeout"
            }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)