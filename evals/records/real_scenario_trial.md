# pax-orchestrate 真实场景试跑记录

## 场景：CMDB 数据订正

### 背景

CMDB（配置管理数据库）中有一批数据字段填写错误，需要批量订正。这个场景涉及：
- 存储后端确认（MySQL vs MongoDB vs 其他）
- 数据订正脚本编写
- 可能的跨仓库操作（后端 API + 前端显示）

### 用户目标

```
CMDB 里有一批服务器的操作系统字段填错了，大概 500 条记录。
需要批量订正成正确的值，最好能有个脚本，支持预览和回滚。
另外前端的服务器列表页面也需要显示更新后的字段。
```

### 预期路由决策

#### 1. 意图分类

- **primary_intent**: `data_ops`（数据操作）
- **secondary_intent**: `data_integrity`（数据完整性）
- **confidence**: `high`（明确的批量数据订正需求）

#### 2. 风险评分

| 维度 | 分数 | 说明 |
|------|------|------|
| irreversibility | 3 | 数据订正可能不可逆，需要备份 |
| impact_scope | 2 | 影响 500 条记录，范围中等 |
| uncertainty | 2 | 存储后端未知，订正逻辑需确认 |
| coordination_cost | 2 | 涉及后端脚本 + 前端显示 |
| **总分** | **9** | **high** |

#### 3. 路由构建

```
route: [pax-clarify, pax-diagnose, pax-plan, pax-execute, pax-review]
diagnose_required: true
storage_backend_required: true
cross_repo: true
execution_strategy_required: true
```

**路由说明**：
1. `pax-clarify`: 澄清需求（存储后端、订正规则、回滚策略）
2. `pax-diagnose`: 诊断存储后端（MySQL/MongoDB/其他），确认数据格式
3. `pax-plan`: 制定订正计划（脚本、测试、回滚）
4. `pax-execute`: 执行订正脚本
5. `pax-review`: 评审订正结果

#### 4. 关键检查点

- [ ] **存储后端确认**：通过 `pax-diagnose` 确认是 MySQL/MongoDB/其他
- [ ] **跨仓库检测**：检测到前端页面需要更新，标注 `cross_repo: true`
- [ ] **执行策略**：后端脚本 + 前端显示更新，需要协调

### 实际路由验证

通过 pax-orchestrate 处理上述用户目标，验证：

1. **意图分类**：是否正确识别为 `data_ops`
2. **风险评分**：总分是否在 9-11 范围内（high）
3. **路由构建**：是否包含 `pax-diagnose`（存储后端确认）
4. **跨仓库检测**：是否标注 `cross_repo: true`
5. **存储后端需求**：是否标注 `storage_backend_required: true`

### 测试结果

```json
{
  "intent": {
    "primary": "data_ops",
    "secondary": ["data_integrity"],
    "confidence": "high"
  },
  "risk": {
    "irreversibility": 3,
    "impact_scope": 2,
    "uncertainty": 2,
    "coordination_cost": 2,
    "total": 9,
    "level": "high"
  },
  "route": ["pax-clarify", "pax-diagnose", "pax-plan", "pax-execute", "pax-review"],
  "diagnose_required": true,
  "storage_backend_required": true,
  "cross_repo": true,
  "execution_strategy_required": true
}
```

### 结论

✅ 路由逻辑正确识别：
- 意图分类：`data_ops`
- 风险等级：`high`（9 分）
- 诊断需求：`true`（存储后端确认）
- 跨仓库：`true`（后端 + 前端）

---

## 场景 2：新功能开发

### 用户目标

```
给系统加一个导出功能，能把用户列表导出成 Excel 文件。
导出应该支持按时间范围筛选，导出格式是 .xlsx。
```

### 预期路由决策

#### 1. 意图分类

- **primary_intent**: `feature_dev`（功能开发）
- **secondary_intent**: []
- **confidence**: `medium`（需求基本清晰，但细节需确认）

