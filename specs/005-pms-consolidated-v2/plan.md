# Implementation Plan: PMS 项目交付管理系统（归纳版）

**Branch**: `005-pms-consolidated-v2` | **Date**: 2026-07-10 | **Spec**: [spec.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/spec.md)

**Input**: Feature specification from `/specs/005-pms-consolidated-v2/spec.md`

## Summary

基于 005 归纳版 spec（17 User Stories、139 FR、38 Key Entities、25 SC、34 Edge Cases），构建新一代 PMS 项目交付管理系统。本 spec 为 003（合并版）与 004（V2 补充）归纳去重后的统一规格基线，新增"桌面客户端离线模式"能力（FR-119a/b/c/d）作为本版关键增强。

系统作为原厂交付体系中枢，覆盖项目全生命周期（立项→指派→实施→闭环）与 8 个交付子阶段（工前→计划→方案→部署→验收→割接→归档），整合售前/转包/回访/维保/技术公告等历史能力与割接平台/服务平台/AI 排障/CRM 同步/ITR-RMA 等新业务增强，对接 18+ 外部系统。

技术架构沿用 003 决策（Spring Boot 3.2 + Vue 3.4 + MySQL 8.0 + Redis 7 + ES 8 + MinIO + Flowable + RocketMQ），新增：桌面客户端（Electron 内嵌 PC Web，本地 SQLite + SQLCipher 加密，离线草稿 + 字段级合并同步）、离线 Token 校验、7 天缓存增量刷新机制。技术选型详见 [research.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/research.md)。

## Technical Context

**Language/Version**:
- 后端：Java 17 LTS（Spring Boot 3.2.x）
- 前端：TypeScript 5.x + Vue 3.4.x
- 移动端：Vue 3 + Vant 4（H5）
- 桌面客户端：TypeScript + Electron 28+（内嵌 PC Web 前端）
- 脚本/工具：Python 3.11+（数据迁移/ETL）

**Primary Dependencies**:
- 后端框架：Spring Boot 3.2.x + Spring Security 6 + Spring Cloud 2023.x（可选微服务）
- 持久层：MyBatis-Plus 3.5.x（替代老系统 iBATIS 2 + MyBatis 双 ORM）
- 工作流：Flowable 7.x（替代 Activiti 5.23.0，保留 BPMN 语义但重写流程定义）
- 认证授权：Spring Security + LDAP/AD 绑定认证 + RBAC + JWT（含离线令牌）
- 前端框架：Vue 3.4.x + Vite 5 + Pinia + Vue Router 4 + Element Plus 2.x（PC）+ Vant 4（H5）
- 数据库：MySQL 8.0 主从 + Redis 7.x（缓存/分布式锁）+ Elasticsearch 8.x（全文检索/日志）
- 消息队列：RocketMQ 5.x（异步事件：审批推送/数据同步/归档/离线同步事件）
- 对象存储：MinIO（交付件/配置 Log/巡检报告存储 + 冷存储分层）
- 桌面客户端：Electron 28+ + better-sqlite3 + SQLCipher（本地加密 SQLite）
- 离线同步：自研 delta-sync 协议（基于版本向量 + 字段级 diff + 乐观锁）
- 文件解析：Apache POI（Excel 导入导出）+ Apache Tika（文件类型识别）
- OCR：百度 OCR 或阿里云 OCR（发票识别）
- 集成：OpenFeign（HTTP 客户端）+ Spring Integration（EDI/文件传输）
- 监控：Spring Boot Actuator + Prometheus + Grafana + SkyWalking（APM 链路追踪）
- 日志：Logback + ELK（Elasticsearch + Logstash + Kibana）

**Storage**:
- 主库：MySQL 8.0（业务数据，多数据源动态路由保留 9 个数据源）
- 缓存：Redis 7.x（会话/字典/配置/分布式锁/限流）
- 搜索：Elasticsearch 8.x（项目/设备/工单全文检索 + 日志分析）
- 文件：对象存储 MinIO（交付件/Log/照片，分层：热存储 + 冷存储低频访问层）
- 桌面本地：SQLite + SQLCipher（加密本地缓存 + 离线草稿 + 版本向量）
- 配置：Nacos 2.x（配置中心 + 服务注册发现，如采用微服务）

