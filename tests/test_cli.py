import subprocess
import sys


def run_cli(*args: str, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pax", *args],
        capture_output=True, text=True, check=False, cwd=cwd,
    )


def test_cli_shows_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_cli_empty_command_exits_nonzero():
    result = run_cli()
    assert result.returncode != 0


def test_cli_version_flag():
    import re
    result = run_cli("--version")
    assert result.returncode == 0
    # 只校验形式，不写死工具包版本字面量（那是独立发版的维度）
    assert re.search(r"pax-forge \d+\.\d+\.\d+", result.stdout)


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


def test_cli_new_creates_skill(tmp_path):
    # 通过 CLI 触发；family root 使用当前项目目录
    dest = tmp_path / "fam"
    r1 = run_cli("init", str(dest))
    assert r1.returncode == 0
    r2 = run_cli("new", "pax-bar", "--layer", "L1",
                 "--description", "desc", cwd=str(dest))
    # 说明：CLI 写到 tmp_path/fam，不污染项目根
    assert r2.returncode == 0
    assert (dest / "skills" / "pax-bar" / "SKILL.md").exists()


def test_cli_patch_apply_empty_manifest():
    # 真实 manifest 是空的（patches=[]），apply 应为 no-op 且 return 0。
    # 输出必须能被下游脚本 parse 出 "applied N" 计数。
    result = run_cli("patch", "apply")
    assert result.returncode == 0
    assert "applied" in result.stdout.lower()
    assert "0" in result.stdout


def test_cli_list_empty_when_no_skills(tmp_path, monkeypatch):
    # 通过 monkeypatch 指向一个空 registry；subprocess 无法继承，
    # 因此直接调用 main() 并捕获 stdout。
    import json
    import io
    from contextlib import redirect_stdout

    from pax.forge import loader
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(
        json.dumps({"family": "pax", "updated_at": None, "skills": []}),
        encoding="utf-8",
    )
    original = loader.REGISTRY_PATH
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)
    try:
        from pax.forge.cli import main
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["list"])
    finally:
        loader.REGISTRY_PATH = original
    assert rc == 0
    assert "empty" in buf.getvalue().lower()
