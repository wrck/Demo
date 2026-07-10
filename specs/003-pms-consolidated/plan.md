# Implementation Plan: PMS 项目管理系统（合并规格）

**Branch**: `003-pms-consolidated` | **Date**: 2026-07-10 | **Spec**: [spec.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/spec.md)

**Input**: Feature specification from `/specs/003-pms-consolidated/spec.md`

## Summary

基于合并 spec（22 User Stories、169 FR、40 Key Entities、29 SC），构建新一代 PMS 项目管理系统。系统作为原厂交付体系中枢，覆盖项目全生命周期（立项→指派→实施→闭环）与 8 个交付子阶段（工前→计划→方案→部署→验收→割接→归档），整合售前/转包/回访/维保/技术公告等历史能力与割接平台/服务平台/AI 排障/CRM 同步/ITR-RMA 等新业务增强，对接 18+ 外部系统。技术架构采用主流企业级栈：Spring Boot 3 + Vue 3 + MySQL + Redis + Flowable，前后端分离，多端覆盖（PC Web + 移动端 H5），模块化按业务域聚合组织。

## Technical Context

**Language/Version**:
- 后端：Java 17 LTS（Spring Boot 3.2.x）
- 前端：TypeScript 5.x + Vue 3.4.x
- 移动端：Vue 3 + Vant 4（H5）
- 脚本/工具：Python 3.11+（数据迁移/ETL）

**Primary Dependencies**:
- 后端框架：Spring Boot 3.2.x + Spring Security 6 + Spring Cloud 2023.x（可选微服务）
- 持久层：MyBatis-Plus 3.5.x（替代老系统 iBATIS 2 + MyBatis 双 ORM）
- 工作流：Flowable 7.x（替代 Activiti 5.23.0，保留 BPMN 语义但重写流程定义）
- 认证授权：Spring Security + LDAP/AD 绑定认证 + RBAC
- 前端框架：Vue 3.4.x + Vite 5 + Pinia + Vue Router 4 + Element Plus 2.x（PC）+ Vant 4（H5）
- 数据库：MySQL 8.0 主从 + Redis 7.x（缓存/分布式锁）+ Elasticsearch 8.x（全文检索/日志）
- 消息队列：RocketMQ 5.x 或 RabbitMQ（异步事件：审批推送/数据同步/归档）
- 对象存储：MinIO 或阿里云 OSS（交付件/配置 Log/巡检报告存储 + 冷存储分层）
- 文件解析：Apache POI（Excel 导入导出）+ Apache Tika（文件类型识别）
- OCR：百度 OCR 或阿里云 OCR（发票识别）
- 集成：OpenFeign（HTTP 客户端）+ Spring Integration（EDI/文件传输）
- 监控：Spring Boot Actuator + Prometheus + Grafana + SkyWalking（APM 链路追踪）
- 日志：Logback + ELK（Elasticsearch + Logstash + Kibana）

**Storage**:
- 主库：MySQL 8.0（业务数据，多数据源动态路由保留 9 个数据源）
- 缓存：Redis 7.x（会话/字典/配置/分布式锁/限流）
- 搜索：Elasticsearch 8.x（项目/设备/工单全文检索 + 日志分析）
- 文件：对象存储（交付件/Log/照片，分层：热存储 + 冷存储低频访问层）
- 配置：Nacos 2.x（配置中心 + 服务注册发现，如采用微服务）

**Testing**:
- 后端：JUnit 5 + Mockito + Spring Boot Test + Testcontainers（集成测试）
- 前端：Vitest + Vue Test Utils + Playwright（E2E）
- 契约：Pact 或 Spring Cloud Contract（外部集成契约测试）
- 性能：JMeter（1000 并发压测）
- 覆盖率：JaCoCo（后端 ≥80%）+ Istanbul/c8（前端 ≥70%）

