# 内部路由数据集 v1.7 扩题设计（25 题）

**状态**：待审查。确认后写入数据集并跑付费调用。

## 1. 覆盖分析

现有 18 题的覆盖空白（按契约维度）：

| 维度 | 已覆盖 | 空白 |
|------|--------|------|
| primary_intent | 全部 6 种 | — |
| secondary_intent | data_integrity, performance | **security, ux_error, integration, deployment 完全未测**；多 secondary 叠加未测 |
| 强制升级：security → high | — | **未测** |
| 强制升级：data_integrity + imp=3 → high | — | **未测**（high-01 无 data_integrity secondary） |
| 强制升级：irr=3 + imp=3 → high | high-02 | 已覆盖 |
| W3 强制诊断：feature_dev + security → diagnose | — | **未测** |
| risk 量纲组合 | 4,6,7,8,9,10 | **5, 11, 12 未测**；多个 4-6 组合缺 |
| route_building | 3 种（diagnose_fix+data_integrity, feature_dev, doc_consult） | **security/ux_error/data_ops/refactor/tool_build 未测** |
| cross_repo | 1 题（前后端） | **微服务/同仓库/多仓库变体未测** |

## 2. 新增 25 题

### 2.1 intent_classification（+9 题）

#### pax-intent-ds-01 — diagnose_fix + security
```
PROMPT: 生产环境发现一个 SQL 注入漏洞，用户输入直接拼接到查询语句里，攻击者可以通过
特殊字符绕过认证。需要立即修复，防止数据泄露。
GOLD: primary=diagnose_fix, secondary=[security]
```
**依据**：契约「安全漏洞、数据泄露」→ `security`；"发现"+"修复" → 缺陷信号 → `diagnose_fix`

#### pax-intent-ux-01 — diagnose_fix + ux_error
```
PROMPT: 用户在网页上点击提交按钮没有任何反应，控制台显示一个 JS 错误，但后端接口其实
返回了正常数据。
GOLD: primary=diagnose_fix, secondary=[ux_error]
```
**依据**：契约「前端报错、点击无响应」→ `ux_error`（缺陷位于前端交互层）；"报错" → `diagnose_fix`

#### pax-intent-ig-01 — diagnose_fix + integration
```
PROMPT: 调用第三方支付接口返回 500 错误，对方说他们的服务正常，我们这边请求格式可能有问题。
GOLD: primary=diagnose_fix, secondary=[integration]
```
**依据**：契约「API 对接异常」→ `integration`；"报错" → `diagnose_fix`

#### pax-intent-de-01 — diagnose_fix + deployment
```
PROMPT: 昨天部署到生产环境后，新版本的配置没有生效，所有用户都看到了旧版本的页面。部署
脚本执行成功了，但配置项没被读取。
GOLD: primary=diagnose_fix, secondary=[deployment]
```
**依据**：契约「部署失败、配置错误、环境差异」→ `deployment`；"没有生效" → 异常 → `diagnose_fix`

#### pax-intent-dpi-01 — diagnose_fix + performance + data_integrity（多 secondary）
```
PROMPT: 最近一周系统响应时间从 200ms 增加到 2s，同时发现数据库里有一些订单状态不一致，
部分订单在业务系统显示已完成但数据库里还是 pending。
GOLD: primary=diagnose_fix, secondary=[performance, data_integrity]
```
**依据**：契约「延迟增加」→ `performance`；「数据不一致」→ `data_integrity`。二级意图可叠加

#### pax-intent-do-02 — data_ops（无 secondary）
```
PROMPT: 需要把用户表里所有 status 为 0 的记录批量更新为 1，这些是测试数据，共约 200 条。
GOLD: primary=data_ops, secondary=[]
```
**依据**：契约「批量更新/批量修改」→ `data_ops`；"测试数据"暗示有意标记，不是数据不一致 → 无 secondary

#### pax-intent-fs-01 — feature_dev + security（触发强制诊断）
```
PROMPT: 给系统加一个管理员后台，管理员可以查看和修改所有用户的个人信息，包括身份证号和
手机号。
GOLD: primary=feature_dev, secondary=[security]
```
**依据**：契约「新建功能」→ `feature_dev`；「权限异常、个人信息」→ `security`
⚠️ **待裁决**：这会触发 W3 强制诊断（feature_dev + security → diagnose=true），但
feature_dev 默认 diagnose=false。gold 里只检查 intent，不检查 diagnose。如果模型判
diagnose=false，route_building 题会 FAIL。

