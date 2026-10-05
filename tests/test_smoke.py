# tests/test_smoke.py
import re

from pax import __version__
from pax.forge import loader


def test_package_version_is_semver():
    """工具包版本是独立于家族版本的维度（见 README「版本」一节）。

    只校验语义版本形式，不写死字面量——否则每次工具包发版都会让测试变红。
    """
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_family_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", loader.load_versions()["version"])
