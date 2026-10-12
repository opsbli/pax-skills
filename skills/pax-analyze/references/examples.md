# pax-analyze 真实样例

> 本文件为 `pax-analyze` 的走查样例（Worked Examples），帮助执行时对齐工作流与输出格式。
> 样例中的路径、组件名、凭据均为**示例占位**：凡含敏感值（密码、token、连接串凭据）一律用
> `<REDACTED>` 替代，**绝不把真实凭据写入本文件 / 快照 / 沉淀文档**。

样例 A：数据链路溯源（「这个接口返回的数据为什么是 0 / 数据是什么时候写入 ES 的」）
样例 B：行为解释 + 方案对比（事实调研、多子问题收敛、含反证证据与残差）

---

## 样例 A：数据链路溯源

**目标语句（`goal.statement`）**
> 帮我分析「查询设备用量」这个接口，返回的数据全是 0。它到底是查的哪个存储，数据是什么时候写入 ES 的？

**澄清收敛（`snapshot.consensus`，doc_consult 轻量）**
- `goal`：确认查询链路与写入链路，判断「为什么返回 0」
- `success_criteria`：给出 ① 该接口实际读取的数据源 ② 数据写入 ES 的时机与入口 ③ 返回 0 的最可能分支
- 用户确认：**只分析，不修复**

### A1 只读边界确认

```yaml
analysis_scope:
  read_only: true
  targets:
    - type: repo_path
      value: "backend/usage-service/"
    - type: config
      value: "backend/usage-service/src/main/resources/application.yml"
    - type: data_source
      value: "elasticsearch://elasticsearch.<REDACTED>:9200（只读查询，禁止写）"
  allowed_reads:
    - "src/**"
    - "config/**"
    - "只读 ES / DB 查询（GET / _search）"
    - "应用日志（stdout / 日志目录）"
  forbidden:
    - "写文件"
    - "数据订正 / 索引重建"
    - "任何破坏性命令"
    - "读取或落盘任何明文凭据"
```

### A2 子问题拆解

| 子问题 | 待验证点 | 证据类型 | 来源 |
|---|---|---|---|
| Q1 | 该接口读哪个存储？ES 还是 DB | code_search | Controller/Service/Repository |
| Q2 | 数据写 ES 的入口与时机（同步/异步、哪个方法触发） | code_search | 写入链路、MQ consumer |
| Q3 | 写入的索引名 / 字段，与查询的索引是否一致 | configuration + code_search | application.yml、@Document/@Index 注解 |
| Q4 | 返回 0 的分支：索引无匹配 vs 查询条件过滤 vs 汇聚字段缺失 | runtime_probe + code_search | 只读 ES _search、查询聚合代码 |

### A3 证据收集

用只读检索逐步收集，每条证据记录来源与方法：

```yaml
evidence_collected:
  - sub_question: Q1
    result:
      - source: "usage-service/src/main/java/com/acme/usage/web/UsageController.java"
        method: code_search    # 复现：grep -n "UsageService" 
        content: "GET /usage/query → 注入 UsageQueryService#query(uid, date)"
        confidence: high
      - source: "usage-service/src/main/java/com/acme/usage/service/UsageQueryService.java"
        method: code_search
        content: "query() 先打 DB，无结果时走 usageSearchRepository.search()（ES）"
        confidence: high
  - sub_question: Q2
    result:
      - source: "usage-service/src/main/java/com/acme/usage/mq/UsageWriteConsumer.java"
        method: code_search
        content: "@KafkaListener 消费 usage.written topic，调用 usageSearchRepository.save() 写 ES"
        confidence: high
      - source: "usage-service/src/main/resources/application.yml"
        method: configuration
        content: "topic: usage.written；写入走异步 MQ，非请求内同步写"
        confidence: high
  - sub_question: Q3
    result:
      - source: "usage-service/.../UsageSearchRepository.java"
        method: code_search
        content: "@Document(indexName = \"usage_daily\")；查询也指向 usage_daily"
        confidence: high
      - source: "只读 ES 查询（/usage_daily/_count）"
        method: runtime_probe
        content: "索引 usage_daily 存在，count=0（无任何文档）"
        confidence: high
      - source: "只读日志（UsageWriteConsumer）"
        method: runtime_probe
        content: "近 24h 日志未见 usage.written 消费记录，offset 无推进"
        confidence: medium   # 日志可能滚动
  - sub_question: Q4
    result:
      - source: "UsageQueryService.query() 分支阅读"
        method: code_search
        content: "DBResult==null → 查 ES → ES 空则返回 0"
        confidence: high
```

### A4 结论合成

```text
逐子问题收敛：
- Q1 确认：接口 DB 优先，DB 空时走 ES 查询。
- Q2 确认：写 ES 是异步（Kafka consumer 消费 usage.written 后 save）。
- Q3 确认：查询与写入索引一致（usage_daily）。
- Q4 关键：ES 索引 count=0，且日志未见 consumer 消费 → 写入链路未消费到消息。

主结论：返回 0 的直接原因是 ES 索引 usage_daily 无数据，而数据写入依赖异步 MQ
（usage.written → UsageWriteConsumer），当前该 consumer 未消费到消息，
因此「数据尚未写入 ES」——问题不在查询层，而在写入/消费链路。
置信度：medium（日志是否滚动未完全排除）。

残差（open_questions）：
- usage.written topic 是否有生产者未投递，还是 consumer 消费失败/offset 停止。
- 是否需要溯源 DB 源头数据是否本身为空。
```

### A5 沉淀与回报（可选）

- 用户未要求留档 → 仅回写 `snapshot.analysis` 并向父会话汇报，不产 ADR。
- 若要求留档 → 调 `pax-docs` 沉淀一条分析记录。

### 输出契约落点（`snapshot.analysis`）

