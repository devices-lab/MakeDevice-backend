from pathlib import Path
import shutil
import subprocess
import sys


def resolve_wasi_svg_flatten() -> str:
    command_path = shutil.which("wasi-svg-flatten")
    if command_path:
        return command_path

    venv_command = Path(sys.prefix) / "bin" / "wasi-svg-flatten"
    if venv_command.exists():
        return str(venv_command)

    raise FileNotFoundError(
        "wasi-svg-flatten was not found. Install svg-flatten-wasi into the active Python environment."
    )


def run_wasi_svg_flatten(args, **kwargs):
    return subprocess.run([resolve_wasi_svg_flatten(), *args], check=True, **kwargs)