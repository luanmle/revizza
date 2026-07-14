import sys
from pathlib import Path

_vendor = Path(__file__).with_name("vendor")
if _vendor.is_dir():
    sys.path.insert(0, str(_vendor))

from . import entry_point  # noqa: E402

entry_point.run()
