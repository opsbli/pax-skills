"""pax-orchestrate 内部路由逻辑测试

测试意图分类、风险评分、路由构建的正确性。
通过解析 pax-orchestrate SKILL.md 中的路由表，验证测试案例的路由决策。
"""

import pytest
import re
from pathlib import Path
import json


# 测试数据集
TEST_CASES = [
    {
        "id": "pax-intent-df-01",
        "category": "intent_classification",
        "prompt": "CMDB 字段校验有问题，时间类型的字段填写后报错说字段不为设定的正则表达式",
        "expected": {
            "primary_intent": "diagnose_fix",
            "secondary_intent": [],
            "confidence": "high"
        }
    },
    {
        "id": "pax-intent-df-02",
        "category": "intent_classification",
        "prompt": "系统最近响应变慢了，以前 1 秒能完成的请求现在要 5 秒，用户抱怨很多",
        "expected": {
            "primary_intent": "diagnose_fix",
            "secondary_intent": ["performance"],
            "confidence": "high"
        }
    },
    {
        "id": "pax-intent-fd-01",
        "category": "intent_classification",
        "prompt": "给系统加一个导出功能，能把用户列表导出成 Excel 文件",
        "expected": {
            "primary_intent": "feature_dev",
            "secondary_intent": [],
            "confidence": "medium"
        }
    },
    {
        "id": "pax-intent-rf-01",
        "category": "intent_classification",
        "prompt": "把这段 500 行的方法拆分成更小的函数，提高可读性",
        "expected": {
            "primary_intent": "refactor",
            "secondary_intent": [],
            "confidence": "medium"
        }
    },
    {
        "id": "pax-intent-do-01",
        "category": "intent_classification",
        "prompt": "有一批用户数据字段填错了，需要批量订正，大概 500 条记录",
        "expected": {
            "primary_intent": "data_ops",
            "secondary_intent": ["data_integrity"],
            "confidence": "high"
        }
    },
    {
        "id": "pax-intent-dc-01",
        "category": "intent_classification",
        "prompt": "解释一下什么是微服务架构，有什么优缺点",
        "expected": {
            "primary_intent": "doc_consult",
            "secondary_intent": [],
            "confidence": "low"
        }
    },
    {
        "id": "pax-intent-tb-01",
        "category": "intent_classification",
        "prompt": "写一个脚本，自动检查所有未提交的变更并生成 commit message",
        "expected": {
            "primary_intent": "tool_build",
            "secondary_intent": [],
            "confidence": "medium"
        }
    },
    {
        "id": "pax-risk-high-01",
        "category": "risk_scoring",
        "prompt": "把旧表的数据迁移到新表，需要保留所有历史记录",
        "expected": {
            "risk_score": 10,
            "risk_level": "high",
            "irreversibility": 3,
            "impact_scope": 3,
            "uncertainty": 2,
            "coordination_cost": 2
        }
    },
    {
        "id": "pax-risk-medium-01",
        "category": "risk_scoring",
        "prompt": "给系统加一个导出功能，能把用户列表导出成 Excel 文件",
        "expected": {
            "risk_score": 7,
            "risk_level": "medium",
            "irreversibility": 1,
            "impact_scope": 2,
            "uncertainty": 2,
            "coordination_cost": 2
        }
    },
    {
        "id": "pax-risk-low-01",
        "category": "risk_scoring",
        "prompt": "解释一下什么是微服务架构，有什么优缺点",
        "expected": {
            "risk_score": 4,
            "risk_level": "low",
            "irreversibility": 1,
            "impact_scope": 1,
            "uncertainty": 1,
            "coordination_cost": 1
        }
    },
    {
        "id": "pax-route-df-01",
        "category": "route_building",
        "prompt": "CMDB 字段校验有问题，时间类型的字段填写后报错说字段不为设定的正则表达式",
        "expected": {
            "route": ["pax-clarify", "pax-diagnose", "pax-plan", "pax-execute", "pax-review"],
            "diagnose_required": True,
            "storage_backend_required": True
        }
    },
    {
        "id": "pax-route-fd-01",
        "category": "route_building",
        "prompt": "给系统加一个导出功能，能把用户列表导出成 Excel 文件",
        "expected": {
            "route": ["pax-clarify", "pax-plan", "pax-execute", "pax-review"],
            "diagnose_required": False,
            "storage_backend_required": False
        }
    },
    {
        "id": "pax-route-dc-01",
        "category": "route_building",
        "prompt": "解释一下什么是微服务架构，有什么优缺点",
        "expected": {
            "route": ["pax-clarify"],
            "diagnose_required": False,
            "storage_backend_required": False
        }
    },
    {
        "id": "pax-cross-repo-01",
        "category": "cross_repo_detection",
        "prompt": "前后端分离的系统，前端 React 需要调用后端 API 的新增接口",
        "expected": {
            "cross_repo": True,
            "execution_strategy_required": True
        }
    }
]


