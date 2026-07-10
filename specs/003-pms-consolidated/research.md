# Research: PMS 项目管理系统（合并规格）

**Date**: 2026-07-10 | **Spec**: [spec.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/003-pms-consolidated/spec.md)

## 研究任务清单

1. 后端框架与持久层选型
2. 工作流引擎迁移方案
3. 前端架构与组件库选型
4. 多数据源与集成模式
5. 数据迁移与灰度切换
6. 安全架构与认证授权
7. 文件存储与分层归档
8. AI 排障架构（RAG）
9. 可观测性与监控
10. 部署架构（容器化）

---

## 1. 后端框架与持久层选型

**Decision**: Spring Boot 3.2.x + MyBatis-Plus 3.5.x + JDK 17

**Rationale**:
- Spring Boot 3.x 是 Java 企业级应用主流框架，JDK 17 LTS 提供长期支持
- 老系统使用 Struts2 2.5.30 + iBATIS 2 + MyBatis 双 ORM 共存（矛盾记录 #1），需统一
- MyBatis-Plus 在 MyBatis 基础上提供 CRUD 增强、分页、逻辑删除、乐观锁、多租户，减少样板代码
- 对动态 SQL 与复杂查询支持良好（覆盖老系统 iBATIS SQL Map 能力，FR-112）
- 团队学习曲线低（MyBatis 在国内普及度高）

**Alternatives**:
- Spring Boot + JPA/Hibernate：JPA 对动态 SQL 与复杂报表查询支持弱，老系统 286 表多表关联查询迁移成本高
- Quarkus/Micronaut：云原生性能优，但生态不如 Spring，团队熟悉度低
- 保持 iBATIS 2：已停止维护，与 JDK 17 不兼容

---

## 2. 工作流引擎迁移方案

**Decision**: Flowable 7.x，保留业务流程语义但重写流程定义，不复用 BPMN 文件

**Rationale**:
- 老系统使用 Activiti 5.23.0（已 EOL），Flowable 是 Activiti 的现代分支，API 兼容
- 老系统 BPMN 文件耦合了 iBATIS SQL 与老表结构，直接迁移不可行（FR-082）
- Flowable 7 支持 BPMN 2.0 + CMMN + DMN，可覆盖审批流、案例管理、决策表
- 支持云原生部署（Docker/K8s），与 Spring Boot 3 集成良好
- 内置任务监听器、超时升级、会签/或签/委派，满足转包多级审批（FR-041）

**迁移策略**:
- 重新设计流程定义（不迁移 BPMN 文件）
- 保留业务流程语义：售前（10→31→32→33→100）、转包（多级审批）、回访、闭环
- 状态机由业务层管理（双层并行模型 FR-025），Flowable 仅驱动审批流
- 历史任务数据迁移至新表

**Alternatives**:
- Camunda 8：功能强大但需 Zeebe 集群，运维复杂度高，一期过度设计
- 自研状态机：无法支持复杂审批（会签/或签/超时升级），且维护成本高
- 保持 Activiti 5：已 EOL，安全漏洞风险

---

## 3. 前端架构与组件库选型

**Decision**: Vue 3.4.x + Vite 5 + Pinia + Element Plus 2.x（PC）+ Vant 4（H5）

**Rationale**:
- Vue 3 Composition API + `<script setup>` 提供更好的类型推导与逻辑复用
- Vite 5 构建速度快（ESM 原生），HMR 即时
- Pinia 是 Vue 3 官方推荐状态管理，TypeScript 友好
- Element Plus 2.x 是国内企业级后台首选组件库，覆盖表单/表格/树/上传/图表等场景
- Vant 4 是移动端 H5 主流组件库，与 Vue 3 兼容
- 现代化交互界面：响应式布局 + 暗黑模式 + 国际化 + 骨架屏 + 虚拟滚动 + 拖拽表单设计器

**架构决策**:
- 单体前端应用（非微前端）：业务模块共享组件与状态，避免 qiankun 的复杂性
- 路由守卫 + 权限指令（v-permission）实现 RBAC 按钮级权限
- 动态表单设计器（基于 Element Plus 表单）支撑工勘/需求分析/问卷等可配置表单
- 网络拓扑可视化：使用 AntV G6 或 D3.js 实现自动生成拓扑（FR-153）
- 拖拽工作流预览：使用 bpmn-js 预览 Flowable 流程图

**Alternatives**:
- React + Ant Design：React 生态强大但国内企业级后台 Vue + Element 更主流
- Angular + NG-Zorro：学习曲线陡峭，团队熟悉度低
- 微前端 qiankun：一期模块耦合度不高，微前端增加路由与状态共享复杂度

---

## 4. 多数据源与集成模式

**Decision**: dynamic-datasource-spring-boot-starter + OpenFeign + Spring Integration

