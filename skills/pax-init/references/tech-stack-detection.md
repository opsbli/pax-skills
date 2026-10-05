# 技术栈检测规则表

> 本文件是 `pax-init` 技术栈检测规则的**单一事实源**：检测哪些特征文件、提取什么内容，以本表为准。
> `scripts/scan_project.py` 按本表实现检测；**新增规则需同时改两处**——在本表追加一行，并在脚本的
> `scan_tech_stack()` 中实现对应提取逻辑。不改脚本时，新规则按本表人工核对，结论口径不变。
>
> **诚实铁律**：每一行检测 MUST 基于特征文件的**实际存在**。命中即记录特征文件路径，未命中标注「未检测到」，
> NEVER 根据目录名、项目名或上下文猜测技术栈。

## 1. 特征文件检测表

| # | 检测目标 | 特征文件（存在即命中） | 提取内容 |
|---|---|---|---|
| 1 | Java / Maven | `pom.xml` | `<java.version>`、`<groupId>`、`<artifactId>`、`<modules>` |
| 2 | Java / Gradle | `build.gradle` / `build.gradle.kts` | `sourceCompatibility`、依赖块 |
| 3 | Spring Boot | `pom.xml` 含 `spring-boot-starter` | Boot 版本、已启用 starter 列表 |
| 4 | RuoYi 框架 | 目录含 `ruoyi-*` 模块 | 框架版本、模块清单、代码生成器模块路径 |
| 5 | TypeScript | `tsconfig.json` | TS 版本、编译选项 |
| 6 | Vite | `vite.config.ts` / `vite.config.js` | Vite 版本、插件 |
| 7 | Vue | `package.json` 依赖含 `"vue"` | Vue 版本、UI 库 |
| 8 | React | `package.json` 依赖含 `"react"` | React 版本、UI 库 |
| 9 | Element Plus | `package.json` 依赖含 `element-plus` | 版本 |
| 10 | Ant Design | `package.json` 依赖含 `ant-design` | 版本 |
| 11 | UnoCSS / Tailwind | `package.json` 依赖含 `unocss` / `tailwindcss` | 版本 |
| 12 | Pinia / Vuex | `package.json` 依赖含 `pinia` / `vuex` | 版本 |
| 13 | Go | `go.mod` | Go 版本、框架（Gin / Echo） |
| 14 | Python | `requirements.txt` / `pyproject.toml` | Python 版本、框架（Django / FastAPI） |
| 15 | Node.js | `package.json` | Node 版本约束、包管理器 |
| 16 | Docker | `Dockerfile` / `docker-compose.yml` | 基础镜像 |
| 17 | CI/CD | `Jenkinsfile` / `.github/workflows/` | CI 工具 |

> 扩展方式：在表尾追加行，填写「检测目标 / 特征文件 / 提取内容」三列；随后在 `scripts/scan_project.py` 的 `scan_tech_stack()` 中实现同名提取逻辑，或改由人工按本表核对。

## 2. 包管理器检测优先级

同一特征文件可能产生多个候选，按优先级取第一个命中项：

| 优先级 | 特征文件 | 判定 |
|---|---|---|
| 1 | `pnpm-lock.yaml` | pnpm |
| 2 | `yarn.lock` | yarn |
| 3 | `package-lock.json` | npm |
| 4 | 仅有 `package.json`、无任何 lock | 未检测到（标「未检测到」，NEVER 猜测） |

> **已知陷阱（实证）**：`package-lock.json` 可能是历史遗留产物，项目实际已迁移到 pnpm——两者同时存在的项目并不少见。
> 因此检测结果 MUST 交用户确认后才写入 `project-profile.json` 的 `frontend.package_manager`；
> 用户确认与 lock 文件冲突时以用户确认为准，并在 profile 中记录差异（`package_manager_note`）。

## 3. 前后端分离识别

| 信号 | 判定 | 记录位置 |
|---|---|---|
| 后端根目录有 `pom.xml` / `go.mod`，且另有独立前端 `package.json` 项目 | 多项目模式 | `repo_path` + `frontend.path` |
| 单目录同时含后端与前端特征文件 | 单项目模式（标注前端内嵌） | `repo_path` |
| 仅前端特征文件 | 单项目模式（仅前端） | `repo_path` |

多项目模式下 API 前缀、端口、跨域配置三项 MUST 显式确认后写入 profile 的 `frontend` 区；
未确认时标注「未检测到」，NEVER 猜测。
