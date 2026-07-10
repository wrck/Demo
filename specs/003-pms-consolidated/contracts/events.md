# 事件契约（异步消息）：PMS 项目管理系统

> **来源**: `spec.md`（003-pms-consolidated 分支）—— 审批推送、状态变更、数据同步、归档、告警等异步消息场景
> **覆盖**: 6 大事件类别，35+ 事件主题
> **状态**: Draft
> **最后更新**: 2026-07-10

---

## 1. 概述

PMS 系统通过异步消息机制实现跨模块、跨系统的解耦通信。事件驱动场景涵盖审批推送、状态变更、数据同步、归档、告警、移动端同步等。

### 1.1 消息中间件

- **消息代理**: 建议采用 Kafka / RabbitMQ（具体选型在 plan 阶段决定）
- **消息格式**: JSON
- **投递语义**: At-Least-Once（至少一次），消费者需幂等
- **命名规范**: `<domain>.<entity>.<action>`（如 `project.status.changed`）

### 1.2 通用事件信封

所有事件采用统一信封格式：

```json
{
  "eventId": "evt-2026-07-10-001",
  "eventType": "project.status.changed",
  "topic": "pms.project.status",
  "source": "pms-project-service",
  "timestamp": "2026-07-10T10:30:00.000+08:00",
  "traceId": "trace-abc123",
  "tenantOfficeId": 12,
  "version": "1.0",
  "payload": {
    "...": "..."
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `eventId` | string | 是 | 事件唯一 ID（UUID） |
| `eventType` | string | 是 | 事件类型（`<domain>.<entity>.<action>`） |
| `topic` | string | 是 | 主题名 |
| `source` | string | 是 | 生产者服务名 |
| `timestamp` | string | 是 | 事件发生时间（ISO 8601） |
| `traceId` | string | 是 | 链路追踪 ID |
| `tenantOfficeId` | long | 否 | 办事处（多租户数据权限） |
| `version` | string | 是 | 事件版本 |
| `payload` | object | 是 | 事件载荷 |

### 1.3 事件类别总览

| 类别 | 主题前缀 | 事件数 | 说明 |
|------|---------|--------|------|
| 审批推送 | `pms.approval.*` | 8 | 工作流审批与钉钉推送 |
| 状态变更 | `pms.<entity>.status.*` | 9 | 项目/售前/技术公告/割接/ITR 状态机流转 |
| 数据同步 | `pms.sync.*` | 10 | CRM/供应链/服务平台/设备信息同步 |
| 归档 | `pms.archive.*` | 3 | 数据归档与冷存储 |
| 告警 | `pms.alert.*` | 5 | 超期/库存/接口失败告警 |
| 移动端 | `pms.mobile.*` | 2 | 离线同步与现场采集 |

---

## 2. 审批推送事件

### 2.1 事件清单

| 主题名 | 事件类型 | 生产者 | 消费者 | 触发时机 | 关联 FR |
|--------|---------|--------|--------|---------|--------|
| `pms.approval.submitted` | approval.submitted | 工作流服务 | 钉钉推送服务、邮件服务、消息中心 | 审批任务生成 | FR-080、FR-120、FR-125、FR-136 |
| `pms.approval.completed` | approval.completed | 工作流服务 | 业务模块、消息中心 | 审批通过/驳回 | FR-081、FR-082 |
| `pms.approval.timeout` | approval.timeout | 定时任务服务 | 邮件服务、钉钉推送服务、上级通知 | 审批超时升级（VAL-046） | FR-088、VAL-046 |
| `pms.approval.construction_plan` | approval.construction_plan | 施工计划模块 | 钉钉推送服务、服务经理 | 施工计划提交审核 | FR-120 |
| `pms.approval.impl_plan` | approval.impl_plan | 实施方案模块 | 钉钉推送服务、服务经理、总部 | 实施方案提交审核（重大项目总部复核） | FR-125 |
| `pms.approval.cutover` | approval.cutover | 割接管理模块 | 钉钉推送服务、服务经理、二线、研发 | 割接审批（A 类服务经理+二线+研发，B 类服务经理+二线） | FR-136 |
| `pms.approval.subcontract` | approval.subcontract | 转包管理模块 | 钉钉推送服务、多级审批节点 | 转包多级审批 | FR-041、SC-004 |
| `pms.approval.closure` | approval.closure | 闭环管理模块 | 钉钉推送服务、多角色审批人 | 项目闭环审批 | FR-049 |

### 2.2 载荷 JSON Schema

#### 2.2.1 approval.submitted

```json
{
  "approvalId": "apr-001",
  "businessType": "CONSTRUCTION_PLAN",
  "businessId": 1,
  "businessNo": "CP20260701001",
  "projectId": 1,
  "projectName": "XX 银行核心网络改造项目",
  "assignee": "user-sm-001",
  "assigneeName": "张服务经理",
  "candidateGroups": ["SERVICE_MANAGER"],
  "approvalTitle": "施工计划审核-XX项目",
  "approvalUrl": "https://pms.example.com/approvals/123",
  "dueDate": "2026-07-15T18:00:00+08:00",
  "priority": 1
}
```

#### 2.2.2 approval.completed

```json
{
  "approvalId": "apr-001",
  "businessType": "CONSTRUCTION_PLAN",
  "businessId": 1,
  "projectId": 1,
  "approved": true,
  "approver": "user-sm-001",
  "approverName": "张服务经理",
  "comment": "计划合理，同意",
  "completedAt": "2026-07-12T14:00:00+08:00",
  "nextNode": null,
  "nextAssignee": null
}
```

#### 2.2.3 approval.timeout

```json
{
  "approvalId": "apr-001",
  "businessType": "SUBCONTRACT",
  "businessId": 1,
  "currentNode": "ENGINEERING_MGMT",
  "assignee": "user-em-001",
  "overdueHours": 48,
  "escalateTo": "user-director-001",
  "escalateToName": "李主任",
  "reminderMessage": "转包审批已超时 48 小时，已升级通知主任"
}
```

#### 2.2.4 approval.cutover

```json
{
  "cutoverId": 1,
  "cutoverNo": "CO20260701001",
  "projectId": 1,
  "cutoverLevel": "A",
  "approvalNodes": [
    { "node": "SERVICE_MANAGER", "assignee": "user-sm-001", "order": 1 },
    { "node": "SECOND_LINE", "assignee": "user-2nd-001", "order": 2 },
    { "node": "RD", "assignee": "user-rd-001", "order": 3 }
  ],
  "requireCustomerApproval": true,
  "customerApprovalFile": "..."
}
```

---

## 3. 状态变更事件

### 3.1 事件清单

| 主题名 | 事件类型 | 生产者 | 消费者 | 触发时机 | 关联 FR |
|--------|---------|--------|--------|---------|--------|
| `pms.project.status.changed` | project.status.changed | 项目服务 | 消息中心、邮件服务、项目跟踪服务 | 项目顶层状态流转（30→31→32→40→100） | FR-002、FR-025 |
| `pms.project.phase.changed` | project.phase.changed | 项目服务 | 项目跟踪服务、报表服务 | 交付子阶段流转（8 阶段） | FR-016、FR-025 |
| `pms.project.rollback` | project.rollback | 项目服务 | 邮件服务、日志服务 | 项目回退（36/38/42），记录日志+邮件通知 | FR-003、VAL-003 |
| `pms.project.overdue` | project.overdue | 定时任务服务 | 消息中心、钉钉、邮件 | 施工阶段超期检测（VAL-039） | FR-018、VAL-038 |
| `pms.presales.status.changed` | presales.status.changed | 售前服务 | 消息中心、邮件服务 | 售前状态流转（10→31→32→33→100） | FR-036、VAL-006 |
| `pms.prob.status.changed` | prob.status.changed | 技术公告服务 | 消息中心、受影响项目 PM | 技术公告状态流转（草稿→待确认→已确认→解决中→已关闭） | FR-059、VAL-007 |
| `pms.cutover.status.changed` | cutover.status.changed | 割接管理服务 | PMS 刷新服务、ITR 同步服务 | 割接状态流转（建单→审批→执行→闭环） | FR-135~FR-140 |
| `pms.itr.status.changed` | itr.status.changed | ITR 服务 | 消息中心、邮件服务、客户档案服务 | ITR 工单状态流转（受理→排查→方案→执行→闭环） | FR-162、FR-166 |
| `pms.subcontract.status.changed` | subcontract.status.changed | 转包服务 | D365 集成服务、消息中心 | 转包状态流转（草稿→审批→合同执行→付款→回访→验收→闭环） | FR-041 |

### 3.2 载荷 JSON Schema

#### 3.2.1 project.status.changed

```json
{
  "projectId": 1,
  "projectNo": "P20260701001",
  "projectName": "XX 银行核心网络改造项目",
  "previousStatus": "31",
  "currentStatus": "32",
  "previousStatusName": "待指派PM",
  "currentStatusName": "已指派PM",
  "serviceManagerId": 200,
  "serviceManagerName": "张服务经理",
  "projectManagerId": 100,
  "projectManagerName": "李项目经理",
  "officeId": 12,
  "transitionTime": "2026-07-10T10:30:00+08:00",
  "triggerBy": "user-sm-001",
  "remark": "指定项目经理"
}
```

#### 3.2.2 project.phase.changed

```json
{
  "projectId": 1,
  "projectNo": "P20260701001",
  "previousPhase": "PRE_CONSTRUCTION",
  "currentPhase": "WRITING_IMPL_PLAN",
  "previousPhaseName": "工前准备",
  "currentPhaseName": "编写实施方案",
  "autoTransition": true,
  "triggerReason": "工前准备交付件完成判定",
  "transitionTime": "2026-07-10T11:00:00+08:00"
}
```

#### 3.2.3 project.rollback

```json
{
  "projectId": 1,
  "projectNo": "P20260701001",
  "rollbackType": "36",
  "rollbackTypeName": "SM回退",
  "fromStatus": "31",
  "toStatus": "30",
  "applicant": "user-pm-001",
  "applicantName": "李项目经理",
  "reason": "客户需求变更需重新评估",
  "notifyEmails": ["sm@example.com", "pm@example.com"],
  "rollbackTime": "2026-07-10T15:00:00+08:00"
}
```

#### 3.2.4 project.overdue

```json
{
  "projectId": 1,
  "projectNo": "P20260701001",
  "projectName": "XX 银行核心网络改造项目",
  "currentPhase": "IMPLEMENTATION_DEPLOYMENT",
  "plannedEndDate": "2026-09-30",
  "overdueDays": 5,
  "projectManagerId": 100,
  "projectManagerName": "李项目经理",
  "serviceManagerId": 200,
  "officeId": 12,
  "highlight": "RED",
  "detectedAt": "2026-10-05T00:00:00+08:00"
}
```

#### 3.2.5 cutover.status.changed

```json
{
  "cutoverId": 1,
  "cutoverNo": "CO20260701001",
  "projectId": 1,
  "previousStatus": "EXECUTING",
  "currentStatus": "CLOSED",
  "cutoverLevel": "A",
  "closedAt": "2026-07-10T20:00:00+08:00",
  "pmsRefreshRequired": true,
  "refreshItems": ["VERSION", "CPLD", "CONBOOT", "SPARE_PART_SERIAL"],
  "notifyStakeholders": ["user-pm-001", "user-sm-001", "customer-contact"]
}
```

#### 3.2.6 prob.status.changed

```json
{
  "probId": 1,
  "probNo": "PB2026-001",
  "title": "XX 产品版本安全漏洞修复公告",
  "previousStatus": "CONFIRMED",
  "currentStatus": "RESOLVING",
  "affectedProjectCount": 15,
  "matchedAutomatically": true,
  "notifyPms": true,
  "transitionTime": "2026-07-10T16:00:00+08:00"
}
```

---

## 4. 数据同步事件

### 4.1 事件清单

| 主题名 | 事件类型 | 生产者 | 消费者 | 触发时机 | 关联 FR |
|--------|---------|--------|--------|---------|--------|
| `pms.sync.crm.to_pms` | sync.crm.to_pms | CRM 集成服务 | 用户服务、客户档案服务 | CRM 用户信息变更同步至 PMS | FR-159、SC-022 |
| `pms.sync.crm.from_pms` | sync.crm.from_pms | 用户服务 | CRM 集成服务 | PMS 用户信息变更反向同步至 CRM | FR-159 |
| `pms.sync.crm.conflict` | sync.crm.conflict | CRM 集成服务 | 冲突处理服务、消息中心 | CRM 双向同步冲突 | FR-159（边缘案例） |
| `pms.sync.supply_chain.imported` | sync.supply_chain.imported | 供应链集成服务 | 设备信息服务、设备增强服务 | 供应链导入出厂产品信息与官网版本 | FR-154 |
| `pms.sync.service_platform.inspection` | sync.service_platform.inspection | 服务平台集成服务 | 设备信息服务、巡检服务 | 服务平台巡检报告同步至 PMS | FR-142 |
| `pms.sync.service_platform.device_info` | sync.service_platform.device_info | 服务平台集成服务 | 设备增强服务 | 服务平台设备信息解析结果同步 | FR-143、SC-019 |
| `pms.sync.service_platform.crt_log` | sync.service_platform.crt_log | 客户端采集服务 | 配置 Log 服务、设备增强服务 | CRT log 自动采集上传 | FR-144 |
| `pms.sync.d365.po_pushed` | sync.d365.po_pushed | D365 集成服务 | 转包服务 | 采购订单推送至 D365 | FR-046、SC-005 |
| `pms.sync.d365.receipt_callback` | sync.d365.receipt_callback | D365 集成服务 | 转包服务 | D365 采购收货状态回调 | FR-046 |
| `pms.sync.itr.archived` | sync.itr.archived | ITR 集成服务 | 客户档案服务、设备信息服务 | 故障报告归档至 ITR，关联 PMS | FR-166、SC-023 |

### 4.2 载荷 JSON Schema

#### 4.2.1 sync.crm.to_pms

```json
{
  "syncBatchId": "sync-001",
  "userCount": 10,
  "users": [
    {
      "userCode": "U001",
      "userName": "XX 银行",
      "userType": "ORDER_CUSTOMER",
      "address": "北京市...",
      "industry": "金融",
      "serviceLevel": "A",
      "company": "XX 银行",
      "department": "信息中心",
      "position": "主任",
      "contactName": "李四",
      "contactPhone": "13800138000",
      "contactEmail": "li4@bank.com"
    }
  ],
  "syncTime": "2026-07-10T10:00:00+08:00",
  "source": "CRM"
}
```

#### 4.2.2 sync.crm.conflict

```json
{
  "userId": 100,
  "userCode": "U001",
  "conflictFields": [
    {
      "field": "address",
      "pmsValue": "北京市朝阳区",
      "crmValue": "北京市海淀区",
      "pmsUpdatedBy": "user-001",
      "crmUpdatedBy": "system"
    }
  ],
  "pmsUpdatedAt": "2026-07-10T09:00:00+08:00",
  "crmUpdatedAt": "2026-07-10T09:01:00+08:00",
  "requireManualResolve": true
}
```

#### 4.2.3 sync.supply_chain.imported

```json
{
  "importBatchId": "sc-001",
  "deviceCount": 50,
  "devices": [
    {
      "serialNo": "SN001",
      "productCode": "P001",
      "productName": "防火墙-2000",
      "factorySwVersion": "V5.0",
      "factoryConboot": "C5.0",
      "factoryCpld": "CPLD5.0",
      "officialVersion": "V5.0",
      "matchedAutomatically": true
    }
  ],
  "dataInconsistencyAlerts": [
    {
      "serialNo": "SN002",
      "field": "productName",
      "pmsExisting": "FW-2000",
      "supplyChainImported": "Firewall-2000",
      "requireManualCheck": true
    }
  ],
  "importTime": "2026-07-10T11:00:00+08:00"
}
```

#### 4.2.4 sync.service_platform.inspection

```json
{
  "inspectionTaskId": 1,
  "deviceSerialId": 1,
  "serialNo": "SN001",
  "reportUrl": "https://umc.example.com/reports/001",
  "inspectionLogUrl": "https://umc.example.com/logs/001",
  "umcEnv": "PROD",
  "syncedToPms": true,
  "syncTime": "2026-07-10T12:00:00+08:00"
}
```

#### 4.2.5 sync.service_platform.device_info

```json
{
  "deviceSerialId": 1,
  "serialNo": "SN001",
  "configInfo": "...",
  "runningFunctions": "防火墙,VPN,IPS",
  "deployRiskAnalysis": "单机部署风险，建议冗余",
  "syncTime": "2026-07-10T12:30:00+08:00",
  "source": "SERVICE_PLATFORM"
}
```

#### 4.2.6 sync.d365.po_pushed

```json
{
  "subcontractId": 1,
  "subcontractNo": "SC20260701001",
  "d365PoNo": "PO-D365-001",
  "poStatus": "PUSHED",
  "pushTime": "2026-07-10T13:00:00+08:00",
  "success": true,
  "retryCount": 0
}
```

#### 4.2.7 sync.itr.archived

```json
{
  "ticketId": 1,
  "ticketNo": "ITR-001",
  "userId": 100,
  "deviceSerialId": 1,
  "projectId": 1,
  "rootCause": "...",
  "solution": "...",
  "fixVersion": "V5.1",
  "probId": 1,
  "bugNo": "BUG-001",
  "archivedAt": "2026-07-10T14:00:00+08:00",
  "customerArchiveType": "FAULT"
}
```

---

## 5. 归档事件

### 5.1 事件清单

| 主题名 | 事件类型 | 生产者 | 消费者 | 触发时机 | 关联 FR |
|--------|---------|--------|--------|---------|--------|
| `pms.archive.retention_expired` | archive.retention_expired | 定时任务服务 | 归档服务 | 数据保留期限到期（VAL-041） | FR-168 |
| `pms.archive.moved_to_cold` | archive.moved_to_cold | 归档服务 | 冷存储服务、日志服务 | 数据归档至冷存储 | FR-168、FR-169 |
| `pms.archive.restored` | archive.restored | 归档服务 | 业务模块、消息中心 | 从冷存储按需取回 | FR-169 |

### 5.2 载荷 JSON Schema

#### 5.2.1 archive.retention_expired

```json
{
  "archiveId": 1,
  "entityType": "DELIVERABLE",
  "entityId": 100,
  "projectId": 1,
  "retentionYears": 5,
  "createdDate": "2021-07-10",
  "expiredDate": "2026-07-10",
  "fileUrl": "...",
  "requireArchive": true
}
```

#### 5.2.2 archive.moved_to_cold

```json
{
  "archiveId": 1,
  "entityType": "CONFIG_LOG",
  "entityId": 200,
  "coldStorageObjectKey": "cold-storage/2026/07/config-log-200.bin",
  "originalUrl": "...",
  "archivedAt": "2026-07-10T02:00:00+08:00",
  "asyncProcessed": true,
  "retentionPermanent": false
}
```

#### 5.2.3 archive.restored

```json
{
  "archiveId": 1,
  "entityType": "DELIVERABLE",
  "entityId": 100,
  "coldStorageObjectKey": "cold-storage/2026/07/deliverable-100.bin",
  "restoredUrl": "...",
  "requestedBy": "user-001",
  "restoredAt": "2026-07-10T10:00:00+08:00",
  "asyncProcessed": true
}
```

**归档策略对照**（VAL-041、VAL-042）：

| 数据类型 | 保留期限 | 归档事件触发 |
|---------|---------|-------------|
| 交付件 | ≥5 年 | `archive.retention_expired`（5 年到期） |
| 配置 Log | ≥5 年 | `archive.retention_expired`（5 年到期） |
| 巡检报告 | ≥3 年 | `archive.retention_expired`（3 年到期） |
| 割接归档 | ≥3 年 | `archive.retention_expired`（3 年到期） |
| AI 训练数据 | 长期保留（脱敏后） | `archive.moved_to_cold`（脱敏后归档，`retentionPermanent=true`） |

---

## 6. 告警事件

### 6.1 事件清单

| 主题名 | 事件类型 | 生产者 | 消费者 | 触发时机 | 关联 FR |
|--------|---------|--------|--------|---------|--------|
| `pms.alert.project_overdue` | alert.project_overdue | 定时任务服务 | 消息中心、钉钉、邮件 | 项目施工阶段超期 | FR-018、VAL-038、VAL-039 |
| `pms.alert.presales_overdue` | alert.presales_overdue | 定时任务服务 | 消息中心、邮件 | 售前测试超期未闭环 | FR-036（边缘案例） |
| `pms.alert.spare_part_low` | alert.spare_part_low | 割接管理服务 | SPMS 集成服务、消息中心 | 割接需备件但库存不足（VAL-032） | FR-139、VAL-032 |
| `pms.alert.integration_failure` | alert.integration_failure | 集成服务 | 消息中心、邮件、日志服务 | 外部系统集成调用失败 | FR-046、FR-101、VAL-045 |
| `pms.alert.license_failure` | alert.license_failure | 售前授权服务 | 消息中心、邮件、钉钉 | 临时授权下发失败（VAL-050） | FR-039、VAL-050 |

### 6.2 载荷 JSON Schema

#### 6.2.1 alert.project_overdue

```json
{
  "alertId": "alt-001",
  "alertType": "PROJECT_OVERDUE",
  "severity": "HIGH",
  "projectId": 1,
  "projectNo": "P20260701001",
  "projectName": "XX 银行核心网络改造项目",
  "currentPhase": "IMPLEMENTATION_DEPLOYMENT",
  "plannedEndDate": "2026-09-30",
  "overdueDays": 5,
  "projectManagerId": 100,
  "projectManagerName": "李项目经理",
  "serviceManagerId": 200,
  "officeId": 12,
  "alertTime": "2026-10-05T08:00:00+08:00",
  "notifyChannels": ["DINGTALK", "EMAIL", "MESSAGE_CENTER"],
  "highlight": "RED"
}
```

#### 6.2.2 alert.spare_part_low

```json
{
  "alertId": "alt-002",
  "alertType": "SPARE_PART_LOW",
  "severity": "CRITICAL",
  "cutoverId": 1,
  "cutoverNo": "CO20260701001",
  "projectId": 1,
  "requiredParts": [
    { "partNo": "SP001", "partName": "电源模块", "requiredQty": 2, "availableQty": 0 }
  ],
  "blockCutover": true,
  "alertTime": "2026-07-10T16:00:00+08:00",
  "notifySpms": true
}
```

#### 6.2.3 alert.integration_failure

```json
{
  "alertId": "alt-003",
  "alertType": "INTEGRATION_FAILURE",
  "severity": "HIGH",
  "targetSystem": "D365",
  "integrationName": "推送采购订单",
  "endpoint": "POST /d365/purchase-orders",
  "errorMessage": "OAuth2 Token 刷新失败",
  "retryCount": 3,
  "lastRetryAt": "2026-07-10T17:00:00+08:00",
  "businessContext": {
    "subcontractId": 1,
    "subcontractNo": "SC20260701001"
  },
  "fallbackTriggered": true,
  "fallbackStrategy": "记录待同步任务，不阻塞转包业务流程",
  "alertTime": "2026-07-10T17:01:00+08:00"
}
```

#### 6.2.4 alert.license_failure

```json
{
  "alertId": "alt-004",
  "alertType": "LICENSE_ACQUISITION_FAILURE",
  "severity": "HIGH",
  "presalesId": 1,
  "presalesNo": "PS20260701001",
  "deviceSerial": "SN001",
  "licenseType": "首次临时授权",
  "errorMessage": "授权下发通道不可达",
  "retryCount": 3,
  "maxRetry": 5,
  "alertTime": "2026-07-10T18:00:00+08:00",
  "requireManualIntervention": true
}
```

---

## 7. 移动端同步事件

### 7.1 事件清单

| 主题名 | 事件类型 | 生产者 | 消费者 | 触发时机 | 关联 FR |
|--------|---------|--------|--------|---------|--------|
| `pms.mobile.offline_sync` | mobile.offline_sync | 移动端同步服务 | 业务模块、文件存储服务 | 弱网环境联网后自动同步离线数据 | FR-093 |
| `pms.mobile.field_collected` | mobile.field_collected | 工程师移动端 | 实施部署服务、文件存储服务 | 现场采集类数据上传（施工照片/工勘表单/配置 Log/签到记录） | FR-090、FR-094 |

### 7.2 载荷 JSON Schema

#### 7.2.1 mobile.offline_sync

```json
{
  "syncBatchId": "sync-mobile-001",
  "userId": "user-engineer-001",
  "clientType": "ENGINEER_H5",
  "syncItems": [
    {
      "itemType": "CHECK_IN",
      "itemId": "ck-001",
      "projectId": 1,
      "data": {
        "latitude": 39.9,
        "longitude": 116.4,
        "photoUrl": "...",
        "checkInTime": "2026-07-10T08:00:00+08:00"
      }
    },
    {
      "itemType": "CONSTRUCTION_PHOTO",
      "itemId": "ph-001",
      "deviceId": 1,
      "data": {
        "photoUrl": "...",
        "watermark": "时间+GPS+上传人",
        "uploadedAt": "2026-07-10T09:00:00+08:00"
      }
    }
  ],
  "syncTime": "2026-07-10T12:00:00+08:00",
  "totalCount": 2,
  "successCount": 2,
  "failedCount": 0
}
```

#### 7.2.2 mobile.field_collected

```json
{
  "userId": "user-engineer-001",
  "clientType": "ENGINEER_H5",
  "projectId": 1,
  "dataType": "CONSTRUCTION_PHOTO",
  "deviceId": 1,
  "data": {
    "photoUrl": "...",
    "watermark": {
      "time": "2026-07-10T09:00:00+08:00",
      "gps": "39.9042,116.4074",
      "uploadedBy": "user-engineer-001"
    },
    "antiCheat": true
  },
  "collectedAt": "2026-07-10T09:00:00+08:00"
}
```

**离线缓存范围约束**（FR-093、VAL-048）：
- 允许离线：只读参考数据（项目信息/设备清单/实施方案）+ 现场采集类数据（施工照片/工勘表单/配置 Log/签到记录）
- 禁止离线：审批/状态变更等写操作 MUST 联机执行

---

## 8. 消费者幂等性约定

所有事件消费者 MUST 实现幂等处理：

1. **基于 eventId 去重**：消费者记录已处理的 `eventId`，重复事件丢弃
2. **基于业务键去重**：如 `projectId + transitionTime`，重复状态变更丢弃
3. **乐观锁保护**：消费时携带 `version`，冲突时跳过

---

## 9. 事件主题总览

| # | 主题名 | 类别 | 生产者 | 主要消费者 |
|---|--------|------|--------|-----------|
| 1 | `pms.approval.submitted` | 审批推送 | 工作流服务 | 钉钉、邮件、消息中心 |
| 2 | `pms.approval.completed` | 审批推送 | 工作流服务 | 业务模块、消息中心 |
| 3 | `pms.approval.timeout` | 审批推送 | 定时任务服务 | 邮件、钉钉、上级通知 |
| 4 | `pms.approval.construction_plan` | 审批推送 | 施工计划模块 | 钉钉、服务经理 |
| 5 | `pms.approval.impl_plan` | 审批推送 | 实施方案模块 | 钉钉、服务经理、总部 |
| 6 | `pms.approval.cutover` | 审批推送 | 割接管理模块 | 钉钉、服务经理、二线、研发 |
| 7 | `pms.approval.subcontract` | 审批推送 | 转包管理模块 | 钉钉、多级审批节点 |
| 8 | `pms.approval.closure` | 审批推送 | 闭环管理模块 | 钉钉、多角色审批人 |
| 9 | `pms.project.status.changed` | 状态变更 | 项目服务 | 消息中心、邮件、跟踪服务 |
| 10 | `pms.project.phase.changed` | 状态变更 | 项目服务 | 跟踪服务、报表服务 |
| 11 | `pms.project.rollback` | 状态变更 | 项目服务 | 邮件、日志服务 |
| 12 | `pms.project.overdue` | 状态变更 | 定时任务服务 | 消息中心、钉钉、邮件 |
| 13 | `pms.presales.status.changed` | 状态变更 | 售前服务 | 消息中心、邮件 |
| 14 | `pms.prob.status.changed` | 状态变更 | 技术公告服务 | 消息中心、受影响项目 PM |
| 15 | `pms.cutover.status.changed` | 状态变更 | 割接管理服务 | PMS 刷新服务、ITR 同步服务 |
| 16 | `pms.itr.status.changed` | 状态变更 | ITR 服务 | 消息中心、邮件、客户档案服务 |
| 17 | `pms.subcontract.status.changed` | 状态变更 | 转包服务 | D365 集成服务、消息中心 |
| 18 | `pms.sync.crm.to_pms` | 数据同步 | CRM 集成服务 | 用户服务、客户档案服务 |
| 19 | `pms.sync.crm.from_pms` | 数据同步 | 用户服务 | CRM 集成服务 |
| 20 | `pms.sync.crm.conflict` | 数据同步 | CRM 集成服务 | 冲突处理服务、消息中心 |
| 21 | `pms.sync.supply_chain.imported` | 数据同步 | 供应链集成服务 | 设备信息服务、设备增强服务 |
| 22 | `pms.sync.service_platform.inspection` | 数据同步 | 服务平台集成服务 | 设备信息服务、巡检服务 |
| 23 | `pms.sync.service_platform.device_info` | 数据同步 | 服务平台集成服务 | 设备增强服务 |
| 24 | `pms.sync.service_platform.crt_log` | 数据同步 | 客户端采集服务 | 配置 Log 服务、设备增强服务 |
| 25 | `pms.sync.d365.po_pushed` | 数据同步 | D365 集成服务 | 转包服务 |
| 26 | `pms.sync.d365.receipt_callback` | 数据同步 | D365 集成服务 | 转包服务 |
| 27 | `pms.sync.itr.archived` | 数据同步 | ITR 集成服务 | 客户档案服务、设备信息服务 |
| 28 | `pms.archive.retention_expired` | 归档 | 定时任务服务 | 归档服务 |
| 29 | `pms.archive.moved_to_cold` | 归档 | 归档服务 | 冷存储服务、日志服务 |
| 30 | `pms.archive.restored` | 归档 | 归档服务 | 业务模块、消息中心 |
| 31 | `pms.alert.project_overdue` | 告警 | 定时任务服务 | 消息中心、钉钉、邮件 |
| 32 | `pms.alert.presales_overdue` | 告警 | 定时任务服务 | 消息中心、邮件 |
| 33 | `pms.alert.spare_part_low` | 告警 | 割接管理服务 | SPMS 集成服务、消息中心 |
| 34 | `pms.alert.integration_failure` | 告警 | 集成服务 | 消息中心、邮件、日志服务 |
| 35 | `pms.alert.license_failure` | 告警 | 售前授权服务 | 消息中心、邮件、钉钉 |
| 36 | `pms.mobile.offline_sync` | 移动端 | 移动端同步服务 | 业务模块、文件存储服务 |
| 37 | `pms.mobile.field_collected` | 移动端 | 工程师移动端 | 实施部署服务、文件存储服务 |

---

*文档结束*
