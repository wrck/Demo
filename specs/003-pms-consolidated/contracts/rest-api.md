# REST API 契约：PMS 项目管理系统

> **来源**: `spec.md`（003-pms-consolidated 分支）+ `data-model.md`
> **覆盖**: FR-001 ~ FR-169 全业务域
> **状态**: Draft
> **最后更新**: 2026-07-10
> **基路径**: `/api/v1`

---

## 1. 通用约定

### 1.1 认证与权限头

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `Authorization` | 是 | `Bearer <JWT>`，通过 LDAP/AD 统一认证后颁发（FR-078） |
| `X-Tenant-Office` | 否 | 办事处标识，用于数据权限过滤（FR-079） |
| `X-Client-Type` | 否 | 客户端类型（`PC_WEB`/`ENGINEER_H5`/`AGENT_H5`/`CUSTOMER_H5`），用于终端适配（FR-089~FR-092） |
| `X-Trace-Id` | 否 | 链路追踪 ID，未提供时由网关生成 |
| `If-Match` | 条件 | 乐观锁版本号，写操作时传递 `version`（FR-026、VAL-037） |

**认证模型**（FR-078、FR-079）：
- 认证入口：LDAP/AD 统一认证，CAS 作为老系统兼容（矛盾 3 裁决采用 LDAP/AD）
- 权限模型：RBAC 功能权限 + 数据权限（按"办事处/项目归属"维度过滤）
- 数据权限范围：`全部` / `办事处` / `项目归属` / `本人`
- 钉钉仅用于审批与任务待办推送，非认证入口（VAL-047）

### 1.2 通用请求参数（分页/排序/筛选）

适用于所有列表型 `GET` 接口：

| 参数 | 位置 | 类型 | 默认 | 说明 |
|------|------|------|------|------|
| `page` | query | int | 1 | 页码，从 1 开始 |
| `pageSize` | query | int | 20 | 每页条数，最大 100 |
| `sort` | query | string | `created_at:desc` | 排序字段，格式 `field:asc\|desc`，多字段逗号分隔 |
| `keyword` | query | string | - | 关键词模糊搜索（按业务域定义搜索字段） |
| `filters` | query | string | - | 筛选条件 JSON，如 `{"status_code":"40","office_id":12}` |
| `include` | query | string | - | 关联资源展开，如 `members,productList` |

### 1.3 通用响应格式

**成功响应**（单资源）：

```json
{
  "code": 0,
  "message": "success",
  "data": { "id": 1, "...": "..." },
  "traceId": "abc123"
}
```

**列表响应**（分页）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ { "id": 1 } ],
    "total": 128,
    "page": 1,
    "pageSize": 20,
    "totalPages": 7
  },
  "traceId": "abc123"
}
```

### 1.4 通用状态码

| HTTP 状态码 | 含义 | 适用场景 |
|-------------|------|---------|
| 200 OK | 成功 | 所有查询、更新 |
| 201 Created | 创建成功 | POST 创建资源 |
| 204 No Content | 成功无返回 | DELETE 删除 |
| 400 Bad Request | 参数错误 | 校验失败（VAL-008~VAL-015） |
| 401 Unauthorized | 未认证 | JWT 缺失/失效 |
| 403 Forbidden | 无权限 | RBAC 校验失败、数据权限越界（VAL-034、VAL-035） |
| 404 Not Found | 资源不存在 | 查询无结果 |
| 409 Conflict | 并发冲突 | 乐观锁版本不一致（FR-026、VAL-037） |
| 412 Precondition Failed | 前置条件不满足 | 状态机非法流转（VAL-001）、文档锁定（VAL-030） |
| 422 Unprocessable Entity | 业务校验失败 | 业务规则违反（VAL-028~VAL-033） |
| 429 Too Many Requests | 限流 | 触发限流策略 |
| 500 Internal Server Error | 服务异常 | 未预期异常 |

### 1.5 通用错误体

```json
{
  "code": 40901,
  "message": "乐观锁版本冲突",
  "data": {
    "conflictFields": ["project_name", "status_code"],
    "currentVersion": 5,
    "yourVersion": 3
  },
  "traceId": "abc123"
}
```

---

## 2. 项目跟踪业务域（FR-016 ~ FR-024）

> 项目总体跟踪页面入口，8 阶段统计卡片与单项目跟踪（来源: 001）

### 2.1 项目总体跟踪

#### 2.1.1 获取项目阶段统计卡片

- **方法**: `GET`
- **路径**: `/api/v1/projects/tracking/phase-stats`
- **权限**: `project:tracking:view`（交付管理人员/服务经理/项目经理）
- **请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `office_id` | long | 否 | 办事处过滤 |
| `project_type` | string | 否 | 项目类型过滤 |

- **响应**:

```json
{
  "code": 0,
  "data": {
    "phases": [
      { "phase": "ALL", "count": 156, "clickable": true },
      { "phase": "NOT_STARTED", "count": 12, "clickable": true },
      { "phase": "PRE_CONSTRUCTION", "count": 23, "clickable": true },
      { "phase": "WRITING_IMPL_PLAN", "count": 18, "clickable": true },
      { "phase": "MAKING_CONSTRUCTION_PLAN", "count": 25, "clickable": true },
      { "phase": "IMPLEMENTATION_DEPLOYMENT", "count": 41, "clickable": true },
      { "phase": "ACCEPTANCE_HANDOVER", "count": 15, "clickable": true },
      { "phase": "OVERDUE", "count": 22, "clickable": true, "highlight": "RED" }
    ]
  }
}
```
- **关联 FR**: FR-016、FR-018、VAL-039
- **状态码**: 200, 401, 403

#### 2.1.2 获取阶段项目列表（卡片点击弹窗）

- **方法**: `GET`
- **路径**: `/api/v1/projects/tracking/by-phase/{phase}`
- **权限**: `project:tracking:view`
- **路径参数**: `phase` ∈ `{NOT_STARTED, PRE_CONSTRUCTION, WRITING_IMPL_PLAN, MAKING_CONSTRUCTION_PLAN, IMPLEMENTATION_DEPLOYMENT, ACCEPTANCE_HANDOVER, OVERDUE}`
- **请求参数**: 通用分页参数 + `office_id`
- **响应**: 项目列表（含 FR-017 字段：办事处、项目名称、合同号、项目级别、用户单位、用户服务等级、项目阶段、项目经理）
- **关联 FR**: FR-016、FR-017

#### 2.1.3 获取项目具体情况表

- **方法**: `GET`
- **路径**: `/api/v1/projects/tracking/details`
- **权限**: `project:tracking:view`
- **请求参数**: 通用分页/排序/筛选 + 以下业务筛选：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phase` | string | 否 | 交付子阶段 |
| `is_overdue` | boolean | 否 | 是否超期（FR-018） |
| `office_id` | long | 否 | 办事处 |
| `project_level` | string | 否 | A/B/C |
| `delivery_status` | string | 否 | 未发货/部分发货/已发货 |

- **响应字段**: 办事处、项目名称、合同号、项目级别、用户单位、用户服务等级、项目阶段（超期标红 `is_overdue=true`）、项目经理、`operation_url`
- **关联 FR**: FR-017、FR-018、VAL-039

### 2.2 单项目跟踪页

#### 2.2.1 获取单项目跟踪视图

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/tracking`
- **权限**: `project:view`（按数据权限过滤）
- **响应**:

```json
{
  "code": 0,
  "data": {
    "basicInfo": { "..." },
    "nav": [
      { "key": "basic", "label": "基本信息" },
      { "key": "pre_construction", "label": "工前准备" },
      { "key": "construction_plan", "label": "制定施工计划" },
      { "key": "impl_plan", "label": "实施方案" },
      { "key": "deployment", "label": "实施部署" },
      { "key": "acceptance", "label": "验收交维" }
    ],
    "currentPhase": "IMPLEMENTATION_DEPLOYMENT",
    "isOverdue": false
  }
}
```
- **关联 FR**: FR-019

#### 2.2.2 获取项目基本信息

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/basic-info`
- **权限**: `project:view`
- **响应字段**（FR-020）：项目名称、合同号、办事处、销售、项目阶段、发货状态、所属行业、项目级别（自动判断）、服务经理（自动指派）、项目经理（手动指派）、下单代理商、实施方式、用户联系人姓名、电话
- **关联 FR**: FR-020

#### 2.2.3 获取产品信息清单

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/product-lists`
- **权限**: `project:view`
- **响应字段**（FR-021）：产品编码、产品型号、产品描述、项目数量、发货数量、未发货数量、序列号（支持点击跳转 `/api/v1/device-serials/{serialId}`）
- **关联 FR**: FR-021

#### 2.2.4 获取团队成员

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/team-members`
- **权限**: `project:view`
- **响应字段**（FR-022）：项目经理、服务经理、销售代表、团队成员、用户主联系人的姓名、联系方式、备注
- **关联 FR**: FR-022

---

## 3. 项目管理核心生命周期业务域（FR-001 ~ FR-015、FR-025、FR-026）

### 3.1 项目 CRUD 与状态机

#### 3.1.1 创建项目

- **方法**: `POST`
- **路径**: `/api/v1/projects`
- **权限**: `project:create`
- **请求体**:

```json
{
  "contract_no": "HT20260701001",
  "project_name": "XX 银行核心网络改造项目",
  "project_type": "DIRECT_SIGN",
  "scenario_template_id": 1,
  "office_id": 12,
  "sales_person": "张三",
  "industry": "金融",
  "execution_mode": "SELF",
  "user_id": 100,
  "end_user_id": 101,
  "planned_start_date": "2026-07-15",
  "planned_end_date": "2026-12-31"
}
```
- **响应**: 201，返回 `project_no`（系统生成）、`status_code=30`、`project_level`（自动判断）、`service_manager_id`（自动指派）
- **校验**: VAL-008（project_no/project_name/status_code/project_type 必填）、VAL-016（project_no 唯一）
- **关联 FR**: FR-001、FR-020、SC-001（3 分钟内完成创建）

