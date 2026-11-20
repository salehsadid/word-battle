"""Builds a one-click Windows executable: WordBattle.exe in the project root.

The .exe contains Python, pygame, the dictionary and the images, so it runs on a computer without Python.

    pip install pyinstaller
    python scripts/build_exe.py
"""

import shutil
import sys
from pathlib import Path

try:
    import PyInstaller.__main__
except ImportError:
    sys.exit("PyInstaller is not installed. Run:  pip install pyinstaller")

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DIST = ROOT / "dist"
SEP = ";" if sys.platform == "win32" else ":"


def data(src: Path, dest: str) -> str:
    """--add-data argument: copy src to dest inside the bundle (paths match the source tree)."""
    return f"--add-data={src}{SEP}{dest}"


def main() -> None:
    PyInstaller.__main__.run([
        str(ROOT / "main.py"),
        "--name=WordBattle",
        "--onefile",            # a single .exe
        "--windowed",           # no console window behind the game
        "--noconfirm",
        "--clean",
        f"--icon={ROOT / 'wordgrid' / 'assets' / 'images' / 'app_icon.ico'}",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        f"--specpath={BUILD}",
        data(ROOT / "data" / "cleaned_words.txt", "data"),
        data(ROOT / "wordgrid" / "assets", "wordgrid/assets"),
        # Test-only and build-only packages are not needed by the game
        "--exclude-module=pytest",
        "--exclude-module=tkinter",
        "--exclude-module=numpy",
        # pygame imports pkg_resources only optionally; bundling it breaks start-up (missing jaraco)
        "--exclude-module=pkg_resources",
        "--exclude-module=setuptools",
    ])
    exe = DIST / "WordBattle.exe"
    shutil.copy2(exe, ROOT / "WordBattle.exe")
    print(f"\nDone: {ROOT / 'WordBattle.exe'}  ({exe.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
