# tests/test_smoke.py
from pax import __version__

def test_version_string():
    assert __version__ == "0.1.0"