#### 3.1.2 查询项目列表

- **方法**: `GET`
- **路径**: `/api/v1/projects`
- **权限**: `project:view`（按数据权限过滤：PM 仅见自己项目，交付管理人员见全局）
- **请求参数**: 通用分页 + 业务筛选（`status_code`、`delivery_phase`、`office_id`、`project_manager_id`、`service_manager_id`、`is_overdue`、`project_type`、`scenario_template_id`）
- **关联 FR**: FR-002、FR-079

#### 3.1.3 获取项目详情

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}`
- **权限**: `project:view`
- **关联 FR**: FR-020

#### 3.1.4 更新项目

- **方法**: `PUT`
- **路径**: `/api/v1/projects/{projectId}`
- **权限**: `project:edit`
- **请求头**: `If-Match: <version>`（乐观锁 FR-026）
- **响应**: 409 Conflict（版本冲突时返回冲突字段，支持字段级合并）
- **关联 FR**: FR-026、VAL-037

#### 3.1.5 项目状态流转

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/transitions`
- **权限**: `project:transition`（按状态码流转分配不同角色权限）
- **请求体**:

```json
{
  "target_status": "31",
  "service_manager_id": 200,
  "remark": "指派服务经理"
}
```
- **校验**: VAL-001（状态机 30→31→32→40→100）、VAL-002（终态 20 仅从 30/31 流转）、VAL-003（回退 36/38/42 需记录日志+邮件通知）、VAL-004（交付子阶段回退需审批）、VAL-005（主项目闭环需子项目全部闭环）
- **响应**: 412 Precondition Failed（非法流转）
- **关联 FR**: FR-002、FR-003、FR-025

#### 3.1.6 标记不予跟踪

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/terminate`
- **权限**: `project:terminate`
- **校验**: VAL-002（仅 30/31 状态可流转至 20）
- **关联 FR**: FR-002

### 3.2 项目成员管理（FR-004）

#### 3.2.1 获取项目成员列表

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/members`
- **权限**: `project:view`

#### 3.2.2 添加/更新项目成员

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/members`
- **权限**: `project:member:manage`
- **请求体**:

```json
{
  "user_id": 100,
  "role_type": "PM",
  "install_address": "北京市XX机房",
  "impl_status": "IN_PROGRESS",
  "remark": "..."
}
```

#### 3.2.3 批量变更项目成员

- **方法**: `PUT`
- **路径**: `/api/v1/projects/{projectId}/members/batch`
- **权限**: `project:member:manage`
- **请求体**: `{ "members": [ { "..." } ] }`
- **约束**: SC-006（支持 100+ 条并发）；并发冲突提示刷新重试
- **关联 FR**: FR-004

### 3.3 项目合同管理（FR-005）

#### 3.3.1 合同合并

- **方法**: `POST`
- **路径**: `/api/v1/contracts/merge`
- **权限**: `contract:merge`
- **请求体**: `{ "contract_ids": [1, 2], "target_contract_no": "HT-NEW-001" }`
- **校验**: VAL-036（校验设备清单与合同关联一致性）
- **关联 FR**: FR-005

#### 3.3.2 合同拆分

- **方法**: `POST`
- **路径**: `/api/v1/contracts/{contractId}/split`
- **权限**: `contract:split`
- **校验**: VAL-036

### 3.4 项目组管理（FR-006）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/project-groups`
- **关联 FR**: FR-006

### 3.5 项目相关方管理（FR-007）

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/projects/{projectId}/stakeholders`
- **关联 FR**: FR-007

### 3.6 项目产品线管理（FR-009）

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/projects/{projectId}/product-lines`
- **关联 FR**: FR-009

### 3.7 项目批量导入（FR-010）

#### 3.7.1 批量导入项目

- **方法**: `POST`
- **路径**: `/api/v1/projects/import`
- **权限**: `project:import`
- **请求**: `multipart/form-data`，字段 `file`（Excel）
- **约束**: SC-008（1000+ 行，失败行精确定位）、VAL-044
- **响应**:

```json
{
  "code": 0,
  "data": {
    "total": 1000,
    "success": 980,
    "failed": 20,
    "failures": [
      { "row": 15, "reason": "合同号重复" }
    ]
  }
}
```
- **关联 FR**: FR-010

### 3.8 设备发货信息查询（FR-012、FR-013）

#### 3.8.1 查询设备发货信息

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/shipments`
- **权限**: `project:view`
- **关联 FR**: FR-012

#### 3.8.2 查询/更新设备软件版本

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/device-serials/{serialId}/software-version`
- **关联 FR**: FR-013

### 3.9 项目设备转移（FR-014）

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/devices/transfer`
- **权限**: `project:device:transfer`
- **请求体**: `{ "serial_ids": [1, 2], "target_project_id": 200 }`
- **关联 FR**: FR-014

### 3.10 现场验货单（FR-011）

#### 3.10.1 导出现场验货单

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/inspection-sheets/export`
- **权限**: `project:export`
- **响应**: Excel 文件流
- **关联 FR**: FR-011

#### 3.10.2 导入现场验货单

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/inspection-sheets/import`

### 3.11 主子项目管理（FR-027 ~ FR-033）

#### 3.11.1 拆分子项目

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/sub-projects`
- **权限**: `project:split`
- **校验**: VAL-005（主项目闭环需子项目全部闭环）
- **关联 FR**: FR-029、FR-032

#### 3.11.2 获取主项目子项目汇总

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/sub-projects/summary`
- **权限**: `project:view`（主项目管理员可查看全部子项目）
- **关联 FR**: FR-030、FR-031、FR-033

#### 3.11.3 业务场景模板管理

- **方法**: `GET` / `POST` / `PUT`
- **路径**: `/api/v1/business-scenario-templates`
- **权限**: 管理员可派生/调整，支持版本管理
- **关联 FR**: FR-027

---

## 4. 工前准备业务域（FR-113 ~ FR-117）

### 4.1 客户联系人管理

#### 4.1.1 获取客户联系人列表

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/user-contacts`
- **权限**: `project:view`
- **响应字段**（FR-113）：联系人属性（主/其他）、姓名、电话、客户单位名称、服务等级、部门、职务
- **关联 FR**: FR-113

#### 4.1.2 创建客户联系人

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/user-contacts`
- **权限**: `project:edit`
- **请求体**:

```json
{
  "user_id": 100,
  "contact_attr": "PRIMARY",
  "contact_name": "李四",
  "phone": "13800138000",
  "company_name": "XX 银行",
  "service_level": "A",
  "department": "信息中心",
  "position": "主任"
}
```
- **说明**: 主联系人显示在项目页面，其他联系人仅在该页面展示；客户基础信息与默认联系人由 CRM 带入
- **关联 FR**: FR-113

#### 4.1.3 更新/删除/失效客户联系人

- **方法**: `PUT` / `DELETE` / `POST`（失效）
- **路径**: `/api/v1/user-contacts/{contactId}`
- **权限**: `project:edit`
- **关联 FR**: FR-113

### 4.2 工勘记录管理

#### 4.2.1 获取/保存工勘记录

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/projects/{projectId}/site-survey`
- **权限**: `project:edit`
- **请求体**（FR-114）:

```json
{
  "project_end_date": "2026-12-31",
  "power_confirmed": true,
  "power_mode": "双路市电",
  "port_type": "万兆光口",
  "rack_resource": "A1-A12",
  "fiber_cable": "...",
  "optical_module": "...",
  "original_optical_module": "...",
  "need_oem_install": true,
  "need_outsource": true,
  "need_rail_tray": true,
  "material_compliance": false,
  "exchange_serials": ["SN001", "SN002"]
}
```
- **校验**: VAL-013（project_end_date、power_confirmed、need_oem_install 必填）
- **关联 FR**: FR-114、FR-115

#### 4.2.2 发起外包流程

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/site-survey/outsource`
- **权限**: `project:edit`
- **触发条件**: `need_oem_install=true` 且 `need_outsource=true`（FR-115）
- **关联 FR**: FR-115

#### 4.2.3 物料领用/外采/换货

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/site-survey/material-pickup` / `/material-purchase` / `/exchange`
- **触发条件**: 工勘页面相应选项为"是"
- **关联 FR**: FR-115

### 4.3 需求分析管理

#### 4.3.1 获取/保存需求分析

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/projects/{projectId}/requirement`
- **权限**: `project:edit`
- **请求体**（FR-116）:

```json
{
  "project_background": "...",
  "project_objective": "...",
  "topology_file_url": "...",
  "transmission_status": ["IPv6", "Jumbo"],
  "traffic_new": "...",
  "traffic_concurrent": "...",
  "traffic_throughput": "...",
  "mgmt_ip": "192.168.1.0/24",
  "public_ip": "...",
  "redundancy_req": "...",
  "protection_req": "...",
  "ops_mgmt_req": ["带内", "SNMP", "UMC"],
  "business_running_json": [{ "...": "..." }]
}
```
- **校验**: VAL-014（project_background、project_objective 必填）
- **关联 FR**: FR-116

#### 4.3.2 生成并下载工程交底书

- **方法**: `POST`（生成） / `GET`（下载）
- **路径**: `/api/v1/projects/{projectId}/requirement/brief-book` / `/download`
- **权限**: `project:edit`
- **说明**: 根据发货设备情况自动生成
- **关联 FR**: FR-117

---

## 5. 施工计划业务域（FR-118 ~ FR-120）

### 5.1 获取/保存施工计划

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/projects/{projectId}/construction-plan`
- **权限**: `project:edit`（仅服务经理可修改，FR-120）
- **请求体**（FR-118）:

