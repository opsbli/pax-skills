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


def test_cli_version_flag():
    result = run_cli("--version")
    assert result.returncode == 0
    assert "pax-forge 0.1.0" in result.stdout


def test_cli_init_creates_skeleton(tmp_path):
    target = tmp_path / "pax-family"
    result = run_cli("init", str(target))
    assert result.returncode == 0, result.stderr
    assert (target / "schemas" / "pax-family.schema.yaml").exists()
    assert (target / "schemas" / "snapshot.schema.json").exists()
    assert (target / "pax-ops" / "versions.json").exists()
    assert (target / "pax-ops" / "registry.json").exists()
    assert (target / "pax-ops" / "patches" / "manifest.json").exists()
    assert (target / "skills").is_dir()
    assert (target / "references").is_dir()
