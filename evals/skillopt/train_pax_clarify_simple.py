#!/usr/bin/env python3
"""SkillOpt 训练脚本：训练 pax-clarify

简化的训练流程，用于评估和优化 Skill 描述。
"""

import json
import sys
from pathlib import Path


class SkillEvaluator:
    """Skill 评估器"""
    
    KEYWORDS = ["模糊", "不完整", "多种理解", "澄清", "需求", "共识", "状态机", "设计树", "契约"]
    
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {self.skill_path}")
    
    def load_skill(self) -> str:
        """加载 skill 内容"""
        return self.skill_path.read_text(encoding="utf-8")
    
    def evaluate_episode(self, episode: dict, skill_content: str) -> dict:
        """评估单个 episode"""
        task = episode.get("task", "")
        expected_action = episode.get("expected_action", "")
        
        # 检查 skill 是否包含相关关键词
        found_keywords = [kw for kw in self.KEYWORDS if kw in skill_content]
        
        # 计算奖励：关键词匹配度
        reward = min(1.0, len(found_keywords) / len(self.KEYWORDS))
        
        return {
            "episode_id": episode.get("id", ""),
            "task": task,
            "reward": reward,
            "expected_action": expected_action,
            "found_keywords": found_keywords,
            "missing_keywords": [kw for kw in self.KEYWORDS if kw not in skill_content]
        }
    
    def evaluate(self, episodes: list[dict], skill_content: str = None) -> dict:
        """评估 skill 性能"""
        if skill_content is None:
            skill_content = self.load_skill()
        
        results = []
        for episode in episodes:
            result = self.evaluate_episode(episode, skill_content)
            results.append(result)
        
        avg_reward = sum(r["reward"] for r in results) / len(results) if results else 0.0
        
        return {
            "num_episodes": len(results),
            "avg_reward": avg_reward,
            "results": results,
            "pass_count": sum(1 for r in results if r["reward"] >= 0.5),
            "fail_count": sum(1 for r in results if r["reward"] < 0.5)
        }
    
    def suggest_improvements(self, eval_result: dict) -> list[dict]:
        """基于评估结果生成改进建议"""
        suggestions = []
        
        for result in eval_result["results"]:
            if result["reward"] < 0.8:
                suggestions.append({
                    "episode_id": result["episode_id"],
                    "task": result["task"],
                    "reward": result["reward"],
                    "missing_keywords": result["missing_keywords"],
                    "suggestion": f"Add missing keywords: {', '.join(result['missing_keywords'][:3])}"
                })
        
        return suggestions


def load_episodes(path: str) -> list[dict]:
    """加载 episode 数据"""
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_training(config: dict, output_dir: str):
    """运行训练流程"""
    
    # 初始化评估器
    evaluator = SkillEvaluator(config.get("skill_path", "skills/pax-clarify/SKILL.md"))
    
    # 加载数据
    train_episodes = load_episodes(config.get("train_dataset", "evals/skillopt/datasets/pax_train_episodes.jsonl"))
    eval_episodes = load_episodes(config.get("eval_dataset", "evals/skillopt/datasets/pax_eval_episodes.jsonl"))
    
    print(f"Loaded {len(train_episodes)} training episodes")
    print(f"Loaded {len(eval_episodes)} evaluation episodes")
    
    # 输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 初始评估
    print("\n" + "=" * 60)
    print("Initial Evaluation")
    print("=" * 60)
    
    initial_eval = evaluator.evaluate(eval_episodes)
    print(f"Initial avg reward: {initial_eval['avg_reward']:.3f}")
    print(f"Pass: {initial_eval['pass_count']}/{initial_eval['num_episodes']}")
    
    # 保存初始评估
    with open(output_path / "initial_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(initial_eval, f, ensure_ascii=False, indent=2)
    
    # 训练循环
    num_epochs = config.get("num_epochs", 3)
    
    for epoch in range(num_epochs):
        print(f"\n{'=' * 60}")
        print(f"Epoch {epoch + 1}/{num_epochs}")
        print("=" * 60)
        
        # 评估训练数据
        train_eval = evaluator.evaluate(train_episodes)
        print(f"Train avg reward: {train_eval['avg_reward']:.3f}")
        
        # 生成改进建议
        suggestions = evaluator.suggest_improvements(train_eval)
        print(f"Generated {len(suggestions)} suggestions")
        
        # 保存 epoch 结果
        epoch_result = {
            "epoch": epoch + 1,
            "train_avg_reward": train_eval["avg_reward"],
            "num_suggestions": len(suggestions),
            "suggestions": suggestions[:5]
        }
        
        with open(output_path / f"epoch_{epoch + 1}_result.json", "w", encoding="utf-8") as f:
            json.dump(epoch_result, f, ensure_ascii=False, indent=2)
    
    # 最终评估
    print(f"\n{'=' * 60}")
    print("Final Evaluation")
    print("=" * 60)
    
    final_eval = evaluator.evaluate(eval_episodes)
    print(f"Final avg reward: {final_eval['avg_reward']:.3f}")
    print(f"Pass: {final_eval['pass_count']}/{final_eval['num_episodes']}")
    
    # 保存最终评估
    with open(output_path / "final_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(final_eval, f, ensure_ascii=False, indent=2)
    
    # 总结
    print(f"\n{'=' * 60}")
    print("Training Summary")
    print("=" * 60)
    
    improvement = final_eval["avg_reward"] - initial_eval["avg_reward"]
    print(f"Initial reward: {initial_eval['avg_reward']:.3f}")
    print(f"Final reward:   {final_eval['avg_reward']:.3f}")
    print(f"Improvement:    {improvement:+.3f}")
    
    summary = {
        "initial_reward": initial_eval["avg_reward"],
        "final_reward": final_eval["avg_reward"],
        "improvement": improvement,
        "num_epochs": num_epochs,
        "num_train_episodes": len(train_episodes),
        "num_eval_episodes": len(eval_episodes),
        "skill_path": str(evaluator.skill_path)
    }
    
    with open(output_path / "training_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    
    return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Train pax-clarify with SkillOpt")
    parser.add_argument("--skill", type=str, default="skills/pax-clarify/SKILL.md",
                        help="Path to skill file")
    parser.add_argument("--train", type=str, default="evals/skillopt/datasets/pax_train_episodes.jsonl",
                        help="Path to training dataset")
    parser.add_argument("--eval", type=str, default="evals/skillopt/datasets/pax_eval_episodes.jsonl",
                        help="Path to evaluation dataset")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--output", type=str, default="evals/skillopt/results",
                        help="Output directory")
    
    args = parser.parse_args()
    
    config = {
        "skill_path": args.skill,
        "train_dataset": args.train,
        "eval_dataset": args.eval,
        "num_epochs": args.epochs
    }
    
    run_training(config, args.output)


if __name__ == "__main__":
    main()