```json
{
  "arrival_sign_date": "2026-08-01",
  "hardware_impl_date": "2026-08-05",
  "device_config_date": "2026-08-10",
  "business_debug_date": "2026-08-15",
  "cutover_online_date": "2026-09-01",
  "first_acceptance_date": "2026-09-15",
  "final_acceptance_date": "2026-10-01"
}
```
- **说明**: `contract_accept_date`（PMS 导入）与 `duration_requirement`（工前准备带入）只读不可调整
- **校验**: VAL-009（直签项目 arrival_sign_date、first_acceptance_date、final_acceptance_date 必填）、VAL-030（已提交审核锁定不可编辑）
- **关联 FR**: FR-118

### 5.2 工期紧张提醒

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/construction-plan/reminder`
- **权限**: `project:view`
- **响应**:

```json
{
  "code": 0,
  "data": {
    "duration_warning": "当前项目工期紧张,请详细落实好工期计划,并与客户确认",
    "delivery_warning": "请与销售确认发货时间",
    "show_crm_reminder_button": true
  }
}
```
- **触发条件**: 工期要求离当前时间不足 3 个月（VAL-038）；未发货/部分发货时显示 CRM 发货提醒按钮
- **关联 FR**: FR-119

### 5.3 提交施工计划审核

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/construction-plan/submit-approval`
- **权限**: `project:edit`
- **说明**: 推送至服务经理钉钉审批（FR-120），审核状态：草稿/待审核/已通过/已驳回
- **关联 FR**: FR-120

### 5.4 审核施工计划

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/construction-plan/approve`
- **权限**: `service_manager`（仅服务经理）
- **请求体**: `{ "approved": true, "remark": "..." }`
- **关联 FR**: FR-120

---

## 6. 实施方案业务域（FR-121 ~ FR-125）

### 6.1 获取/保存实施方案

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/projects/{projectId}/implementation-plan`
- **权限**: `project:edit`
- **请求体**（FR-122~FR-124）:

```json
{
  "has_customer_plan": true,
  "customer_plan_file": "...",
  "overview_json": { "...": "..." },
  "current_network_json": { "...": "..." },
  "design_json": {
    "deploy_location": "...",
    "interface_interconnect": "...",
    "ip_vlan": "...",
    "software_version": "..."
  },
  "config_script": "...",
  "impl_steps": "...",
  "other_plans_json": {
    "quality_assurance": "...",
    "risk_control": "...",
    "ops_delivery": "...",
    "doc_archive": "..."
  },
  "training_json": { "...": "..." },
  "after_sales_json": { "...": "..." }
}
```
- **说明**: 总体方案设计数据同步更新至序列号模块（FR-123）；引用前序数据（FR-122）
- **校验**: VAL-030（已提交审核锁定）
- **关联 FR**: FR-121、FR-122、FR-123、FR-124

### 6.2 上传客户方案文件并自动填充

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/implementation-plan/upload-customer-plan`
- **权限**: `project:edit`
- **请求**: `multipart/form-data`
- **说明**: 上传后"提交系统判断"自动填充至下方表单（FR-121）
- **关联 FR**: FR-121

### 6.3 生成实施方案

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/implementation-plan/generate`
- **权限**: `project:edit`
- **说明**: 系统自动生成方案
- **关联 FR**: FR-125

### 6.4 下载实施方案

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/implementation-plan/download`
- **权限**: `project:view`
- **响应**: 文件流
- **关联 FR**: FR-125

### 6.5 提交实施方案审核

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/implementation-plan/submit-approval`
- **权限**: `project:edit`
- **说明**: 服务经理审核；重大项目提交总部复核
- **关联 FR**: FR-125

---

## 7. 实施部署业务域（FR-126 ~ FR-130）

### 7.1 到货签收（FR-126）

#### 7.1.1 上传到货签收单

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/deployment/arrival-sign/upload`
- **权限**: `project:deployment:edit`
- **请求**: `multipart/form-data`
- **说明**: 文件上传成功后可在交付件页面查看下载
- **关联 FR**: FR-126

### 7.2 硬件安装（FR-127）

#### 7.2.1 获取设备安装清单

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/deployment/hardware-install`
- **权限**: `project:view`
- **响应字段**: 序列号、产品名称（PMS 导入）、安装位置（需求分析自动带入可修改）
- **关联 FR**: FR-127

#### 7.2.2 更新设备安装位置

- **方法**: `PUT`
- **路径**: `/api/v1/projects/{projectId}/deployment/hardware-install/{serialId}`
- **权限**: `project:deployment:edit`
- **请求体**: `{ "install_location": "A机柜12U" }`

#### 7.2.3 上传安装照片

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/deployment/hardware-install/{serialId}/photos`
- **权限**: `project:deployment:edit`
- **说明**: 自动添加水印（时间+GPS+上传人，VAL-049）
- **关联 FR**: FR-127、FR-094

### 7.3 配置调试（FR-128）

#### 7.3.1 上传配置 Log 文件

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/deployment/config-logs`
- **权限**: `project:deployment:edit`
- **请求**: `multipart/form-data`，字段 `file`、`device_serial_id`
- **约束**: VAL-043（大文件断点续传）、SC-009（100MB+）
- **关联 FR**: FR-128

### 7.4 业务联调（FR-129）

#### 7.4.1 保存设备连接信息

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/deployment/business-debug/connections`
- **权限**: `project:deployment:edit`
- **请求体**:

```json
{
  "device_name": "Core-SW-01",
  "ip": "192.168.1.1",
  "username": "admin",
  "password": "***",
  "login_method": "SSH",
  "port": 22,
  "baud_rate": 9600
}
```
- **关联 FR**: FR-129

#### 7.4.2 一键收集配置信息

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/deployment/business-debug/collect-config`
- **权限**: `project:deployment:edit`
- **说明**: 采集设备配置信息，更新设备清单（设备型号、序列号、运行业务描述）
- **关联 FR**: FR-129

### 7.5 割接上线（FR-130）

#### 7.5.1 检查前期流程完成状态

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/deployment/cutover/readiness`
- **权限**: `project:view`
- **响应**: `{ "ready": false, "pending_steps": ["硬件安装", "配置调试"] }`
- **校验**: VAL-031（前期流程未完成时按钮失效）
- **关联 FR**: FR-130

#### 7.5.2 发起割接上线流程

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/deployment/cutover/initiate`
- **权限**: `project:deployment:edit`
- **说明**: 全部完成后可发起割接上线流程，进入割接管理平台
- **关联 FR**: FR-130、FR-135

---

## 8. 割接管理业务域（FR-135 ~ FR-140）

### 8.1 割接单管理

#### 8.1.1 创建割接单

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders`
- **权限**: `cutover:create`
- **请求体**:

```json
{
  "project_id": 1,
  "cutover_source": "ENGINEERING_DELIVERY",
  "cutover_type": "FRIENDLY_VENDOR_REPLACE",
  "cutover_object": "...",
  "cutover_network": "..."
}
```
- **校验**: VAL-012（cutover_source、cutover_type 必填）
- **说明**: 携带 PMS 实施信息与客户资产库/RMA/ITR 信息
- **关联 FR**: FR-135

#### 8.1.2 查询割接单列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/cutover-orders` / `/api/v1/cutover-orders/{cutoverId}`
- **权限**: `cutover:view`
- **请求参数**: 通用分页 + `cutover_source`、`cutover_type`、`cutover_level`、`status`

#### 8.1.3 割接等级评定

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/assess-level`
- **权限**: `cutover:assess`
- **说明**: 依据割接等级评定办法自动评定 A/B 类
- **响应**: `{ "level": "A", "auto": true }`
- **关联 FR**: FR-136

#### 8.1.4 调整割接等级

- **方法**: `PUT`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/level`
- **权限**: `cutover:assess`
- **请求体**: `{ "level": "B", "remark": "边界调整" }`
- **关联 FR**: FR-136

### 8.2 割接审批（FR-136）

#### 8.2.1 发起割接审批

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/approvals`
- **权限**: `cutover:approve:initiate`
- **说明**: A 类需服务经理+二线+研发；B 类需服务经理+二线；外部客户割接需上传客户审批确认单
- **关联 FR**: FR-136

#### 8.2.2 审批割接

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/approvals/{approvalId}`
- **权限**: 按审批节点角色（service_manager/second_line/rd）
- **请求体**: `{ "approved": true, "remark": "..." }`

#### 8.2.3 上传客户审批确认单

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/customer-approval`
- **权限**: `cutover:approve:initiate`
- **请求**: `multipart/form-data`
- **关联 FR**: FR-136

### 8.3 割接方案与操作单（FR-137、FR-138）

#### 8.3.1 生成割接方案

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/scheme/generate`
- **权限**: `cutover:scheme:generate`
- **说明**: 基于模板库生成，通过 7 类工具集完成风险确认与配置一致性确认
- **关联 FR**: FR-137

#### 8.3.2 生成操作单与 checklist

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/ops-sheets/generate`
- **权限**: `cutover:scheme:generate`
- **说明**: 自动生成割接准备/割接/割接后/回退操作单及 checklist
- **响应**:

```json
{
  "code": 0,
  "data": {
    "prep_ops_sheet": "...",
    "cutover_ops_sheet": "...",
    "post_ops_sheet": "...",
    "rollback_ops_sheet": "...",
    "checklist_json": { "...": "..." }
  }
}
```
- **关联 FR**: FR-138

### 8.4 割接资源管理（FR-139）

#### 8.4.1 割接资源 CRUD

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/resources`
- **权限**: `cutover:resource:manage`
- **资源类型**: 人员（操作人/复核人/验证人/保障人）、备件
- **关联 FR**: FR-139