**Target Platform**:
- 服务端：Linux（CentOS 7+ / Ubuntu 22.04+），Docker 容器化部署
- PC Web：Chrome/Edge/Firefox 最新版 + Safari 15+（现代浏览器）
- 移动端 H5：iOS 14+ / Android 10+（微信内置浏览器兼容）
- 可用性：7×24，SLA 99.9%（年停机 ≤8.76 小时）

**Project Type**: Web 应用（前后端分离）+ 移动端 H5 + 多外部系统集成

**Performance Goals**:
- 1000 并发用户，报表 P95 ≤2 秒（SC-007/SC-013）
- 接口 P95 ≤500ms（非报表）
- 文件上传支持 100MB+，断点续传
- 7×24 可用性 ≥99.9%（SC-029）
- 跨系统集成点同步成功率 ≥99%（SC-025）

**Constraints**:
- 1000 并发用户无 degradation
- 数据权限按"办事处/项目归属"过滤
- 多数据源动态路由（保留 9 个数据源）
- 离线缓存限定只读+现场采集
- 老系统业务流程语义保留（状态机/审批节点/角色指派）
- 新老系统并行运行+增量同步+灰度切换+可回滚
- 数据分级保留：交付件 ≥5 年、巡检/割接 ≥3 年、AI 训练数据脱敏长期

**Scale/Scope**:
- 286 老表 + 43 视图迁移至新系统
- 169 FR、22 User Stories、40 Key Entities
- 18+ 外部系统集成（D365/SMS/OA/EHR/CRM/SAP/MES/钉钉/LDAP-AD/迪普服务平台/ITR/RMA/客户资产库/供应链/割接管理平台/冷存储/SPMS/CAS）
- 4 类终端（PC Web/工程师 H5/代理商 H5/客户 H5）
- 预估代码量：后端 15 万行 + 前端 10 万行

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 为空模板（`.specify/memory/constitution.md` 未实例化），无原则约束。视为 gate 全部通过，无 violations。

## Project Structure

### Documentation (this feature)

```text
specs/003-pms-consolidated/
├── plan.md              # 本文件（/speckit-plan 输出）
├── research.md          # Phase 0 输出（技术选型研究）
├── data-model.md        # Phase 1 输出（实体数据模型）
├── quickstart.md        # Phase 1 输出（端到端验证指南）
├── contracts/           # Phase 1 输出（接口契约）
│   ├── rest-api.md          # REST API 契约
│   ├── external-integrations.md  # 外部系统集成契约
│   └── events.md            # 事件契约（异步消息）
├── spec.md              # 特性规格（/speckit-specify 输出）
├── checklists/
│   └── requirements.md  # 质量检查清单
└── tasks.md             # Phase 2 输出（/speckit-tasks，非本命令创建）
```

### Source Code (repository root)

采用 Web Application 结构（前后端分离 + 移动端 H5）。模块按业务域聚合组织（003 澄清：项目交付生命周期为主线 + 横切模块独立）。

