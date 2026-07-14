"""Build and smoke-test the distributable Anki add-on."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
PACKAGE_SOURCE = ROOT / "ankihub_br"
RUNTIME_REQUIREMENTS = ROOT / "requirements-vendor.txt"
RUNTIME_MODULES = ("peewee", "requests", "sentry_sdk")
OUTPUT = ROOT / "dist" / "ankihub_br.ankiaddon"


def write_archive(package: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w") as archive:
        for path in sorted(package.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(package).as_posix()
            info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED)


def verify_archive(archive: Path) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        package = root / "ankihub_br"
        package.mkdir()
        with ZipFile(archive) as bundled:
            bundled.extractall(package)
        code = f"""
import importlib
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
importlib.import_module("ankihub_br")
vendor = root / "ankihub_br" / "vendor"
for name in {RUNTIME_MODULES!r}:
    module = importlib.import_module(name)
    if not Path(module.__file__).resolve().is_relative_to(vendor):
        raise SystemExit(f"{{name}} imported outside package vendor")
"""
        subprocess.run([sys.executable, "-I", "-S", "-c", code, str(root)], check=True)


def build_addon() -> Path:
    with tempfile.TemporaryDirectory() as temporary:
        package = Path(temporary) / "ankihub_br"
        shutil.copytree(
            PACKAGE_SOURCE,
            package,
            ignore=shutil.ignore_patterns("vendor", "__pycache__", "*.py[co]"),
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-compile",
                "--requirement",
                str(RUNTIME_REQUIREMENTS),
                "--target",
                str(package / "vendor"),
            ],
            check=True,
        )
        write_archive(package, OUTPUT)
    verify_archive(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build_addon())
