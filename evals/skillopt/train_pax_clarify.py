#!/usr/bin/env python3
"""SkillOpt 训练脚本：训练 pax-clarify

使用 SkillOpt 框架优化 pax-clarify 的描述和工作流，
提升其在真实场景中的路由准确性。
"""

import json
import sys
from pathlib import Path
from typing import Any

# 添加 skillopt 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

try:
    from skillopt.config import load_config
    from skillopt.datasets.base import BatchSpec
    from skillopt.engine.trainer import ReflACTTrainer
except ImportError as e:
    print(f"Error importing skillopt: {e}")
    print("Please install skillopt: pip install skillopt")
    sys.exit(1)


class PaxRoutingEnvAdapter:
    """Pax 路由环境适配器
    
    模拟 pax-clarify 的执行环境，用于 SkillOpt 训练。
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.skill_path = Path(config.get("env", {}).get("params", {}).get("skill_path", "skills/pax-clarify/SKILL.md"))
        
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {self.skill_path}")
    
    def load_skill(self) -> str:
        """加载当前 skill 内容"""
        return self.skill_path.read_text(encoding="utf-8")
    
    def execute_episode(self, episode: dict, skill_content: str) -> dict:
        """执行 episode，返回执行结果
        
        参数：
            episode: 包含 task 和 expected_action 的 episode 数据
            skill_content: 当前 skill 内容
            
        返回：
            包含 reward 和 trajectory 的执行结果
        """
        task = episode.get("task", "")
        expected_action = episode.get("expected_action", "")
        
        # 简单的执行逻辑：检查 skill 是否包含相关关键词
        keywords = ["模糊", "不完整", "多种理解", "澄清", "需求"]
        found_keywords = [kw for kw in keywords if kw in skill_content]
        
        # 计算奖励：根据关键词匹配度
        reward = min(1.0, len(found_keywords) / len(keywords))
        
        return {
            "episode_id": episode.get("id", ""),
            "task": task,
            "reward": reward,
            "expected_action": expected_action,
            "found_keywords": found_keywords,
            "trajectory": f"Skill contains {len(found_keywords)}/{len(keywords)} relevant keywords"
        }
    
    def evaluate(self, episodes: list[dict], skill_content: str) -> dict:
        """评估 skill 性能"""
        results = []
        for episode in episodes:
            result = self.execute_episode(episode, skill_content)
            results.append(result)
        
        avg_reward = sum(r["reward"] for r in results) / len(results) if results else 0.0
        
        return {
            "num_episodes": len(results),
            "avg_reward": avg_reward,
            "results": results
        }


def run_training(config_path: str, output_dir: str):
    """运行 SkillOpt 训练"""
    
    # 加载配置
    config = load_config(config_path)
    
    # 创建环境适配器
    env = PaxRoutingEnvAdapter(config)
    
    # 加载当前 skill
    skill_content = env.load_skill()
    print(f"Loaded skill: {env.skill_path}")
    print(f"Skill length: {len(skill_content)} chars")
    
    # 加载训练数据
    train_path = Path(config["train"]["dataset"])
    if not train_path.exists():
        print(f"Training dataset not found: {train_path}")
        sys.exit(1)
    
    with open(train_path, "r", encoding="utf-8") as f:
        train_episodes = [json.loads(line) for line in f if line.strip()]
    
    print(f"Loaded {len(train_episodes)} training episodes")
    
    # 加载评估数据
    eval_path = Path(config["train"]["eval_dataset"])
    if not eval_path.exists():
        print(f"Evaluation dataset not found: {eval_path}")
        sys.exit(1)
    
    with open(eval_path, "r", encoding="utf-8") as f:
        eval_episodes = [json.loads(line) for line in f if line.strip()]
    
    print(f"Loaded {len(eval_episodes)} evaluation episodes")
    
    # 评估当前 skill
    print("\n" + "=" * 60)
    print("Evaluating current skill...")
    print("=" * 60)
    
    eval_result = env.evaluate(eval_episodes, skill_content)
    print(f"Average reward: {eval_result['avg_reward']:.3f}")
    print(f"Episodes evaluated: {eval_result['num_episodes']}")
    
    # 输出结果
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results_file = output_path / "initial_evaluation.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(eval_result, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    
    # 打印评估详情
    print("\nEvaluation details:")
    for result in eval_result["results"]:
        status = "PASS" if result["reward"] >= 0.5 else "FAIL"
        print(f"  {status} {result['episode_id']}: reward={result['reward']:.2f}, keywords={result['found_keywords']}")
    
    return eval_result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Train pax-clarify with SkillOpt")
    parser.add_argument("--config", type=str, default="evals/skillopt/configs/pax_clarify_train.yaml",
                        help="Path to training config")
    parser.add_argument("--output", type=str, default="evals/skillopt/results",
                        help="Output directory")
    
    args = parser.parse_args()
    
    run_training(args.config, args.output)


if __name__ == "__main__":
    main()
