from subprocess import run
from os import makedirs, name as os_name
from sys import argv

DEBUG = True
HOST = "0.0.0.0"
PORT = 8090

if __name__ == "__main__":
    makedirs("./tmp", exist_ok=True)
    if len(argv) == 2:
        if argv[1].lower().strip() == "setup":
            run([
                "python",
                "-m",
                "venv",
                "venv"
            ])
            run([
                ".\\venv\\Scripts\\python.exe" if os_name == "nt" else "./venv/bin/python",
                "-m"
                "pip",
                "install",
                "-U",
                "wheel",
            ])
            run([
                ".\\venv\\Scripts\\python.exe" if os_name == "nt" else "./venv/bin/python",
                "-m"
                "pip",
                "install",
                "-r",
                "requirements.txt"
            ])
    else:
        run([
            "flask",
            "--app",
            "server",
            "run",
            "--host",
            HOST,
            "--port",
            str(PORT),
            "--debugger" if DEBUG else "--no-debugger",
        ])
