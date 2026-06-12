import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DJANGO_DIR = PROJECT_ROOT / "object_detection_system"
DEFAULT_URL = "http://127.0.0.1:8000/"


def python_command():
    return os.environ.get("PYTHON_BIN") or sys.executable


def start_process(args):
    return subprocess.Popen(
        [python_command(), "manage.py", *args],
        cwd=DJANGO_DIR,
    )


def terminate_process(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main():
    parser = argparse.ArgumentParser(description="Start RF-DETR Object Detection System services.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="8000")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--browser-delay", type=float, default=3.0)
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"
    processes = []
    stopping = False

    def shutdown(signum=None, frame=None):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for process in reversed(processes):
            terminate_process(process)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        print("Starting Django server...")
        processes.append(start_process(["runserver", f"{args.host}:{args.port}"]))

        print(f"Django URL: {url}")
        print("Press Ctrl+C to stop services.")

        if not args.no_browser:
            time.sleep(args.browser_delay)
            webbrowser.open(url)

        while not stopping:
            for process in processes:
                code = process.poll()
                if code is not None:
                    print(f"Process exited with code {code}. Stopping remaining services.")
                    shutdown()
                    return code
            time.sleep(0.5)
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
