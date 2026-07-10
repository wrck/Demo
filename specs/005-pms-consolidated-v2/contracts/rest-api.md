# REST API 契约：PMS 项目交付管理系统

**Date**: 2026-07-10
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Research**: [research.md](../research.md)

## 通用约定

### 统一前缀

所有接口前缀：`/api/v1/`

### 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | integer | 0 表示成功，非 0 表示业务错误码（详见各接口） |
| message | string | 提示信息，成功为 "success" |
| data | object/array | 业务数据，错误时为 null |

### 分页响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "total": 0,
    "pageNum": 1,
    "pageSize": 20
  }
}
```

### 鉴权与权限

- 所有接口需在请求头携带 `Authorization: Bearer {token}`（JWT，含在线 Access Token 与离线令牌两种）
- 权限标识在每条接口「权限要求」中标注，格式 `system:user:list`（模块:资源:操作）
- 数据权限按"办事处/项目归属"维度过滤，由服务端拦截器统一处理

### 通用错误码

| code | HTTP Status | 说明 |
|------|-------------|------|
| 0 | 200 | 成功 |
| 40001 | 400 | 参数校验失败 |
| 40101 | 401 | 未登录或令牌过期 |
| 40102 | 401 | 离线令牌已失效（账户变更/黑名单） |
| 40301 | 403 | 无功能权限 |
| 40302 | 403 | 无数据权限 |
| 40401 | 404 | 资源不存在 |
| 40901 | 409 | 并发冲突（乐观锁失败） |
| 40902 | 409 | 离线同步字段冲突（需人工裁定） |
| 40903 | 409 | 离线覆盖锁定字段被拒绝 |
| 42201 | 422 | 业务规则校验失败 |
| 50001 | 500 | 服务端内部错误 |

---

## 1. 项目交付核心生命周期

### 1.1 项目立项

#### POST /api/v1/projects - 创建项目

由合同号录入创建项目，状态置为"30 已创建"。

**权限要求**：`project:project:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| contractNo | string | 是 | 合同号 |
| projectName | string | 是 | 项目名称 |
| projectType | string | 是 | 项目类型（direct-直签 / indirect-非直签 / presale-售前测试） |
| projectLevel | string | 是 | 项目级别（A/B/C/D） |
| customerId | long | 是 | 客户单位 ID（由 CRM 带入） |
| finalCustomerId | long | 否 | 最终客户 ID（下单与最终使用不一致时） |
| officeId | long | 是 | 办事处 ID |
| contractAcceptTime | date | 是 | 合同验收时间 |
| parentId | long | 否 | 主项目 ID（创建子项目时传入） |

**响应数据**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "projectId": 10001,
    "statusCode": "30",
    "statusName": "已创建",
    "createdAt": "2026-07-10T10:00:00Z"
  }
}
```

#### GET /api/v1/projects - 项目列表查询

**权限要求**：`project:project:list`

**请求参数**（Query）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pageNum | integer | 否 | 页码，默认 1 |
| pageSize | integer | 否 | 每页条数，默认 20 |
| officeId | long | 否 | 办事处 |
| projectName | string | 否 | 项目名称（模糊） |
| contractNo | string | 否 | 合同号 |
| projectLevel | string | 否 | 项目级别 |
| customerId | long | 否 | 客户单位 |
| statusCode | string | 否 | 生命周期状态码 |
| subStage | string | 否 | 交付子阶段 |
| overdueOnly | boolean | 否 | 仅查超期项目 |

#### GET /api/v1/projects/{projectId} - 项目详情

**权限要求**：`project:project:view`

#### PUT /api/v1/projects/{projectId} - 更新项目

**权限要求**：`project:project:update`

#### DELETE /api/v1/projects/{projectId} - 删除项目

**权限要求**：`project:project:delete`（仅状态为 30 且无子项目时可删）

### 1.2 项目状态流转

#### POST /api/v1/projects/{projectId}/assign-sm - 指定服务经理

状态 30 → 31。

**权限要求**：`project:project:assign`（管理员）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| smUserId | long | 是 | 服务经理用户 ID |

**响应**：返回新状态 31，并触发 `project.status-changed` 事件通知 SM。

#### POST /api/v1/projects/{projectId}/assign-pm - 指定项目经理

状态 31 → 32。

**权限要求**：`project:project:assign`（服务经理）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pmUserId | long | 是 | 项目经理用户 ID |

#### POST /api/v1/projects/{projectId}/start-implementation - 启动实施

状态 32 → 40，进入交付子阶段。

**权限要求**：`project:project:update`（项目经理）

#### POST /api/v1/projects/{projectId}/close - 发起闭环

状态 40 → 100。主项目闭环需所有子项目已闭环。

**权限要求**：`project:project:close`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| closureReason | string | 是 | 闭环说明 |
| attachmentIds | array | 否 | 闭环附件 |

**错误码**：42201 - 存在未闭环子项目（响应返回未闭环子项目清单）

#### GET /api/v1/projects/{projectId}/status-history - 状态流转历史

**权限要求**：`project:project:view`

### 1.3 主子项目

#### POST /api/v1/projects/{projectId}/sub-projects - 创建子项目

大型全国项目拆分为区域子项目。

**权限要求**：`project:project:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subProjects | array | 是 | 子项目列表（含 region/officeId/projectName 等） |

#### GET /api/v1/projects/{projectId}/sub-projects - 子项目列表

**权限要求**：`project:project:view`

#### GET /api/v1/projects/{projectId}/closure-check - 闭环前置校验

