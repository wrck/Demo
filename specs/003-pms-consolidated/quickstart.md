# 端到端验证指南：PMS 项目管理系统（合并规格）

> **来源**: `spec.md`（22 个 User Stories / 169 FR / 29 SC）、`plan.md`（Technical Context / Project Structure）、`data-model.md`（40 实体 + 状态机）、`contracts/`（REST API + 外部集成 + 事件契约）
> **目标**: 提供可运行的验证场景，证明 PMS 核心功能端到端可用
> **状态**: Draft | **最后更新**: 2026-07-10 | **适用分支**: `003-pms-consolidated`

本指南仅包含验证步骤、命令与预期结果，**不包含完整实现代码**。校验点引用 [data-model.md](./data-model.md)、[contracts/rest-api.md](./contracts/rest-api.md)、[contracts/external-integrations.md](./contracts/external-integrations.md)、[contracts/events.md](./contracts/events.md) 的具体定义，不重复内容。

---

## 1. 前置条件

### 1.1 环境与依赖

| 类别 | 组件 | 版本要求 | 用途 |
|------|------|---------|------|
| 运行时 | JDK | 17 LTS | 后端运行 |
| 运行时 | Node.js | 20.x LTS | 前端构建 |
| 运行时 | Python | 3.11+ | 数据迁移/ETL 脚本 |
| 中间件 | MySQL | 8.0 主从 | PMS 主库 + 9 数据源（见 [external-integrations.md §3](./contracts/external-integrations.md#3-多数据源架构集成来源-002)） |
| 中间件 | Redis | 7.x | 会话/字典/分布式锁/限流 |
| 中间件 | Elasticsearch | 8.x | 全文检索/日志分析 |
| 中间件 | RocketMQ 或 RabbitMQ | 5.x / 3.x | 异步事件（[events.md](./contracts/events.md)） |
| 中间件 | MinIO 或阿里云 OSS | - | 交付件/Log/照片（热存储 + 冷存储分层） |
| 容器 | Docker | 24+ | 容器化部署 |
| 构建 | Maven | 3.9+ | 后端构建 |
| 构建 | pnpm | 8+ | 前端/移动端依赖管理 |

### 1.2 外部系统 Mock 准备

PMS 与 20 个外部系统集成（见 [external-integrations.md §1.1](./contracts/external-integrations.md#11-集成系统总览)）。验证环境必须 mock 的关键外部系统：

| Mock 目标 | Mock 端点/能力 | 关联验证场景 |
|----------|---------------|------------|
| LDAP/AD | `ldap://mock-ad:389`，预置测试用户 `user-pm-001`/`user-sm-001`/`user-em-001`/`user-admin`/`user-director` | 登录认证、RBAC、组织同步 |
| 钉钉开放平台 | `POST /dingtalk/approvals/push`、`POST /dingtalk/tasks/push`（捕获推送内容） | 施工计划/实施方案/割接审批推送（场景 4/5/8） |
| D365 | `POST /d365/purchase-orders`、`POST /d365/purchase-receipts`、`POST /api/v1/integrations/d365/po-callback` | 转包合同执行（场景 10） |
| CRM | 双向同步 API：`POST /api/v1/users/sync-from-crm`、回写 CRM 接口 | 用户信息同步（场景 13） |
| ITR | `POST /itr/tickets/sync`、工单查询 | ITR 工单同步、割接失败提交（场景 8/14） |
| RMA | `POST /rma/orders`、`GET /rma/orders/{rmaId}` | 硬件故障 RMA 调用（场景 14） |
| 服务平台（迪普） | `POST /api/v1/device-serials/{id}/enhancement/sync-from-platform` 回调、UMC 环境上传 | 巡检与设备信息解析（场景 12/17） |
| 客户资产库 | `GET /customer-asset/by-serial/{serialNo}` | 割接建单携带资产（场景 8） |
| 供应链系统 | `POST /api/v1/device-serials/supply-chain/import` 回调 | 出厂信息导入与官网版本匹配（场景 12/19） |
| 割接管理平台 | 等级评定规则、模板库、7 类工具集、操作单/checklist 生成 | 割接全流程（场景 8） |
| SPMS 备件系统 | `POST /spms/spare-parts/*`（领用/归还/返修/替换） | 割接备件关联（场景 8） |
| 邮件服务（SMTP） | `smtp://mock-smtp:25`，捕获邮件内容 | 回退/审批/技术公告通知（场景 1/6/11） |
| 冷存储 | 对象存储低频访问层 API | 数据归档（场景 7/24） |
| 一码通定位 | `GET /one-code/location?code=...` | 设备地址定位（场景 12/19） |
| 临时授权下发通道 | `POST /license/issue` | 售前测试临时授权（场景 9） |

### 1.3 数据库与种子数据

1. 执行 `deploy/sql/schema.sql` 初始化 9 个数据源 schema（按 [external-integrations.md §3](./contracts/external-integrations.md#3-多数据源架构集成来源-002) 列表）。
2. 执行 `scripts/seed/seed-basic-data.sql` 初始化基础数据：
   - 4 种业务场景模板（标准实施/售前测试/转包代施/维保，[FR-027](./spec.md)）。
   - 数据字典：项目类型、产品线、区域、设备类别、任务类型（[FR-074](./spec.md)）。
   - 角色与权限：管理员/服务经理/项目经理/工程管理部/主任/实施人员/交付人员（[rest-api.md 附录 B](./contracts/rest-api.md#附录-b权限码清单rbac)）。
3. 执行 `scripts/seed/seed-demo-projects.sql` 初始化跨阶段分布的演示项目（≥ 30 个，覆盖 8 个交付子阶段 + 超期项目），用于场景 2 的统计卡片校验。

### 1.4 测试用户清单

| 登录名 | 角色 | 数据范围 | 关联场景 |
|--------|------|---------|---------|
| `user-admin` | 管理员 | 全部 | 系统管理、技术公告 |
| `user-sm-001` | 服务经理 | 办事处 12 | 项目指派、施工/实施方案审批 |
| `user-pm-001` | 项目经理 | 项目归属（P20260701001 等） | 项目执行全流程 |
| `user-em-001` | 工程管理部 | 全部 | 回访、闭环审批 |
| `user-director` | 主任 | 全部 | 转包主任审批 |
| `user-2nd-001` | 二线 | 全部 | 割接二线审批 |
| `user-rd-001` | 研发 | 全部 | 割接研发审批、ITR 升单 |
| `user-impl-001` | 实施人员 | 项目归属 | 实施部署、割接执行 |
| `user-acceptance-001` | 交付人员 | 项目归属 | 验收交维 |
| `agent-user-001` | 代理商工程师 | 本公司数据 | 代理商 H5 |
| `customer-phone-001` | 客户（手机号） | 关联项目 | 客户 H5 |

---

## 2. 启动命令

### 2.1 后端（Spring Boot）

```bash
# 在 pms/backend 目录下
mvn clean install -DskipTests
java -jar pms-app/target/pms-app.jar \
  --spring.profiles.active=dev \
  --spring.datasource.dynamic.primary=dataSourceLocal \
  --spring.ldap.url=ldap://mock-ad:389 \
  --spring.mail.host=mock-smtp \
  --integration.dingtalk.mock=true \
  --integration.d365.base-url=http://mock-d365:8080 \
  --integration.crm.base-url=http://mock-crm:8080 \
  --integration.itr.base-url=http://mock-itr:8080 \
  --integration.rma.base-url=http://mock-rma:8080 \
  --integration.service-platform.base-url=http://mock-dptech:8080 \
  --integration.cutover-platform.base-url=http://mock-cutover:8080 \
  --integration.spms.base-url=http://mock-spms:8080 \
  --integration.supply-chain.base-url=http://mock-supply:8080
```

预期：应用监听 `8080` 端口，启动日志输出 `Started PmsApplication in X seconds`，9 个数据源初始化成功，Flowable 工作流引擎初始化完成。

### 2.2 前端（PC Web）

```bash
# 在 pms/frontend 目录下
pnpm install
pnpm dev
```

预期：Vite 启动，访问 `http://localhost:5173`，跳转至 LDAP/AD 登录页。

### 2.3 移动端 H5

```bash
# 工程师/代理商 H5
cd pms/mobile
pnpm install
pnpm dev --mode engineer   # 工程师 H5，默认端口 5174
pnpm dev --mode agent      # 代理商 H5，默认端口 5175
pnpm dev --mode customer   # 客户 H5，默认端口 5176
```

### 2.4 基础设施（Docker Compose 一键拉起）

```bash
cd deploy/docker
docker compose -f docker-compose-dev.yml up -d
# 包含：mysql、redis、elasticsearch、rocketmq、minio、mock-ad、mock-smtp
```

### 2.5 健康检查

```bash
curl -s http://localhost:8080/actuator/health | jq .
# 预期：{"status":"UP","components":{"db":{"status":"UP"},"redis":{"status":"UP"},...}}
```

---

## 3. 验证场景（按 User Story 分组）

> 通用约定：
> - 所有 HTTP 请求基路径 `/api/v1`，认证头 `Authorization: Bearer <JWT>`（[rest-api.md §1.1](./contracts/rest-api.md#11-认证与权限头)）。
> - 写操作须带 `If-Match: <version>` 乐观锁头（[FR-026](./spec.md)）。
> - 通用响应格式与状态码见 [rest-api.md §1.3 / §1.4](./contracts/rest-api.md#13-通用响应格式)。

---

### 场景 1 — 项目全生命周期管理（US-1）

**覆盖**: 30→31→32→40→100 状态流转、回退 36/38/42、终态 20、主子项目拆分。状态机定义见 [data-model.md §2.1](./data-model.md#21-project-双层并行状态机)。

#### 步骤 1.1 创建项目（30）

1. 以 `user-admin` 登录：`POST /api/v1/auth/login`，body `{"username":"user-admin","password":"..."}`，预期 `200`，返回 JWT。
2. 创建项目：`POST /api/v1/projects`，body 含 `contract_no=HT20260701001`、`project_type=DIRECT_SIGN`、`scenario_template_id=1`、`office_id=12`、`execution_mode=SELF`（完整字段见 [rest-api.md §3.1.1](./contracts/rest-api.md#311-创建项目)）。

**预期结果**：HTTP `201`，响应含 `project_no`（系统生成）、`status_code=30`、`project_level`（自动判断）、`service_manager_id`（自动指派）。

**校验点**：① `SC-001` 创建耗时 ≤ 3 分钟；② 数据库 `pm_project` 表新增 1 行，`status_code=30`，`delivery_phase` 为 NULL（仅 status=40 时有效，[data-model.md §3.1.1](./data-model.md#311-project项目)）；③ `IntegrationPoint` 表无新增（创建为内部操作）。

#### 步骤 1.2 指派 SM（30→31）

`POST /api/v1/projects/{projectId}/transitions`，body `{"target_status":"31","service_manager_id":200}`。

**预期**：`200`，`status_code=31`。

**校验点**：① 事件 `pms.project.status.changed` 发布（[events.md §3.1](./contracts/events.md#31-事件清单)），payload `previousStatus=30`、`currentStatus=31`；② 邮件服务收到通知；③ 消息中心向 SM 推送待办。

#### 步骤 1.3 SM 指派 PM（31→32）

以 `user-sm-001` 调用 `POST /api/v1/projects/{projectId}/transitions`，body `{"target_status":"32","project_manager_id":100}`。

**校验点**：① 仅 `service_manager` 角色可执行（其他角色返回 `403`）；② `Member` 表新增 PM 记录；③ PM 收到钉钉任务待办（mock 钉钉捕获到 `POST /dingtalk/tasks/push`）。

#### 步骤 1.4 PM 启动实施（32→40）

以 `user-pm-001` 调用 `POST /api/v1/projects/{projectId}/transitions`，body `{"target_status":"40"}`。

**预期**：`status_code=40`，`delivery_phase=NOT_STARTED`（自动进入"未开始"子阶段，[FR-025](./spec.md)）。

**校验点**：① 事件 `pms.project.phase.changed` 发布；② 单项目跟踪页（`GET /api/v1/projects/{projectId}/tracking`）返回 6 项二级导航（[rest-api.md §2.2.1](./contracts/rest-api.md#221-获取单项目跟踪视图)）。

#### 步骤 1.5 闭环审批（40→100）

1. 以 `user-pm-001` 调用 `POST /api/v1/projects/{projectId}/closure/apply`（[rest-api.md §11.4.1](./contracts/rest-api.md#1141-发起项目闭环申请)），预期启动多角色工作流。
2. 以 `user-em-001` 审批：`POST /api/v1/projects/{projectId}/closure/approve`，body `{"approved":true}`。

**预期**：`status_code=100`，`closed_at` 写入。

**校验点**：① `SC-002` 状态流转 100% 遵循状态机；② 非法流转（如 100→40）返回 `412 Precondition Failed`（[rest-api.md §1.4](./contracts/rest-api.md#14-通用状态码)）。

#### 步骤 1.6 回退分支（36/38/42）

在 31 状态调用 `POST /transitions` `{"target_status":"36"}`，预期 `200`，并发送邮件（[VAL-003](./contracts/rest-api.md#15-通用错误体)）。校验：`OperateLog` 表记录回退日志 + 邮件服务捕获到通知。

#### 步骤 1.7 终态 20

在 30/31 状态调用 `POST /api/v1/projects/{projectId}/terminate`（[rest-api.md §3.1.6](./contracts/rest-api.md#316-标记不予跟踪)），预期 `status_code=20`。校验：在 32 状态调用返回 `412`（仅 30/31 可流转至 20，[VAL-002](./contracts/rest-api.md#311-创建项目)）。

#### 步骤 1.8 主子项目拆分（[FR-029 / FR-032](./spec.md)）

1. 以 `user-pm-001` 调用 `POST /api/v1/projects/{parentId}/sub-projects` 拆分 3 个子项目。
2. 闭合 2 个子项目后尝试闭环主项目：`POST /api/v1/projects/{parentId}/closure/apply`。

**预期**：第 3 个子项目未闭环时，主项目闭环返回 `422`，提示未闭环子项目清单（[VAL-005](./contracts/rest-api.md#311-创建项目)）。

---

### 场景 2 — 项目总体跟踪与进度监控（US-10）

**覆盖**: 8 阶段统计卡片、超期标红、单项目跳转。FR-016~FR-018。

#### 步骤 2.1 加载统计卡片

以交付管理人员登录，调用 `GET /api/v1/projects/tracking/phase-stats`（[rest-api.md §2.1.1](./contracts/rest-api.md#2111-获取项目阶段统计卡片)）。

**预期**：`200`，返回 8 个 phase 计数（ALL/NOT_STARTED/PRE_CONSTRUCTION/WRITING_IMPL_PLAN/MAKING_CONSTRUCTION_PLAN/IMPLEMENTATION_DEPLOYMENT/ACCEPTANCE_HANDOVER/OVERDUE）。

**校验点**：① 与种子数据（≥30 个项目跨阶段分布）实际计数一致；② `OVERDUE` 项含 `highlight=RED`（[FR-018](./spec.md)）；③ 响应时间 P95 ≤ 500ms（[plan.md Performance Goals](./plan.md)）；④ `SC-016` 管理者 10 秒内掌握全局。

#### 步骤 2.2 卡片点击弹窗

调用 `GET /api/v1/projects/tracking/by-phase/IMPLEMENTATION_DEPLOYMENT`。

**预期**：返回处于实施部署阶段的全部项目列表，字段含办事处/项目名称/合同号/项目级别/用户单位/用户服务等级/项目阶段/项目经理（[FR-017](./spec.md)）。

#### 步骤 2.3 超期项目标红

调用 `GET /api/v1/projects/tracking/details?is_overdue=true`，校验返回项目 `is_overdue=true`，前端渲染阶段文字标红（[VAL-039](./contracts/rest-api.md#2113-获取项目具体情况表)）。

#### 步骤 2.4 跳转单项目跟踪

调用 `GET /api/v1/projects/{projectId}/tracking`，校验返回 `operation_url` 与 6 项导航（基本信息/工前准备/制定施工计划/实施方案/实施部署/验收交维）。

---

### 场景 3 — 工前准备（US-11）

**覆盖**: 客户联系人、工勘、需求分析、工程交底书。FR-113~FR-117。

#### 步骤 3.1 录入主联系人

1. 以 `user-pm-001` 调用 `POST /api/v1/projects/{projectId}/user-contacts`，body 含 `contact_attr=PRIMARY`（[rest-api.md §4.1.2](./contracts/rest-api.md#412-创建客户联系人)）。
2. 调用 `GET /api/v1/projects/{projectId}`，校验 `primary_contact_id` 已关联至项目页面。
3. 调用 `POST /api/v1/user-contacts/{contactId}/deactivate` 失效该联系人，预期 `status=失效`。

**校验点**：① 主联系人显示在项目主页面，其他联系人仅在客户联系人页面展示；② `SC-018` 工前准备耗时较线下方式减少 50%+。

#### 步骤 3.2 工勘与外包流程触发

1. `PUT /api/v1/projects/{projectId}/site-survey`，body `need_oem_install=true`、`need_outsource=true`、`need_rail_tray=true`、`material_compliance=false`、`exchange_serials=["SN001","SN002"]`（[rest-api.md §4.2.1](./contracts/rest-api.md#421-获取保存工勘记录)）。
2. 调用 `POST /api/v1/projects/{projectId}/site-survey/outsource`，预期返回外包流程链接（[FR-115](./spec.md)）。
3. 调用 `POST /api/v1/projects/{projectId}/site-survey/material-pickup` 与 `/material-purchase`，预期返回物料领用/外采链接。
4. 调用 `POST /api/v1/projects/{projectId}/site-survey/exchange`，预期返回换货流程链接。

**校验点**：① 必填字段校验 [VAL-013](./contracts/rest-api.md#421-获取保存工勘记录)（project_end_date、power_confirmed、need_oem_install 缺失返回 `400`）；② 工勘数据写入 `SiteSurvey` 表（1:1 Project，[data-model.md §3.2.2](./data-model.md#322-sitesurvey工勘记录)）。

#### 步骤 3.3 需求分析与工程交底书

1. `PUT /api/v1/projects/{projectId}/requirement`，body 含项目背景、目标、传输现状多选 `["IPv6","Jumbo"]`、运维管理要求多选 `["带内","SNMP","UMC"]`（[rest-api.md §4.3.1](./contracts/rest-api.md#431-获取保存需求分析)）。
2. 调用 `POST /api/v1/projects/{projectId}/requirement/brief-book` 生成工程交底书。
3. 调用 `GET /api/v1/projects/{projectId}/requirement/brief-book/download` 下载。

**预期**：`201` 生成，`200` 文件流下载。校验 `Requirement` 表 `brief_book_url` 已写入（[data-model.md §3.2.3](./data-model.md#323-requirement需求分析)）。

---

### 场景 4 — 制定施工计划与审批（US-12）

**覆盖**: 只读基础信息、工期紧张提醒、钉钉审批。FR-118~FR-120。

#### 步骤 4.1 只读字段校验

调用 `GET /api/v1/projects/{projectId}/construction-plan`，校验 `contract_accept_date`（PMS 导入）与 `duration_requirement`（工前准备带入）字段返回 `readonly=true`，`PUT` 修改这两个字段返回 `422`（[VAL-030](./contracts/rest-api.md#51-获取保存施工计划)）。

#### 步骤 4.2 工期紧张提醒

构造项目 `duration_requirement` 离当前时间 < 3 个月且 `delivery_status=未发货`，调用 `GET /api/v1/projects/{projectId}/construction-plan/reminder`。

**预期**：返回 `duration_warning`（"当前项目工期紧张..."）、`delivery_warning`（"请与销售确认发货时间"）、`show_crm_reminder_button=true`（[rest-api.md §5.2](./contracts/rest-api.md#52-工期紧张提醒)）。

**校验点**：`SC-018` 工期不足提醒触发条件 [VAL-038](./contracts/rest-api.md#52-工期紧张提醒)。

#### 步骤 4.3 提交审核与钉钉推送

1. 以 `user-pm-001` 调用 `PUT /api/v1/projects/{projectId}/construction-plan` 填写各阶段时间（直签项目须含 arrival_sign_date、first_acceptance_date、final_acceptance_date，[VAL-009](./contracts/rest-api.md#51-获取保存施工计划)）。
2. 调用 `POST /api/v1/projects/{projectId}/construction-plan/submit-approval`，预期 `status=待审核`、`locked=1`。
3. 校验 mock 钉钉捕获到 `POST /dingtalk/approvals/push`，`approval_type=CONSTRUCTION_PLAN`、`assignee=user-sm-001`（[external-integrations.md §2.3](./contracts/external-integrations.md#23-钉钉)）。
4. 校验事件 `pms.approval.construction_plan` 发布（[events.md §2.1](./contracts/events.md#21-事件清单)）。
5. 尝试再次 `PUT` 修改计划，预期返回 `412`（已提交审核锁定不可编辑，[FR-026](./spec.md)）。

#### 步骤 4.4 服务经理审批

以 `user-sm-001` 调用 `POST /api/v1/projects/{projectId}/construction-plan/approve`，body `{"approved":true,"remark":"计划合理"}`，预期 `status=已通过`。

**校验点**：① 仅服务经理可修改计划（其他角色返回 `403`）；② `SC-011` 工作流任务 100% 有记录可追溯。

---

### 场景 5 — 编写实施方案与审核（US-13）

**覆盖**: 客户方案自动填充、前序数据引用、其他方案模板、生成/下载/审核。FR-121~FR-125。

#### 步骤 5.1 上传客户方案并自动填充

调用 `POST /api/v1/projects/{projectId}/implementation-plan/upload-customer-plan`（multipart，[rest-api.md §6.2](./contracts/rest-api.md#62-上传客户方案文件并自动填充)），预期返回解析后的 `overview_json`/`design_json` 等已自动填充字段，可继续编辑。

#### 步骤 5.2 前序数据引用校验

调用 `GET /api/v1/projects/{projectId}/implementation-plan`，校验：
- 项目概述章节引用工前准备的 `project_background` / `project_objective`（[FR-122](./spec.md)）。
- 项目团队引用 `Member` 表。
- 项目清单引用 `ProductList`。
- 项目进度计划引用 `ConstructionPlan`。

#### 步骤 5.3 总体方案设计同步序列号

调用 `PUT /api/v1/projects/{projectId}/implementation-plan`，更新 `design_json`（含 `deploy_location`、`interface_interconnect`、`ip_vlan`、`software_version`，[rest-api.md §6.1](./contracts/rest-api.md#61-获取保存实施方案)）。

**校验点**：`DeviceSerial` 表对应记录的 `factory_sw_version` / `online_sw_version` 等字段被同步更新（[FR-123](./spec.md)）。

#### 步骤 5.4 其他方案模板

调用 `PUT` 时 `other_plans_json` 勾选 `quality_assurance`、`risk_control`、`ops_delivery`、`doc_archive`，预期返回模板内容并支持"添加到实施方案"（[FR-124](./spec.md)）。

#### 步骤 5.5 生成/下载/提交审核

1. `POST /api/v1/projects/{projectId}/implementation-plan/generate`，预期 `status=已生成`、`generated_at` 写入。
2. `GET /api/v1/projects/{projectId}/implementation-plan/download`，预期文件流 `200`。
3. `POST /api/v1/projects/{projectId}/implementation-plan/submit-approval`，预期钉钉推送至服务经理；重大项目（`project_level=A`）同时推送总部复核（[FR-125](./spec.md)）。

---

### 场景 6 — 实施部署（US-14）

**覆盖**: 到货签收/硬件安装/配置调试/业务联调/割接上线按钮。FR-126~FR-130。

#### 步骤 6.1 到货签收

调用 `POST /api/v1/projects/{projectId}/deployment/arrival-sign/upload`（multipart，[rest-api.md §7.1.1](./contracts/rest-api.md#711-上传到货签收单)）。

**校验点**：`Deliverable` 表新增记录，`deliverable_type=到货签收单`、`source=手动上传`、`retention_years=5`（[data-model.md §3.2.6](./data-model.md#326-deliverable交付件)）。

#### 步骤 6.2 硬件安装

1. `GET /api/v1/projects/{projectId}/deployment/hardware-install`，校验返回清单的 `serial_no` / `product_name` 由 PMS 导入，`install_location` 由需求分析自动带入。
2. `PUT /api/v1/projects/{projectId}/deployment/hardware-install/{serialId}`，body `{"install_location":"A机柜12U"}`。
3. `POST /api/v1/projects/{projectId}/deployment/hardware-install/{serialId}/photos`（multipart）。

**校验点**：照片自动添加水印（时间+GPS+上传人，[VAL-049](./contracts/rest-api.md#723-上传安装照片)）。

#### 步骤 6.3 配置调试

调用 `POST /api/v1/device-serials/{serialId}/config-logs`（multipart，[rest-api.md §14.2.2](./contracts/rest-api.md#1422-上传配置-log)）。

**校验点**：① `SC-009` 支持 100MB+ 大文件断点续传（[VAL-043](./contracts/rest-api.md#1422-上传配置-log)）；② `ConfigLog` 表新增记录，`source=手动上传`、`retention_years=5`；③ `DeviceSerial.config_log_url` 更新。

#### 步骤 6.4 业务联调

1. `PUT /api/v1/projects/{projectId}/deployment/business-debug` 填写设备连接信息（设备名称/IP/登录用户名/密码/登录方式/端口/波特率，[FR-129](./spec.md)）。
2. `POST /api/v1/projects/{projectId}/deployment/business-debug/collect-config` 一键收集配置信息。

**预期**：返回采集的设备配置信息，`DeviceSerial` 表 `DeviceEnhancement` 同步更新（含 `enabled_functions`、`interface_table_json`）。

#### 步骤 6.5 割接上线按钮状态

1. 前期流程未完成时，调用 `GET /api/v1/projects/{projectId}/deployment/cutover-online`，预期返回 `can_initiate=false`（按钮失效，[FR-130](./spec.md)）。
2. 完成步骤 6.1~6.4 后再次调用，预期 `can_initiate=true`。

---

### 场景 7 — 验收交维（US-15）

**覆盖**: 培训/满意度/初终验/交付件。FR-131~FR-134。

#### 步骤 7.1 现场培训

1. `PUT /api/v1/projects/{projectId}/acceptance/training`，body 含培训记录各字段（[rest-api.md §20.1.1](./contracts/rest-api.md#2011-获取保存培训记录)）。
2. `GET /api/v1/projects/{projectId}/acceptance/training/sample`，预期文件流 `200`。

#### 步骤 7.2 满意度调查

1. `POST /api/v1/projects/{projectId}/acceptance/satisfaction/generate` 生成完工证明与满意度调查表。
2. `POST /api/v1/projects/{projectId}/acceptance/satisfaction/push` 推送至客户 H5（[rest-api.md §20.2.2](./contracts/rest-api.md#2022-推送满意度调查至客户)）。
3. 客户在客户 H5 签字回传（短信验证码登录后操作）。
4. `GET /api/v1/projects/{projectId}/acceptance/satisfaction/download`，预期下载满意度调查报告。

**校验点**：评分分档 100/80/60/40/0（[FR-132](./spec.md)），`Deliverable` 表新增 `deliverable_type=满意度报告`。

#### 步骤 7.3 初验与终验

1. `POST /api/v1/projects/{projectId}/acceptance/first-acceptance/upload`（multipart）。
2. `POST /api/v1/projects/{projectId}/acceptance/final-acceptance/upload`（multipart）。

#### 步骤 7.4 查看交付件集中下载

`GET /api/v1/projects/{projectId}/deliverables`，校验集中列出 6 类交付件：到货签收单、实施方案、初验报告、终验报告、现场培训记录、满意度调查报告，均可下载（[FR-134](./spec.md)）。

---

### 场景 8 — 割接管理与割接平台集成（US-16）

**覆盖**: 建单/评级/方案/操作单/备件/承诺书/闭环归档。FR-135~FR-140。实体见 [data-model.md §3.3](./data-model.md#33-割接管理)。

#### 步骤 8.1 发起割接

1. 完成场景 6 全部实施部署后，调用 `POST /api/v1/cutover-orders`，body 含 `cutover_source=ENGINEERING_DELIVERY`、`cutover_type=FRIENDLY_VENDOR_REPLACE`（[rest-api.md §8.1.1](./contracts/rest-api.md#811-创建割接单)）。
2. 校验割接单携带 PMS 实施信息、客户资产库数据、RMA/ITR 待闭环问题（[FR-135](./spec.md)）。

**预期**：`201`，`status=建单`。

#### 步骤 8.2 自动评定等级

调用 `POST /api/v1/cutover-orders/{cutoverId}/assess-level`，预期返回 `{"level":"A","auto":true}`（依据固定规则，[FR-136](./spec.md)）。

**校验点**：① A 类需服务经理+二线+研发审批，B 类需服务经理+二线；② 边界争议支持人工调整：`PUT /api/v1/cutover-orders/{cutoverId}/level`，`level_adjusted=1`、`level_remark` 写入（[data-model.md §3.3.1](./data-model.md#331-cutoverorder割接单)）。

#### 步骤 8.3 分级审批与钉钉推送

1. `POST /api/v1/cutover-orders/{cutoverId}/approvals` 发起审批。
2. 外部客户割接需 `POST /api/v1/cutover-orders/{cutoverId}/customer-approval` 上传客户审批确认单。
3. 依次以 `user-sm-001` / `user-2nd-001` / `user-rd-001`（A 类）调用 `POST /api/v1/cutover-orders/{cutoverId}/approvals/{approvalId}`。
4. 校验事件 `pms.approval.cutover` 发布（[events.md §2.1](./contracts/events.md#21-事件清单)），钉钉捕获到推送。

#### 步骤 8.4 生成方案与操作单

1. `POST /api/v1/cutover-orders/{cutoverId}/scheme/generate` 基于模板库生成割接方案（[FR-137](./spec.md)）。
2. `POST /api/v1/cutover-orders/{cutoverId}/ops-sheets/generate`，预期返回 4 类操作单（prep/cutover/post/rollback）+ checklist（[rest-api.md §8.3.2](./contracts/rest-api.md#832-生成操作单与-checklist)）。

**校验点**：`SC-026` 操作单与 checklist 100% 自动生成。

#### 步骤 8.5 备件关联与 SPMS

1. `POST /api/v1/cutover-orders/{cutoverId}/spare-parts/apply`，预期关联 SPMS 备件申请流程。
2. 库存不足场景：构造 `SparePart.status=在库` 数量 < 申请数量，预期返回 `422` 并阻断（[VAL-032](./contracts/rest-api.md#842-关联备件申请)）。

#### 步骤 8.6 采集设备信息与承诺书

1. `POST /api/v1/cutover-orders/{cutoverId}/post-cutover/device-info` 采集三大日志、版本/热补丁/license 备份、整机配置、tech-support。
2. `POST /api/v1/cutover-orders/{cutoverId}/commitment` 上传《机房割接实施承诺书》+ checklist 签字。

#### 步骤 8.7 闭环归档与 PMS 刷新

1. 校验备件已退回（`SparePart.return_status=已退回`，[VAL-033](./contracts/rest-api.md#853-割接闭环归档)）。
2. `POST /api/v1/cutover-orders/{cutoverId}/close`。

**预期**：`status=闭环`、`closed_at` 写入、`pms_refresh_status=已刷新`。

**校验点**：① `DeviceSerial` 表 `factory_sw_version`/`factory_conboot`/`factory_cpld`/序列号刷新；② `show tech-support` 备份至对象存储；③ 《客户技术档案》更新；④ 事件 `pms.cutover.status.changed` 发布；⑤ `SC-025` 割接闭环归档刷新及时率 100%；⑥ `SC-026` 割接全流程闭环率 ≥ 95%。

#### 步骤 8.8 割接失败提交问题工单

构造割接失败场景，调用 `POST /api/v1/cutover-orders/{cutoverId}/failure-ticket`，预期 ITR 创建问题单并关联割接单与设备（[FR-140](./spec.md)）。

#### 步骤 8.9 已知隐患匹配技术公告

构造割接单的设备序列号关联到已确认的技术公告，校验 `matched_prob_id` 自动写入（[FR-135 / US-6 AC-6](./spec.md)）。

---

### 场景 9 — 售前测试管理（US-2）

**覆盖**: 申请/审批/跟踪/回访/临时授权。FR-034~FR-039。状态机见 [data-model.md §2.2](./data-model.md#22-presales-售前测试状态机)。

#### 步骤 9.1 申请（10）

调用 `POST /api/v1/presales-projects`，body 含 `applicant_id`、`product_line_json`、`rma_info_json`、`deliverable_json`（[rest-api.md §9.1.1](./contracts/rest-api.md#911-创建售前测试申请)）。

**预期**：`201`，`status_code=10`。

#### 步骤 9.2 状态流转 10→31→32→33→100

依次调用 `POST /api/v1/presales-projects/{presalesId}/transitions`：
1. `{"target_status":"31"}` → SM 审批指定 PM。
2. `{"target_status":"32"}` → PM 跟踪。
3. `{"target_status":"33"}` → EM 回访。
4. `{"target_status":"100"}` → 闭环。

**校验点**：① [VAL-006](./contracts/rest-api.md#913-售前状态流转) 状态机校验（非法跳转返回 `412`）；② 事件 `pms.presales.status.changed` 多次发布；③ `SC-003` 各阶段耗时可见：`GET /api/v1/presales-projects/{presalesId}/duration` 返回 4 项 duration 字段（[rest-api.md §9.2.1](./contracts/rest-api.md#921-获取售前各阶段耗时)）。

#### 步骤 9.3 终止分支

在任意非闭环状态调用 transitions `{"target_status":"20"}`，预期 `status_code=20`（终态）。

#### 步骤 9.4 临时授权自动获取

1. 构造售前测试设备已发货状态（mock 供应链触发 `POST /api/v1/device-serials/supply-chain/import` 导入序列号）。
2. 调用 `POST /api/v1/presales-projects/{presalesId}/temporary-licenses/auto-acquire`（[rest-api.md §9.5.1](./contracts/rest-api.md#951-自动获取首次临时授权)）。

**预期**：`TemporaryLicense` 表新增记录，`status=已下发`、`license_key` 写入。

**校验点**：① `SC-024` 售前测试首次临时授权 100% 自动获取；② 下发失败场景 [VAL-050](./contracts/rest-api.md#951-自动获取首次临时授权) 触发告警与重试（`retry_count` 递增，`error_msg` 写入）；③ mock 临时授权通道捕获到 `POST /license/issue`。

---

### 场景 10 — 转包管理（US-3）

**覆盖**: 创建/多级审批/D365 集成/发票 OCR/付款/回访/验收。FR-040~FR-048。实体见 [data-model.md §3.5](./data-model.md#35-转包管理)。

#### 步骤 10.1 创建转包

调用 `POST /api/v1/subcontracts`，body 含 `project_id`、`facilitator_id`、`device_list_json`、`price_json`、`payment_json`（[rest-api.md §10.1.1](./contracts/rest-api.md#1011-创建转包项目)）。

**预期**：`201`，`status=草稿`。校验 [VAL-015](./contracts/rest-api.md#1011-创建转包项目) 必填校验与 [VAL-026](./contracts/rest-api.md#1011-创建转包项目) 唯一性。

#### 步骤 10.2 多级审批

1. `POST /api/v1/subcontracts/{subcontractId}/approvals` 发起审批。
2. 依次以受益部门服务经理 → 通用审批节点 → 工程管理部 → 主任 完成审批（4 节点，[FR-041](./spec.md)）。

**校验点**：① `SC-004` 100% 完成全部节点方可进入合同执行；② 跳过节点返回 `422`；③ 事件 `pms.approval.subcontract` 多次发布；④ 超时场景：构造审批停留 > 设定阈值，校验 `pms.approval.timeout` 事件触发上级升级通知（[VAL-046](./contracts/rest-api.md#2313-办理任务)）。

#### 步骤 10.3 D365 采购订单推送

调用 `POST /api/v1/subcontracts/{subcontractId}/d365/push-po`（[rest-api.md §10.3.1](./contracts/rest-api.md#1031-推送采购订单至-d365)）。

**校验点**：① mock D365 捕获到 `POST /d365/purchase-orders`，载荷含 `subcontract_no` / `po_lines` / `facilitator_code`；② `SubcontractProject.d365_po_no` / `d365_po_status` 写入；③ `SC-005` 成功率 ≥ 99%；④ OAuth2 Token 缓存命中（[VAL-045](./contracts/rest-api.md#1031-推送采购订单至-d365)）；⑤ 失败场景重试 3 次并记录日志，不阻塞业务。

#### 步骤 10.4 发票 OCR 识别

调用 `POST /api/v1/subcontracts/{subcontractId}/invoices/ocr`（multipart），预期返回识别结果，`invoice_ocr_status` 写入（[FR-047](./spec.md)）。

#### 步骤 10.5 付款审批

调用 `POST /api/v1/subcontracts/{subcontractId}/payments/approve` 启动付款审批流。

#### 步骤 10.6 回访与验收

1. `POST /api/v1/subcontracts/{subcontractId}/callbacks` 发起回访。
2. 完成回访问卷填写与审批（流程同场景 4 / 11）。
3. 进入验收并闭环：`status=已闭环`。

---

### 场景 11 — 项目回访与闭环管理（US-4）

**覆盖**: 回访/审批/问卷/评分/闭环状态回 10。FR-049~FR-053。

#### 步骤 11.1 发起回访

以 `user-em-001` 调用 `POST /api/v1/callbacks`，body `{"project_id":1,"callback_type":"PROJECT","applicant_id":100}`（[rest-api.md §11.1.1](./contracts/rest-api.md#1111-创建回访申请)）。

#### 步骤 11.2 问卷缺失阻止审批

不填写问卷直接调用 `POST /api/v1/callbacks/{callbackId}/approve`，预期返回 `422`（[VAL-029](./contracts/rest-api.md#1121-审批回访)）。

#### 步骤 11.3 填写问卷并计算评分

1. `PUT /api/v1/callbacks/{callbackId}/questionnaire`，body 含 `template_id` 与多个 item，评分 100/80/60/40/0 分档（[rest-api.md §11.3.1](./contracts/rest-api.md#1131-获取保存回访问卷)）。
2. `POST /api/v1/callbacks/{callbackId}/questionnaire/submit`，预期返回 `total_score`。

#### 步骤 11.4 审批与闭环状态联动

1. `POST /api/v1/callbacks/{callbackId}/approve` 通过。
2. 调用 `POST /api/v1/projects/{projectId}/closure/approve`，预期闭环流程状态回到 `10`，项目可正式闭环 `100`（[FR-052](./spec.md)）。

#### 步骤 11.5 驳回重提

调用 `POST /api/v1/callbacks/{callbackId}/reject`，预期 `status=已驳回`；重新提交后回到审批环节（[FR-050](./spec.md)）。

---

### 场景 12 — 设备信息增强管理（US-19）

**覆盖**: 配置历史/部署风险/运行业务档案/启用功能/接口对照表/拓扑/供应链同步。FR-150~FR-156。实体见 [data-model.md §3.8](./data-model.md#38-设备信息增强)。

#### 步骤 12.1 设备序列号详情

`GET /api/v1/device-serials/{serialId}`，校验返回字段含序列号、产品编码、安装位置、出厂/官网/在网/分支版本、受影响技术公告、维保信息、配置 Log 超链接（[FR-023](./spec.md)、[FR-155](./spec.md)）。

#### 步骤 12.2 配置历史对比

1. 多次更新设备配置（触发服务平台同步或手动 `PUT`）。
2. `GET /api/v1/device-serials/{serialId}/enhancement`，校验 `config_history_json` 含多次变更记录，支持对比（[FR-150](./spec.md)）。

#### 步骤 12.3 部署风险与冗余

`PUT /api/v1/device-serials/{serialId}/enhancement/deploy-risk`，body 含 `deploy_risk_desc`（单机/单点风险描述）与 `redundancy_desc`（冗余部署情况）。

#### 步骤 12.4 运行业务档案

`PUT /api/v1/device-serials/{serialId}/enhancement/business-archive`，将运行业务与配置关联绑定，预期上传至设备与项目（[FR-150](./spec.md)）。

#### 步骤 12.5 启用功能自动回传

触发设备配置命令采集（mock 服务平台回调 `POST /api/v1/device-serials/{serialId}/enhancement/enabled-functions`，[rest-api.md §14.4.1](./contracts/rest-api.md#1441-回传启用功能)），预期 `enabled_functions` 自动更新。

#### 步骤 12.6 接口对照表与拓扑

1. `PUT /api/v1/device-serials/{serialId}/enhancement/interface-table` 维护接口配置与对端信息。
2. `POST /api/v1/device-serials/{serialId}/enhancement/generate-topology` 自动生成网络拓扑。

**校验点**：① 返回非图片拓扑（JSON，标注上下游设备与接口互联）；② `network_topology_json` 同步至 `DeviceEnhancement`；③ `SC-021` 100% 设备序列号具备增强维度。

#### 步骤 12.7 供应链导入与版本匹配

mock 供应链触发 `POST /api/v1/device-serials/supply-chain/import`（[rest-api.md §14.6.1](./contracts/rest-api.md#1461-供应链导入出厂信息)）。

**校验点**：① `DeviceSerial.supply_chain_synced=1`；② `official_version` 自动匹配写入；③ 出厂信息与 PMS 已有数据不一致场景触发告警（[external-integrations.md §4.4](./contracts/external-integrations.md#44-数据同步冲突处理)）。

#### 步骤 12.8 一码通定位

`GET /api/v1/device-serials/{serialId}/location/one-code` → `PUT /api/v1/device-serials/{serialId}/location`（multipart 上传设备照片），校验 `one_code_address` / `device_photo_url` 写入（[FR-156](./spec.md)）。

---

### 场景 13 — 用户管理与 CRM 同步（US-20）

**覆盖**: CRM 同步/反向同步/最终用户/客户档案。FR-157~FR-161。实体见 [data-model.md §3.11](./data-model.md#311-用户管理)。

#### 步骤 13.1 CRM → PMS 同步

触发 mock CRM 调用 `POST /api/v1/users/sync-from-crm`（[rest-api.md §18.3.1](./contracts/rest-api.md#1831-触发-crm-同步至-pms)）。

**预期**：`User` 表新增/更新记录，`crm_sync_status=已同步`、`crm_last_synced_at` 写入。

**校验点**：`SC-022` 同步延迟 ≤ 5 分钟。

#### 步骤 13.2 PMS → CRM 反向同步

修改 PMS 用户信息后调用 `POST /api/v1/users/{userId}/sync-to-crm`，预期 mock CRM 收到反向同步请求。

#### 步骤 13.3 同步冲突处理

构造 PMS 与 CRM 同时修改同一用户，调用 `POST /api/v1/users/{userId}/resolve-crm-conflict`，预期返回两端版本，人工裁定后同步方向写入（[external-integrations.md §2.2](./contracts/external-integrations.md#22-crm-系统)）。

#### 步骤 13.4 最终用户与下单客户区分

调用 `POST /api/v1/users/{userId}/end-users`，body `{"end_user_id":101}`，校验 `User.parent_customer_id` 写入，项目页面区别展示下单客户与最终用户（[FR-158](./spec.md)）。

#### 步骤 13.5 日常工作维护用户信息

调用 `POST /api/v1/users/{userId}/daily-works`，校验用户信息更新（[FR-160](./spec.md)）。

#### 步骤 13.6 客户档案

1. `GET /api/v1/users/{userId}/archives?archive_type=故障档案` 与 `archive_type=服务档案`。
2. `POST /api/v1/users/{userId}/archives` 创建客户档案，关联 ITR 工单等业务 ID。

---

### 场景 14 — ITR 故障处理与 RMA 联动（US-21）

**覆盖**: 工单/级别/升单/解决方案/RMA 调用/闭环归档。FR-162~FR-166。实体见 [data-model.md §3.12](./data-model.md#312-itr-故障处理)。

#### 步骤 14.1 创建问题单

调用 `POST /api/v1/itr-tickets`，body 含来电人/设备/问题描述/级别（[rest-api.md §17.1.1](./contracts/rest-api.md#1711-创建-itr-问题单)）。

**校验点**：① 工单关联 PMS 设备与用户（`device_serial_id` / `user_id` / `project_id` 写入）；② 一级问题触发邮件通报（`notify_email=1`，mock SMTP 捕获）。

#### 步骤 14.2 升单

调用 `POST /api/v1/itr-tickets/{ticketId}/escalate`，body `{"escalate_to":"SECOND_LINE"}`，预期 `escalate=1`、`escalate_to=SECOND_LINE`。

#### 步骤 14.3 提交解决方案

调用 `POST /api/v1/itr-tickets/{ticketId}/solution`，body 含 `root_cause` / `solution` / `fix_version` / `bug_no` / `prob_id` / `product_line` 等（[rest-api.md §17.3.1](./contracts/rest-api.md#1731-提交解决方案)）。

**校验点**：`prob_id` 关联技术公告编号（[FR-164](./spec.md)、[US-6 AC-7](./spec.md)）。

#### 步骤 14.4 硬件故障调用 RMA

构造解决方案为硬件故障，调用 `POST /api/v1/itr-tickets/{ticketId}/rma`（[rest-api.md §17.4.1](./contracts/rest-api.md#1741-调用-rma-流程)）。

**预期**：`201`，返回 `RMAOrder`，`ITRTicket.rma_order_id` 关联，`RMAOrder.device_serial_id` / `spare_part_id` 写入。

**校验点**：① `SC-023` 硬件故障 RMA 自动调用率 100%；② mock RMA 捕获到 `POST /rma/orders`；③ RMA 接口不可用时不阻塞 ITR 工单创建（标记待调用重试，[external-integrations.md §2.6](./contracts/external-integrations.md#26-rma-系统)）。

#### 步骤 14.5 关闭工单与归档

调用 `POST /api/v1/itr-tickets/{ticketId}/close`。

**校验点**：① `archived=1` 故障报告归档至 ITR；② 关联 PMS 设备与用户；③ `CustomerArchive` 表新增故障档案；④ `SC-023` ITR 闭环率 ≥ 95%、故障报告 100% 归档；⑤ 事件 `pms.itr.status.changed` 发布。

---

### 场景 15 — 技术公告与修复任务（US-6）

**覆盖**: 创建/审批/影响范围匹配/修复任务/阅读确认/割接隐患匹配/ITR 关联。FR-059~FR-064。实体见 [data-model.md §3.7](./data-model.md#37-技术公告)。

#### 步骤 15.1 创建与审批

1. 以 `user-admin` 调用 `POST /api/v1/probs`，body 含 `title`、`software_version_json:["V5.0","V5.1"]`（[rest-api.md §13.1.1](./contracts/rest-api.md#1311-创建技术公告)）。
2. `POST /api/v1/probs/{probId}/submit` 提交审批（草稿→待确认）。
3. `POST /api/v1/probs/{probId}/approve` body `{"approved":true}`（待确认→已确认）。

**校验点**：[VAL-007](./contracts/rest-api.md#1311-创建技术公告) 状态机校验。

#### 步骤 15.2 影响范围匹配

调用 `POST /api/v1/probs/{probId}/match-affected`，预期返回受影响项目列表。

**校验点**：① `SC-015` 匹配准确率 ≥ 95%；② 无匹配场景返回 `matched=false` 并允许手动指定（[VAL-040](./contracts/rest-api.md#1331-匹配受影响项目)）；③ `prob_device_rel` 中间表写入受影响设备关联。

#### 步骤 15.3 发布修复任务与跟踪

1. `POST /api/v1/probs/{probId}/fix-tasks` 发布修复任务（已确认→解决中）。
2. `PUT /api/v1/fix-tasks/{fixTaskId}/progress` 更新进展，校验 `FixTaskProcess` 子表写入流程过程记录与周报。
3. `POST /api/v1/fix-tasks/{fixTaskId}/close` 关闭（解决中→已关闭）。

#### 步骤 15.4 阅读确认

以普通用户调用 `POST /api/v1/probs/{probId}/read-confirm`，校验阅读记录表写入（[FR-062](./spec.md)）。

#### 步骤 15.5 割接已知隐患自动匹配

在场景 8 创建割接单时，构造设备序列号关联到本场景技术公告，校验 `CutOverOrder.matched_prob_id` 自动写入（[US-6 AC-6](./spec.md)）。

#### 步骤 15.6 统计报表

调用 `GET /api/v1/probs/statistics`，校验返回图表可视化数据（[FR-064](./spec.md)）。

---

### 场景 16 — 维保记录管理（US-5）

**覆盖**: 4 种类型维护记录/问卷/交付件/统计。FR-054~FR-058。实体见 [data-model.md §3.6](./data-model.md#36-维保管理)。

#### 步骤 16.1 创建维护记录（4 种类型）

分别以 `project_type=10/20/30/40` 调用 `POST /api/v1/maintenances`，校验：
- `project_type=10`（售后）关联 `Project`。
- `project_type=20`（售前）关联 `PresalesProject`，`presales_id` 必填。
- `project_type=30/40` 关联基础数据。

#### 步骤 16.2 维护问卷与交付件

1. `PUT /api/v1/maintenances/{maintenanceId}/questionnaire`，body 含头表 + 行表 JSON。
2. `POST /api/v1/maintenances/{maintenanceId}/deliverables` 上传交付件。

#### 步骤 16.3 服务交付统计与维保状态

1. `GET /api/v1/maintenances/{maintenanceId}/delivery-statistics`，校验统计 JSON。
2. `GET /api/v1/projects/{projectId}/warranty-state`，校验维保状态返回（[FR-058](./spec.md)）。

---

### 场景 17 — 服务平台集成与设备信息自动采集（US-17）

**覆盖**: 巡检任务/log/报告同步/设备信息解析/CRT log 自动采集。FR-141~FR-144。实体见 [data-model.md §3.9](./data-model.md#39-服务平台集成)。

#### 步骤 17.1 创建巡检任务并执行

1. `POST /api/v1/inspection-tasks`，body 含 `device_serial_id` / `device_type` / `target_ip` / `scenario_lib`（[rest-api.md §15.1.1](./contracts/rest-api.md#1511-创建巡检任务)）。
2. `POST /api/v1/inspection-tasks/{taskId}/logs` 上传巡检 log，预期同步至 UMC 环境。
3. `POST /api/v1/inspection-tasks/{taskId}/sync-pms` 同步巡检报告至 PMS。

**校验点**：`InspectionTask.synced_to_pms=1`、`synced_at` 写入、`report_url` 写入。

#### 步骤 17.2 设备信息解析同步

mock 服务平台回调 `POST /api/v1/device-serials/{serialId}/enhancement/sync-from-platform`，body 含 `config_info` / `running_functions` / `deploy_risk_analysis`（[rest-api.md §15.2.1](./contracts/rest-api.md#1521-同步设备信息解析结果)）。

**校验点**：`DeviceEnhancement` 表对应字段更新，`sync_status=已同步`、`last_synced_at` 写入；`SC-019` 采集比例 ≥ 95%。

#### 步骤 17.3 CRT Log 自动采集

mock 客户端回调 `POST /api/v1/device-serials/{serialId}/config-logs/crt-upload`（[rest-api.md §15.3.1](./contracts/rest-api.md#1531-接收客户端上传-crt-log)）。

**校验点**：`ConfigLog` 表新增记录，`source=自动采集CRT log`；服务端识别解析后同步 PMS 并自动回传。

#### 步骤 17.4 服务平台降级

mock UMC 环境不可达，再次执行 17.1，校验巡检与解析结果缓存（`InspectionTask.status=同步中` 重试），不阻塞主业务（[external-integrations.md §2.7](./contracts/external-integrations.md#27-服务平台迪普)）。

---

### 场景 18 — AI 排障与知识库管理（US-18）

**覆盖**: 诊断/知识库/排障经验转换/Skill 训练。FR-145~FR-149。实体见 [data-model.md §3.10](./data-model.md#310-ai-排障)。

#### 步骤 18.1 提交故障类诊断

调用 `POST /api/v1/ai-troubleshooting/diagnose`，body 含 `scenario_type=FAULT`、`product_type=FW-2000`、`version_no=V5.0`、`typical_problem`、`consult_content`（[rest-api.md §16.1.1](./contracts/rest-api.md#1611-提交排障请求)）。

**预期**：返回 `sessionId`，调用 `GET /api/v1/ai-troubleshooting/sessions/{sessionId}` 获取诊断与解决方案。

**校验点**：① 引用相关手册材料、技术公告、经典案例；② `SC-020` 命中率 ≥ 70%；③ AI 诊断错误或知识库缺失场景回退人工排障并标记。

#### 步骤 18.2 知识库 CRUD

调用 `POST /api/v1/knowledge-bases` 维护 11 类知识库（产品标准手册/命令行手册/典配手册/日志手册/Mib 节点手册/API 手册/技术公告/已知隐患/FAQ/经典案例/排障经验，[FR-147](./spec.md)）。

#### 步骤 18.3 排障经验转换模板

调用 `POST /api/v1/troubleshooting-experiences`，body 含 `ticket_no` / `fault_phenomenon` / `product_arch` / `trigger_factor` / `troubleshooting_process`（[rest-api.md §16.3.1](./contracts/rest-api.md#1631-提交排障经验转换模板)）。

**校验点**：`TroubleshootingExperience.converted_to_training=1`，沉淀至知识库形成训练数据；`desensitized=1` 脱敏处理（[VAL-042](./contracts/rest-api.md#2412-归档至冷存储)）。

#### 步骤 18.4 公共 KB 与 Skill 训练

1. `POST /api/v1/knowledge-bases/public` 维护产品典型故障对照表、功能模块与产品对照表、硬件定位处理手册。
2. `POST /api/v1/knowledge-bases/{kbId}/train-skill` 训练 Skill，校验 `skill_trained=1`（[FR-149](./spec.md)）。

---

### 场景 19 — 项目周报与交付件管理（US-7）

**覆盖**: 周报继承/草稿/提交/反馈/交付件/线上操作自动存储。FR-065~FR-070。

#### 步骤 19.1 创建周报并继承

1. 创建上期周报并提交。
2. 调用 `POST /api/v1/projects/{projectId}/weeklies` 创建本期周报，校验自动继承上期数据（`inherited_from` 写入，[FR-065](./spec.md)）。

**校验点**：`SC-014` 减少 50%+ 重复录入。

#### 步骤 19.2 草稿/提交/反馈

1. `PUT` 保存草稿，`POST` 提交，校验 `WeeklyContent` 与 `WeeklyFeedback` 表写入。
2. 上级调用反馈接口，校验反馈记录写入。

#### 步骤 19.3 交付件自动存储

触发工作流执行（如实施方案生成、割接闭环），校验 `Deliverable` 表新增记录，`source=PMS线上产生` 或 `source=工作流自动存储`，按规范格式保存至对象存储（[FR-070](./spec.md)）。

---

### 场景 20 — 系统管理与权限控制（US-8）

**覆盖**: 用户/角色/部门/字典/配置/日志/消息/LDAP-AD/RBAC/数据权限。FR-071~FR-079。

#### 步骤 20.1 LDAP/AD 登录与组织同步

1. 调用 `POST /api/v1/auth/login`，body `{"username":"user-pm-001","password":"..."}`，预期 `200` 返回 JWT。
2. 调用 `GET /api/v1/auth/profile`，校验返回角色与办事处。

**校验点**：① mock LDAP 捕获到 Bind 请求；② 部门与角色从 LDAP 同步至 `Department` / `Role` 表（`ldap_synced=1`，[data-model.md §3.13.2](./data-model.md#3132-department部门)）；③ `SC-027` 100% 用户通过 LDAP/AD 统一认证。

#### 步骤 20.2 客户 H5 短信验证码登录

调用 `POST /api/v1/auth/sms-login`，body `{"phone":"...","sms_code":"..."}`（[rest-api.md §22.8.2](./contracts/rest-api.md#2282-客户-h5-短信验证码登录)），预期 `200` 返回 JWT。

#### 步骤 20.3 RBAC 功能权限

1. 以 `user-admin` 创建用户并分配角色：`POST /api/v1/system/users` + `POST /api/v1/system/roles`（[rest-api.md §22.1 / §22.2](./contracts/rest-api.md#221-用户管理fr-071)）。
2. 以新用户（仅 `project:view` 权限）尝试调用 `POST /api/v1/projects`，预期返回 `403 Forbidden`（[rest-api.md §1.4](./contracts/rest-api.md#14-通用状态码)）。

#### 步骤 20.4 数据权限隔离

1. 以 `user-pm-001`（项目归属）调用 `GET /api/v1/projects`，校验仅返回自己负责的项目。
2. 以交付管理人员调用同一接口，校验返回全局项目。
3. 以代理商用户调用，校验仅返回本公司数据。

**校验点**：① `SC-012` 数据权限 100% 隔离，代理商不可见其他代理商/客户/成本敏感数据；② 越权访问拦截并记录安全日志（`OperateLog.log_type=安全日志`，[FR-105](./spec.md)）；③ `SC-027` 越权访问拦截率 100%。

#### 步骤 20.5 部门/字典/配置/日志/消息

1. 部门树形管理：`POST /api/v1/system/departments`，校验 `parent_id` 树形结构。
2. 字典管理：`POST /api/v1/system/dicts`，校验 [VAL-021](./contracts/rest-api.md#224-数据字典管理) `dict_type+dict_code` 联合唯一。
3. 日志查询：`GET /api/v1/system/logs/operate`、`/login`、`/integration`，校验分类查询。
4. 消息中心：`GET /api/v1/system/messages`，`POST` 标记已读。

---

### 场景 21 — 报表分析（US-9）

**覆盖**: 项目/设备/资源/财务报表 + Excel 导出。FR-083~FR-087。

#### 步骤 21.1 项目进度汇总表

调用 `GET /api/v1/reports/project-progress-summary?office_id=12&start_date=2026-01-01&end_date=2026-12-31`（[rest-api.md §21.1.1](./contracts/rest-api.md#2111-项目进度汇总表)）。

**校验点**：① 多维度（阶段/区域/客户）汇总；② `SC-007` P95 ≤ 2 秒（百万级数据，1000 并发，[plan.md Performance Goals](./plan.md)）。

#### 步骤 21.2 设备/资源/财务报表

分别调用 `/reports/device-status`、`/reports/engineer-workload`、`/reports/project-cost-summary`，校验返回数据。

#### 步骤 21.3 Excel 导出

调用 `POST /api/v1/reports/export?report_type=PROJECT_PROGRESS`，预期返回 Excel 文件流 `200`（[FR-087](./spec.md)）。

---

### 场景 22 — 跨系统数据集成（US-22）

**覆盖**: 40+ 集成点数据流转验证。FR-167。集成矩阵见 [external-integrations.md §5](./contracts/external-integrations.md#5-集成矩阵按业务场景)。

#### 步骤 22.1 集成点配置查询

调用 `GET /api/v1/system/integration-points`，校验返回 20 个集成点记录（`IntegrationPoint` 实体，[data-model.md §3.13.6](./data-model.md#3136-integrationpoint跨系统集成点)），含方向/协议/触发时机/认证方式/重试策略/降级策略。

#### 步骤 22.2 集成场景矩阵验证

按 [external-integrations.md §5](./contracts/external-integrations.md#5-集成矩阵按业务场景) 9 个业务场景逐项验证：

| 业务场景 | 触发动作 | 校验点 |
|---------|---------|-------|
| 转包合同执行 | 场景 10.3 推送 D365 | D365 收到采购订单；回写验收节点 |
| 项目闭环归档 | 场景 1.5 闭环 | ITR 待闭环问题更新、客户资产库同步、割接平台刷新 PMS |
| 售前测试发货 | 场景 9.4 发货 | 供应链导入出厂信息，临时授权自动获取 |
| 割接全流程 | 场景 8 全流程 | PMS ↔ 割接平台、SPMS、ITR、客户资产库数据流转 |
| 巡检与设备解析 | 场景 17.1/17.2 | 巡检报告与解析结果同步至 PMS |
| 用户信息维护 | 场景 13.1/13.2 | PMS ↔ CRM 双向同步 |
| 认证与组织 | 场景 20.1 | LDAP/AD、EHR → PMS 同步 |
| 审批推送 | 场景 4.3/8.3/15.1 | PMS → 钉钉、邮件推送 |
| 数据归档 | 场景 7/24 | PMS → 冷存储归档 |

**校验点**：① `SC-025` 跨系统 40+ 集成点数据同步成功率 ≥ 99%；② 集成调用日志记录至 `OperateLog`（`log_type=集成调用日志`，[FR-076](./spec.md)）；③ 失败场景重试 3 次并降级（[external-integrations.md §4.3](./contracts/external-integrations.md#43-重试与降级通用策略)）。

---

### 场景 23 — 多终端访问（US-1 跨终端 + US-15 + US-16）

**覆盖**: PC Web/工程师 H5/代理商 H5/客户 H5。FR-089~FR-094。

#### 步骤 23.1 PC Web 全功能覆盖

以 `user-admin` 登录 `http://localhost:5173`，校验可访问全部业务菜单（项目/交付/割接/售前/转包/维保/技术公告/设备/ITR/周报/报表/系统管理/AI 排障，[FR-089](./spec.md)）。

#### 步骤 23.2 工程师 H5 现场作业

1. 工程师 H5（`http://localhost:5174`）登录。
2. 调用 `POST /api/v1/mobile/check-in`，body 含 `project_id` / `latitude` / `longitude` / `photo`（[rest-api.md §25.1.1](./contracts/rest-api.md#2511-gps-签到打卡)）。

**校验点**：① 照片自动添加水印（时间+GPS+上传人，[VAL-049](./contracts/rest-api.md#2511-gps-签到打卡)）；② `SC-094` 防作弊；③ 离线场景：断网后调用签到，预期进入 IndexedDB 离线缓存，联网后调用 `POST /api/v1/mobile/offline-sync` 同步。

#### 步骤 23.3 离线缓存范围限制

断网后尝试：
- 只读参考数据（项目信息/设备清单/实施方案）：可离线查看。
- 现场采集类数据（施工照片/工勘表单/配置 Log/签到记录）：可离线缓存，联网同步。
- 审批/状态变更等写操作：离线禁用，调用返回 `412`（[VAL-048](./contracts/rest-api.md#2512-离线数据同步)）。

#### 步骤 23.4 代理商 H5

代理商 H5（`http://localhost:5175`）登录，调用 `POST /api/v1/mobile/agent/orders/accept` 接单，`POST /api/v1/mobile/agent/progress-report` 上报进度，校验数据权限仅限本公司（[FR-091](./spec.md)）。

#### 步骤 23.5 客户 H5

1. 客户 H5（`http://localhost:5176`）通过短信验证码登录（场景 20.2）。
2. 调用 `GET /api/v1/mobile/customer/projects/{projectId}`，校验仅返回极有限只读字段（项目进度/割接审批/验收签核/文档下载，[FR-092](./spec.md)）。
3. 客户完成满意度调查签字回传（场景 7.2）与割接审批（场景 8.3）。

---

### 场景 24 — 数据归档与可用性（横切）

**覆盖**: 分级保留/冷存储归档/SLA。FR-168~FR-169。

#### 步骤 24.1 归档至冷存储

构造交付件 `created_at` 超 5 年、巡检/割接归档超 3 年，调用 `POST /api/v1/archives/{archiveId}/move-to-cold-storage`（[rest-api.md §24.1.2](./contracts/rest-api.md#2412-归档至冷存储)）。

**校验点**：① `Deliverable.archived=1` / `ConfigLog.archived=1`；② 异步处理不阻塞核心业务（[VAL-041](./contracts/rest-api.md#2412-归档至冷-storage)）；③ AI 训练数据脱敏后长期保留（[VAL-042](./contracts/rest-api.md#2412-归档至冷-storage)）。

#### 步骤 24.2 冷存储取回

调用 `POST /api/v1/archives/{archiveId}/restore-from-cold-storage`，预期异步返回取回任务 ID，不阻塞（[FR-169](./spec.md)）。

#### 步骤 24.3 可用性验证

持续运行系统 24 小时，校验：
- 接口可用率 ≥ 99.9%（[SC-029](./spec.md)）。
- 割接窗口期（夜间 02:00-06:00）系统 100% 可用。
- 年停机 ≤ 8.76 小时推算符合。

---

### 场景 25 — 乐观锁与并发控制（横切，FR-026）

#### 步骤 25.1 乐观锁冲突

1. 用户 A 与用户 B 同时 `GET /api/v1/projects/{projectId}`，获得 `version=3`。
2. 用户 A `PUT /api/v1/projects/{projectId}`（`If-Match: 3`），预期 `200`，`version=4`。
3. 用户 B `PUT /api/v1/projects/{projectId}`（`If-Match: 3`），预期 `409 Conflict`，返回 `conflictFields` 与 `currentVersion=4`、`yourVersion=3`（[rest-api.md §1.5](./contracts/rest-api.md#15-通用错误体)）。

**校验点**：① `SC-028` 乐观锁检测准确率 100%；② 字段级合并成功率 ≥ 95%；③ 已提交审核的施工计划/实施方案 `locked=1`，编辑返回 `412`（[VAL-030](./contracts/rest-api.md#51-获取保存施工计划)）。

---

## 4. 性能与可量化指标汇总

| 指标 ID | 验证项 | 目标值 | 验证场景 |
|---------|-------|-------|---------|
| SC-001 | 项目创建耗时 | ≤ 3 分钟 | 场景 1.1 |
| SC-002 | 状态流转合法性 | 100% 遵循状态机 | 场景 1.1~1.5 |
| SC-004 | 转包审批节点完成率 | 100% | 场景 10.2 |
| SC-005 | D365 接口成功率 | ≥ 99% | 场景 10.3 |
| SC-006 | 项目成员批量变更 | 100+ 并发 | 场景 1（成员批量） |
| SC-007 | 报表响应 P95 | ≤ 2 秒 | 场景 21.1 |
| SC-009 | 大文件上传 | 100MB+，断点续传 | 场景 6.3 |
| SC-011 | 工作流任务记录率 | 100% | 场景 4.4 |
| SC-012 | 数据权限隔离率 | 100% | 场景 20.4 |
| SC-014 | 周报数据继承减少录入 | ≥ 50% | 场景 19.1 |
| SC-015 | 技术公告匹配准确率 | ≥ 95% | 场景 15.2 |
| SC-016 | 总体跟踪页响应 | ≤ 10 秒 | 场景 2.1 |
| SC-018 | 工前准备耗时减少 | ≥ 50% | 场景 3 |
| SC-019 | 设备信息自动采集率 | ≥ 95%，人工补录降低 ≥ 80% | 场景 17 |
| SC-020 | AI 排障命中率 | ≥ 70% | 场景 18.1 |
| SC-021 | 设备增强维度覆盖率 | 100% | 场景 12 |
| SC-022 | CRM 同步延迟 | ≤ 5 分钟 | 场景 13.1 |
| SC-023 | ITR 闭环率 / RMA 调用率 / 归档率 | ≥ 95% / 100% / 100% | 场景 14 |
| SC-024 | 售前临时授权自动获取率 | 100%，等待时间 0 | 场景 9.4 |
| SC-025 | 跨系统集成同步成功率 | ≥ 99%，PMS 刷新及时率 100% | 场景 22 |
| SC-026 | 割接闭环率 / 操作单自动生成率 | ≥ 95% / 100% | 场景 8 |
| SC-027 | LDAP/AD 认证覆盖率 / 越权拦截率 | 100% / 100% | 场景 20 |
| SC-028 | 乐观锁检测 / 字段级合并 | 100% / ≥ 95% | 场景 25 |
| SC-029 | 系统可用性 | ≥ 99.9% | 场景 24.3 |

接口性能通用目标（[plan.md Performance Goals](./plan.md)）：
- 非报表接口 P95 ≤ 500ms
- 报表接口 P95 ≤ 2 秒
- 1000 并发用户无 degradation

---

## 5. 自动化执行建议

1. **API 契约测试**：使用 Pact 或 Spring Cloud Contract，针对 [rest-api.md](./contracts/rest-api.md) 各端点生成契约测试，覆盖状态码 `200/201/204/400/401/403/404/409/412/422/429/500`。
2. **E2E 测试**：Playwright 覆盖 PC Web 关键路径（场景 1/2/3/8/20），移动端 H5 使用 Appium 或 Playwright Mobile 预览。
3. **性能压测**：JMeter 脚本 `scripts/perf/*.jmx`，1000 并发压测场景 2.1（统计卡片）、场景 21.1（项目进度汇总表），目标 P95 达标。
4. **Mock 验证**：所有 mock 服务启动后执行 `scripts/mock/verify-mocks.sh`，校验 mock 端点可访问。
5. **覆盖率**：后端 JaCoCo ≥ 80%，前端 Istanbul/c8 ≥ 70%（[plan.md Testing](./plan.md)）。

---

## 6. 引用文档索引

| 引用目标 | 路径 | 用途 |
|---------|------|------|
| 特性规格 | [spec.md](./spec.md) | User Stories / FR / SC / 边界条件 |
| 实施计划 | [plan.md](./plan.md) | 技术栈 / 项目结构 / 性能目标 |
| 数据模型 | [data-model.md](./data-model.md) | 40 实体字段 / 状态机 / 关系映射 |
| REST API 契约 | [contracts/rest-api.md](./contracts/rest-api.md) | 25 业务域 API / 状态码 / 权限码 |
| 外部集成契约 | [contracts/external-integrations.md](./contracts/external-integrations.md) | 20 集成系统 / 多数据源 / 重试降级 |
| 事件契约 | [contracts/events.md](./contracts/events.md) | 35+ 事件主题 / 异步消息载荷 |

---

*文档结束*