```yaml
analysis:
  findings:
    - id: F1
      sub_question: "Q1"
      statement: "接口取数：DB 优先，DB 空则查 ES"
      evidence:
        - source: "UsageController.java / UsageQueryService.java"
          method: code_search
          content: "query() → DB → fallback ES search"
          confidence: high
      supports: true
    - id: F2
      sub_question: "Q2"
      statement: "写 ES 为异步：Kafka consumer 消费 usage.written 后 save"
      evidence:
        - source: "UsageWriteConsumer.java / application.yml"
          method: code_search
          content: "@KafkaListener usage.written → usageSearchRepository.save()"
          confidence: high
      supports: true
    - id: F3
      sub_question: "Q3"
      statement: "查询与写入索引一致：usage_daily"
      evidence:
        - source: "UsageSearchRepository.java"
          method: code_search
          content: "@Document(indexName=\"usage_daily\") + 查询同索引"
          confidence: high
      supports: true
    - id: F4
      sub_question: "Q4"
      statement: "索引 usage_daily 当前 count=0，且日志未见 consumer 消费"
      evidence:
        - source: "只读 ES /usage_daily/_count ; 日志"
          method: runtime_probe
          content: "count=0；近 24h 无消费记录"
          confidence: medium
      supports: true
  conclusion: "返回 0 的直接原因是 ES 索引 usage_daily 无数据；写入依赖异步 MQ，当前 consumer 未消费到消息，问题在写入/消费链路而非查询层。"
  confidence: medium
  open_questions:
    - "usage.written 是否有生产者投递失败，或 consumer 消费失败 / offset 停止"
    - "DB 源头数据是否本身为空（上游入库是否成功）"
  read_only: true
```

---

## 样例 B：行为解释 + 方案对比（事实调研）

**目标语句（`goal.statement`）**
> 解释这个 `@EnableScheduling` 配置在项目里的作用，并对比「用定时任务 vs 用 Kafka 延迟队列」做数据刷新的差异。

**澄清收敛**
- `goal`：① 说清该配置当前作用 ② 对比两种刷新方案的事实差异（不选型）
- `success_criteria`：给出①配置触发点与调度周期 ②两者在触发方式/可靠性/运维差异上的事实对比

### A1 只读边界

```yaml
analysis_scope:
  read_only: true
  targets:
    - type: repo_path
      value: "backend/usage-service/"
      allowed_reads: ["src/**", "config/**"]
  forbidden: ["写文件", "选型落地", "改调度策略"]
```

### A2 子问题拆解

| 子问题 | 待验证点 | 证据类型 | 来源 |
|---|---|---|---|
| Q1 | @EnableScheduling 实际开启/关闭哪里的调度 | code_search | 配置类、@Scheduled 方法 |
| Q2 | 该调度任务的周期与副作用 | configuration + code_search | cron、方法体 |
| Q3 | 定时 vs 延迟队列：触发模型/可靠性/运维差异 | documentation | 官方文档、项目现状 |

### A3 证据收集

```yaml
evidence_collected:
  - sub_question: Q1
    result:
      - source: ".../config/SchedulingConfig.java"
        method: code_search
        content: "@EnableScheduling 开启 Spring 调度，并配置 ThreadPoolTaskScheduler 池大小"
        confidence: high
  - sub_question: Q2
    result:
      - source: ".../job/UsageDailyRollupJob.java"
        method: code_search
        content: "@Scheduled(cron=\"0 0 2 * * ?\") 每日 02:00 触发日汇总刷新"
        confidence: high
      - source: "只读 Cron 有效性核对"
        method: configuration
        content: "cron 表达式合法，单机执行（默认单线程下无并发问题）"
        confidence: high
  - sub_question: Q3
    result:
      - source: "官方文档 + 项目 MQ 现状"
        method: documentation
        content: "定时任务依赖时钟与单机存活；Kafka 延迟队列依赖消息到期语义与重投，可靠性更高但需额外 topic 与消费者"
        confidence: medium   # 依赖对现状的准确了解
```

### A4 结论合成

```text
Q1/Q2 确认：@EnableScheduling 开启 Spring 调度，承载每日 02:00 的 usage 日汇总刷新。
Q3：两种方案事实差异——定时任务实现简单、依赖单机时钟与存活；延迟队列触发更精准、
可重投、不依赖单机，但引入 MQ 与消费侧运维成本。
主结论：当前项目用定时任务做周期刷新；若刷新强依赖「到期即触发 + 容错重投」，
延迟队列在可靠性上更优，但两者是「取舍」而非「孰优」，选型超出仅分析边界。
置信度：medium。
残差：项目当前 MQ 是否已有可复用的延迟语义未完全核实。
```

### 输出契约落点（截选 `snapshot.analysis`）

```yaml
analysis:
  findings:
    - id: F1
      sub_question: "Q3"
      statement: "定时任务：简单、依赖单机时钟/存活；延迟队列：触发精准、可重投、不依赖单机，但引入 MQ 运维成本"
      evidence:
        - source: "官方文档 / 项目 MQ 现状"
          method: documentation
          content: "对比触发模型与可靠性"
          confidence: medium
      supports: true
  conclusion: "@EnableScheduling 开启 Spring 调度并承载每日 02:00 的 usage 日汇总；定时任务与延迟队列是可靠性/运维成本间的取舍，选型应另走决策流程。"
  confidence: medium
  open_questions:
    - "项目现有 MQ 实例是否已具备可复用的延迟语义（真实实例/集群情况）"
  read_only: true
```

> 说明：样例 B 遇到「选型」超出只读分析边界——pax-analyze 只给事实差异并写明残差，
> 不落地选型；若用户确实要做决策，应在编排层评估是否升级到 `pax-advisor`/`pax-council`。