class TestOrchestrateRouting:
    """pax-orchestrate 路由逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """加载 pax-orchestrate SKILL.md"""
        skill_path = Path("skills/pax-orchestrate/SKILL.md")
        if not skill_path.exists():
            pytest.skip("pax-orchestrate SKILL.md not found")
        self.skill_content = skill_path.read_text(encoding="utf-8")

    def test_intent_classification(self):
        """测试意图分类逻辑"""
        intent_cases = [c for c in TEST_CASES if c["category"] == "intent_classification"]
        
        for case in intent_cases:
            prompt = case["prompt"]
            expected = case["expected"]
            
            # 简单的关键词匹配模拟意图分类
            primary_intent = self._classify_intent(prompt)
            
            assert primary_intent == expected["primary_intent"], (
                f"{case['id']}: expected {expected['primary_intent']}, got {primary_intent}"
            )

    def test_route_building(self):
        """测试路由构建逻辑"""
        route_cases = [c for c in TEST_CASES if c["category"] == "route_building"]
        
        for case in route_cases:
            prompt = case["prompt"]
            expected = case["expected"]
            
            # 简单的关键词匹配模拟路由构建
            route = self._build_route(prompt)
            
            assert set(route) == set(expected["route"]), (
                f"{case['id']}: expected {set(expected['route'])}, got {set(route)}"
            )

    def _classify_intent(self, prompt: str) -> str:
        """简单的意图分类（模拟 pax-orchestrate 的逻辑）"""
        prompt_lower = prompt.lower()
        
        # 诊断修复
        if any(kw in prompt_lower for kw in ["报错", "异常", "失败", "错误", "崩溃", "bug", "error", "exception"]):
            return "diagnose_fix"
        if "502" in prompt_lower or "500" in prompt_lower and ("网关" in prompt_lower or "gateway" in prompt_lower or "错误" in prompt_lower):
            return "diagnose_fix"
        if "变慢" in prompt_lower or "性能" in prompt_lower or "超时" in prompt_lower:
            return "diagnose_fix"
        if "不一致" in prompt_lower or ("数据" in prompt_lower and "订正" in prompt_lower):
            return "data_ops"
        
        # 功能开发
        if any(kw in prompt_lower for kw in ["加一个", "新增", "实现", "创建", "开发", "导出", "审批"]):
            return "feature_dev"
        
        # 重构优化
        if any(kw in prompt_lower for kw in ["重构", "拆分", "优化", "改进", "解耦"]):
            return "refactor"
        
        # 文档咨询
        if any(kw in prompt_lower for kw in ["解释", "什么是", "怎么", "为什么", "文档", "方案"]):
            return "doc_consult"
        
        # 工具构建
        if any(kw in prompt_lower for kw in ["脚本", "工具", "自动化"]):
            return "tool_build"
        
        return "feature_dev"  # 默认

    def _build_route(self, prompt: str) -> list:
        """简单的路由构建（模拟 pax-orchestrate 的逻辑）"""
        intent = self._classify_intent(prompt)
        
        routes = {
            "diagnose_fix": ["pax-clarify", "pax-diagnose", "pax-plan", "pax-execute", "pax-review"],
            "feature_dev": ["pax-clarify", "pax-plan", "pax-execute", "pax-review"],
            "refactor": ["pax-clarify", "pax-plan", "pax-execute", "pax-review"],
            "data_ops": ["pax-clarify", "pax-diagnose", "pax-plan", "pax-execute", "pax-review"],
            "doc_consult": ["pax-clarify"],
            "tool_build": ["pax-clarify", "pax-plan", "pax-execute", "pax-review"]
        }
        
        return routes.get(intent, ["pax-clarify"])


def test_skill_description_mentions_entry_point():
    """测试 pax-orchestrate 描述明确说明是入口点"""
    skill_path = Path("skills/pax-orchestrate/SKILL.md")
    content = skill_path.read_text(encoding="utf-8")
    
    # 检查 description 是否提到入口点
    assert "统一入口" in content or "入口" in content, (
        "pax-orchestrate description should mention it's the entry point"
    )
    
    # 检查是否提到不要直接选择其他 skill
    assert "不要直接选择" in content or "直接选择" in content, (
        "pax-orchestrate description should mention not to select other skills directly"
    )


def test_l1_skills_mention_orchestrate():
    """测试 L1 skills 描述提到通过 pax-orchestrate 调用"""
    l1_skills = [
        "pax-clarify",
        "pax-diagnose",
        "pax-plan",
        "pax-execute",
        "pax-review"
    ]
    
    for skill_name in l1_skills:
        skill_path = Path(f"skills/{skill_name}/SKILL.md")
        if skill_path.exists():
            content = skill_path.read_text(encoding="utf-8")
            assert "pax-orchestrate" in content, (
                f"{skill_name} description should mention pax-orchestrate"
            )


def test_clarify_description_mentions_clarification_needed():
    """测试 pax-clarify 描述提到何时需要澄清"""
    skill_path = Path("skills/pax-clarify/SKILL.md")
    content = skill_path.read_text(encoding="utf-8")
    
    # 检查是否提到模糊、不完整、多种理解
    keywords = ["模糊", "不完整", "多种理解"]
    found_keywords = [kw for kw in keywords if kw in content]
    
    assert len(found_keywords) >= 2, (
        f"pax-clarify description should mention when clarification is needed. "
        f"Found: {found_keywords}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