#### 8.4.2 关联备件申请

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/spare-parts/apply`
- **权限**: `cutover:resource:manage`
- **校验**: VAL-032（备件库存不足阻断割接发起）
- **说明**: 自动关联 SPMS 备件申请流程
- **关联 FR**: FR-139、FR-100

### 8.5 割接执行与闭环（FR-139、FR-140）

#### 8.5.1 采集割接后设备信息

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/post-cutover/device-info`
- **权限**: `cutover:execute`
- **说明**: 采集三大日志、版本/热补丁/license 备份、整机配置文件、tech-support 一键收集
- **关联 FR**: FR-139

#### 8.5.2 提交承诺书与 checklist 核验

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/commitment`
- **权限**: `cutover:execute`
- **请求**: 上传《机房割接实施承诺书》+ checklist 签字
- **关联 FR**: FR-139

#### 8.5.3 割接闭环归档

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/close`
- **权限**: `cutover:close`
- **校验**: VAL-033（备件退回完成才能闭环）
- **说明**: 闭环归档含 show tech-support 备份、文档更新《客户技术档案》、PMS 刷新版本/CPLD/conboot/备件序列号；推送闭环通知至干系人
- **关联 FR**: FR-140

#### 8.5.4 割接失败提交问题工单

- **方法**: `POST`
- **路径**: `/api/v1/cutover-orders/{cutoverId}/failure-ticket`
- **权限**: `cutover:execute`
- **说明**: 提交问题工单至 ITR，关联割接单与设备
- **关联 FR**: FR-140

---

## 9. 售前管理业务域（FR-034 ~ FR-039）

### 9.1 售前测试项目 CRUD

#### 9.1.1 创建售前测试申请

- **方法**: `POST`
- **路径**: `/api/v1/presales-projects`
- **权限**: `presales:create`
- **请求体**:

```json
{
  "applicant_id": 100,
  "product_line_json": [{ "...": "..." }],
  "rma_info_json": { "...": "..." },
  "deliverable_json": [{ "...": "..." }]
}
```
- **响应**: 201，`status_code=10`
- **校验**: VAL-025（presales_no 唯一）
- **关联 FR**: FR-034、FR-035

#### 9.1.2 查询售前测试列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/presales-projects` / `/api/v1/presales-projects/{presalesId}`
- **权限**: `presales:view`
- **请求参数**: 通用分页 + `status_code`、`sm_id`、`pm_id`

#### 9.1.3 售前状态流转

- **方法**: `POST`
- **路径**: `/api/v1/presales-projects/{presalesId}/transitions`
- **权限**: 按状态流转分配（SM 审批指定 PM、PM 跟踪、EM 回访）
- **校验**: VAL-006（10→31→32→33→100，终止 20）
- **关联 FR**: FR-036

### 9.2 售前耗时统计（FR-037）

#### 9.2.1 获取售前各阶段耗时

- **方法**: `GET`
- **路径**: `/api/v1/presales-projects/{presalesId}/duration`
- **权限**: `presales:view`
- **响应**: `duration_phase1`、`duration_phase2`、`duration_phase3`、`duration_total`
- **关联 FR**: FR-037

### 9.3 售前回访问卷（FR-038）

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/presales-projects/{presalesId}/callbacks`
- **关联 FR**: FR-038

### 9.4 售前发货与借转销（FR-038）

#### 9.4.1 查询发货信息/借转销/核销

- **方法**: `GET`
- **路径**: `/api/v1/presales-projects/{presalesId}/shipments` / `/loan-sales` / `/writeoff`
- **关联 FR**: FR-038

### 9.5 临时授权管理（FR-039）

#### 9.5.1 自动获取首次临时授权

- **方法**: `POST`
- **路径**: `/api/v1/presales-projects/{presalesId}/temporary-licenses/auto-acquire`
- **权限**: `presales:license:manage`
- **说明**: 设备发货后自动触发；支持重试
- **校验**: VAL-050（下发失败告警并重试）
- **关联 FR**: FR-039、SC-024

#### 9.5.2 查询临时授权列表

- **方法**: `GET`
- **路径**: `/api/v1/presales-projects/{presalesId}/temporary-licenses`
- **关联 FR**: FR-039

---

## 10. 转包管理业务域（FR-040 ~ FR-048）

### 10.1 转包项目 CRUD

#### 10.1.1 创建转包项目

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts`
- **权限**: `subcontract:create`
- **请求体**:

```json
{
  "project_id": 1,
  "facilitator_id": 10,
  "device_list_json": [{ "...": "..." }],
  "price_json": { "...": "..." },
  "payment_json": { "...": "..." }
}
```
- **响应**: 201，`status=草稿`
- **校验**: VAL-015（subcontract_no、project_id、facilitator_id 必填）、VAL-026（subcontract_no 唯一）
- **关联 FR**: FR-040、FR-042

#### 10.1.2 查询转包列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/subcontracts` / `/api/v1/subcontracts/{subcontractId}`
- **权限**: `subcontract:view`
- **请求参数**: 通用分页 + `status`、`facilitator_id`、`project_id`

### 10.2 转包审批（FR-041）

#### 10.2.1 发起转包审批

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/approvals`
- **权限**: `subcontract:approve:initiate`
- **说明**: 多级审批（受益部门服务经理→通用→工程管理部→主任→合同执行）
- **校验**: VAL-028（完成全部节点方可进入合同执行）
- **关联 FR**: FR-041、SC-004

#### 10.2.2 审批转包

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/approvals/{approvalId}`
- **权限**: 按审批节点角色

### 10.3 转包合同执行与 D365 集成（FR-046、FR-048）

#### 10.3.1 推送采购订单至 D365

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/d365/push-po`
- **权限**: `subcontract:d365:push`
- **说明**: OAuth2 认证，Token 带缓存；失败重试并记录日志
- **校验**: VAL-045、SC-005（成功率 ≥99%）
- **关联 FR**: FR-046、FR-048

#### 10.3.2 推送采购收货

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/d365/push-receipt`
- **关联 FR**: FR-046

### 10.4 发票 OCR 识别（FR-047）

#### 10.4.1 发票 OCR 识别验证

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/invoices/ocr`
- **权限**: `subcontract:invoice:ocr`
- **请求**: `multipart/form-data`
- **关联 FR**: FR-047、FR-106

### 10.5 转包付款审批（FR-043）

#### 10.5.1 提交付款申请

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/payments`
- **权限**: `subcontract:payment:apply`
- **关联 FR**: FR-043

#### 10.5.2 付款审批

- **方法**: `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/payments/{paymentId}/approve`

### 10.6 转包回访（FR-044）

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/callbacks`
- **关联 FR**: FR-044

### 10.7 转包交付件（FR-045）

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/subcontracts/{subcontractId}/deliverables`
- **关联 FR**: FR-045

### 10.8 服务商管理（FR-042）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/facilitators`
- **权限**: `facilitator:manage`
- **校验**: VAL-027（facilitator_code 唯一）
- **关联 FR**: FR-042

---

## 11. 回访与闭环业务域（FR-049 ~ FR-053）

### 11.1 回访申请

#### 11.1.1 创建回访申请

- **方法**: `POST`
- **路径**: `/api/v1/callbacks`
- **权限**: `callback:create`（EM 人员）
- **请求体**:

```json
{
  "project_id": 1,
  "callback_type": "PROJECT",
  "applicant_id": 100
}
```
- **关联 FR**: FR-050

#### 11.1.2 查询回访列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/callbacks` / `/api/v1/callbacks/{callbackId}`
- **权限**: `callback:view`
- **请求参数**: 通用分页 + `status`、`callback_type`、`project_id`

### 11.2 回访审批（FR-050）

#### 11.2.1 审批回访

- **方法**: `POST`
- **路径**: `/api/v1/callbacks/{callbackId}/approve`
- **权限**: `callback:approve`
- **请求体**: `{ "approved": true, "remark": "..." }`
- **校验**: VAL-029（问卷未填写阻止审批通过）
- **关联 FR**: FR-050

#### 11.2.2 驳回回访

- **方法**: `POST`
- **路径**: `/api/v1/callbacks/{callbackId}/reject`
- **关联 FR**: FR-050

### 11.3 回访问卷（FR-051）

#### 11.3.1 获取/保存回访问卷

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/callbacks/{callbackId}/questionnaire`
- **权限**: `callback:edit`
- **请求体**:

```json
{
  "template_id": 1,
  "items": [
    { "question": "工程质量评分", "answer": "良好", "score": 80 },
    { "question": "产品质量评分", "answer": "优秀", "score": 100 }
  ]
}
```
- **说明**: 评分分档 100/80/60/40/0
- **关联 FR**: FR-051

#### 11.3.2 提交回访问卷

- **方法**: `POST`
- **路径**: `/api/v1/callbacks/{callbackId}/questionnaire/submit`
- **说明**: 计算总评分
- **关联 FR**: FR-051

### 11.4 项目闭环（FR-049、FR-052）

#### 11.4.1 发起项目闭环申请

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/closure/apply`
- **权限**: `project:closure:apply`
- **说明**: 通过工作流驱动多角色审批
- **校验**: VAL-005（主项目闭环需子项目全部闭环）
- **关联 FR**: FR-049、FR-052

#### 11.4.2 审批项目闭环

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/closure/approve`
- **权限**: `project:closure:approve`
- **说明**: 回访通过后闭环流程状态回到 10，项目可正式闭环
- **关联 FR**: FR-052

### 11.5 评价记录（FR-053）

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/callbacks/{callbackId}/evaluations`
- **关联 FR**: FR-053

