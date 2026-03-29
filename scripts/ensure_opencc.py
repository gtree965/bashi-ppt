"""
Ensure OpenCC is importable for the current Python interpreter.

Why this exists:
- Some Windows / OneDrive environments intermittently fail to install the
  `opencc-python-reimplemented` wheel through pip temp directories.
- For Bashi PPT we only need the pure-Python wheel contents inside the active
  site-packages directory, so a direct download + extract fallback is enough.
"""

from __future__ import annotations

import site
import ssl
import tempfile
import urllib.request
import zipfile
from pathlib import Path


WHEEL_URL = (
    "https://mirrors.aliyun.com/pypi/packages/30/6b/"
    "055b7806f320cc8f2cdf23c5f70221c0dc1683fca9ffaf76dfc2ad4b91b6/"
    "opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl"
)
WHEEL_NAME = "opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl"


def _site_packages_dir() -> Path:
    for candidate in site.getsitepackages():
        path = Path(candidate)
        if path.exists():
            return path
    return Path(site.getusersitepackages())


def main() -> int:
    try:
        import opencc  # noqa: F401
        print("[OK] OpenCC already available.")
        return 0
    except ImportError:
        pass

    target_dir = _site_packages_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="slideforge-opencc-") as tmp:
        wheel_path = Path(tmp) / WHEEL_NAME
        print("[SETUP] Downloading OpenCC wheel...")
        with urllib.request.urlopen(WHEEL_URL, context=ssl.create_default_context()) as response:
            wheel_path.write_bytes(response.read())

        print(f"[SETUP] Extracting OpenCC into {target_dir} ...")
        with zipfile.ZipFile(wheel_path, "r") as archive:
            archive.extractall(target_dir)

    import opencc  # noqa: F401
    print("[OK] OpenCC installed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