校验主项目是否满足闭环条件（子项目全部闭环）。

**权限要求**：`project:project:view`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "canClose": false,
    "unClosedSubProjects": [
      { "projectId": 10002, "projectName": "XX项目-华东区", "statusCode": "40" }
    ]
  }
}
```

### 1.4 总体跟踪

#### GET /api/v1/tracking/overview - 总体跟踪统计卡片

返回 8 个阶段统计卡片数据。

**权限要求**：`project:tracking:view`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "stageCards": [
      { "statusCode": "30", "statusName": "已创建", "count": 12 },
      { "statusCode": "31", "statusName": "待指派PM", "count": 5 },
      { "statusCode": "32", "statusName": "已指派PM", "count": 8 },
      { "statusCode": "40", "statusName": "实施中", "count": 45, "overdueCount": 6 }
    ],
    "totalOverdue": 6
  }
}
```

#### GET /api/v1/tracking/projects - 跟踪项目搜索

支持按办事处/项目名称/合同号/项目级别/客户单位搜索。

**权限要求**：`project:tracking:view`

#### GET /api/v1/tracking/overdue - 超期项目列表

**权限要求**：`project:tracking:view`

### 1.5 单项目跟踪

#### GET /api/v1/projects/{projectId}/tracking - 单项目全流程跟踪

返回项目基础信息 + 各交付子阶段进度 + 关键产出物状态。

**权限要求**：`project:project:view`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "projectId": 10001,
    "projectName": "XX网络升级项目",
    "statusCode": "40",
    "subStage": "deploy",
    "subStageName": "实施部署",
    "stageProgress": [
      { "stage": "prework", "stageName": "工前准备", "status": "done", "overdue": false },
      { "stage": "plan", "stageName": "施工计划", "status": "done", "overdue": false },
      { "stage": "scheme", "stageName": "实施方案", "status": "done", "overdue": false },
      { "stage": "deploy", "stageName": "实施部署", "status": "in_progress", "overdue": false },
      { "stage": "acceptance", "stageName": "验收交维", "status": "pending", "overdue": false }
    ]
  }
}
```

### 1.6 业务场景模板

#### GET /api/v1/templates/scenarios - 业务场景模板列表

**权限要求**：`system:template:list`

#### POST /api/v1/templates/scenarios - 创建业务场景模板

**权限要求**：`system:template:create`

---

## 2. 工前准备

### 2.1 客户联系人

#### GET /api/v1/projects/{projectId}/customer-contacts - 客户联系人列表

**权限要求**：`project:contact:view`

#### POST /api/v1/projects/{projectId}/customer-contacts - 新增客户联系人

**权限要求**：`project:contact:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 姓名 |
| phone | string | 是 | 手机号 |
| email | string | 否 | 邮箱 |
| position | string | 否 | 躯位 |
| isPrimary | boolean | 是 | 是否主联系人（主联系人显示在项目页面） |
| customerLevel | string | 否 | 联系人级别 |

#### PUT /api/v1/projects/{projectId}/customer-contacts/{contactId} - 更新联系人

**权限要求**：`project:contact:update`

#### DELETE /api/v1/projects/{projectId}/customer-contacts/{contactId} - 删除/失效联系人

**权限要求**：`project:contact:delete`

### 2.2 工勘

#### GET /api/v1/projects/{projectId}/site-survey - 工勘详情

**权限要求**：`project:survey:view`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "projectId": 10001,
    "durationRequirement": "2026-12-31",
    "siteSurveyItems": [
      { "itemKey": "power_supply", "itemName": "机房供电", "value": "ok", "needVendor": false },
      { "itemKey": "network_port", "itemName": "网口", "value": "ok" },
      { "itemKey": "rack_install_poweron_vendor", "itemName": "上架加电需要原厂实施", "value": "yes", "needOutsource": true, "showOutsourceLink": true },
      { "itemKey": "rail_tray", "itemName": "需要导轨托盘", "value": "yes", "showMaterialLinks": true },
      { "itemKey": "shipped_material_fit", "itemName": "发货物料是否符合现场施工环境", "value": "no", "showMaterialSelect": true }
    ]
  }
}
```

#### PUT /api/v1/projects/{projectId}/site-survey - 保存工勘

**权限要求**：`project:survey:update`

#### POST /api/v1/projects/{projectId}/site-survey/outsourse - 发起外包流程

对"上架加电需要原厂实施-需要外包"选择"是"时触发。

**权限要求**：`project:survey:update`

### 2.3 需求分析

#### GET /api/v1/projects/{projectId}/requirement-analysis - 需求分析详情

**权限要求**：`project:requirement:view`

#### PUT /api/v1/projects/{projectId}/requirement-analysis - 保存需求分析

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectBackground | string | 是 | 项目背景 |
| projectGoal | string | 是 | 项目目标 |
| topologyFileId | long | 否 | 网络拓扑文件 ID |
| transmissionStatus | array | 否 | 传输现状（勾选项） |
| trafficStatus | string | 否 | 流量现状 |
| ipResources | string | 否 | IP 资源 |
| redundancyBackup | string | 否 | 冗余备份 |
| protectionOps | string | 否 | 防护与运维要求 |

**权限要求**：`project:requirement:update`

#### GET /api/v1/projects/{projectId}/requirement-analysis/handover-doc - 下载工程交底书

根据发货设备情况自动生成工程交底书。

**权限要求**：`project:requirement:view`

### 2.4 物料换货

#### GET /api/v1/projects/{projectId}/materials - 发货物料清单

**权限要求**：`project:material:view`

#### POST /api/v1/projects/{projectId}/materials/exchange - 发起换货流程

勾选需换货物料并填写不符合项说明，推送至 CRM 对应销售处。

**权限要求**：`project:material:exchange`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| materials | array | 是 | 换货物料列表 |
| materials[].serialNo | string | 是 | 序列号 |
| materials[].productCode | string | 是 | 产品编码 |
| materials[].productName | string | 是 | 产品名称 |
| materials[].reason | string | 是 | 不符合项说明 |

---

## 3. 施工计划

### 3.1 三层时间模型

#### GET /api/v1/projects/{projectId}/construction-plan - 施工计划详情

返回三层时间：阶段计划时间（PM 填写）、工期要求时间（只读）、工期建议计划时间（系统倒推计算）。

**权限要求**：`project:plan:view`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "projectId": 10001,
    "projectType": "indirect",
    "contractAcceptTime": "2026-12-31",
    "durationRequirement": "2026-12-31",
    "stages": [
      {
        "stage": "prework",
        "stageName": "工前准备",
        "planTime": "2026-08-15",
        "requirementTime": null,
        "suggestedTime": "2026-08-15",
        "editable": true
      },
      {
        "stage": "hardware_install",
        "stageName": "硬件实施",
        "planTime": "2026-08-29",
        "requirementTime": null,
        "suggestedTime": "2026-08-29"
      },
      {
        "stage": "device_config",
        "stageName": "设备配置",
        "planTime": "2026-09-12",
        "suggestedTime": "2026-09-12"
      },
      {
        "stage": "cutover_online",
        "stageName": "割接-上线",
        "planTime": "2026-10-12",
        "suggestedTime": "2026-10-12"
      }
    ],
    "durationWarning": "当前项目工期紧张，请详细落实好工期计划，并与客户确认"
  }
}
```