---

## 12. 维保管理业务域（FR-054 ~ FR-058）

### 12.1 维护记录 CRUD（FR-054）

#### 12.1.1 创建维护记录

- **方法**: `POST`
- **路径**: `/api/v1/maintenances`
- **权限**: `maintenance:create`
- **请求体**:

```json
{
  "project_id": 1,
  "project_type": "10",
  "presales_id": null
}
```
- **说明**: project_type（10 售后/20 售前/30 非业务/40 自定义）关联对应项目主表
- **关联 FR**: FR-054

#### 12.1.2 查询维护记录列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/maintenances` / `/api/v1/maintenances/{maintenanceId}`
- **权限**: `maintenance:view`
- **请求参数**: 通用分页 + `project_type`、`project_id`

### 12.2 维护问卷（FR-055）

#### 12.2.1 获取/保存维护问卷

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/maintenances/{maintenanceId}/questionnaire`
- **权限**: `maintenance:edit`
- **说明**: 问卷结果头表 + 行表
- **关联 FR**: FR-055

### 12.3 维护交付件（FR-056）

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/maintenances/{maintenanceId}/deliverables`
- **关联 FR**: FR-056

### 12.4 服务交付统计（FR-057）

#### 12.4.1 获取服务交付统计

- **方法**: `GET`
- **路径**: `/api/v1/maintenances/{maintenanceId}/delivery-statistics`
- **权限**: `maintenance:view`
- **关联 FR**: FR-057

### 12.5 项目维保状态查询（FR-058）

#### 12.5.1 查询项目维保状态

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/warranty-state`
- **权限**: `project:view`
- **关联 FR**: FR-058

---

## 13. 技术公告业务域（FR-059 ~ FR-064）

### 13.1 技术公告 CRUD（FR-059）

#### 13.1.1 创建技术公告

- **方法**: `POST`
- **路径**: `/api/v1/probs`
- **权限**: `prob:create`（管理员）
- **请求体**:

```json
{
  "title": "XX 产品版本安全漏洞修复公告",
  "description": "...",
  "software_version_json": ["V5.0", "V5.1"]
}
```
- **响应**: 201，`status=草稿`
- **校验**: VAL-024（prob_no 唯一）、VAL-007（状态机）
- **关联 FR**: FR-059

#### 13.1.2 查询技术公告列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/probs` / `/api/v1/probs/{probId}`
- **权限**: `prob:view`
- **请求参数**: 通用分页 + `status`、`software_version`

### 13.2 技术公告审批（FR-059）

#### 13.2.1 提交技术公告审批

- **方法**: `POST`
- **路径**: `/api/v1/probs/{probId}/submit`
- **权限**: `prob:create`
- **说明**: 草稿→待确认
- **关联 FR**: FR-059

#### 13.2.2 审批技术公告

- **方法**: `POST`
- **路径**: `/api/v1/probs/{probId}/approve`
- **权限**: `prob:approve`（管理员）
- **请求体**: `{ "approved": true }` → 已确认；`{ "approved": false }` → 已拒绝
- **关联 FR**: FR-059

### 13.3 影响范围匹配（FR-060）

#### 13.3.1 匹配受影响项目

- **方法**: `POST`
- **路径**: `/api/v1/probs/{probId}/match-affected`
- **权限**: `prob:match`
- **说明**: 按软件版本影响范围匹配，检索受影响项目
- **响应**: `{ "affected_projects": [{ "..." }], "matched": true }`
- **校验**: VAL-040（匹配失败提示"无受影响项目"并允许手动指定）、SC-015（准确率 ≥95%）
- **关联 FR**: FR-060

#### 13.3.2 手动指定受影响项目

- **方法**: `POST`
- **路径**: `/api/v1/probs/{probId}/affected-projects`
- **权限**: `prob:match`
- **请求体**: `{ "project_ids": [1, 2] }`

### 13.4 修复任务（FR-061）

#### 13.4.1 发布修复任务

- **方法**: `POST`
- **路径**: `/api/v1/probs/{probId}/fix-tasks`
- **权限**: `prob:fixtask:publish`
- **说明**: 已确认→解决中
- **关联 FR**: FR-061

#### 13.4.2 更新修复进展

- **方法**: `PUT`
- **路径**: `/api/v1/fix-tasks/{fixTaskId}/progress`
- **权限**: `prob:fixtask:edit`
- **说明**: 记录流程过程与进展周报
- **关联 FR**: FR-061

#### 13.4.3 关闭修复任务

- **方法**: `POST`
- **路径**: `/api/v1/fix-tasks/{fixTaskId}/close`
- **关联 FR**: FR-061

### 13.5 技术公告阅读确认（FR-062）

#### 13.5.1 确认阅读技术公告

- **方法**: `POST`
- **路径**: `/api/v1/probs/{probId}/read-confirm`
- **权限**: 已登录用户
- **关联 FR**: FR-062

### 13.6 产品组件/型号管理（FR-063）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/product-components` / `/api/v1/product-models`
- **权限**: `prob:product:manage`
- **关联 FR**: FR-063

### 13.7 技术公告统计报表（FR-064）

#### 13.7.1 获取技术公告统计

- **方法**: `GET`
- **路径**: `/api/v1/probs/statistics`
- **权限**: `prob:view`
- **响应**: 图表可视化数据
- **关联 FR**: FR-064

---

## 14. 设备信息增强业务域（FR-150 ~ FR-156）

### 14.1 设备序列号 CRUD

#### 14.1.1 查询设备序列号列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/device-serials` / `/api/v1/device-serials/{serialId}`
- **权限**: `device:view`
- **请求参数**: 通用分页 + `project_id`、`product_code`、`serial_no`、`warranty_end`（维保到期）
- **响应字段**（FR-023）：序列号、产品编码、产品名称、安装位置、出厂软件/conboot/cpld 版本、官网版本、在网软件/conboot/cpld 版本、分支版本、受影响技术公告、维保时长、维保起止时间、续保次数、配置 Log 超链接
- **校验**: VAL-018（serial_no 唯一）
- **关联 FR**: FR-023、FR-155

### 14.2 配置 Log 管理（FR-024）

#### 14.2.1 获取配置 Log 列表

- **方法**: `GET`
- **路径**: `/api/v1/device-serials/{serialId}/config-logs`
- **权限**: `device:view`
- **响应字段**: Log 文件、上传人、上传时间
- **关联 FR**: FR-024

#### 14.2.2 上传配置 Log

- **方法**: `POST`
- **路径**: `/api/v1/device-serials/{serialId}/config-logs`
- **权限**: `device:edit`
- **约束**: VAL-043（断点续传）、SC-009
- **关联 FR**: FR-128、FR-144

### 14.3 设备信息增强管理

#### 14.3.1 获取设备增强信息

- **方法**: `GET`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement`
- **权限**: `device:view`
- **响应字段**: 配置历史、部署风险描述、冗余部署情况、运行业务档案、启用功能、接口对照表、网络拓扑（自动生成）
- **关联 FR**: FR-150

#### 14.3.2 更新部署风险/冗余情况

- **方法**: `PUT`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement/deploy-risk`
- **权限**: `device:edit`
- **关联 FR**: FR-150

#### 14.3.3 保存运行业务档案

- **方法**: `PUT`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement/business-archive`
- **权限**: `device:edit`
- **说明**: 运行业务与配置关联绑定，上传至设备与项目
- **关联 FR**: FR-150

#### 14.3.4 接口对照表

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement/interface-table`
- **权限**: `device:edit`
- **关联 FR**: FR-152

#### 14.3.5 自动生成网络拓扑

- **方法**: `POST`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement/generate-topology`
- **权限**: `device:edit`
- **说明**: 基于接口对照表自动生成（非图片，标注上下游与接口互联），同步至设备信息
- **关联 FR**: FR-153

### 14.4 启用功能自动回传（FR-151）

#### 14.4.1 回传启用功能

- **方法**: `POST`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement/enabled-functions`
- **权限**: `device:edit`（或服务平台回调）
- **说明**: 通过设备配置命令获取后自动回传
- **关联 FR**: FR-151

### 14.5 设备安装地址（FR-156）

#### 14.5.1 一码通获取定位

- **方法**: `GET`
- **路径**: `/api/v1/device-serials/{serialId}/location/one-code`
- **权限**: `device:edit`
- **关联 FR**: FR-156

#### 14.5.2 更新设备地址/照片

- **方法**: `PUT`
- **路径**: `/api/v1/device-serials/{serialId}/location`
- **权限**: `device:edit`
- **请求**: `multipart/form-data`（设备照片）
- **关联 FR**: FR-156

### 14.6 供应链信息同步（FR-154）

#### 14.6.1 供应链导入出厂信息

- **方法**: `POST`
- **路径**: `/api/v1/device-serials/supply-chain/import`
- **权限**: `device:import`（供应链系统回调）
- **说明**: 导入真实产品信息，自动匹配官网版本
- **关联 FR**: FR-154

---

## 15. 服务平台集成业务域（FR-141 ~ FR-144）

### 15.1 巡检任务管理（FR-142）

#### 15.1.1 创建巡检任务

- **方法**: `POST`
- **路径**: `/api/v1/inspection-tasks`
- **权限**: `inspection:create`
- **请求体**:

```json
{
  "device_serial_id": 1,
  "device_type": "FW",
  "target_ip": "192.168.1.1",
  "scenario_lib": "标准巡检"
}
```
- **关联 FR**: FR-142