```text
pms/
├── backend/                          # 后端 Spring Boot 应用
│   ├── pom.xml                        # Maven 父 POM
│   ├── pms-common/                    # 通用模块（工具类/常量/枚举/异常）
│   ├── pms-domain/                    # 领域模型（Entity/VO/DTO/枚举）
│   ├── pms-infra/                     # 基础设施层
│   │   ├── persistence/               # 持久化（MyBatis-Plus Mapper/多数据源配置）
│   │   ├── security/                  # 安全（LDAP/AD 认证/RBAC/数据权限）
│   │   ├── storage/                   # 对象存储（MinIO/OSS 分层）
│   │   ├── messaging/                 # 消息队列（RocketMQ 生产者/消费者）
│   │   ├── search/                    # 搜索（Elasticsearch 索引/查询）
│   │   └── integration/               # 外部集成客户端（D365/CRM/钉钉/ITR/RMA 等）
│   ├── pms-workflow/                  # 工作流引擎（Flowable 流程定义/监听器/任务管理）
│   ├── pms-modules/                  # 业务模块（按业务域聚合）
│   │   ├── pms-project/               # 项目生命周期（立项/指派/状态机/主子项目）
│   │   ├── pms-delivery/              # 交付生命周期（工前/计划/方案/部署/验收/归档）
│   │   │   ├── prework/               # 工前准备（客户联系人/工勘/需求分析）
│   │   │   ├── plan/                  # 施工计划
│   │   │   ├── scheme/                # 实施方案
│   │   │   ├── deploy/                # 实施部署（到货/硬件/配置/联调/割接发起）
│   │   │   └── acceptance/            # 验收交维（培训/满意度/初终验/交付件）
│   │   ├── pms-cutover/               # 割接管理（割接平台集成/操作单/checklist/归档）
│   │   ├── pms-presales/              # 售前测试（申请/审批/跟踪/临时授权）
│   │   ├── pms-subcontract/           # 转包管理（审批/合同/付款/回访/验收）
│   │   ├── pms-maintenance/           # 维保管理（维护记录/问卷/交付件）
│   │   ├── pms-techbulletin/          # 技术公告（发布/影响范围/修复任务）
│   │   ├── pms-device/                # 设备信息增强（配置历史/部署风险/接口对照/拓扑/版本）
│   │   ├── pms-service-platform/      # 服务平台集成（巡检/CRT log/解析回传）
│   │   ├── pms-ai-troubleshoot/       # AI 排障（AGENT/知识库/工具集/Skill 训练）
│   │   ├── pms-user/                  # 用户管理（CRM 同步/最终用户/客户档案）
│   │   ├── pms-itr/                   # ITR 故障处理（工单/解决方案/RMA 调用）
│   │   ├── pms-weekly/                # 周报与文件管理
│   │   └── pms-report/               # 报表分析
│   ├── pms-api/                      # API 层（REST Controller/OpenAPI 文档）
│   ├── pms-migration/                # 数据迁移（ETL 脚本/校验/灰度切换）
│   └── pms-app/                      # 启动应用（Spring Boot 主类/配置）
│
├── frontend/                         # 前端 Vue 3 应用
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/                    # Vue Router（路由守卫/权限过滤）
│   │   ├── stores/                    # Pinia 状态管理
│   │   ├── api/                       # API 客户端（Axios 封装/请求拦截）
│   │   ├── components/                # 通用组件
│   │   │   ├── layout/                # 布局（Header/Sidebar/Breadcrumb/TagsView）
│   │   │   ├── form/                  # 表单组件（动态表单/表单设计器）
│   │   │   ├── table/                 # 表格组件（可编辑表格/列配置/导出）
│   │   │   ├── upload/                # 上传组件（断点续传/水印/预览）
│   │   │   ├── workflow/              # 工作流组件（审批流转/流程图预览）
│   │   │   ├── chart/                 # 图表组件（ECharts 封装）
│   │   │   └── topolog/               # 拓扑可视化（网络拓扑自动生成）
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
│   │   │   ├── system/                # 系统管理
│   │   │   └── ai-troubleshoot/       # AI 排障
│   │   ├── composables/               # 组合式函数（权限/字典/上传/水印）
│   │   ├── directives/                # 自定义指令（权限按钮 v-permission）
│   │   ├── locales/                   # 国际化
│   │   └── assets/                    # 静态资源
│   └── tests/                        # 前端测试
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
│   ├── architecture/                  # 架构文档（C4 模型/部署图）
│   ├── api/                           # API 文档（OpenAPI 生成）
│   └── runbook/                       # 运维手册
│
└── scripts/                         # 工具脚本
    ├── migration/                     # 数据迁移脚本（Python）
    ├── seed/                          # 种子数据
    └── ci/                            # CI/CD 脚本
```

