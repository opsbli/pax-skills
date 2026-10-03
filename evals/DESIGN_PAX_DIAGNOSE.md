# pax-diagnose 评估设计（方向2）

2026-10-03。目标：把 pax-orchestrate 的评估方法（契约原文当系统提示、gold 可仅凭
prompt + 契约推导、锁定 holdout、双口径报告）应用到 **pax-diagnose**。

## 一、契约分析：哪些点可评估

pax-diagnose 的工作流 D1→D6，其中可结构化为「输入 → 枚举值 → 对比 gold」的判定点：

| 阶段 | 判定点 | 取值域 | 可评估性 |
|------|--------|--------|----------|
| D1 | `reproduction.status` | reproduced / not_reproduced / partial | 高（三值枚举） |
| D2 | 证据类型覆盖 | log / stack_trace / change / metric / config / dependency | 中（集合，需定义"足够"） |
| D2 | 存储后端确认触发 | 强制 / 非强制 | 高（布尔，有明确触发条件） |
| D3 | 假设数量 | 2–5 条 | 中（区间） |
| D4 | 验证状态 | confirmed / rejected / inconclusive | 中 |
| D5 | `root_cause.severity` | P0 / P1 / P2 | **高（有量化标准）** |
| D5 | `severity_rationale` 4 维度 | 布尔 + 4 值枚举 | **高（结构化）** |

**选 D5 作为首个评估点**，理由与 W2 风险评分相同：它是「4 个输入维度 → 1 个聚合等级」
的结构化判定，最容易做成客观 gold，也最容易暴露契约边界模糊。

## 二、契约缺陷发现

排查契约引用时发现 **pax-diagnose 引用了两个不存在的文件**：

| 引用位置 | 引用文件 | 状态 |
|----------|----------|------|
| SKILL.md:270「严重度量化标准」 | `references/severity-criteria.md` | **缺失** |
| SKILL.md:350「格式由…约束」 | `schemas/snapshot.schema.json` | **缺失** |

对比：`pax-clarify/references/domain-dependencies.md` 和
`pax-orchestrate/references/domain-dependencies.md` 都存在。

**影响**：D5 的详细量化标准不在契约里，模型只能从 SKILL.md 的简表推导：

```
| P0 | 核心流程完全不可用 / 影响所有用户 / 无规避 / 安全相关 | 强制升级 pax-council |
| P1 | 核心流程部分不可用 / 影响部分用户 / 有临时规避        | 走 plan → execute → review |
| P2 | 非核心流程部分不可用 / 影响少量用户 / 有明显规避      | 可合并到常规迭代 |
```

**两个未定义边界**（静态分析）：

- **HD1**：P0/P1/P2 判据用「/」分隔，语义是「或」还是「且」？契约 W2 的同类问题
  （G5）已定义「1 档全部条件须同时满足」，但 D5 没写。
- **HD2**：「安全相关」单独就能定 P0，还是要和「核心流程不可用」联合？
  P0 行有 4 个条件，若任一满足即 P0，则「安全相关但非核心流程」也是 P0。

## 三、场景设计（6 个）

设计原则与内部路由一致：**gold 必须能仅凭 prompt + 契约文字推导**；
题面不出现会替模型下结论的暗示词。

### 场景 1：P0 明确

**prompt**：生产环境订单支付接口全部返回 500 错误，所有用户都无法完成下单，
无任何可用支付方式，也没有临时规避方案。

**gold**：
```yaml
severity: P0
severity_rationale:
  core_flow_broken: true      # 支付是核心流程，且完全不可用
  affected_users: all         # 所有用户
  workaround_available: false # 无规避
  security_relevant: false    # 与安全无关
```

**契约依据**：P0「核心流程完全不可用 / 影响所有用户 / 无规避」三条全中。

### 场景 2：P1 明确

**prompt**：优惠券核销接口在高并发时段偶发失败，约 30% 的下单用户会遇到；
用户可以稍后重试完成核销，重试通常成功。

**gold**：
```yaml
severity: P1
severity_rationale:
  core_flow_broken: false     # 核销是下单的辅助环节，下单主流程仍可用
  affected_users: some        # 约 30%
  workaround_available: true  # 稍后重试
  security_relevant: false
```

**契约依据**：P1「影响部分用户 / 有临时规避」；不中 P0 的「完全不可用 / 无规避」。