**Testing**:
- 后端：JUnit 5 + Mockito + Spring Boot Test + Testcontainers（集成测试）
- 前端：Vitest + Vue Test Utils + Playwright（E2E）
- 桌面客户端：Playwright（Electron E2E）+ Jest（主进程单元测试）
- 契约：Pact 或 Spring Cloud Contract（外部集成契约测试）
- 离线同步：专项测试（冲突合并/超期/账户变更/断网恢复场景）
- 性能：JMeter（1000 并发压测）
- 覆盖率：JaCoCo（后端 ≥80%）+ Istanbul/c8（前端 ≥70%）

**Target Platform**:
- 服务端：Linux（CentOS 7+ / Ubuntu 22.04+），Docker 容器化部署
- PC Web：Chrome/Edge/Firefox 最新版 + Safari 15+（现代浏览器）
- 桌面客户端：Windows 10+ / macOS 12+ / 麒麟 V10+（国产化适配）
- 移动端 H5：iOS 14+ / Android 10+（微信内置浏览器兼容）
- 可用性：7×24，SLA 99.9%（年停机 ≤8.76 小时）

**Project Type**: Web 应用（前后端分离）+ 桌面客户端（Electron）+ 移动端 H5 + 多外部系统集成

**Performance Goals**:
- 1000 并发用户，报表 P95 ≤2 秒（SC-021）
- 接口 P95 ≤500ms（非报表）
- 文件上传支持 100MB+，断点续传
- 7×24 可用性 ≥99.9%（SC-023）
- 跨系统集成点同步成功率 ≥99%（SC-017）
- 桌面客户端离线写操作本地响应 ≤200ms，联网后增量同步 ≤30 秒/项目
- CRM 双向同步延迟 ≤5 分钟，客户服务等级同步延迟 ≤1 分钟（SC-012）

**Constraints**:
- 1000 并发用户无 degradation
- 数据权限按"办事处/项目归属"过滤
- 多数据源动态路由（保留 9 个数据源）
- 桌面客户端离线：仅允许填写类写操作暂存草稿；审批/状态流转/割接发起/闭环/转包发起等强一致性写操作离线禁用
- 本地缓存加密 + 登录态校验 + 7 天有效期 + 退出清除
- 老系统业务流程语义保留（状态机/审批节点/角色指派）
- 新老系统并行运行+增量同步+灰度切换+可回滚
- 数据分级保留：交付件 ≥5 年、巡检/割接 ≥3 年、AI 训练数据脱敏长期

**Scale/Scope**:
- 286 老表 + 43 视图迁移至新系统
- 139 FR、17 User Stories、38 Key Entities、34 Edge Cases
- 18+ 外部系统集成（D365/SMS/OA/EHR/CRM/SAP/MES/钉钉/LDAP-AD/迪普服务平台/ITR/RMA/客户资产库/供应链/割接管理平台/冷存储/SPMS/CAS/FP）
- 5 类终端（PC Web / 桌面客户端 / 工程师 H5 / 代理商 H5 / 客户 H5）
- 预估代码量：后端 15 万行 + 前端 10 万行 + 桌面客户端 2 万行 + 移动端 3 万行

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 为空模板（`.specify/memory/constitution.md` 未实例化），无原则约束。视为 gate 全部通过，无 violations。

后续若项目落地 Constitution，需补充并重新校验以下原则对齐：
- 模块边界与业务域聚合原则（005 spec 已按项目交付生命周期组织模块）
- 安全与合规原则（LDAP/AD + 数据权限 + 本地加密）
- 可观测性原则（SkyWalking + Prometheus + ELK）
- 离线优先 vs 在线优先原则（FR-119 系列确立"桌面客户端离线写草稿 + 强一致性联机"模型）