**Rationale**:
- 老系统配置 9 个数据源（MySQL + SQL Server 混合），新系统 MUST 保留多数据源（FR-010 假设）
- dynamic-datasource-spring-boot-starter 提供注解式数据源切换（`@DS("d365")`），对业务代码透明
- OpenFeign 用于 REST API 集成（D365 OAuth2、钉钉、ITR、RMA、服务平台等）
- Spring Integration 用于文件传输与 EDI 场景（如 D365 采购订单推送）
- 对外集成采用适配器模式，每个外部系统一个 Adapter，支持降级（FR-101 SPMS 不可用降级）

**数据源映射**:
| 数据源 | 类型 | 用途 | 集成方式 |
|--------|------|------|---------|
| local | MySQL 8.0 | PMS 主库 | 直连 |
| d365 | SQL Server | D365 采购/收货/合同 | 直连（只读）+ API（写） |
| crm | SQL Server | CRM 用户/客户 | 直连（只读）+ API（双向同步） |
| ehr | MySQL | EHR 组织/员工 | 直连（只读） |
| sms | MySQL | SMS 发货信息 | 直连（只读） |
| oa | MySQL | OA 系统 | 直连（只读） |
| sap | SQL Server | SAP 财务 | 直连（只读） |
| sse | MySQL | SSE 视图（转包付款） | 直连（只读） |
| itr | MySQL | ITR 工单 | 直连（只读）+ API（写） |

**Alternatives**:
- Debezium CDC：实时变更捕获，但运维复杂，一期可降级为定时增量同步
- 单库 + API 集成：外部系统数据所有权分散，合并需大量 ETL 且违反数据所有权边界
- Apache Camel：集成模式丰富但重量级，Spring Integration 足够

---

## 5. 数据迁移与灰度切换

**Decision**: Python ETL（petl + SQLAlchemy）+ 增量同步（定时任务）+ 灰度切换（按办事处）

**Rationale**:
- 老系统 286 表 + 43 视图，核心表迁移范围已明确（FR-095/FR-096）
- Python petl 轻量级 ETL 库，配合 SQLAlchemy 可直连多数据源
- 灰度切换按办事处（FR-098），先试点后推广，切换失败可回滚
- 并行运行期间增量同步采用定时任务（每 5 分钟），核心表双向同步
- 迁移完整性校验：记录数对比 + 关键字段抽样核对（FR-097）

**迁移步骤**:
1. 全量迁移历史数据（核心业务表 + 基础数据 + 用户/部门）
2. 新老系统并行运行，定时增量同步双向同步
3. 按办事处灰度切换（先 1 个试点，验证后推广）
4. 切换后老系统只读归档，保留 6 个月回滚窗口

**冲突处理**:
- 并行期间同一记录双端修改：以最后修改时间为准，冲突时提示人工裁定（Edge Case）
- 灰度切换回滚：已同步至新系统的增量数据保留，回滚后老系统继续运行

**Alternatives**:
- Debezium CDC 实时同步：运维复杂，且老系统 binlog 可能未开启
- 商业 ETL 工具（Informatica/Kettle）：成本高，团队熟悉度低
- 直接切换（冷切换）：业务连续性风险高，不符合 SC-013

---

## 6. 安全架构与认证授权

**Decision**: Spring Security 6 + LDAP/AD 绑定认证 + RBAC + 数据权限拦截器

**Rationale**:
- 003 澄清明确采用 LDAP/AD 统一认证（非 CAS），钉钉仅用于审批与通知推送
- Spring Security 6 是 Spring Boot 3 标配，与 LDAP/AD 集成成熟（LdapAuthenticationProvider）
- RBAC 模型：用户→角色→权限（菜单/按钮/数据），权限通过注解 `@PreAuthorize` 控制
- 数据权限按"办事处/项目归属"过滤（FR-079），通过 MyBatis-Plus 拦截器自动注入 WHERE 条件
- 老系统的 XSS/CSRF/SQL 注入防护（FR-102/103/104）在新框架内置

**安全措施**:
- 认证：LDAP/AD 绑定认证（bind authentication），不存储密码
- 授权：RBAC + 数据权限（按办事处/项目归属过滤）
- 传输：HTTPS 全站，HSTS
- 输入验证：Bean Validation + 前端校验
- XSS：Spring Security 默认 HTML 转义
- CSRF：SameSite Cookie + Token
- SQL 注入：MyBatis-Plus 参数预编译
- 安全日志：可疑请求与拦截事件记录（FR-105）
- 移动端：客户 H5 使用短信验证码登录，不暴露敏感字段（FR-092）

**Alternatives**:
- OAuth2/OIDC：钉钉/企业微信 OAuth2 可作为未来扩展，一期 LDAP/AD 足够
- Shiro：老系统使用 Shiro，但 Spring Security 6 与 Spring Boot 3 集成更紧密
- 自研认证：安全风险高，不推荐

---

## 7. 文件存储与分层归档

**Decision**: MinIO（私有部署）或阿里云 OSS（云部署）+ 分层存储（热+冷）+ tus 协议断点续传

