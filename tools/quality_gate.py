#!/usr/bin/env python3
"""
pax-* Skill 质量门禁检查脚本

检查项:
1. Skill 格式合规性
2. 版本一致性
3. 文档完整性
4. 契约测试
5. 路由完整性
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def check_skill_format(skill_dir: Path) -> List[str]:
    """检查 Skill 格式合规性"""
    
    errors = []
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        errors.append(f"Missing SKILL.md")
        return errors
    
    content = skill_md.read_text(encoding="utf-8")
    
    # 检查 frontmatter
    if not content.startswith("---"):
        errors.append("Missing frontmatter")
        return errors
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Invalid frontmatter format")
        return errors
    
    frontmatter = parts[1]
    
    # 检查必需字段
    required_fields = ["name", "description", "version", "family", "layer", "optional", "requires_snapshot"]
    for field in required_fields:
        if f"{field}:" not in frontmatter:
            errors.append(f"Missing field: {field}")
    
    # 检查必需段落
    required_sections = [
        "## Execution Contract",
        "## 职责边界",
        "## 输入",
        "## 工作流",
        "## 输出契约",
        "## 失败模式",
        "## 何时升级"
    ]
    
    for section in required_sections:
        if section not in content:
            errors.append(f"Missing section: {section}")
    
    # 检查 version 格式
    version_match = re.search(r"version:\s*([^\n]+)", frontmatter)
    if version_match:
        version = version_match.group(1).strip()
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            errors.append(f"Invalid version format: {version}")
    
    # 检查 layer 值
    layer_match = re.search(r"layer:\s*([^\n]+)", frontmatter)
    if layer_match:
        layer = layer_match.group(1).strip()
        if layer not in ["L0", "L1", "L2", "L3", "L4"]:
            errors.append(f"Invalid layer: {layer}")
    
    return errors


def check_version_consistency() -> List[str]:
    """检查版本一致性"""
    
    errors = []
    
    # 读取 versions.json
    versions_path = Path("pax-ops/versions.json")
    if not versions_path.exists():
        errors.append("Missing pax-ops/versions.json")
        return errors
    
    versions = json.loads(versions_path.read_text(encoding="utf-8"))
    
    # 检查每个 skill
    skills_dir = Path("skills")
    if not skills_dir.exists():
        errors.append("Missing skills/ directory")
        return errors
    
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        
        skill_name = skill_dir.name
        
        # 检查是否在 versions.json 中
        if skill_name not in versions.get("skills", {}):
            errors.append(f"{skill_name}: not in versions.json")
            continue
        
        # 提取 SKILL.md 中的 version
        content = skill_md.read_text(encoding="utf-8")
        version_match = re.search(r"version:\s*([^\n]+)", content)
        if not version_match:
            errors.append(f"{skill_name}: missing version in SKILL.md")
            continue
        
        skill_version = version_match.group(1).strip()
        expected_version = versions["skills"][skill_name]["version"]
        
        if skill_version != expected_version:
            errors.append(f"{skill_name}: SKILL.md version {skill_version} != versions.json {expected_version}")
    
    return errors


def check_documentation() -> List[str]:
    """检查文档完整性"""
    
    errors = []
    
    # 检查 README.md
    if not Path("README.md").exists():
        errors.append("Missing README.md")
    
    # 检查 CONTRIBUTING.md
    if not Path("CONTRIBUTING.md").exists():
        errors.append("Missing CONTRIBUTING.md")
    
    # 检查 CHANGELOG.md
    if not Path("CHANGELOG.md").exists():
        errors.append("Missing CHANGELOG.md")
    
    # 检查 docs/ 目录
    docs_dir = Path("docs")
    if docs_dir.exists():
        # 检查使用示例
        if not (docs_dir / "usage-examples.md").exists():
            errors.append("Missing docs/usage-examples.md")
        
        # 检查教程
        if not (docs_dir / "tutorial.md").exists():
            errors.append("Missing docs/tutorial.md")
    
    return errors


def check_routing_completeness() -> List[str]:
    """检查路由完整性"""
    
    errors = []
    
    # 读取 registry.json
    registry_path = Path("pax-ops/registry.json")
    if not registry_path.exists():
        errors.append("Missing pax-ops/registry.json")
        return errors
    
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    skills = registry.get("skills", [])
    
    # 检查是否有 pax-orchestrate
    has_orchestrate = any(s.get("name") == "pax-orchestrate" for s in skills)
    if not has_orchestrate:
        errors.append("Missing pax-orchestrate in registry")
    
    # 检查 L1 核心 Skill
    core_skills = ["pax-clarify", "pax-diagnose", "pax-plan", "pax-execute", "pax-review"]
    for skill_name in core_skills:
        skill = next((s for s in skills if s.get("name") == skill_name), None)
        if not skill:
            errors.append(f"Missing core skill: {skill_name}")
        else:
            # 检查核心 Skill 的 optional 属性
            # pax-clarify, pax-plan, pax-execute, pax-review 应该是 optional: false
            # pax-diagnose 应该是 optional: true
            expected_optional = skill_name == "pax-diagnose"
            actual_optional = skill.get("optional", True)
            if actual_optional != expected_optional:
                errors.append(f"{skill_name}: optional should be {expected_optional}, but got {actual_optional}")
    
    return errors


def check_contracts() -> List[str]:
    """运行契约测试"""
    
    errors = []
    
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pax", "test"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            errors.append(f"Contract test failed: {result.stderr}")
        
    except Exception as e:
        errors.append(f"Failed to run contract tests: {e}")
    
    return errors


def main():
    """主函数"""
    
    print("=" * 60)
    print("pax-* Skill 质量门禁检查")
    print("=" * 60)
    
    all_errors = []
    checks = [
        ("Skill 格式合规性", check_skill_format),
        ("版本一致性", check_version_consistency),
        ("文档完整性", check_documentation),
        ("路由完整性", check_routing_completeness),
        ("契约测试", check_contracts)
    ]
    
    for check_name, check_func in checks:
        print(f"\n[{check_name}]")
        print("-" * 40)
        
        if check_name == "Skill 格式合规性":
            skills_dir = Path("skills")
            if skills_dir.exists():
                for skill_dir in sorted(skills_dir.iterdir()):
                    if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                        errors = check_func(skill_dir)
                        if errors:
                            print(f"  [FAIL] {skill_dir.name}:")
                            for error in errors:
                                print(f"     - {error}")
                            all_errors.extend([f"{skill_dir.name}: {error}" for error in errors])
                        else:
                            print(f"  [PASS] {skill_dir.name}")
            else:
                print("  [FAIL] Missing skills/ directory")
                all_errors.append("Missing skills/ directory")
        else:
            errors = check_func()
            if errors:
                for error in errors:
                    print(f"  [FAIL] {error}")
                    all_errors.append(error)
            else:
                print(f"  [PASS] {check_name}")
    
    print("\n" + "=" * 60)
    print("质量门禁检查结果")
    print("=" * 60)
    
    if all_errors:
        print(f"\n[FAIL] 失败 ({len(all_errors)} 个错误):")
        for error in all_errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("\n[PASS] 所有质量门禁检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()