## Project Structure

### Documentation (this feature)

```text
specs/005-pms-consolidated-v2/
├── plan.md              # 本文件（/speckit-plan 输出）
├── research.md          # Phase 0 输出（技术选型研究）
├── data-model.md        # Phase 1 输出（实体数据模型）
├── quickstart.md        # Phase 1 输出（端到端验证指南）
├── contracts/           # Phase 1 输出（接口契约）
│   ├── rest-api.md           # REST API 契约（按业务域分组）
│   ├── external-integrations.md  # 外部系统集成契约（18+ 系统）
│   ├── desktop-sync.md       # 桌面客户端离线同步协议契约
│   └── events.md             # 事件契约（异步消息主题与载荷）
├── spec.md              # 特性规格（/speckit-specify 输出）
├── checklists/
│   └── requirements.md  # 质量检查清单
└── tasks.md             # Phase 2 输出（/speckit-tasks，非本命令创建）
```

### Source Code (repository root)

采用 Web Application + 桌面客户端 + 移动端 H5 结构。模块按业务域聚合组织（005 spec：项目交付生命周期为主线 + 横切模块独立）。

```text
pms/
├── backend/                          # 后端 Spring Boot 应用
│   ├── pom.xml                        # Maven 父 POM
│   ├── pms-common/                    # 通用模块（工具类/常量/枚举/异常）
│   ├── pms-domain/                    # 领域模型（Entity/VO/DTO/枚举）
│   ├── pms-infra/                     # 基础设施层
│   │   ├── persistence/               # 持久化（MyBatis-Plus Mapper/多数据源配置）
│   │   ├── security/                  # 安全（LDAP/AD 认证/RBAC/数据权限/JWT 离线令牌）
│   │   ├── storage/                   # 对象存储（MinIO 分层）
│   │   ├── messaging/                 # 消息队列（RocketMQ 生产者/消费者）
│   │   ├── search/                    # 搜索（Elasticsearch 索引/查询）
│   │   ├── sync/                      # 桌面客户端离线同步服务端（delta-sync/版本向量/字段合并）
│   │   └── integration/              # 外部集成客户端（D365/CRM/钉钉/ITR/RMA/MES 等）
│   ├── pms-workflow/                  # 工作流引擎（Flowable 流程定义/监听器/任务管理）
│   ├── pms-modules/                   # 业务模块（按业务域聚合）
│   │   ├── pms-project/               # 项目生命周期（立项/指派/状态机/主子项目）
│   │   ├── pms-delivery/              # 交付生命周期（工前/计划/方案/部署/验收/归档）
│   │   │   ├── prework/               # 工前准备（客户联系人/工勘/需求分析/物料换货）
│   │   │   ├── plan/                  # 施工计划（三层时间模型/工期倒推）
│   │   │   ├── scheme/                # 实施方案
│   │   │   ├── deploy/                # 实施部署（到货/硬件/配置 Log/联调/割接发起）
│   │   │   └── acceptance/            # 验收交维（培训/满意度/初终验/交付件）
│   │   ├── pms-cutover/               # 割接管理（割接平台集成/操作单/checklist/归档）
│   │   ├── pms-presales/              # 售前测试（申请/审批/跟踪/临时授权）
│   │   ├── pms-subcontract/           # 转包管理（审批/合同/付款/回访/验收）
│   │   ├── pms-maintenance/           # 维保管理（维护记录/问卷/交付件）
│   │   ├── pms-techbulletin/          # 技术公告（发布/影响范围/修复任务）
│   │   ├── pms-device/                # 设备信息增强（配置历史/部署风险/接口对照/拓扑/版本）
│   │   ├── pms-service-platform/      # 服务平台集成（巡检/CRT log/解析回传）
│   │   ├── pms-ai-troubleshoot/       # AI 排障（AGENT/知识库/工具集/Skill 训练）
│   │   ├── pms-customer/              # 客户管理与资产库（CRM 同步/最终客户/资产库视图）
│   │   ├── pms-itr/                   # ITR 故障处理（工单/解决方案/RMA 调用）
│   │   ├── pms-weekly/                # 周报与文件管理
│   │   └── pms-report/               # 报表分析
│   ├── pms-api/                      # API 层（REST Controller/OpenAPI 文档/桌面同步端点）
│   ├── pms-migration/                # 数据迁移（ETL 脚本/校验/灰度切换）
│   └── pms-app/                      # 启动应用（Spring Boot 主类/配置）
│
├── frontend/                         # 前端 Vue 3 应用（PC Web + 桌面客户端内嵌）
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/                    # Vue Router（路由守卫/权限过滤/离线模式路由标记）
│   │   ├── stores/                    # Pinia 状态管理（含离线状态/同步队列/缓存元数据）
│   │   ├── api/                       # API 客户端（Axios 封装/请求拦截/离线降级）
│   │   ├── offline/                   # 离线能力（仅在桌面客户端激活）
│   │   │   ├── db.ts                  # 本地 SQLite 访问层（better-sqlite3 封装）
│   │   │   ├── crypto.ts              # 本地缓存加密（SQLCipher/AES-256）
│   │   │   ├── sync-engine.ts         # 同步引擎（delta-sync/版本向量/字段合并）
│   │   │   ├── conflict-resolver.ts   # 冲突裁定 UI 与逻辑
│   │   │   └── token-validator.ts     # 离线登录态校验
│   │   ├── components/                # 通用组件
│   │   │   ├── layout/                # 布局（Header/Sidebar/Breadcrumb/TagsView）
│   │   │   ├── form/                  # 表单组件（动态表单/表单设计器）
│   │   │   ├── table/                 # 表格组件（可编辑表格/列配置/导出）
│   │   │   ├── upload/                # 上传组件（断点续传/水印/预览）
│   │   │   ├── workflow/              # 工作流组件（审批流转/流程图预览）
│   │   │   ├── chart/                 # 图表组件（ECharts 封装）
│   │   │   ├── topolog/               # 拓扑可视化（网络拓扑自动生成）
│   │   │   └── offline/               # 离线状态指示/缓存过期提示/同步进度
│   │   ├── views/                     # 页面（按业务域聚合）
│   │   │   ├── project/               # 项目跟踪（总体跟踪/单项目跟踪）
│   │   │   ├── delivery/              # 交付（工前/计划/方案/部署/验收）
│   │   │   ├── cutover/               # 割接管理
│   │   │   ├── presales/              # 售前测试
│   │   │   ├── subcontract/           # 转包管理
│   │   │   ├── maintenance/           # 维保管理
│   │   │   ├── techbulletin/          # 技术公告
│   │   │   ├── device/                # 设备信息
│   │   │   ├── itr/                   # ITR 故障
│   │   │   ├── weekly/                # 周报
│   │   │   ├── report/                # 报表
│   │   │   ├── customer/              # 客户与资产库
│   │   │   ├── system/                # 系统管理
│   │   │   └── ai-troubleshoot/       # AI 排障
│   │   ├── composables/               # 组合式函数（权限/字典/上传/水印/离线写操作）
│   │   ├── directives/                # 自定义指令（权限按钮 v-permission/离线禁用 v-offline-disabled）
│   │   ├── locales/                   # 国际化
│   │   └── assets/                    # 静态资源
│   └── tests/                         # 前端测试
│
├── desktop/                          # 桌面客户端 Electron 壳
│   ├── package.json
│   ├── electron/                     # 主进程
│   │   ├── main.ts                   # 主进程入口（窗口管理/生命周期）
│   │   ├── preload.ts                # 预加载脚本（IPC 桥接/本地文件系统访问）
│   │   ├── sqlite/                   # SQLite + SQLCipher 集成
│   │   ├── auto-updater.ts           # 自动更新
│   │   └── cleanup.ts                # 退出清除本地缓存
│   ├── electron-builder.yml          # 打包配置（Windows/macOS/麒麟）
│   └── tests/
│
├── mobile/                           # 移动端 H5 应用
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/                    # 路由（工程师/代理商/客户入口）
│   │   ├── stores/                    # Pinia（离线缓存状态）
│   │   ├── api/                       # API 客户端
│   │   ├── components/                # 移动端组件
│   │   │   ├── sign-in/               # 签到（GPS+水印拍照）
│   │   │   ├── offline/               # 离线缓存（IndexedDB 封装）
│   │   │   └── upload/                # 离线上传（断点续传）
│   │   └── views/
│   │       ├── engineer/              # 工程师工作台（签到/施工/上报）
│   │       ├── agent/                  # 代理商工作台（接单/上报/交付）
│   │       └── customer/              # 客户入口（进度/审批/签核）
│   └── tests/
│
├── deploy/                           # 部署配置
│   ├── docker/                        # Dockerfile（后端/前端/移动端）
│   ├── k8s/                           # Kubernetes 编排（如采用）
│   ├── nginx/                         # Nginx 配置（前端/移动端静态+反代）
│   └── sql/                           # 数据库初始化脚本
│
├── docs/                             # 项目文档
│   ├── architecture/                  # 架构文档（C4 模型/部署图/离线同步时序图）
│   ├── api/                           # API 文档（OpenAPI 生成）
│   └── runbook/                       # 运维手册
│
└── scripts/                         # 工具脚本
    ├── migration/                     # 数据迁移脚本（Python）
    ├── seed/                          # 种子数据
    └── ci/                            # CI/CD 脚本
```