**Rationale**:
- 交付件/配置 Log/巡检报告/施工照片需对象存储，文件系统不适合分布式部署
- MinIO 与 S3 API 兼容，可私有部署，适合内网环境；OSS 适合云部署
- 分层存储（FR-168）：交付件 ≥5 年、巡检/割接 ≥3 年、AI 训练数据脱敏长期
- 超期数据自动归档至冷存储（低频访问层），按需取回
- tus 协议实现断点续传（FR-009），支持大文件上传中断恢复
- 施工照片自动添加水印（时间+GPS+上传人，FR-094）

**存储分层**:
| 层级 | 访问频率 | 保留期限 | 存储 |
|------|---------|---------|------|
| 热存储 | 频繁 | 0-1 年 | 标准存储 |
| 温存储 | 偶尔 | 1-3 年 | 低频访问 |
| 冷存储 | 罕见 | 3-5+ 年 | 归档存储（取回需分钟级） |

**Alternatives**:
- 文件系统 + NFS：不适合分布式，无分层
- 数据库 BLOB：性能差，不适合大文件
- 商业 NAS：成本高，扩展性差

---

## 8. AI 排障架构（RAG）

**Decision**: RAG（检索增强生成）+ 向量数据库（PgVector）+ LLM 集成

**Rationale**:
- AI 排障（FR-145~FR-149）需要基于知识库回答，RAG 是主流模式
- 知识库含手册/技术公告/FAQ/经典案例/排障经验（FR-147），需向量检索
- PgVector 是 PostgreSQL 的向量扩展，可与现有数据库集成，无需额外服务
- LLM 集成：支持 OpenAI/通义千问/文心一言等，通过提示模板训练 Skill
- 排障经验转换模板（FR-148）沉淀为训练数据，持续优化

**架构**:
1. 知识库构建：手册/公告/案例 → 文档切片 → 向量化 → PgVector 索引
2. 在线排障：用户输入故障描述 → 向量检索相关知识 → LLM 生成诊断与方案
3. 经验沉淀：排障过程记录 → 转换模板填写 → 沉淀至知识库
4. 训练优化：提示模板训练 Skill + 大模型提问重写

**脱敏**:
- AI 训练数据含客户敏感信息时 MUST 脱敏（FR-168）
- 脱敏规则：客户名称/IP/序列号/合同号等替换为占位符
- 脱敏后数据长期保留

**Alternatives**:
- Milvus：专业向量数据库，但运维复杂，PgVector 足够
- 微调 LLM：成本高，且知识更新频繁，RAG 更灵活
- 自建知识图谱：复杂度高，一期 RAG 足够

---

## 9. 可观测性与监控

**Decision**: Spring Boot Actuator + Prometheus + Grafana + SkyWalking + ELK

**Rationale**:
- 18+ 外部系统集成需链路追踪，SkyWalking 支持 Java/HTTP/RPC 调用链
- Prometheus + Grafana 是监控主流组合，指标采集与告警成熟
- ELK 集中日志管理，支持项目/设备/工单全文检索（Elasticsearch）
- Spring Boot Actuator 提供健康检查、指标、配置查看
- 99.9% SLA（SC-029）需实时监控与告警

**监控指标**:
- 应用：QPS/响应时间/错误率/JVM/线程池
- 数据库：连接池/慢查询/锁等待
- 集成：各外部系统接口成功率/延迟/重试
- 业务：项目状态分布/超期数/审批时效/割接闭环率
- 基础设施：CPU/内存/磁盘/网络

**告警规则**:
- 接口成功率 < 99%
- 响应时间 P95 > 2 秒
- 外部系统集成失败
- 数据库连接池耗尽
- 磁盘使用率 > 80%

**Alternatives**:
- Zipkin：功能不如 SkyWalking 全面
- Datadog：商业产品，成本高
- 自建监控：开发成本高

---

## 10. 部署架构（容器化）

**Decision**: Docker 容器化 + Docker Compose（单机）或 K8s（集群）

**Rationale**:
- 容器化部署是现代标准，环境一致性与水平扩展能力强
- 一期可采用 Docker Compose 单机部署（简化运维）
- 二期可平滑迁移至 K8s 集群（支持水平扩展与自愈）
- Nginx 作为反向代理与静态资源服务
- 数据库（MySQL/Redis/ES）独立部署或容器化

**部署拓扑**:
```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (反代+静态)  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
    │  Backend    │ │  Frontend   │ │  Mobile  │
    │ (Spring Boot)│ │ (Vue3+Vite) │ │  (H5)    │
    └──────┬──────┘ └─────────────┘ └──────────┘
           │
    ┌──────┼──────┬──────┬──────┬──────┐
    │      │      │      │      │      │
┌───▼─┐┌───▼─┐┌───▼─┐┌───▼─┐┌───▼─┐┌───▼─┐
│MySQL││Redis││ ES  ││MinIO││Flow.││RMQ  │
└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘
```

**CI/CD**:
- GitLab CI 或 Jenkins
- 构建 → 单元测试 → 集成测试 → 构建 Docker 镜像 → 部署
- 蓝绿部署或滚动更新（K8s）

**Alternatives**:
- 传统 WAR 部署：扩展性差，环境不一致
- 裸机部署：运维成本高
- Serverless：不适合长时间运行的企业级应用