#### pax-intent-rp-01 — refactor + performance
```
PROMPT: 用户列表查询接口在数据量超过 10 万条时很慢，需要优化查询逻辑，加索引或改分页
策略，但不改变接口的入参和出参。
GOLD: primary=refactor, secondary=[performance]
```
**依据**：契约「不改变外部行为，改善内部结构/性能」→ `refactor`；「响应慢」→ `performance`

#### pax-intent-ti-01 — tool_build + integration
```
PROMPT: 写一个脚本，定时从公司内部的 GitLab API 拉取代码提交记录，汇总成日报发送到飞书群。
GOLD: primary=tool_build, secondary=[integration]
```
**依据**：契约「构建工具、脚本、自动化」→ `tool_build`；「API 对接」→ `integration`

---

### 2.2 risk_scoring（+8 题）

#### pax-risk-low-03 — (1,2,1,1)=5/low
```
PROMPT: 把团队内部的一个共享脚本里的日志格式从纯文本改成 JSON，方便机器解析。团队内 3 个
人会用这个脚本，改动后本地覆盖旧版本即可，不需要部署。改动很明确，就是把 print 改成
json.dumps。
GOLD: irr=1, imp=2, unc=1, cco=1, score=5, level=low
```
**依据**：irr=1「有备份、不触发部署」（本地覆盖）；imp=2「多使用人」；unc=1「需求明确」；cco=1「单人」

#### pax-risk-low-04 — (1,1,2,1)=5/low
```
PROMPT: 在本地开发环境试一下用 Redis 替代内存缓存，写个原型验证性能差异。改动只在
我的开发分支上，不影响任何生产数据。没用过 Redis 客户端库，需要先看一下文档。
GOLD: irr=1, imp=1, unc=2, cco=1, score=5, level=low
```
**依据**：irr=1「未上线的本地改动」；imp=1「仅本人」；unc=2「新库」；cco=1「单人」

#### pax-risk-low-05 — (2,1,1,1)=5/low
```
PROMPT: 把本地开发环境的 Node.js 版本从 18 升到 20，改一下 package.json 的 engines 字段。
改完需要重新部署到开发服务器，但可以一键回退到旧版本。需求很明确，不涉及生产环境，
只有我一个人用这个开发环境。
GOLD: irr=2, imp=1, unc=1, cco=1, score=5, level=low
```
**依据**：irr=2「改动需部署才能生效，即使可回滚也至少算 2」；imp=1「仅本人」；unc=1「明确」；cco=1「单人」

#### pax-risk-low-06 — (1,2,2,1)=6/low
```
PROMPT: 给团队共享的内部工具加一个数据导出功能，团队内 5 个人会用。导出格式用 CSV 还是
Excel 还没确定，需要先跟产品经理确认。改动在工具内部，本地覆盖旧版本即可。
GOLD: irr=1, imp=2, unc=2, cco=1, score=6, level=low
```
**依据**：irr=1「本地覆盖/有备份」；imp=2「多使用人」；unc=2「需产品确认即至少算 2」；cco=1「单人」

#### pax-risk-medium-04 — (2,2,2,1)=7/medium
```
PROMPT: 把用户注册接口从 HTTP 升级到 HTTPS，需要配置 SSL 证书。接口有 3 个调用方（都在
同一个仓库内）。证书配置流程不熟，需要先查文档验证一轮。改动由我一个人完成，不需要
code review。
GOLD: irr=2, imp=2, unc=2, cco=1, score=7, level=medium
```
**依据**：irr=2「部署可回滚」；imp=2「跨模块/有内部依赖」；unc=2「需要验证一个未验证的假设」；
cco=1「单人可完成」（契约：prompt 明确写"不需要 code review"，以"单人可完成"为准判 1）