**Structure Decision**:
采用 Web Application + 桌面客户端 + 移动端 H5 结构。后端按分层架构 + 业务域模块化组织：
- **分层**：common/domain/infra/workflow/api/app 横切分层
- **业务域**：pms-modules 下按"项目交付生命周期"主线聚合（project/delivery/cutover/presales/subcontract/maintenance/techbulletin/device/service-platform/ai-troubleshoot/customer/itr/weekly/report），符合 005 spec 的"按业务域聚合"决策
- **前端**：PC Web（Element Plus）+ 移动端 H5（Vant 4）+ 桌面客户端（Electron 内嵌 PC Web）共享同一前端代码库，通过 `src/offline/` 模块在桌面客户端激活离线能力
- **桌面客户端**：Electron 作为壳，复用 frontend 前端代码，主进程管理 SQLite 本地存储、加密、同步引擎、自动更新
- **离线同步服务端**：后端 pms-infra/sync 模块提供 delta-sync 端点，支持版本向量比对、字段级 diff、冲突检测与合并

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 9 个数据源（保留多数据源） | 老系统依赖 9 个外部库（D365/CRM/SAP/MES 等直连查询），合并为单库需大量 ETL 且数据所有权分散 | 单库方案需迁移所有外部数据，违反数据所有权边界且实时性损失 |
| 桌面客户端 Electron + 本地 SQLite | FR-119a/b/c/d 要求离线全功能操作 + 提前缓存项目数据 + 本地加密 + 7 天有效期 + 增量同步 | 纯 PWA + IndexedDB 无法满足：IndexedDB 容量限制、加密能力弱、无法支持复杂 SQL 查询、无法稳定后台同步 |
| 离线字段级合并同步协议（自研） | FR-119a 要求未冲突字段自动合并、冲突字段人工裁定、已审核锁定字段拒绝覆盖；既有乐观锁仅覆盖在线并发 | 纯 Last-Write-Wins 会静默覆盖业务关键数据；纯 CRDT 过于复杂且不适合业务语义裁定 |
| 离线登录态校验（JWT 离线令牌） | FR-119c 要求账户锁定/变更后本地缓存不可用，离线时需校验上次登录令牌有效期 | 纯在线校验在离线时无法使用；纯本地免校验存在账户停用后数据泄露风险 |
| Flowable 工作流引擎 | 老系统 Activiti 5.23 已 EOL，业务流程复杂（售前/转包/回访/闭环多级审批） | 自研状态机无法支持复杂审批流（会签/或签/委派/超时升级） |
| Elasticsearch 全文检索 | 286 表百万级数据的项目/设备/工单检索，MySQL LIKE 性能不足 | MySQL 全文索引对中文支持差且无分词，无法满足 P95 ≤2 秒 |
| 对象存储分层（热+冷） | 交付件保留 ≥5 年，全热存储成本高 | 全热存储成本 5 倍以上，冷存储取回虽慢但符合归档场景 |
| 多终端 5 类终端 | FR-119/119a-d/120/121/122 要求 PC Web + 桌面客户端 + 工程师 H5 + 代理商 H5 + 客户 H5 | 单一 Web 无法满足现场作业离线、客户轻量入口、客户手机签核等多场景需求 |
| AI 排障 RAG 架构 | FR-095~098 要求 AI 诊断命中率 ≥70%，需向量检索 + 知识库 | 纯关键词检索无法理解故障语义，命中率不足 |