**Structure Decision**:
采用 Web Application 结构（前后端分离 + 移动端 H5）。后端按分层架构 + 业务域模块化组织：
- **分层**：common/domain/infra/workflow/api/app 横切分层
- **业务域**：pms-modules 下按"项目交付生命周期"主线聚合（project/delivery/cutover/presales/subcontract/maintenance/techbulletin/device/service-platform/ai-troubleshoot/user/itr/weekly/report），符合 003 澄清的"按业务域聚合"决策
- **前端**：PC Web（Element Plus）+ 移动端 H5（Vant 4）独立应用，共享 API 客户端与类型定义

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 9 个数据源（保留多数据源） | 老系统依赖 9 个外部库（D365/CRM/SAP/MES 等直连查询），合并为单库需大量 ETL 且数据所有权分散 | 单库方案需迁移所有外部数据，违反数据所有权边界且实时性损失 |
| 微服务可选（Spring Cloud） | 18+ 外部系统集成需独立扩展与故障隔离 | 单体应用在集成点故障时全局受影响，但一期可采用模块化单体（Modulith）后续拆分 |
| Flowable 工作流引擎 | 老系统 Activiti 5.23 已 EOL，业务流程复杂（售前/转包/回访/闭环多级审批） | 自研状态机无法支持复杂审批流（会签/或签/委派/超时升级） |
| Elasticsearch 全文检索 | 286 表百万级数据的项目/设备/工单检索，MySQL LIKE 性能不足 | MySQL 全文索引对中文支持差且无分词，无法满足 P95 ≤2 秒 |
| 对象存储分层（热+冷） | 交付件保留 ≥5 年，全热存储成本高 | 全热存储成本 5 倍以上，冷存储取回虽慢但符合归档场景 |
| 离线缓存（IndexedDB） | 移动端弱网环境下现场作业需持续可用 | 纯在线方案在弱网时无法施工记录，影响交付效率 |

---

## Phase 0: Outline & Research

详见 [research.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/research.md)

### 研究任务清单

1. **技术栈选型研究**：Spring Boot 3 vs Spring Cloud Gateway、MyBatis-Plus vs JPA、Flowable 7 vs Camunda 8
2. **架构模式研究**：模块化单体（Modulith）vs 微服务、CQRS 适用性、事件驱动架构
3. **前端架构研究**：Vue 3 + Element Plus vs Ant Design Vue、微前端（qiankun）适用性、表单设计器
4. **多数据源与集成研究**：动态数据源路由（dynamic-datasource）、Spring Integration vs Camel、OAuth2 客户端
5. **工作流迁移研究**：Activiti 5 → Flowable 7 迁移模式、BPMN 转换、流程定义重写
6. **数据迁移研究**：Python ETL 框架（Bonobo/Petl）、增量同步（Debezium CDC）、灰度切换策略
7. **安全架构研究**：LDAP/AD 绑定认证、RBAC + 数据权限拦截器、XSS/CSRF 防护
8. **文件存储研究**：MinIO vs 阿里云 OSS、分层存储、断点续传（tus 协议）
9. **AI 排障研究**：RAG 架构、向量数据库（Milvus/PgVector）、LLM 集成（提示模板/Skill 训练）
10. **可观测性研究**：SkyWalking 链路追踪、Prometheus 指标、ELK 日志、告警规则

## Phase 1: Design & Contracts

### 数据模型

详见 [data-model.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/data-model.md)

覆盖 40 个核心实体的字段定义、关系映射、状态机、校验规则。

### 接口契约

详见 contracts/ 目录：
- [rest-api.md](file:///d:/开发资料/PMS资料/优化/2026\阶段性汇报文件/specs/003-pms-consolidated/contracts/rest-api.md)：REST API 契约（按业务域分组）
- [external-integrations.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/contracts/external-integrations.md)：外部系统集成契约（18+ 系统）
- [events.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/contracts/events.md)：事件契约（异步消息主题与载荷）

### 端到端验证

详见 [quickstart.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/quickstart.md)

## Constitution Re-Check (Post-Design)

Constitution 为空模板，无 gate 约束。Phase 1 设计完成后再确认无 violation。当前设计符合 spec 所有澄清：双层并行状态机、按业务域聚合模块、99.9% SLA、灰度切换、离线缓存范围限定。
