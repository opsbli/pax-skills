# 贡献指南

## 如何新增一个 pax-* Skill

1. 使用 `pax-forge` 生成骨架：
   ```bash
   pax-forge new pax-<capability> --layer <L0|L1|L2|L3|L4> [--optional]
   ```
2. 编辑 `skills/pax-<capability>/SKILL.md`：
   - 补充 `description`
   - 按层模板填充所有 `##` 段
   - 若有跨 skill 依赖，在"何时升级"段列出
3. 校验：
   ```bash
   pax-forge validate skills/pax-<capability>
   ```
4. 注册：
   ```bash
   pax-forge register skills/pax-<capability>
   ```
5. 更新 `pax-ops/versions.json` 的 `skills` 段
6. 跑契约测试：
   ```bash
   pax-forge test
   ```
7. 若涉及 breaking change，`pax-forge version major` 并更新兼容矩阵

## 分支策略

- 主线：`main`，受保护
- 特性分支：`feat/<short-name>`
- 修复分支：`fix/<short-name>`

## 提交规范

Conventional Commits：`feat:` / `fix:` / `docs:` / `test:` / `chore:` / `refactor:`

## PR 检查清单

- [ ] `pax-forge test` 通过
- [ ] 新增 skill 已注册到 `versions.json` 和 `registry.json`
- [ ] 如有 breaking change，`versions.json` 已 bump major
- [ ] 兼容矩阵已更新
- [ ] 文档同步