#### pax-risk-medium-05 — (3,2,1,1)=7/medium
```
PROMPT: 删除生产数据库中已过期 1 年的测试环境数据备份（非生产数据），物理删除无法恢复。
这些备份只有测试团队内部使用。删除操作有标准手册，我一个人执行即可。
GOLD: irr=3, imp=2, unc=1, cco=1, score=7, level=medium
```
**依据**：irr=3「不可逆」；imp=2「单团队」（不是"全用户/核心链路"）；unc=1「标准手册=有先例可循」；cco=1「单人」
⚠️ 注意：irr=3 但 imp=2（不是 3），**不触发**强制升级。总分 7 → medium

#### pax-risk-high-03 — (3,3,2,2)=10/high
```
PROMPT: 把生产数据库的用户表从 MySQL 迁移到 PostgreSQL，涉及用户表、订单表、支付记录表
共 8 张表的关联迁移，数据量约 2000 万行。迁移后需要验证数据一致性，有回滚脚本但回滚
需要重新导入全量数据。涉及后端和前端两个团队的协调。
GOLD: irr=3, imp=3, unc=2, cco=3, score=10, level=high
```
**依据**：irr=3「大规模数据迁移/回滚成本极高」；imp=3「跨≥5张表且≥1000万行」；unc=2「需验证一致性」；
cco=3「跨团队协调」

#### pax-risk-high-04 — (2,3,2,2)=9/medium → **强制 high**
```
PROMPT: 生产环境中发现订单状态与支付状态不一致，部分用户已支付但订单仍显示待支付。
需要排查不一致的原因并批量订正，涉及订单表、支付表、用户表共 3 张表的数据修复，
影响所有用户。修复方案需要先验证一轮再上线，改动涉及后端和前端两个模块，需要
code review。
GOLD: irr=2, imp=3, unc=2, cco=2, score=9, level=high
```
**依据**：维度分 2+3+2+2=9（medium），但 prompt 描述「数据不一致」→ `data_integrity`，
且 imp=3 → **强制升级 high**（契约 W2 强制升级规则）
⚠️ **关键测试**：gold risk_level=high 而非按维度分的 medium。模型必须从 prompt 推断
data_integrity 并应用强制升级规则

#### pax-risk-high-05 — (1,3,1,1)=6/low → **强制 high**
```
PROMPT: 生产环境的用户登录日志表里，有部分记录的 login_time 字段是空值，导致报表统计时
出现 NULL 错误。需要排查原因并批量填充这些空值。涉及所有用户的历史登录记录，数据量约
5000 万行。操作前有完整备份，按标准流程执行，我一个人完成即可。
GOLD: irr=1, imp=3, unc=1, cco=1, score=6, level=high
```
**依据**：维度分 1+3+1+1=6（low），但「字段空值」→ `data_integrity`，imp=3
（≥1000万行）→ **强制升级 high**
⚠️ **关键测试**：维度分是 low 但强制升 high。irr=1（有备份，标准流程）

---

### 2.3 route_building（+5 题）

#### pax-route-ds-01 — diagnose_fix + security
```
PROMPT: 生产环境发现一个 SQL 注入漏洞，用户输入直接拼接到查询语句里，攻击者可以通过
特殊字符绕过认证。需要立即修复。
GOLD: route=[clarify,diagnose,plan,execute,review], diagnose=true, storage=false
```
**依据**：diagnose_fix → diagnose=true；security 不触发 storage_backend_required
（只有 data_ops 或 data_integrity 触发）

#### pax-route-ux-01 — diagnose_fix + ux_error
```
PROMPT: 用户在网页上点击提交按钮没有任何反应，控制台显示一个 JS 错误，但后端接口其实
返回了正常数据。
GOLD: route=[clarify,diagnose,plan,execute,review], diagnose=true, storage=false
```
**依据**：diagnose_fix → diagnose=true；ux_error 不触发 storage（触发 frontend_involved，
但不在 route_building gold 里）

#### pax-route-do-02 — data_ops（无 secondary）
```
PROMPT: 需要把用户表里所有 status 为 0 的记录批量更新为 1，这些是测试数据，共约 200 条。
GOLD: route=[clarify,diagnose,plan,execute,review], diagnose=true, storage=true
```
**依据**：data_ops → diagnose=true（W3 强制）且 storage_backend_required=true（W4）

