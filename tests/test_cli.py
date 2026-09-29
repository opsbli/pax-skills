import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pax", *args],
        capture_output=True, text=True, check=False,
    )


def test_cli_shows_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_cli_empty_command_exits_nonzero():
    result = run_cli()
    assert result.returncode != 0