#### 15.1.2 查询巡检任务列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/inspection-tasks` / `/api/v1/inspection-tasks/{taskId}`
- **权限**: `inspection:view`
- **请求参数**: 通用分页 + `device_serial_id`、`status`

#### 15.1.3 上传巡检 Log

- **方法**: `POST`
- **路径**: `/api/v1/inspection-tasks/{taskId}/logs`
- **权限**: `inspection:execute`
- **说明**: 同步至总部数据中心（UMC 环境）
- **关联 FR**: FR-142

#### 15.1.4 同步巡检报告至 PMS

- **方法**: `POST`
- **路径**: `/api/v1/inspection-tasks/{taskId}/sync-pms`
- **权限**: `inspection:sync`
- **说明**: 输出巡检报告并同步至 PMS
- **关联 FR**: FR-142

### 15.2 设备信息解析（FR-143）

#### 15.2.1 同步设备信息解析结果

- **方法**: `POST`
- **路径**: `/api/v1/device-serials/{serialId}/enhancement/sync-from-platform`
- **权限**: `device:sync`（服务平台回调）
- **请求体**:

```json
{
  "config_info": "...",
  "running_functions": "...",
  "deploy_risk_analysis": "..."
}
```
- **说明**: 解析结果同步至 PMS 设备序列号对应位置
- **关联 FR**: FR-143

### 15.3 CRT Log 自动采集（FR-144）

#### 15.3.1 接收客户端上传 CRT Log

- **方法**: `POST`
- **路径**: `/api/v1/device-serials/{serialId}/config-logs/crt-upload`
- **权限**: `device:sync`（客户端回调）
- **说明**: 客户端自动采集并完成前端数据初筛后上传；服务端识别解析、同步 PMS、数据自动回传
- **关联 FR**: FR-144

### 15.4 服务平台工具管理（FR-141）

#### 15.4.1 公共/私有工具管理

- **方法**: `GET` / `POST` / `PUT`
- **路径**: `/api/v1/service-platform/tools`
- **权限**: `service-platform:tool:manage`
- **说明**: 公共工具与私有工具（支持权限管理）
- **关联 FR**: FR-141

---

## 16. AI 排障业务域（FR-145 ~ FR-149）

### 16.1 AI 排障诊断

#### 16.1.1 提交排障请求

- **方法**: `POST`
- **路径**: `/api/v1/ai-troubleshooting/diagnose`
- **权限**: `ai:diagnose`
- **请求体**:

```json
{
  "scenario_type": "FAULT",
  "product_type": "FW-2000",
  "version_no": "V5.0",
  "typical_problem": "...",
  "consult_content": "..."
}
```
- **说明**: AI 工具集（命令解析/功能配置/日志解析/MIB 解析/API 解析/场景答疑）调用知识库
- **关联 FR**: FR-145、FR-146、SC-020（命中率 ≥70%）

#### 16.1.2 获取诊断结果

- **方法**: `GET`
- **路径**: `/api/v1/ai-troubleshooting/sessions/{sessionId}`
- **响应**: 诊断与解决方案，引用手册材料、技术公告、经典案例
- **关联 FR**: FR-145

### 16.2 知识库管理（FR-147）

#### 16.2.1 知识库 CRUD

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/knowledge-bases`
- **权限**: `kb:manage`
- **说明**: 类型含产品标准手册/命令行手册/典配手册/日志手册/Mib节点手册/API手册/技术公告/已知隐患/FAQ/经典案例/排障经验
- **关联 FR**: FR-147

### 16.3 排障经验管理（FR-148）

#### 16.3.1 提交排障经验转换模板

- **方法**: `POST`
- **路径**: `/api/v1/troubleshooting-experiences`
- **权限**: `ai:experience:convert`
- **请求体**:

```json
{
  "ticket_no": "ITR-001",
  "scenario_type": "FAULT",
  "product_type": "...",
  "fault_phenomenon": "...",
  "product_arch": "...",
  "trigger_factor": "...",
  "troubleshooting_process": "..."
}
```
- **说明**: 沉淀至知识库形成训练数据
- **关联 FR**: FR-148

#### 16.3.2 公共 KB 维护

- **方法**: `GET` / `POST` / `PUT`
- **路径**: `/api/v1/knowledge-bases/public`
- **权限**: `kb:public:manage`
- **说明**: 产品典型故障对照表、功能模块与产品对照表、硬件定位处理手册
- **关联 FR**: FR-148

### 16.4 Skill 训练（FR-149）

#### 16.4.1 训练 Skill

- **方法**: `POST`
- **路径**: `/api/v1/knowledge-bases/{kbId}/train-skill`
- **权限**: `kb:train`
- **说明**: 通过提示模板训练 Skill、产品分类与大模型提问重写
- **关联 FR**: FR-149

---

## 17. ITR 故障处理业务域（FR-162 ~ FR-166）

### 17.1 ITR 问题单 CRUD（FR-162、FR-163）

#### 17.1.1 创建 ITR 问题单

- **方法**: `POST`
- **路径**: `/api/v1/itr-tickets`
- **权限**: `itr:create`
- **请求体**:

```json
{
  "caller_name": "王五",
  "caller_phone": "13900139000",
  "user_id": 100,
  "device_serial_id": 1,
  "project_id": 1,
  "description": "...",
  "occur_time": "2026-07-10T10:00:00",
  "impact_duration": 30,
  "problem_level": "TWO"
}
```
- **校验**: VAL-011（ticket_no、description、problem_level 必填）、VAL-022（ticket_no 唯一）
- **说明**: 关联 PMS 设备与用户；符合通报标准邮件通报
- **关联 FR**: FR-162、FR-163

#### 17.1.2 查询 ITR 问题单列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/itr-tickets` / `/api/v1/itr-tickets/{ticketId}`
- **权限**: `itr:view`
- **请求参数**: 通用分页 + `status`、`problem_level`、`device_serial_id`、`user_id`

### 17.2 问题级别与升单（FR-162）

#### 17.2.1 确定问题级别

- **方法**: `POST`
- **路径**: `/api/v1/itr-tickets/{ticketId}/set-level`
- **权限**: `itr:edit`
- **请求体**: `{ "problem_level": "ONE", "notify_email": true }`
- **说明**: 一/二/三级，符合通报标准邮件通报
- **关联 FR**: FR-162

#### 17.2.2 升单

- **方法**: `POST`
- **路径**: `/api/v1/itr-tickets/{ticketId}/escalate`
- **权限**: `itr:edit`
- **请求体**: `{ "escalate_to": "SECOND_LINE" }`
- **关联 FR**: FR-162

### 17.3 提交解决方案（FR-164）

#### 17.3.1 提交解决方案

- **方法**: `POST`
- **路径**: `/api/v1/itr-tickets/{ticketId}/solution`
- **权限**: `itr:solution:submit`
- **请求体**:

```json
{
  "root_cause": "...",
  "solution": "...",
  "fix_version": "V5.1",
  "bug_no": "BUG-001",
  "prob_id": 1,
  "product_line": "...",
  "cause_category": "...",
  "cause_subcategory": "...",
  "current_official_version": "V5.0",
  "is_official_version": true,
  "internal_tracking": false,
  "reference_material": "...",
  "material_source": "...",
  "is_detailed": true
}
```
- **关联 FR**: FR-164

### 17.4 RMA 联动（FR-165）

#### 17.4.1 调用 RMA 流程

- **方法**: `POST`
- **路径**: `/api/v1/itr-tickets/{ticketId}/rma`
- **权限**: `itr:rma:invoke`
- **说明**: 解决方案为硬件故障时直接调用 RMA 流程
- **响应**: 201，返回 RMA 工单
- **关联 FR**: FR-165、SC-023（硬件故障 RMA 自动调用率 100%）

#### 17.4.2 查询 RMA 工单

- **方法**: `GET`
- **路径**: `/api/v1/rma-orders/{rmaId}`
- **权限**: `itr:view`

#### 17.4.3 更新 RMA 处理进展

- **方法**: `PUT`
- **路径**: `/api/v1/rma-orders/{rmaId}/progress`
- **关联 FR**: FR-165

### 17.5 ITR 闭环归档（FR-166）

#### 17.5.1 关闭 ITR 工单

- **方法**: `POST`
- **路径**: `/api/v1/itr-tickets/{ticketId}/close`
- **权限**: `itr:close`
- **说明**: 故障报告归档至 ITR，关联 PMS 系统
- **关联 FR**: FR-166、SC-023（闭环率 ≥95%）

---

## 18. 用户管理与 CRM 同步业务域（FR-157 ~ FR-161）

### 18.1 用户管理

#### 18.1.1 用户 CRUD

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/users`
- **权限**: `user:manage`
- **校验**: VAL-010（user_code、user_name、user_type 必填）、VAL-019（user_code 唯一）
- **关联 FR**: FR-157

#### 18.1.2 查询用户列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/users` / `/api/v1/users/{userId}`
- **请求参数**: 通用分页 + `user_type`（下单客户/最终用户/内部用户）、`industry`、`service_level`

### 18.2 最终用户管理（FR-158）

#### 18.2.1 创建/关联最终用户

- **方法**: `POST`
- **路径**: `/api/v1/users/{userId}/end-users`
- **权限**: `user:manage`
- **请求体**: `{ "end_user_id": 101 }`
- **说明**: 区别下单客户和最终使用用户
- **关联 FR**: FR-158

### 18.3 CRM 同步（FR-159）

#### 18.3.1 触发 CRM 同步至 PMS

- **方法**: `POST`
- **路径**: `/api/v1/users/sync-from-crm`
- **权限**: `user:sync`（CRM 回调或定时任务）
- **说明**: 用户信息从 CRM 同步至 PMS
- **关联 FR**: FR-159、SC-022（延迟 ≤5 分钟）