### 场景 3：P2 明确

**prompt**：用户个人中心的头像上传偶发失败，仅不到 1% 的用户遇到；
失败后刷新页面重试即可成功，不影响其他功能。

**gold**：
```yaml
severity: P2
severity_rationale:
  core_flow_broken: false
  affected_users: few         # <1%
  workaround_available: true  # 刷新重试
  security_relevant: false
```

**契约依据**：P2「非核心流程 / 影响少量用户 / 有明显规避」三条全中。

### 场景 4：安全相关（边界，测 HD2）

**prompt**：发现订单查询接口未校验用户身份，任意登录用户传入订单号即可查看
他人的订单详情，包括收货地址和手机号。

**gold（建议 A）**：
```yaml
severity: P0
severity_rationale:
  core_flow_broken: false     # 查询接口本身可用
  affected_users: all         # 所有用户的数据都有泄露风险
  workaround_available: false # 用户无法自行规避
  security_relevant: true     # 越权访问 = 安全相关
```

**契约依据（待裁决 HD2）**：
- 若按 P0「安全相关」任一即算 → P0。
- 若要求「核心流程不可用」和「安全相关」联合 → 本条 core_flow_broken=false，则是 P1。

**这是 HD2 的暴露题**。建议 gold 取 P0（与常见安全实践一致：越权 = P0）。

### 场景 5：影响所有用户但非核心流程（边界）

**prompt**：系统公告栏的字体在部分浏览器下显示为默认字体，所有用户都会看到，
但公告内容可正常阅读，不影响任何功能操作。

**gold**：
```yaml
severity: P2
severity_rationale:
  core_flow_broken: false
  affected_users: all         # 所有用户可见
  workaround_available: true  # 不影响使用
  security_relevant: false
```

**契约依据**：不中 P0（非核心流程、无不可用）；命中 P2「非核心流程 + 有明显规避」。
**注意**：affected_users=all 但等级是 P2——测试模型是否会把「影响所有用户」
直接等同于高等级。

### 场景 6：复现困难（测 D1）

**prompt**：用户反馈偶发登录失败（约每天 1–2 次），但服务端日志无异常记录，
本地尝试 20 次登录全部成功，无法稳定复现。

**gold**：
```yaml
reproduction:
  status: not_reproduced      # 20 次尝试全成功
severity: P2                  # 间歇性、有重试空间
severity_rationale:
  core_flow_broken: false     # 偶发，非持续
  affected_users: few         # 每天 1–2 次
  workaround_available: true  # 重试
  security_relevant: false
```

**契约依据**：D1「`not_reproduced` → 标记 `status: blocked`，附 `missing_information`」。

## 四、评估方法

复用 `run_internal_routing_eval.py` 的框架：

1. **系统提示** = pax-diagnose SKILL.md 的原文（不注入契约外澄清），与内部路由一致
2. **输出格式** = 让模型返回结构化 JSON：`reproduction.status`、`severity`、
   `severity_rationale` 4 维度
3. **打分** = 逐字段对比 gold，检查项门槛复用内部路由的分档逻辑：
   - `severity`：≥0.85（聚合判定）
   - `severity_rationale` 4 维度：≥0.80（1–3 量纲类似的主观判定，这里退化为布尔/枚举）
   - `reproduction.status`：≥0.95（三值枚举，类似 primary_intent）
4. **锁定**：6 个场景写入后不修订 prompt 或 gold，答错如实记 FAIL

## 五、成本

- 6 场景 × 5 repeats = **30 次付费调用**（单模型）
- 若要跨模型对照，再 ×2 = 60 次

## 六、待用户裁决

| 项 | 问题 | 候选 |
|----|------|------|
| **HD1** | P0/P1/P2 的「/」是「或」还是「且」？ | A 全部条件须同时满足（与 G5 一致） / B 任一即算 |
| **HD2** | 「安全相关」单独能否定 P0？ | A 能（场景 4 = P0） / B 不能（场景 4 = P1） |
| **HD3** | 缺失的 `severity-criteria.md` 是否补写？ | A 补写完整量化标准 / B 把标准内联进 SKILL.md |

**HD3 的建议**：先补 `severity-criteria.md`（选 A）还是内联（选 B），
影响评估的契约基准——若不补，评估测的是「SKILL.md 简表」而非「完整标准」。