#### PUT /api/v1/projects/{projectId}/construction-plan - 保存施工计划

**权限要求**：`project:plan:update`（项目经理）

#### GET /api/v1/projects/{projectId}/construction-plan/suggest - 工期倒推计算

按项目类型动态裁定倒推逻辑。

**权限要求**：`project:plan:view`

**请求参数**（Query）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectType | string | 是 | direct（割接上线=初验时间-3个月-2周）/ indirect（割接上线=工期时间-2周） |

### 3.2 工期紧张提醒与发货提醒

#### POST /api/v1/projects/{projectId}/construction-plan/crm-reminder - 发起 CRM 发货提醒

工期不足 3 个月且未发货时触发。

**权限要求**：`project:plan:update`

### 3.3 施工计划审批

#### POST /api/v1/projects/{projectId}/construction-plan/submit - 提交施工计划审核

推送到服务经理钉钉审批，仅服务经理可修改计划。

**权限要求**：`project:plan:submit`（项目经理）

---

## 4. 实施方案

### 4.1 实施方案生成

#### GET /api/v1/projects/{projectId}/implementation-scheme - 实施方案详情

**权限要求**：`project:scheme:view`

**响应数据**（章节结构）：

```json
{
  "code": 0,
  "data": {
    "projectId": 10001,
    "sections": [
      { "sectionKey": "overview", "sectionName": "项目概述", "content": "..." },
      { "sectionKey": "current_status", "sectionName": "现网现状分析", "content": "..." },
      { "sectionKey": "overall_design", "sectionName": "总体方案设计", "content": "...",
        "linkedFields": ["deviceDeployLocation", "interfaceConnection", "ipVlan", "softwareVersion"] },
      { "sectionKey": "config_script", "sectionName": "配置脚本", "content": "..." },
      { "sectionKey": "implementation_steps", "sectionName": "实施步骤", "content": "..." },
      { "sectionKey": "other_schemes", "sectionName": "其他方案", "templates": ["quality","risk","ops","issue"] },
      { "sectionKey": "training", "sectionName": "项目培训及资料移交", "content": "..." },
      { "sectionKey": "after_sales", "sectionName": "售后服务", "content": "..." }
    ],
    "hasCustomerScheme": false,
    "status": "draft"
  }
}
```

#### PUT /api/v1/projects/{projectId}/implementation-scheme - 保存实施方案草稿

**权限要求**：`project:scheme:update`（项目经理）

#### POST /api/v1/projects/{projectId}/implementation-scheme/upload-existing - 上传已有客户方案

选择"是否已有客户方案"上传后自动填充至表单。

**权限要求**：`project:scheme:update`

**请求参数**：`multipart/form-data`，字段 `file`

#### POST /api/v1/projects/{projectId}/implementation-scheme/generate - 生成实施方案

**权限要求**：`project:scheme:update`

#### GET /api/v1/projects/{projectId}/implementation-scheme/download - 下载实施方案

**权限要求**：`project:scheme:view`

### 4.2 其他方案模板

#### GET /api/v1/scheme-templates - 其他方案模板列表

返回质量保障/风险管控/运维交付/问题闭环模板。

**权限要求**：`project:scheme:view`

### 4.3 实施方案审核

#### POST /api/v1/projects/{projectId}/implementation-scheme/submit-review - 提交审核

服务经理审核，重大项目提交总部复核。

**权限要求**：`project:scheme:submit`（项目经理）

#### POST /api/v1/projects/{projectId}/implementation-scheme/review - 审核实施方案

**权限要求**：`project:scheme:review`（服务经理/总部）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| result | string | 是 | approved / rejected |
| comment | string | 否 | 审核意见 |

---

## 5. 实施部署

### 5.1 到货签收