---

## Phase 0: Outline & Research

详见 [research.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/research.md)

### 研究任务清单

1. **桌面客户端技术选型**：Electron vs Tauri vs CEF（跨平台/国产化/包体积/性能）
2. **本地存储与加密**：SQLite + SQLCipher vs IndexedDB + Web Crypto API vs LevelDB
3. **离线同步协议设计**：版本向量 vs 时间戳 vs CRDT；字段级 diff 算法；冲突检测与合并策略
4. **离线登录态校验**：JWT 离线令牌有效期与刷新机制；LDAP/AD 账户变更实时同步
5. **增量缓存刷新**：基于 updated_at 的增量拉取 vs 基于 Oplog 的变更流；缓存过期与强制刷新策略
6. **网络拓扑自动生成**：图布局算法（dagre/d3-force/cytoscape）；从接口对照表生成拓扑数据结构
7. **AI 排障 RAG 架构**：向量数据库选型（Milvus/PgVector/Elasticsearch kNN）；LLM 集成与提示模板
8. **多数据源动态路由**：dynamic-datasource-spring-boot-starter vs 自研 AbstractRoutingDataSource
9. **工作流迁移**：Activiti 5 → Flowable 7 迁移模式；BPMN 转换；流程定义重写
10. **数据迁移与灰度切换**：Python ETL 框架；Debezium CDC 增量同步；灰度切换与回滚策略
11. **安全架构**：LDAP/AD 绑定认证；RBAC + 数据权限拦截器；XSS/CSRF 防护；本地缓存加密
12. **可观测性**：SkyWalking 链路追踪；Prometheus 指标；ELK 日志；离线同步专项监控