#### 2. 风险评分

| 维度 | 分数 | 说明 |
|------|------|------|
| irreversibility | 1 | 新增功能，不影响现有数据 |
| impact_scope | 2 | 影响用户列表模块 |
| uncertainty | 2 | 导出格式、性能需求需确认 |
| coordination_cost | 1 | 单模块开发 |
| **总分** | **6** | **medium** |

#### 3. 路由构建

```
route: [pax-clarify, pax-plan, pax-execute, pax-review]
diagnose_required: false
storage_backend_required: false
cross_repo: false
```

**路由说明**：
1. `pax-clarify`: 澄清需求（导出格式、性能需求、UI 交互）
2. `pax-plan`: 制定开发计划
3. `pax-execute`: 实现功能
4. `pax-review`: 代码评审

### 测试结果

```json
{
  "intent": {
    "primary": "feature_dev",
    "secondary": [],
    "confidence": "medium"
  },
  "risk": {
    "irreversibility": 1,
    "impact_scope": 2,
    "uncertainty": 2,
    "coordination_cost": 1,
    "total": 6,
    "level": "medium"
  },
  "route": ["pax-clarify", "pax-plan", "pax-execute", "pax-review"],
  "diagnose_required": false,
  "storage_backend_required": false,
  "cross_repo": false
}
```

### 结论

✅ 路由逻辑正确识别：
- 意图分类：`feature_dev`
- 风险等级：`medium`（6 分）
- 诊断需求：`false`（新功能开发不需要诊断）
- 跨仓库：`false`（单模块开发）

---

## 场景 3：文档咨询

### 用户目标

```
解释一下什么是微服务架构，有什么优缺点。
我想了解一下在我们系统里是否适合用微服务。
```

### 预期路由决策

#### 1. 意图分类

- **primary_intent**: `doc_consult`（文档咨询）
- **secondary_intent**: []
- **confidence**: `low`（纯咨询，无实际变更）

#### 2. 风险评分

| 维度 | 分数 | 说明 |
|------|------|------|
| irreversibility | 1 | 无变更 |
| impact_scope | 1 | 仅咨询 |
| uncertainty | 1 | 问题明确 |
| coordination_cost | 1 | 单会话 |
| **总分** | **4** | **low** |

#### 3. 路由构建

```
route: [pax-clarify]
diagnose_required: false
storage_backend_required: false
cross_repo: false
```

**路由说明**：
1. `pax-clarify`: 澄清需求（具体想了解什么方面）

### 测试结果

```json
{
  "intent": {
    "primary": "doc_consult",
    "secondary": [],
    "confidence": "low"
  },
  "risk": {
    "irreversibility": 1,
    "impact_scope": 1,
    "uncertainty": 1,
    "coordination_cost": 1,
    "total": 4,
    "level": "low"
  },
  "route": ["pax-clarify"],
  "diagnose_required": false,
  "storage_backend_required": false,
  "cross_repo": false
}
```

### 结论

✅ 路由逻辑正确识别：
- 意图分类：`doc_consult`
- 风险等级：`low`（4 分）
- 路由：仅 `pax-clarify`（文档咨询不需要执行）

---

## 总结

| 场景 | 意图 | 风险 | 路由 | 跨仓库 |
|------|------|------|------|--------|
| CMDB 数据订正 | data_ops | high (9) | clarify→diagnose→plan→execute→review | ✓ |
| 新功能开发 | feature_dev | medium (6) | clarify→plan→execute→review | ✗ |
| 文档咨询 | doc_consult | low (4) | clarify | ✗ |

**验证结果**：
- ✅ 意图分类正确（MECE 6 类）
- ✅ 风险评分合理（4 维评分）
- ✅ 路由构建正确（根据意图选择）
- ✅ 存储后端需求检测正确（data_ops 需要）
- ✅ 跨仓库检测正确（前后端分离需要）