#### GET /api/v1/projects/{projectId}/delivery-receipt - 到货签收记录

**权限要求**：`project:deploy:view`

#### POST /api/v1/projects/{projectId}/delivery-receipt - 上传到货签收单

**权限要求**：`project:deploy:update`

**请求参数**：`multipart/form-data`，字段 `file`

### 5.2 硬件安装

#### GET /api/v1/projects/{projectId}/hardware-installations - 硬件安装记录列表

**权限要求**：`project:deploy:view`

#### POST /api/v1/projects/{projectId}/hardware-installations - 新增硬件安装记录

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| serialNo | string | 是 | 序列号（PMS 导入） |
| productName | string | 是 | 产品名称（PMS 导入） |
| installLocation | string | 是 | 安装位置（需求分析带入，可修改） |
| photoFileIds | array | 是 | 安装照片文件 ID |

**权限要求**：`project:deploy:update`

#### PUT /api/v1/projects/{projectId}/hardware-installations/{installId} - 更新硬件安装记录

**权限要求**：`project:deploy:update`

### 5.3 配置 Log

#### POST /api/v1/projects/{projectId}/config-logs/read-path - 设置 Log 读取路径自动读取

设置 Log 读取路径，系统自动读取对应路径下配置 Log 文件，按序列号解析配置信息回填。

**权限要求**：`project:deploy:update`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| logPath | string | 是 | Log 文件读取路径 |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "parsedDevices": [
      { "serialNo": "SN001", "productName": "DeviceA", "configInfo": { "ip": "10.0.0.1", "version": "V2.0" } }
    ],
    "failedFiles": []
  }
}
```

#### POST /api/v1/projects/{projectId}/config-logs/upload - 本地上传配置 Log

**权限要求**：`project:deploy:update`

**请求参数**：`multipart/form-data`

#### GET /api/v1/projects/{projectId}/config-logs - 配置 Log 列表

**权限要求**：`project:deploy:view`

### 5.4 业务联调

#### GET /api/v1/projects/{projectId}/integration-test - 业务联调记录

设备清单展示设备级运行业务描述。

**权限要求**：`project:deploy:view`

#### POST /api/v1/projects/{projectId}/integration-test - 保存业务联调

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| connectionInfo | object | 是 | 连接信息 |
| devices | array | 是 | 设备清单（含运行业务描述） |

**权限要求**：`project:deploy:update`

#### POST /api/v1/projects/{projectId}/integration-test/collect-config - 一键收集设备配置

**权限要求**：`project:deploy:update`

### 5.5 割接发起

#### POST /api/v1/projects/{projectId}/cutover/initiate - 发起割接

割接上线前期流程未完成时按钮失效，完成后可发起。

**权限要求**：`project:cutover:initiate`（强一致性，离线禁用）

**错误码**：42201 - 前置流程未完成

---

## 6. 验收交维

### 6.1 培训

#### GET /api/v1/projects/{projectId}/trainings - 培训记录列表

**权限要求**：`project:acceptance:view`

#### POST /api/v1/projects/{projectId}/trainings - 新增培训记录

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trainingDate | date | 是 | 培训日期 |
| trainees | array | 是 | 参训人员 |
| content | string | 是 | 培训内容 |
| attachmentIds | array | 否 | 培训资料 |

**权限要求**：`project:acceptance:update`

### 6.2 满意度

#### GET /api/v1/projects/{projectId}/satisfaction - 满意度调查

**权限要求**：`project:acceptance:view`

#### POST /api/v1/projects/{projectId}/satisfaction - 提交满意度

**权限要求**：`project:acceptance:update`

### 6.3 初验/终验

#### POST /api/v1/projects/{projectId}/acceptance/preliminary - 提交初验

**权限要求**：`project:acceptance:update`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acceptanceDate | date | 是 | 初验日期 |
| result | string | 是 | passed / failed |
| attachmentIds | array | 是 | 验收附件 |

#### POST /api/v1/projects/{projectId}/acceptance/final - 提交终验

**权限要求**：`project:acceptance:update`

### 6.4 交付件

#### GET /api/v1/projects/{projectId}/deliverables - 交付件清单

**权限要求**：`project:acceptance:view`

#### POST /api/v1/projects/{projectId}/deliverables - 上传交付件

**权限要求**：`project:acceptance:update`

---

## 7. 售前测试管理

### 7.1 售前测试申请

#### POST /api/v1/presales/applications - 创建售前测试申请

**权限要求**：`presales:application:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| customerName | string | 是 | 客户名称 |
| testPurpose | string | 是 | 测试目的 |
| devices | array | 是 | 测试设备清单 |
| expectedShipDate | date | 否 | 预期发货日期 |

#### GET /api/v1/presales/applications - 售前测试列表

**权限要求**：`presales:application:list`

#### GET /api/v1/presales/applications/{applicationId} - 售前测试详情

**权限要求**：`presales:application:view`

### 7.2 售前测试状态流转

状态：31 待服务经理指定PM → 32 已指定PM → 33 PM已跟踪 → 100 已闭环。

#### POST /api/v1/presales/applications/{applicationId}/approve - SM 审批指定 PM

**权限要求**：`presales:application:approve`（服务经理）

#### POST /api/v1/presales/applications/{applicationId}/pm-track - PM 跟踪完成

**权限要求**：`presales:application:update`（项目经理）

#### POST /api/v1/presales/applications/{applicationId}/em-visit - EM 回访

**权限要求**：`presales:application:em-visit`（工程管理部）

### 7.3 临时授权

