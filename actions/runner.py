# Runs Python files

import subprocess

def run_python(file_name: str):
    try:
        result = subprocess.run([
            "python", file_name
        ], text=True, capture_output=True)

        print(result.stdout)
        if result.stderr:
            print("ERROR:\n", result.stderr)

    except Exception as e:
        print(f"Error running file: {e}")