## Phase 1: Design & Contracts

### 数据模型

详见 [data-model.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/data-model.md)

覆盖 38 个核心实体的字段定义、关系映射、状态机、校验规则，新增桌面客户端离线同步相关实体（LocalCacheMeta / SyncQueue / ConflictRecord）。

### 接口契约

详见 contracts/ 目录：
- [rest-api.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/contracts/rest-api.md)：REST API 契约（按业务域分组，含桌面同步端点）
- [external-integrations.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/contracts/external-integrations.md)：外部系统集成契约（18+ 系统）
- [desktop-sync.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/contracts/desktop-sync.md)：桌面客户端离线同步协议契约
- [events.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/contracts/events.md)：事件契约（异步消息主题与载荷）

### 端到端验证

详见 [quickstart.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/quickstart.md)

## Constitution Re-Check (Post-Design)

Constitution 为空模板，无 gate 约束。Phase 1 设计完成后确认无 violation：
- 双层并行状态机：FR-020 已实现
- 按业务域聚合模块：pms-modules 组织符合
- 99.9% SLA：技术栈支持（Docker + K8s + 监控）
- 灰度切换：FR-126 + pms-migration 模块
- 离线缓存范围限定：FR-119b 已明确强一致性操作禁用
- 本地缓存加密：FR-119c 已要求 SQLCipher/AES-256
- 字段级合并同步：FR-119a 已定义策略