#### POST /api/v1/presales/applications/{applicationId}/temp-license - 自动获取首次临时授权

设备发货后系统自动获取首次临时授权，实现零等待授权。

**权限要求**：`presales:license:acquire`

---

## 8. 转包管理

### 8.1 转包创建与审批

#### POST /api/v1/projects/{projectId}/subcontracts - 创建转包

**权限要求**：`subcontract:create`（项目经理）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentId | long | 是 | 代理商 ID |
| subcontractScope | string | 是 | 转包范围 |
| amount | decimal | 是 | 转包金额 |
| attachments | array | 否 | 附件 |

#### POST /api/v1/subcontracts/{subcontractId}/submit - 发起转包申请

启动多级审批（受益部门服务经理→通用审批→工程管理部→主任）。

**权限要求**：`subcontract:submit`（项目经理）

#### GET /api/v1/subcontracts/{subcontractId}/approval - 转包审批详情

**权限要求**：`subcontract:view`

#### POST /api/v1/subcontracts/{subcontractId}/approve - 审批转包

**权限要求**：`subcontract:approve`

### 8.2 转包合同执行

#### POST /api/v1/subcontracts/{subcontractId}/d365-push - 推送 D365 采购订单

审批通过后向 D365 推送采购订单并跟踪采购收货。

**权限要求**：`subcontract:d365:push`

#### GET /api/v1/subcontracts/{subcontractId}/d365-purchase - D365 采购订单状态

**权限要求**：`subcontract:view`

### 8.3 转包付款

#### POST /api/v1/subcontracts/{subcontractId}/payments - 提交付款申请

系统识别发票并启动付款审批流。

**权限要求**：`subcontract:payment:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| invoiceFileId | long | 是 | 发票文件 ID（OCR 识别） |
| amount | decimal | 是 | 付款金额 |

### 8.4 转包回访与验收

#### POST /api/v1/subcontracts/{subcontractId}/visit - 转包回访

**权限要求**：`subcontract:visit`

#### POST /api/v1/subcontracts/{subcontractId}/acceptance - 转包验收

**权限要求**：`subcontract:acceptance`

---

## 9. 闭环与回访管理

#### POST /api/v1/projects/{projectId}/closure-request - 发起闭环申请

**权限要求**：`project:closure:request`（强一致性，离线禁用）

#### GET /api/v1/projects/{projectId}/closure-approvals - 闭环审批列表

**权限要求**：`project:closure:view`

#### POST /api/v1/projects/{projectId}/closure-approvals/{approvalId} - 审批闭环

**权限要求**：`project:closure:approve`

#### POST /api/v1/projects/{projectId}/visit - 发起客户回访

**权限要求**：`project:visit:create`

---

## 10. 维保管理

#### GET /api/v1/maintenance/records - 维保记录列表

**权限要求**：`maintenance:record:list`

#### GET /api/v1/maintenance/records/{recordId} - 维保记录详情

**权限要求**：`maintenance:record:view`

#### POST /api/v1/maintenance/records - 创建维保记录

**权限要求**：`maintenance:record:create`

#### GET /api/v1/maintenance/questionnaires - 维保问卷列表

**权限要求**：`maintenance:questionnaire:list`

#### POST /api/v1/maintenance/questionnaires - 创建维保问卷

**权限要求**：`maintenance:questionnaire:create`

#### GET /api/v1/maintenance/deliverables - 维保交付件

**权限要求**：`maintenance:deliverable:list`

---

## 11. 技术公告与修复任务

#### GET /api/v1/tech-bulletins - 技术公告列表

**权限要求**：`techbulletin:list`

#### POST /api/v1/tech-bulletins - 发布技术公告

**权限要求**：`techbulletin:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 标题 |
| content | string | 是 | 内容 |
| affectedProducts | array | 是 | 影响产品范围 |
| severity | string | 是 | 严重等级 |

#### GET /api/v1/tech-bulletins/{bulletinId}/impact - 公告影响范围

**权限要求**：`techbulletin:view`

#### GET /api/v1/tech-bulletins/{bulletinId}/fix-tasks - 修复任务列表

**权限要求**：`techbulletin:fixtask:list`

#### POST /api/v1/tech-bulletins/{bulletinId}/fix-tasks - 创建修复任务

**权限要求**：`techbulletin:fixtask:create`

#### PUT /api/v1/fix-tasks/{taskId} - 更新修复任务状态

**权限要求**：`techbulletin:fixtask:update`

---

## 12. 周报与文件管理

#### GET /api/v1/weekly-reports - 周报列表

**权限要求**：`weekly:list`

#### POST /api/v1/weekly-reports - 提交周报

**权限要求**：`weekly:create`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| reportWeek | string | 是 | 报告周（如 2026-W28） |
| content | string | 是 | 周报内容 |
| projectId | long | 否 | 关联项目 |

#### GET /api/v1/files/{fileId}/download - 文件下载

**权限要求**：按文件归属校验

#### POST /api/v1/files/upload - 文件上传（支持断点续传）

**权限要求**：登录即可

#### POST /api/v1/files/upload/init - 初始化分片上传

**权限要求**：登录即可

#### POST /api/v1/files/upload/chunk - 上传分片

**权限要求**：登录即可

#### POST /api/v1/files/upload/complete - 完成分片上传

**权限要求**：登录即可

---

## 13. 客户资产库管理

#### GET /api/v1/customer-asset-library/{customerId} - 客户资产库视图

整合性查询界面，集中查看客户单位信息、联系人、归属项目清单、归属设备清单、服务记录、故障记录、续保记录。