#### 18.3.2 触发 PMS 反向同步至 CRM

- **方法**: `POST`
- **路径**: `/api/v1/users/{userId}/sync-to-crm`
- **权限**: `user:sync`
- **说明**: PMS 维护的用户信息变更回传 CRM
- **关联 FR**: FR-159

#### 18.3.3 CRM 同步冲突处理

- **方法**: `POST`
- **路径**: `/api/v1/users/{userId}/resolve-crm-conflict`
- **权限**: `user:sync`
- **说明**: 处理 PMS 与 CRM 同一用户信息被同时修改的冲突

### 18.4 日常工作维护用户信息（FR-160）

#### 18.4.1 记录日常工作

- **方法**: `POST`
- **路径**: `/api/v1/users/{userId}/daily-works`
- **权限**: `user:edit`
- **说明**: 通过日常工作记录更新维护用户信息
- **关联 FR**: FR-160

### 18.5 客户档案（FR-161）

#### 18.5.1 查询客户档案

- **方法**: `GET`
- **路径**: `/api/v1/users/{userId}/archives`
- **权限**: `user:view`
- **请求参数**: `archive_type`（故障档案/服务档案）
- **关联 FR**: FR-161

#### 18.5.2 创建客户档案

- **方法**: `POST`
- **路径**: `/api/v1/users/{userId}/archives`
- **权限**: `user:edit`
- **关联 FR**: FR-161

---

## 19. 周报与文件管理业务域（FR-065 ~ FR-070）

### 19.1 项目周报

#### 19.1.1 创建周报（继承上期）

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/weeklies`
- **权限**: `weekly:create`
- **说明**: 自动继承上期周报数据
- **关联 FR**: FR-065、SC-014

#### 19.1.2 查询周报列表/详情

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/weeklies` / `/api/v1/weeklies/{weeklyId}`
- **权限**: `weekly:view`

#### 19.1.3 保存周报草稿

- **方法**: `PUT`
- **路径**: `/api/v1/weeklies/{weeklyId}/draft`
- **权限**: `weekly:edit`
- **关联 FR**: FR-066

#### 19.1.4 提交周报

- **方法**: `POST`
- **路径**: `/api/v1/weeklies/{weeklyId}/submit`
- **权限**: `weekly:edit`
- **关联 FR**: FR-066

#### 19.1.5 周报反馈

- **方法**: `POST`
- **路径**: `/api/v1/weeklies/{weeklyId}/feedbacks`
- **权限**: `weekly:feedback`
- **请求体**: `{ "feedback_content": "..." }`
- **关联 FR**: FR-066

#### 19.1.6 上传周报附件

- **方法**: `POST`
- **路径**: `/api/v1/weeklies/{weeklyId}/attachments`
- **权限**: `weekly:edit`
- **关联 FR**: FR-069

### 19.2 项目文件管理（FR-067）

#### 19.2.1 上传/下载/删除项目文件

- **方法**: `POST` / `GET` / `DELETE`
- **路径**: `/api/v1/projects/{projectId}/files`
- **权限**: `file:manage`
- **约束**: VAL-043（断点续传）、SC-009（100MB+）
- **关联 FR**: FR-067

### 19.3 项目交付件管理（FR-068、FR-070）

#### 19.3.1 交付件 CRUD

- **方法**: `GET` / `POST` / `DELETE`
- **路径**: `/api/v1/projects/{projectId}/deliverables`
- **权限**: `deliverable:manage`
- **请求参数**: `deliverable_type`、`source`
- **说明**: 来源含手动上传/PMS 线上产生/工作流自动存储；保留 ≥5 年（VAL-041）
- **关联 FR**: FR-068、FR-070

#### 19.3.2 查看交付件集中页（FR-134）

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/deliverables/all`
- **权限**: `project:view`
- **说明**: 集中查看并下载到货签收单、实施方案、初验报告、终验报告、现场培训记录、满意度调查报告
- **关联 FR**: FR-134

---

## 20. 验收交维业务域（FR-131 ~ FR-134）

### 20.1 现场培训（FR-131）

#### 20.1.1 获取/保存培训记录

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/projects/{projectId}/acceptance/training`
- **权限**: `project:acceptance:edit`
- **请求体**:

```json
{
  "user_unit": "XX 银行",
  "user_contact": "李四",
  "contact_phone": "13800138000",
  "device_types": ["FW", "SW"],
  "device_model": "...",
  "training_time": "2026-10-01",
  "training_engineer": "赵六",
  "training_content": "...",
  "customer_feedback": "..."
}
```
- **关联 FR**: FR-131

#### 20.1.2 下载培训记录表样例

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/acceptance/training/sample`
- **权限**: `project:view`
- **响应**: 文件流
- **关联 FR**: FR-131

### 20.2 满意度调查（FR-132）

#### 20.2.1 生成完工证明与满意度调查表

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/acceptance/satisfaction/generate`
- **权限**: `project:acceptance:edit`
- **说明**: 多维度评分（工程质量/产品质量/服务质量，100/80/60/40/0 分档）
- **关联 FR**: FR-132

#### 20.2.2 推送满意度调查至客户

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/acceptance/satisfaction/push`
- **权限**: `project:acceptance:edit`
- **说明**: 推送至客户 H5 入口
- **关联 FR**: FR-132

#### 20.2.3 下载满意度调查表/报告

- **方法**: `GET`
- **路径**: `/api/v1/projects/{projectId}/acceptance/satisfaction/download`
- **权限**: `project:view`
- **说明**: 客户签字回传后产生满意度调查报告
- **关联 FR**: FR-132

### 20.3 初验&终验（FR-133）

#### 20.3.1 上传初验报告

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/acceptance/first-acceptance/upload`
- **权限**: `project:acceptance:edit`
- **请求**: `multipart/form-data`
- **关联 FR**: FR-133

#### 20.3.2 上传终验报告

- **方法**: `POST`
- **路径**: `/api/v1/projects/{projectId}/acceptance/final-acceptance/upload`
- **权限**: `project:acceptance:edit`
- **关联 FR**: FR-133

---

## 21. 报表分析业务域（FR-083 ~ FR-087）

### 21.1 项目报表

#### 21.1.1 项目进度汇总表

- **方法**: `GET`
- **路径**: `/api/v1/reports/project-progress-summary`
- **权限**: `report:view`
- **请求参数**: `office_id`、`project_type`、`start_date`、`end_date`
- **约束**: SC-007（P95 ≤2 秒）
- **关联 FR**: FR-083

#### 21.1.2 项目延期分析表

- **方法**: `GET`
- **路径**: `/api/v1/reports/project-delay-analysis`
- **关联 FR**: FR-083

#### 21.1.3 历史项目检索

- **方法**: `GET`
- **路径**: `/api/v1/reports/historical-projects`
- **关联 FR**: FR-083

### 21.2 设备报表（FR-084）

#### 21.2.1 设备状态分布

- **方法**: `GET`
- **路径**: `/api/v1/reports/device-status-distribution`
- **响应**: 饼图/柱图数据
- **关联 FR**: FR-084

#### 21.2.2 BOM 完成率

- **方法**: `GET`
- **路径**: `/api/v1/reports/bom-completion-rate`

#### 21.2.3 设备到货/安装/验收趋势

- **方法**: `GET`
- **路径**: `/api/v1/reports/device-trends`

### 21.3 资源报表（FR-085）

#### 21.3.1 工程师负荷报表

- **方法**: `GET`
- **路径**: `/api/v1/reports/engineer-workload`
- **关联 FR**: FR-085

#### 21.3.2 工时统计

- **方法**: `GET`
- **路径**: `/api/v1/reports/engineer-hours`

#### 21.3.3 代理商使用情况

- **方法**: `GET`
- **路径**: `/api/v1/reports/facilitator-usage`
- **关联 FR**: FR-085

### 21.4 财务报表（FR-086）

#### 21.4.1 项目成本汇总

- **方法**: `GET`
- **路径**: `/api/v1/reports/project-cost-summary`

#### 21.4.2 利润分析

- **方法**: `GET`
- **路径**: `/api/v1/reports/profit-analysis`

### 21.5 报表导出（FR-087）

#### 21.5.1 导出 Excel

- **方法**: `GET`
- **路径**: `/api/v1/reports/{reportType}/export`
- **权限**: `report:export`
- **响应**: Excel 文件流
- **关联 FR**: FR-087

---

## 22. 系统管理业务域（FR-071 ~ FR-079）

### 22.1 用户管理（FR-071）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/system/users`
- **权限**: `system:user:manage`
- **说明**: 增删改查、角色分配、状态管理、密码重置
- **关联 FR**: FR-071

### 22.2 角色权限管理（FR-072）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/system/roles`
- **权限**: `system:role:manage`
- **说明**: 菜单权限、按钮权限、数据权限配置
- **关联 FR**: FR-072、FR-079

### 22.3 部门管理（FR-073）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/system/departments`
- **权限**: `system:dept:manage`
- **说明**: 树形结构
- **校验**: VAL-020（dept_code 唯一）
- **关联 FR**: FR-073

### 22.4 数据字典管理（FR-074）

- **方法**: `GET` / `POST` / `PUT` / `DELETE`
- **路径**: `/api/v1/system/dicts`
- **权限**: `system:dict:manage`
- **校验**: VAL-021（dict_type+dict_code 联合唯一）
- **关联 FR**: FR-074

### 22.5 系统配置（FR-075）

- **方法**: `GET` / `PUT`
- **路径**: `/api/v1/system/configs`
- **权限**: `system:config:manage`
- **说明**: 通知模板、审批流程、项目模板、集成配置
- **关联 FR**: FR-075

### 22.6 日志查询（FR-076）