#### pax-route-rf-01 — refactor
```
PROMPT: 把 500 行的单体方法拆分成多个职责单一的函数，保持接口行为不变。
GOLD: route=[clarify,plan,execute,review], diagnose=false, storage=false
```
**依据**：refactor → diagnose=false（W3「纯重构不改变外部行为」→ 跳过诊断）

#### pax-route-fs-01 — feature_dev + security → 强制诊断
```
PROMPT: 给系统加一个管理员后台，管理员可以查看和修改所有用户的个人信息，包括身份证号和
手机号。
GOLD: route=[clarify,diagnose,plan,execute,review], diagnose=true, storage=false
```
**依据**：feature_dev 默认 diagnose=false，但 W3 强制诊断条件「secondary 包含 security」
→ **强制 diagnose=true**
⚠️ **关键测试**：feature_dev + security 的路由是否包含 diagnose

---

### 2.4 cross_repo_detection（+3 题）

#### pax-cross-repo-02 — 微服务跨服务
```
PROMPT: 订单服务需要调用用户服务的新接口来获取用户偏好信息，两个服务部署在不同的服务器上。
GOLD: cross_repo=true, execution_strategy_required=true
```
**依据**：契约 is_cross_repo 信号「另一个服务」→ true

#### pax-cross-repo-03 — 同仓库跨模块 → false
```
PROMPT: 在同一个仓库内，服务 A 需要调用服务 B 的新函数，两个服务在同一个代码仓库里。
GOLD: cross_repo=false, execution_strategy_required=false
```
**依据**：契约 is_cross_repo 信号不包含"同一个仓库"→ false

#### pax-cross-repo-04 — 多仓库（含已知仓库名）
```
PROMPT: 前端 React 项目需要调用后端 Express 项目的新接口，两个项目分别在 ops-pilot-web
和 ops-monitor 两个仓库中。
GOLD: cross_repo=true, execution_strategy_required=true
```
**依据**：契约 is_cross_repo 信号「ops-monitor」「ops-pilot-web」→ true

---

## 3. 待裁决点（5 项）

| # | 题 | 争议 | 我的判定 | 备选 |
|---|-----|------|----------|------|
| 1 | pax-intent-do-02 | "批量更新测试数据"算不算 data_integrity？ | 否。"测试数据"暗示有意标记，不是不一致 | 若算 data_integrity，则 do-02 的 secondary=[data_integrity]，触发 storage_backend_required |
| 2 | pax-risk-low-03 | "本地覆盖旧版本"算不算 irr=1 的"有备份"？ | 是。覆盖前旧版本自然作为备份存在 | 若不算，irr=2，总分变 6 |
| 3 | pax-risk-medium-04 | "不需要 code review"能否判 cco=1？ | 是。契约明确「prompt 写'不需要配合'以'单人可完成'为准判 1」 | 若不算，cco=2，总分变 8 |
| 4 | pax-risk-high-04 | 维度分 9（medium）但强制升 high，gold 写 high | 是。模型必须从 prompt 推断 data_integrity 并应用强制升级 | 若只按维度分，gold=medium，但契约矛盾 |
| 5 | pax-route-fs-01 | feature_dev + security 的 diagnose_required | true。W3 强制诊断「secondary 含 security」 | 若 false，与 W3 契约矛盾 |

## 4. 统计

| 类别 | 现有 | 新增 | 合计 |
|------|------|------|------|
| intent_classification | 7 | 9 | 16 |
| risk_scoring | 7 | 8 | 15 |
| route_building | 3 | 5 | 8 |
| cross_repo_detection | 1 | 3 | 4 |
| **总计** | **18** | **25** | **43** |

holdout 标记：全部 25 题标记 `holdout: true`（gold 一次性推导，写入后不修订）。

付费调用：43 题 × 5 repeats = **215 次**（新增 125 次）。

## 5. 强制升级规则覆盖验证

| 规则 | 覆盖题 |
|------|--------|
| security → high | pax-intent-fs-01（intent 层）、pax-route-ds-01（route 层） |
| data_integrity + imp=3 → high | pax-risk-high-04（维度9→high）、pax-risk-high-05（维度6→high） |
| irr=3 + imp=3 → high | pax-risk-high-02（已有）、pax-risk-high-03 |
| W3 强制诊断：feature_dev + security → diagnose=true | pax-route-fs-01 |