**权限要求**：`customer:asset:view`（按角色+数据权限分级控制）

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "customerId": 20001,
    "customerCode": "C001",
    "customerName": "XX集团",
    "address": "...",
    "industry": "金融",
    "serviceLevel": "VIP",
    "contacts": [],
    "projects": [],
    "devices": [],
    "serviceRecords": [],
    "faultRecords": [],
    "warrantyRecords": []
  }
}
```

#### PUT /api/v1/customer-asset-library/{customerId}/service-level - 修改客户服务等级

修改后对所有关联项目生效。

**权限要求**：`customer:asset:update`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| serviceLevel | string | 是 | 服务等级 |

---

## 14. 客户管理与 CRM 同步

#### GET /api/v1/customers - 客户列表

**权限要求**：`customer:list`

#### GET /api/v1/customers/{customerId} - 客户详情

**权限要求**：`customer:view`

#### POST /api/v1/customers/sync/from-crm - 从 CRM 同步客户信息

**权限要求**：`customer:sync`（系统调用）

#### POST /api/v1/customers/sync/to-crm - 反向同步至 CRM

PMS 维护变更可反向同步至 CRM。

**权限要求**：`customer:sync`

#### GET /api/v1/customers/{customerId}/final-customer - 最终客户信息

区别下单客户与最终使用客户。

**权限要求**：`customer:view`

#### PUT /api/v1/customers/{customerId}/final-customer - 录入最终客户

**权限要求**：`customer:update`

---

## 15. 割接管理

### 15.1 割接操作单

#### GET /api/v1/cutover/operations - 割接操作单列表

**权限要求**：`cutover:operation:list`

#### POST /api/v1/cutover/operations - 创建割接操作单

**权限要求**：`cutover:operation:create`

#### GET /api/v1/cutover/operations/{operationId} - 割接操作单详情

**权限要求**：`cutover:operation:view`

#### PUT /api/v1/cutover/operations/{operationId}/checklist - 填写割接 checklist

**权限要求**：`cutover:operation:update`

### 15.2 割接平台集成

#### POST /api/v1/cutover/operations/{operationId}/sync-platform - 同步至割接管理平台

**权限要求**：`cutover:operation:sync`（强一致性，离线禁用）

#### POST /api/v1/cutover/operations/{operationId}/refresh - 从割接平台刷新闭环状态

**权限要求**：`cutover:operation:view`

### 15.3 割接归档

#### POST /api/v1/cutover/operations/{operationId}/archive - 割接归档

**权限要求**：`cutover:operation:archive`

---

## 16. 服务平台集成

#### POST /api/v1/service-platform/inspection/sync - 同步巡检数据

从迪普服务平台同步巡检数据。

**权限要求**：`service:platform:sync`

#### POST /api/v1/service-platform/device-info/parse - 设备信息解析回传

从服务平台解析设备信息并回传 PMS。

**权限要求**：`service:platform:parse`

#### GET /api/v1/devices/{deviceId}/crt-log - CRT log 读取

**权限要求**：`service:platform:view`

---

## 17. AI 排障与知识库

### 17.1 AI 排障诊断

#### POST /api/v1/ai-troubleshoot/diagnose - AI 故障诊断

基于 RAG 架构（ES 8 kNN 向量检索 + LLM 集成），命中率目标 ≥70%。

**权限要求**：`ai:troubleshoot:diagnose`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| faultDescription | string | 是 | 故障现象描述 |
| deviceId | long | 否 | 设备 ID |
| faultNo | string | 否 | 故障单号 |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "diagnosisId": "D001",
    "possibleCauses": [
      { "cause": "配置错误", "confidence": 0.85, "evidence": [...] }
    ],
    "solutions": [
      { "solution": "检查 OSPF 配置", "steps": [...] }
    ],
    "references": [
      { "type": "manual", "title": "命令行手册", "section": "..." }
    ],
    "hitRate": 0.72
  }
}
```

### 17.2 知识库管理

#### GET /api/v1/knowledge-base - 知识库列表

知识库类型：产品标准手册/命令行手册/典配手册/日志手册/Mib 节点手册/API 手册/技术公告/已知隐患/FAQ/经典案例/排障经验。

**权限要求**：`ai:kb:list`

#### POST /api/v1/knowledge-base - 新增知识库条目

**权限要求**：`ai:kb:create`

#### POST /api/v1/knowledge-base/{kbId}/vectorize - 知识库向量化

将知识库内容向量化后存入 ES。

**权限要求**：`ai:kb:vectorize`

### 17.3 AI AGENT 工具集

#### GET /api/v1/ai-tools - AI AGENT 工具集列表

工具集：命令解析/功能配置/日志解析/MIB 解析/API 解析/场景答疑。

**权限要求**：`ai:tool:list`

#### POST /api/v1/ai-tools/{toolKey}/invoke - 调用 AI 工具

**权限要求**：`ai:tool:invoke`

### 17.4 排障经验沉淀

#### POST /api/v1/ai-troubleshoot/experiences - 沉淀排障经验

将故障单号/现象/产品架构/触发因素/排查过程转换为训练数据。

**权限要求**：`ai:experience:create`

---

## 18. 设备信息增强

#### GET /api/v1/devices - 设备列表

**权限要求**：`device:list`

#### GET /api/v1/devices/{deviceId} - 设备详情

**权限要求**：`device:view`

#### GET /api/v1/devices/{deviceId}/config-history - 设备配置历史

**权限要求**：`device:view`

#### GET /api/v1/devices/{deviceId}/deploy-risk - 设备部署风险