#### 22.6.1 操作日志查询

- **方法**: `GET`
- **路径**: `/api/v1/system/logs/operate`
- **权限**: `system:log:view`
- **请求参数**: 通用分页 + `user_id`、`module`、`log_type`、`start_date`、`end_date`
- **关联 FR**: FR-076

#### 22.6.2 登录日志查询

- **方法**: `GET`
- **路径**: `/api/v1/system/logs/login`

#### 22.6.3 集成调用日志查询

- **方法**: `GET`
- **路径**: `/api/v1/system/logs/integration`

### 22.7 消息中心（FR-077）

- **方法**: `GET` / `POST`（标记已读） / `PUT`（消息设置）
- **路径**: `/api/v1/system/messages`
- **权限**: 已登录用户
- **关联 FR**: FR-077

### 22.8 认证（FR-078）

#### 22.8.1 LDAP/AD 登录

- **方法**: `POST`
- **路径**: `/api/v1/auth/login`
- **权限**: 公开
- **请求体**: `{ "username": "...", "password": "..." }`
- **说明**: LDAP/AD 统一认证，角色与组织架构数据同步
- **关联 FR**: FR-078

#### 22.8.2 客户 H5 短信验证码登录

- **方法**: `POST`
- **路径**: `/api/v1/auth/sms-login`
- **权限**: 公开
- **请求体**: `{ "phone": "...", "sms_code": "..." }`
- **关联 FR**: FR-092

#### 22.8.3 获取当前用户信息与权限

- **方法**: `GET`
- **路径**: `/api/v1/auth/profile`
- **权限**: 已登录

---

## 23. 工作流业务域（FR-080 ~ FR-082）

### 23.1 工作流任务管理（FR-081）

#### 23.1.1 查询待办任务

- **方法**: `GET`
- **路径**: `/api/v1/workflow/tasks/todo`
- **权限**: 已登录用户
- **请求参数**: 通用分页 + `business_type`、`assignee`
- **关联 FR**: FR-081

#### 23.1.2 查询历史任务

- **方法**: `GET`
- **路径**: `/api/v1/workflow/tasks/history`
- **关联 FR**: FR-081

#### 23.1.3 办理任务

- **方法**: `POST`
- **路径**: `/api/v1/workflow/tasks/{taskId}/complete`
- **权限**: `workflow:task:handle`
- **请求体**: `{ "approved": true, "comment": "..." }`
- **校验**: VAL-046（超时升级通知）
- **关联 FR**: FR-080、FR-081、SC-011

### 23.2 工作流与业务状态机联动（FR-082）

#### 23.2.1 启动工作流

- **方法**: `POST`
- **路径**: `/api/v1/workflow/processes`
- **权限**: 按业务类型
- **请求体**: `{ "business_type": "PRESALES", "business_id": 1 }`
- **说明**: 不复用老 BPMN 文件，重新实现流程定义
- **关联 FR**: FR-080、FR-082

---

## 24. 数据归档业务域（FR-168、FR-169）

### 24.1 数据归档

#### 24.1.1 查询归档数据

- **方法**: `GET`
- **路径**: `/api/v1/archives`
- **权限**: `archive:view`
- **请求参数**: `entity_type`、`archived`、`retention_years`
- **关联 FR**: FR-168

#### 24.1.2 归档至冷存储

- **方法**: `POST`
- **路径**: `/api/v1/archives/{archiveId}/move-to-cold-storage`
- **权限**: `archive:manage`
- **说明**: 超期数据自动归档至冷存储（对象存储低频访问层），异步处理
- **校验**: VAL-041（交付件/配置 Log ≥5 年，巡检/割接归档 ≥3 年）、VAL-042（AI 训练数据脱敏长期保留）
- **关联 FR**: FR-168、FR-169

#### 24.1.3 从冷存储取回

- **方法**: `POST`
- **路径**: `/api/v1/archives/{archiveId}/restore-from-cold-storage`
- **权限**: `archive:manage`
- **说明**: 异步处理，不阻塞核心业务
- **关联 FR**: FR-169

---

## 25. 移动端专项业务域（FR-090 ~ FR-094）

### 25.1 工程师移动端

#### 25.1.1 GPS 签到打卡

- **方法**: `POST`
- **路径**: `/api/v1/mobile/check-in`
- **权限**: `mobile:checkin`
- **请求体**: `{ "project_id": 1, "latitude": 39.9, "longitude": 116.4, "photo": "..." }`
- **说明**: 照片自动添加水印（时间+GPS+上传人，VAL-049）
- **关联 FR**: FR-090、FR-094

#### 25.1.2 离线数据同步

- **方法**: `POST`
- **路径**: `/api/v1/mobile/offline-sync`
- **权限**: `mobile:sync`
- **说明**: 离线缓存范围限定只读参考数据+现场采集类数据；审批/状态变更离线禁用（VAL-048）
- **关联 FR**: FR-093

### 25.2 代理商 H5

- **方法**: `GET` / `POST`
- **路径**: `/api/v1/mobile/agent/{...}`
- **权限**: 代理商（数据权限限制为本公司）
- **关联 FR**: FR-091

### 25.3 客户 H5

- **方法**: `GET`（仅极有限只读字段）
- **路径**: `/api/v1/mobile/customer/projects/{projectId}`
- **权限**: 客户（短信验证码登录）
- **说明**: 项目进度查看、割接审批、验收签核、文档下载
- **关联 FR**: FR-092

---

## 附录 A：业务域与 FR 映射总览

| 业务域 | FR 范围 | 核心资源路径 |
|--------|---------|-------------|
| 项目跟踪 | FR-016~FR-024 | `/projects/tracking/*`、`/projects/{id}/tracking` |
| 项目核心生命周期 | FR-001~FR-015、FR-025、FR-026、FR-027~FR-033 | `/projects`、`/contracts`、`/project-groups`、`/business-scenario-templates` |
| 工前准备 | FR-113~FR-117 | `/projects/{id}/user-contacts`、`/site-survey`、`/requirement` |
| 施工计划 | FR-118~FR-120 | `/projects/{id}/construction-plan` |
| 实施方案 | FR-121~FR-125 | `/projects/{id}/implementation-plan` |
| 实施部署 | FR-126~FR-130 | `/projects/{id}/deployment/*` |
| 验收交维 | FR-131~FR-134 | `/projects/{id}/acceptance/*`、`/deliverables` |
| 割接管理 | FR-135~FR-140 | `/cutover-orders`、`/cutover-orders/{id}/*` |
| 售前管理 | FR-034~FR-039 | `/presales-projects`、`/temporary-licenses` |
| 转包管理 | FR-040~FR-048 | `/subcontracts`、`/facilitators` |
| 回访与闭环 | FR-049~FR-053 | `/callbacks`、`/projects/{id}/closure` |
| 维保管理 | FR-054~FR-058 | `/maintenances` |
| 技术公告 | FR-059~FR-064 | `/probs`、`/fix-tasks` |
| 设备信息增强 | FR-150~FR-156 | `/device-serials`、`/device-serials/{id}/enhancement` |
| 服务平台集成 | FR-141~FR-144 | `/inspection-tasks`、`/service-platform/tools` |
| AI 排障 | FR-145~FR-149 | `/ai-troubleshooting`、`/knowledge-bases` |
| ITR 故障处理 | FR-162~FR-166 | `/itr-tickets`、`/rma-orders` |
| 用户管理 CRM 同步 | FR-157~FR-161 | `/users`、`/users/sync-from-crm` |
| 周报与文件 | FR-065~FR-070 | `/weeklies`、`/projects/{id}/files`、`/deliverables` |
| 报表分析 | FR-083~FR-087 | `/reports/*` |
| 系统管理 | FR-071~FR-079 | `/system/*`、`/auth/*` |
| 工作流 | FR-080~FR-082 | `/workflow/*` |
| 数据归档 | FR-168、FR-169 | `/archives/*` |
| 移动端 | FR-090~FR-094 | `/mobile/*` |

---

## 附录 B：权限码清单（RBAC）

| 权限码 | 说明 | 关联角色 |
|--------|------|---------|
| `project:create` | 创建项目 | PM、管理员 |
| `project:view` | 查看项目 | 全部（按数据权限过滤） |
| `project:edit` | 编辑项目 | PM、实施人员 |
| `project:transition` | 状态流转 | 按状态码分配 |
| `project:closure:apply` | 发起闭环 | PM |
| `project:closure:approve` | 审批闭环 | EM、主任 |
| `project:tracking:view` | 项目跟踪视图 | 交付管理人员、SM、PM |
| `project:deployment:edit` | 实施部署编辑 | 实施人员 |
| `project:acceptance:edit` | 验收交维编辑 | 交付人员 |
| `service_manager` | 服务经理（审批/修改计划） | SM |
| `cutover:*` | 割接管理 | 实施人员、二线、研发 |
| `presales:*` | 售前管理 | SM、PM、EM |
| `subcontract:*` | 转包管理 | PM、主任 |
| `callback:*` | 回访管理 | EM |
| `maintenance:*` | 维保管理 | PM |
| `prob:*` | 技术公告 | 管理员、工程师 |
| `device:*` | 设备信息 | 实施人员、用服 |
| `itr:*` | ITR 故障处理 | 用服、二线、研发 |
| `user:manage` | 用户管理 | 管理员 |
| `user:sync` | CRM 同步 | 系统/集成账户 |
| `system:*` | 系统管理 | 管理员 |
| `report:view` | 报表查看 | 管理层 |
| `report:export` | 报表导出 | 管理层 |
| `archive:manage` | 归档管理 | 管理员 |
| `mobile:checkin` | 移动端签到 | 工程师、代理商 |

---

*文档结束*