**权限要求**：`device:view`

#### GET /api/v1/projects/{projectId}/interface-matrix - 接口对照表

用于网络拓扑自动生成（FR-100）。

**权限要求**：`project:device:view`

#### GET /api/v1/projects/{projectId}/topology - 网络拓扑数据

基于 Cytoscape.js + dagre 布局算法生成拓扑数据结构（FR-101）。

**权限要求**：`project:device:view`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "nodes": [
      { "id": "dev1", "label": "DeviceA", "type": "upstream" },
      { "id": "dev2", "label": "DeviceB", "type": "downstream" }
    ],
    "edges": [
      { "source": "dev1", "target": "dev2", "label": "GE0/0/1-GE0/0/2" }
    ]
  }
}
```

#### GET /api/v1/devices/{deviceId}/versions - 设备版本信息

**权限要求**：`device:view`

---

## 19. ITR 故障与 RMA

### 19.1 ITR 故障工单

#### GET /api/v1/itr/tickets - ITR 故障工单列表

**权限要求**：`itr:ticket:list`

#### GET /api/v1/itr/tickets/{ticketId} - ITR 故障工单详情

**权限要求**：`itr:ticket:view`

#### POST /api/v1/itr/tickets - 创建 ITR 故障工单

**权限要求**：`itr:ticket:create`

#### GET /api/v1/itr/tickets/pending-closure - 待闭环问题列表

**权限要求**：`itr:ticket:list`

#### POST /api/v1/itr/tickets/{ticketId}/solution - 提交解决方案

**权限要求**：`itr:ticket:update`

### 19.2 RMA 硬件故障流程

#### POST /api/v1/itr/tickets/{ticketId}/rma - 调用 RMA 硬件故障流程

**权限要求**：`itr:rma:invoke`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| deviceId | long | 是 | 故障设备 ID |
| faultType | string | 是 | 故障类型 |
| description | string | 是 | 故障描述 |

#### GET /api/v1/rma/records - RMA 记录列表

**权限要求**：`itr:rma:list`

#### GET /api/v1/rma/records/{rmaId} - RMA 记录详情

**权限要求**：`itr:rma:view`

---

## 20. 系统管理与权限

### 20.1 用户管理

#### GET /api/v1/system/users - 用户列表

**权限要求**：`system:user:list`

#### POST /api/v1/system/users - 创建用户

**权限要求**：`system:user:create`

#### PUT /api/v1/system/users/{userId} - 更新用户

**权限要求**：`system:user:update`

#### DELETE /api/v1/system/users/{userId} - 删除用户

**权限要求**：`system:user:delete`

### 20.2 角色管理

#### GET /api/v1/system/roles - 角色列表

**权限要求**：`system:role:list`

#### POST /api/v1/system/roles - 创建角色

**权限要求**：`system:role:create`

#### PUT /api/v1/system/roles/{roleId} - 更新角色

**权限要求**：`system:role:update`

#### PUT /api/v1/system/roles/{roleId}/permissions - 分配权限

**权限要求**：`system:role:assign`

### 20.3 部门管理

#### GET /api/v1/system/departments - 部门列表

**权限要求**：`system:dept:list`

#### POST /api/v1/system/departments - 创建部门

**权限要求**：`system:dept:create`

### 20.4 基础数据

#### GET /api/v1/system/dict - 字典列表

**权限要求**：`system:dict:list`

#### POST /api/v1/system/dict - 新增字典

**权限要求**：`system:dict:create`

### 20.5 认证

#### POST /api/v1/auth/login - 登录（LDAP/AD 绑定认证）

**权限要求**：无

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "expiresIn": 3600,
    "userInfo": { "userId": 1, "username": "...", "roles": [] }
  }
}
```

#### POST /api/v1/auth/refresh - 刷新令牌

**权限要求**：无

#### POST /api/v1/auth/logout - 登出

**权限要求**：登录即可

#### GET /api/v1/auth/account-status - 账户状态校验

联网瞬间立即向服务端发起"令牌 + 账户状态"联合校验。

**权限要求**：无

---

## 21. 工作流引擎

#### GET /api/v1/workflow/definitions - 流程定义列表

**权限要求**：`workflow:definition:list`

#### POST /api/v1/workflow/definitions/deploy - 部署流程定义

Flowable 7.x BPMN 流程定义。

**权限要求**：`workflow:definition:deploy`

#### GET /api/v1/workflow/tasks - 待办任务列表

**权限要求**：`workflow:task:list`

#### POST /api/v1/workflow/tasks/{taskId}/complete - 完成任务

支持会签/或签/委派/超时升级。

**权限要求**：`workflow:task:complete`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| variables | object | 否 | 流程变量 |
| comment | string | 否 | 审批批注 |

#### POST /api/v1/workflow/tasks/{taskId}/delegate - 委派任务

**权限要求**：`workflow:task:delegate`

#### GET /api/v1/workflow/instances/{instanceId}/diagram - 流程图

**权限要求**：`workflow:instance:view`

### DMN 决策表

#### GET /api/v1/workflow/dmn/tables - DMN 决策表列表

用于割接等级评定规则。

**权限要求**：`workflow:dmn:list`

---

## 22. 报表分析

#### GET /api/v1/reports/delivery-statistics - 交付统计报表

**权限要求**：`report:delivery:view`

#### GET /api/v1/reports/overdue-analysis - 超期分析报表

**权限要求**：`report:overdue:view`

#### GET /api/v1/reports/customer-statistics - 客户统计报表

**权限要求**：`report:customer:view`

#### POST /api/v1/reports/export - 导出报表

**权限要求**：`report:export`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| reportType | string | 是 | 报表类型 |
| format | string | 是 | excel / csv |
| filters | object | 否 | 过滤条件 |

---

## 23. 多终端支持

5 类终端：PC Web / 桌面客户端 / 工程师 H5 / 代理商 H5 / 客户 H5。

#### GET /api/v1/mobile/engineer/workbench - 工程师工作台

**权限要求**：`mobile:engineer:view`

#### GET /api/v1/mobile/agent/workbench - 代理商工作台

**权限要求**：`mobile:agent:view`

#### GET /api/v1/mobile/customer/workbench - 客户工作台

**权限要求**：`mobile:customer:view`

#### POST /api/v1/mobile/sign-in - 移动端签到（GPS+水印拍照）

**权限要求**：`mobile:signin:create`

---

## 24. 数据迁移

#### POST /api/v1/migration/start - 启动数据迁移

**权限要求**：`migration:execute`

#### GET /api/v1/migration/status - 迁移状态

**权限要求**：`migration:view`

#### POST /api/v1/migration/verify - 迁移完整性校验

记录数对比 + 关键字段抽样核对。

**权限要求**：`migration:verify`

#### POST /api/v1/migration/cutover - 灰度切换

按办事处或项目类型分批切换。

**权限要求**：`migration:cutover`

#### POST /api/v1/migration/rollback - 回滚至老系统

**权限要求**：`migration:rollback`

---

## 25. SPMS 备件集成

#### GET /api/v1/spms/spare-parts - 备件列表

**权限要求**：`spms:spare:list`

#### POST /api/v1/spms/spare-parts/borrow - 备件领用

**权限要求**：`spms:spare:borrow`

#### POST /api/v1/spms/spare-parts/return - 备件归还

**权限要求**：`spms:spare:return`

#### POST /api/v1/spms/spare-parts/repair - 备件返修

**权限要求**：`spms:spare:repair`

#### POST /api/v1/spms/spare-parts/replace - 备件替换

**权限要求**：`spms:spare:replace`

---

## 26. 安全防护

#### GET /api/v1/security/audit-logs - 操作审计日志

**权限要求**：`security:audit:list`

#### GET /api/v1/security/login-logs - 登录日志

**权限要求**：`security:login:list`

#### GET /api/v1/security/integration-logs - 集成调用日志

**权限要求**：`security:integration:list`

---

## 27. 发票与合同集成

### 27.1 发票 OCR

#### POST /api/v1/invoices/ocr - 发票 OCR 识别

百度 OCR 或阿里云 OCR。

**权限要求**：`invoice:ocr`

**请求参数**：`multipart/form-data`，字段 `file`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "invoiceNo": "INV001",
    "invoiceDate": "2026-07-10",
    "amount": 10000.00,
    "buyer": "...",
    "seller": "..."
  }
}
```

### 27.2 FP 平台合同校验

#### POST /api/v1/contracts/verify - 合同数据校验

与 FP 平台合同数据校验。

**权限要求**：`contract:verify`

#### GET /api/v1/contracts/{contractId} - 合同详情

**权限要求**：`contract:view`

---

## 28. 规则引擎

#### GET /api/v1/rules - 规则列表

**权限要求**：`rule:list`

#### POST /api/v1/rules - 创建规则

**权限要求**：`rule:create`

#### POST /api/v1/rules/{ruleId}/execute - 执行规则

**权限要求**：`rule:execute`

---

## 29. 跨系统数据集成

#### GET /api/v1/integration/health - 集成健康检查

返回 18+ 外部系统连通状态。

**权限要求**：`integration:health`

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "systems": [
      { "system": "LDAP/AD", "status": "healthy", "latency": 30 },
      { "system": "CRM", "status": "healthy", "latency": 120 },
      { "system": "D365", "status": "degraded", "latency": 2000 }
    ]
  }
}
```

#### GET /api/v1/integration/sync-status - 集成同步状态

跨系统集成点同步成功率 ≥99%。

**权限要求**：`integration:status`

#### POST /api/v1/integration/retry - 重试失败集成

**权限要求**：`integration:retry`

---

## 30. 归档管理

#### POST /api/v1/archive/projects/{projectId} - 归档项目

**权限要求**：`archive:project:archive`

#### GET /api/v1/archive/records - 归档记录列表

**权限要求**：`archive:record:list`

#### POST /api/v1/archive/cold-storage/move - 移至冷存储

对象存储分层归档（热存储 + 冷存储低频访问层）。

**权限要求**：`archive:coldstorage:move`

---

## 附录：权限标识汇总

权限标识遵循 `模块:资源:操作` 三段式格式，与 RBAC 角色绑定。数据权限按"办事处/项目归属"维度由服务端拦截器统一过滤，不在接口权限标识中体现。

**离线禁用清单（强一致性操作，桌面客户端离线模式不可用）**：
- 项目闭环：`project:closure:request` / `project:closure:approve`
- 割接发起：`project:cutover:initiate` / `cutover:operation:sync`
- 状态流转：`project:project:assign` / `project:project:close`
- 转包发起：`subcontract:submit` / `subcontract:approve`
- 审批操作：`project:scheme:review` / `project:plan:submit`
- 数据迁移：`migration:*`
- 系统管理写操作：`system:*:create` / `system:*:update` / `system:*:delete`

离线模式下仅允许填写类写操作暂存草稿，详见 [desktop-sync.md](./desktop-sync.md)。
