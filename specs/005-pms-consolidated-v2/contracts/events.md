# 事件契约：PMS 项目交付管理系统

**Date**: 2026-07-10
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Research**: [research.md](../research.md)

## 通用约定

### 消息中间件

RocketMQ 5.x（异步事件：审批推送/数据同步/归档/离线同步事件）

### 主题命名规范

主题命名格式：`pms-{domain}-{event}`

- 全部小写，单词用连字符分隔
- domain 为业务域
- event 为具体事件动作（过去式）

### 消息通用结构

所有消息遵循统一信封格式：

```json
{
  "eventId": "evt-uuid-001",
  "eventType": "project.created",
  "topic": "pms-project-created",
  "timestamp": "2026-07-10T10:00:00.000Z",
  "source": "pms-project-service",
  "tenantId": "default",
  "traceId": "trace-xxx",
  "payload": { }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| eventId | string | 事件唯一 ID（UUID） |
| eventType | string | 事件类型 |
| topic | string | RocketMQ 主题名 |
| timestamp | string | 事件产生时间（ISO 8601） |
| source | string | 事件源服务 |
| tenantId | string | 租户 ID |
| traceId | string | 链路追踪 ID（SkyWalking） |
| payload | object | 事件载荷（业务数据） |

### 消息可靠性

- 投递语义：At-least-once（至少一次），消费者需幂等
- 消费失败：重试 3 次后进入死信队列（DLQ），告警通知运维
- 消息顺序：同一业务记录的事件按 key 分区保证顺序（rocketmq-tag）

---

## 1. 项目事件

### 1.1 project.created - 项目创建

**主题**：`pms-project-created`
**生产者**：pms-project-service（项目立项）
**消费者**：钉钉通知服务、报表服务、CRM 同步服务
**触发时机**：合同号录入并创建项目，状态置为"30 已创建"

```json
{
  "eventId": "evt-001",
  "eventType": "project.created",
  "topic": "pms-project-created",
  "timestamp": "2026-07-10T10:00:00Z",
  "source": "pms-project-service",
  "payload": {
    "projectId": 10001,
    "projectName": "XX网络升级项目",
    "contractNo": "HT2026001",
    "projectType": "direct",
    "projectLevel": "A",
    "customerId": 20001,
    "officeId": 3001,
    "statusCode": "30",
    "statusName": "已创建",
    "createdBy": { "userId": 1, "username": "admin" },
    "parentId": null
  }
}
```

### 1.2 project.status-changed - 项目状态流转

**主题**：`pms-project-status-changed`
**生产者**：pms-project-service（状态机流转）
**消费者**：钉钉通知服务、报表服务、总体跟踪服务
**触发时机**：项目状态流转（30→31→32→40→100）

```json
{
  "eventId": "evt-002",
  "eventType": "project.status-changed",
  "topic": "pms-project-status-changed",
  "timestamp": "2026-07-10T11:00:00Z",
  "source": "pms-project-service",
  "payload": {
    "projectId": 10001,
    "fromStatus": "30",
    "fromStatusName": "已创建",
    "toStatus": "31",
    "toStatusName": "待指派PM",
    "changedBy": { "userId": 1, "username": "admin" },
    "assignee": { "userId": 5, "username": "sm_zhang", "role": "SM" },
    "subStage": null,
    "reason": "指定服务经理"
  }
}
```

### 1.3 project.sub-stage-changed - 交付子阶段流转

**主题**：`pms-project-sub-stage-changed`
**生产者**：pms-delivery-service（交付子阶段自动流转）
**消费者**：报表服务、跟踪服务
**触发时机**：交付子阶段自动流转（FR-020 双层并行模型，已完成上一阶段所有工作和产出时自动进入下一阶段）

```json
{
  "eventId": "evt-003",
  "eventType": "project.sub-stage-changed",
  "topic": "pms-project-sub-stage-changed",
  "timestamp": "2026-07-10T12:00:00Z",
  "source": "pms-delivery-service",
  "payload": {
    "projectId": 10001,
    "fromStage": "prework",
    "fromStageName": "工前准备",
    "toStage": "scheme",
    "toStageName": "编写实施方案",
    "autoTriggered": true,
    "completedOutputs": ["site_survey", "requirement_analysis"]
  }
}
```

### 1.4 project.closed - 项目闭环

**主题**：`pms-project-closed`
**生产者**：pms-project-service（闭环审批通过）
**消费者**：归档服务、报表服务、维保服务、CRM 同步服务
**触发时机**：项目闭环申请审批通过，状态流转为"100 已闭环"

```json
{
  "eventId": "evt-004",
  "eventType": "project.closed",
  "topic": "pms-project-closed",
  "timestamp": "2026-07-10T15:00:00Z",
  "source": "pms-project-service",
  "payload": {
    "projectId": 10001,
    "projectName": "XX网络升级项目",
    "closedBy": { "userId": 1, "username": "admin" },
    "closureReason": "项目验收完成",
    "closedAt": "2026-07-10T15:00:00Z",
    "warrantyStartDate": "2026-07-10"
  }
}
```

### 1.5 project.overdue - 项目超期

**主题**：`pms-project-overdue`
**生产者**：pms-delivery-service（定时扫描）
**消费者**：钉钉通知服务、报表服务、告警服务
**触发时机**：施工阶段超期

```json
{
  "eventId": "evt-005",
  "eventType": "project.overdue",
  "topic": "pms-project-overdue",
  "timestamp": "2026-07-10T08:00:00Z",
  "source": "pms-delivery-service",
  "payload": {
    "projectId": 10001,
    "projectName": "XX网络升级项目",
    "overdueStage": "deploy",
    "overdueStageName": "实施部署",
    "planTime": "2026-07-01",
    "overdueDays": 9,
    "pmUserId": 10,
    "smUserId": 5
  }
}
```

---

## 2. 审批事件

### 2.1 approval.submitted - 审批提交

**主题**：`pms-approval-submitted`
**生产者**：pms-workflow-service（Flowable 流程引擎）
**消费者**：钉钉通知服务、待办服务
**触发时机**：施工计划审核/实施方案审核/转包审批/闭环审批等提交

```json
{
  "eventId": "evt-010",
  "eventType": "approval.submitted",
  "topic": "pms-approval-submitted",
  "timestamp": "2026-07-10T14:00:00Z",
  "source": "pms-workflow-service",
  "payload": {
    "approvalId": "ap-001",
    "businessType": "construction_plan",
    "businessId": "plan-5001",
    "projectId": 10001,
    "approvalTitle": "XX项目施工计划审核",
    "submitter": { "userId": 10, "username": "pm_zhang" },
    "approvers": [
      { "userId": 5, "username": "sm_li", "role": "SM" }
    ],
    "approvalLevel": "normal",
    "deadline": "2026-07-12T14:00:00Z"
  }
}
```

### 2.2 approval.approved - 审批通过

**主题**：`pms-approval-approved`
**生产者**：pms-workflow-service
**消费者**：业务模块（触发后续流程）、钉钉通知服务
**触发时机**：审批通过

```json
{
  "eventId": "evt-011",
  "eventType": "approval.approved",
  "topic": "pms-approval-approved",
  "timestamp": "2026-07-10T16:00:00Z",
  "source": "pms-workflow-service",
  "payload": {
    "approvalId": "ap-001",
    "businessType": "construction_plan",
    "businessId": "plan-5001",
    "projectId": 10001,
    "approver": { "userId": 5, "username": "sm_li", "role": "SM" },
    "comment": "计划合理，通过",
    "approvedAt": "2026-07-10T16:00:00Z"
  }
}
```

### 2.3 approval.rejected - 审批驳回

**主题**：`pms-approval-rejected`
**生产者**：pms-workflow-service
**消费者**：业务模块（回退流程）、钉钉通知服务
**触发时机**：审批驳回

```json
{
  "eventId": "evt-012",
  "eventType": "approval.rejected",
  "topic": "pms-approval-rejected",
  "timestamp": "2026-07-10T16:00:00Z",
  "source": "pms-workflow-service",
  "payload": {
    "approvalId": "ap-001",
    "businessType": "construction_plan",
    "businessId": "plan-5001",
    "projectId": 10001,
    "approver": { "userId": 5, "username": "sm_li", "role": "SM" },
    "comment": "工期安排过紧，请调整",
    "rejectedAt": "2026-07-10T16:00:00Z"
  }
}
```

---

## 3. 交付事件

### 3.1 delivery.sub-stage-changed - 交付子阶段变更

**主题**：`pms-delivery-sub-stage-changed`
**生产者**：pms-delivery-service
**消费者**：跟踪服务、报表服务
**触发时机**：交付子阶段流转（与 project.sub-stage-changed 互补，本事件聚焦交付产出完成度）

```json
{
  "eventId": "evt-020",
  "eventType": "delivery.sub-stage-changed",
  "topic": "pms-delivery-sub-stage-changed",
  "timestamp": "2026-07-10T12:00:00Z",
  "source": "pms-delivery-service",
  "payload": {
    "projectId": 10001,
    "fromStage": "prework",
    "toStage": "plan",
    "stageOutputs": {
      "siteSurvey": "completed",
      "requirementAnalysis": "completed",
      "handoverDoc": "generated"
    }
  }
}
```

### 3.2 delivery.overdue - 交付超期

**主题**：`pms-delivery-overdue`
**生产者**：pms-delivery-service（定时扫描）
**消费者**：钉钉通知服务、告警服务
**触发时机**：交付阶段超期

```json
{
  "eventId": "evt-021",
  "eventType": "delivery.overdue",
  "topic": "pms-delivery-overdue",
  "timestamp": "2026-07-10T08:00:00Z",
  "source": "pms-delivery-service",
  "payload": {
    "projectId": 10001,
    "overdueStage": "deploy",
    "planTime": "2026-07-01",
    "actualTime": null,
    "overdueDays": 9,
    "severity": "high",
    "notifyUsers": [10, 5]
  }
}
```

---

## 4. 客户事件

### 4.1 customer.synced - 客户信息同步

**主题**：`pms-customer-synced`
**生产者**：CRM 同步服务
**消费者**：客户资产库服务、项目服务
**触发时机**：CRM 客户信息同步至 PMS（双向同步延迟 ≤5 分钟）

```json
{
  "eventId": "evt-030",
  "eventType": "customer.synced",
  "topic": "pms-customer-synced",
  "timestamp": "2026-07-10T10:30:00Z",
  "source": "pms-customer-sync-service",
  "payload": {
    "customerId": 20001,
    "customerCode": "C001",
    "customerName": "XX集团",
    "syncDirection": "from_crm",
    "changedFields": ["address", "contacts"],
    "syncLatencyMs": 120000
  }
}
```

### 4.2 customer.service-level-changed - 客户服务等级变更

**主题**：`pms-customer-service-level-changed`
**生产者**：客户资产库服务
**消费者**：项目服务（更新关联项目联系人服务等级）
**触发时机**：客户资产库修改服务等级，同步延迟 ≤1 分钟

```json
{
  "eventId": "evt-031",
  "eventType": "customer.service-level-changed",
  "topic": "pms-customer-service-level-changed",
  "timestamp": "2026-07-10T10:31:00Z",
  "source": "pms-customer-service",
  "payload": {
    "customerId": 20001,
    "fromLevel": "normal",
    "toLevel": "VIP",
    "changedBy": { "userId": 1, "username": "admin" },
    "affectedProjectIds": [10001, 10002, 10003]
  }
}
```

---

## 5. 设备事件

### 5.1 device.config-updated - 设备配置更新

**主题**：`pms-device-config-updated`
**生产者**：pms-deploy-service（配置 Log 解析）
**消费者**：设备信息增强服务、客户资产库服务
**触发时机**：配置 Log 读取或本地上传后解析配置信息回填

```json
{
  "eventId": "evt-040",
  "eventType": "device.config-updated",
  "topic": "pms-device-config-updated",
  "timestamp": "2026-07-10T13:00:00Z",
  "source": "pms-deploy-service",
  "payload": {
    "deviceId": "dev-001",
    "serialNo": "SN001",
    "projectId": 10001,
    "configSource": "log_read",
    "updatedFields": ["ip", "version", "vlan"],
    "configVersion": 2
  }
}
```

### 5.2 device.info-enhanced - 设备信息增强

**主题**：`pms-device-info-enhanced`
**生产者**：pms-device-service（设备信息增强模块）
**消费者**：客户资产库服务、报表服务
**触发时机**：设备配置历史/部署风险/接口对照/版本信息更新

```json
{
  "eventId": "evt-041",
  "eventType": "device.info-enhanced",
  "topic": "pms-device-info-enhanced",
  "timestamp": "2026-07-10T13:30:00Z",
  "source": "pms-device-service",
  "payload": {
    "deviceId": "dev-001",
    "serialNo": "SN001",
    "enhancementType": "interface_matrix",
    "projectId": 10001,
    "topologyGenerated": true
  }
}
```

---

## 6. 割接事件

### 6.1 cutover.initiated - 割接发起

**主题**：`pms-cutover-initiated`
**生产者**：pms-cutover-service
**消费者**：割接管理平台集成服务、钉钉通知服务
**触发时机**：割接上线前期流程完成，发起割接

```json
{
  "eventId": "evt-050",
  "eventType": "cutover.initiated",
  "topic": "pms-cutover-initiated",
  "timestamp": "2026-07-10T20:00:00Z",
  "source": "pms-cutover-service",
  "payload": {
    "cutoverId": "ct-001",
    "projectId": 10001,
    "operationId": "op-001",
    "initiatedBy": { "userId": 10, "username": "pm_zhang" },
    "cutoverPlan": {
      "startTime": "2026-07-10T22:00:00Z",
      "endTime": "2026-07-11T02:00:00Z"
    },
    "checklistCompleted": true
  }
}
```

### 6.2 cutover.completed - 割接完成

**主题**：`pms-cutover-completed`
**生产者**：割接管理平台集成服务（Webhook 回传）
**消费者**：pms-cutover-service、归档服务、报表服务
**触发时机**：割接平台闭环刷新 PMS

```json
{
  "eventId": "evt-051",
  "eventType": "cutover.completed",
  "topic": "pms-cutover-completed",
  "timestamp": "2026-07-11T02:30:00Z",
  "source": "pms-cutover-integration-service",
  "payload": {
    "cutoverId": "ct-001",
    "projectId": 10001,
    "operationId": "op-001",
    "closureStatus": "success",
    "completedAt": "2026-07-11T02:30:00Z",
    "platformClosureTime": "2026-07-11T02:25:00Z"
  }
}
```

### 6.3 cutover.failed - 割接失败

**主题**：`pms-cutover-failed`
**生产者**：割接管理平台集成服务
**消费者**：pms-cutover-service、钉钉通知服务、告警服务
**触发时机**：割接执行失败

```json
{
  "eventId": "evt-052",
  "eventType": "cutover.failed",
  "topic": "pms-cutover-failed",
  "timestamp": "2026-07-11T01:00:00Z",
  "source": "pms-cutover-integration-service",
  "payload": {
    "cutoverId": "ct-001",
    "projectId": 10001,
    "operationId": "op-001",
    "failReason": "设备配置回滚失败",
    "failedAt": "2026-07-11T01:00:00Z",
    "rollbackTriggered": true,
    "notifyUsers": [10, 5]
  }
}
```

---

## 7. 集成事件

### 7.1 integration.d365-pushed - D365 推送

**主题**：`pms-integration-d365-pushed`
**生产者**：D365 集成服务
**消费者**：转包服务、报表服务
**触发时机**：转包审批通过，向 D365 推送采购订单

```json
{
  "eventId": "evt-060",
  "eventType": "integration.d365-pushed",
  "topic": "pms-integration-d365-pushed",
  "timestamp": "2026-07-10T17:00:00Z",
  "source": "pms-d365-integration-service",
  "payload": {
    "integrationId": "int-001",
    "system": "D365",
    "operation": "push_purchase_order",
    "businessType": "subcontract",
    "businessId": "sub-001",
    "purchaseOrderNo": "PO2026001",
    "pushStatus": "success",
    "latencyMs": 800
  }
}
```

### 7.2 integration.crm-synced - CRM 同步

**主题**：`pms-integration-crm-synced`
**生产者**：CRM 同步服务
**消费者**：客户服务、报表服务
**触发时机**：CRM 双向同步完成

```json
{
  "eventId": "evt-061",
  "eventType": "integration.crm-synced",
  "topic": "pms-integration-crm-synced",
  "timestamp": "2026-07-10T10:30:00Z",
  "source": "pms-crm-sync-service",
  "payload": {
    "integrationId": "int-002",
    "system": "CRM",
    "syncDirection": "bidirectional",
    "syncedRecords": 15,
    "syncLatencyMs": 120000,
    "syncStatus": "success"
  }
}
```

### 7.3 integration.itr-created - ITR 工单创建

**主题**：`pms-integration-itr-created`
**生产者**：ITR 集成服务
**消费者**：AI 排障服务、报表服务
**触发时机**：PMS 创建 ITR 故障工单并推送至 ITR 系统

```json
{
  "eventId": "evt-062",
  "eventType": "integration.itr-created",
  "topic": "pms-integration-itr-created",
  "timestamp": "2026-07-10T11:00:00Z",
  "source": "pms-itr-integration-service",
  "payload": {
    "integrationId": "int-003",
    "system": "ITR",
    "ticketNo": "ITR2026001",
    "customerId": 20001,
    "deviceId": "dev-001",
    "faultType": "hardware",
    "createdBy": { "userId": 10, "username": "pm_zhang" }
  }
}
```

### 7.4 integration.rma-invoked - RMA 调用

**主题**：`pms-integration-rma-invoked`
**生产者**：RMA 集成服务
**消费者**：ITR 服务、客户资产库服务
**触发时机**：ITR 故障判定为硬件故障，调用 RMA 流程

```json
{
  "eventId": "evt-063",
  "eventType": "integration.rma-invoked",
  "topic": "pms-integration-rma-invoked",
  "timestamp": "2026-07-10T11:30:00Z",
  "source": "pms-rma-integration-service",
  "payload": {
    "integrationId": "int-004",
    "system": "RMA",
    "rmaNo": "RMA2026001",
    "itrTicketNo": "ITR2026001",
    "deviceId": "dev-001",
    "faultType": "hardware",
    "invokeStatus": "success"
  }
}
```

---

## 8. 数据迁移事件

### 8.1 migration.started - 迁移开始

**主题**：`pms-migration-started`
**生产者**：pms-migration-service
**消费者**：报表服务、告警服务
**触发时机**：启动数据迁移（Python ETL + Debezium CDC）

```json
{
  "eventId": "evt-070",
  "eventType": "migration.started",
  "topic": "pms-migration-started",
  "timestamp": "2026-07-10T02:00:00Z",
  "source": "pms-migration-service",
  "payload": {
    "migrationId": "mig-001",
    "batch": "office-3001",
    "totalTables": 286,
    "totalViews": 43,
    "startedBy": { "userId": 1, "username": "admin" },
    "strategy": "etl_cdc_incremental"
  }
}
```

### 8.2 migration.completed - 迁移完成

**主题**：`pms-migration-completed`
**生产者**：pms-migration-service
**消费者**：报表服务、灰度切换服务
**触发时机**：数据迁移完成并通过完整性校验

```json
{
  "eventId": "evt-071",
  "eventType": "migration.completed",
  "topic": "pms-migration-completed",
  "timestamp": "2026-07-10T06:00:00Z",
  "source": "pms-migration-service",
  "payload": {
    "migrationId": "mig-001",
    "batch": "office-3001",
    "migratedRecords": 1500000,
    "verificationPassed": true,
    "recordCountMatch": true,
    "sampleFieldMatch": true,
    "duration": "4h"
  }
}
```

### 8.3 migration.rollback - 迁移回滚

**主题**：`pms-migration-rollback`
**生产者**：pms-migration-service
**消费者**：告警服务、报表服务
**触发时机**：灰度切换失败，回滚至老系统

```json
{
  "eventId": "evt-072",
  "eventType": "migration.rollback",
  "topic": "pms-migration-rollback",
  "timestamp": "2026-07-10T08:00:00Z",
  "source": "pms-migration-service",
  "payload": {
    "migrationId": "mig-001",
    "batch": "office-3001",
    "rollbackReason": "完整性校验失败",
    "rollbackStatus": "success",
    "oldSystemActivated": true
  }
}
```

---

## 9. 离线同步事件

### 9.1 sync.started - 同步开始

**主题**：`pms-sync-started`
**生产者**：桌面客户端（经同步服务端转发）
**消费者**：监控服务、报表服务
**触发时机**：桌面客户端联网后发起同步

```json
{
  "eventId": "evt-080",
  "eventType": "sync.started",
  "topic": "pms-sync-started",
  "timestamp": "2026-07-10T09:00:00Z",
  "source": "pms-sync-service",
  "payload": {
    "userId": 10,
    "deviceId": "client-node-001",
    "lastConsumedLogId": 10000,
    "pendingOps": 5,
    "offlineDuration": "2h30m"
  }
}
```

### 9.2 sync.completed - 同步完成

**主题**：`pms-sync-completed`
**生产者**：pms-sync-service
**消费者**：监控服务
**触发时机**：同步完成（含 ACK）

```json
{
  "eventId": "evt-081",
  "eventType": "sync.completed",
  "topic": "pms-sync-completed",
  "timestamp": "2026-07-10T09:00:30Z",
  "source": "pms-sync-service",
  "payload": {
    "userId": 10,
    "deviceId": "client-node-001",
    "syncedOps": 5,
    "conflictsDetected": 0,
    "duration": "30s",
    "latestLogId": 10050,
    "syncStatus": "success"
  }
}
```

### 9.3 sync.conflict-detected - 冲突检测

**主题**：`pms-sync-conflict-detected`
**生产者**：pms-sync-service
**消费者**：监控服务、告警服务
**触发时机**：同步过程中检测到字段级冲突

```json
{
  "eventId": "evt-082",
  "eventType": "sync.conflict-detected",
  "topic": "pms-sync-conflict-detected",
  "timestamp": "2026-07-10T09:00:15Z",
  "source": "pms-sync-service",
  "payload": {
    "userId": 10,
    "deviceId": "client-node-001",
    "conflictId": "conflict-001",
    "recordId": "impl-scheme-5001",
    "entityType": "implementation_scheme",
    "field": "configScript",
    "conflictType": "real_conflict",
    "baseVersion": 3,
    "currentVersion": 5
  }
}
```

### 9.4 sync.conflict-resolved - 冲突解决

**主题**：`pms-sync-conflict-resolved`
**生产者**：pms-sync-service
**消费者**：监控服务
**触发时机**：用户人工裁定冲突并提交

```json
{
  "eventId": "evt-083",
  "eventType": "sync.conflict-resolved",
  "topic": "pms-sync-conflict-resolved",
  "timestamp": "2026-07-10T09:05:00Z",
  "source": "pms-sync-service",
  "payload": {
    "userId": 10,
    "deviceId": "client-node-001",
    "conflictId": "conflict-001",
    "recordId": "impl-scheme-5001",
    "field": "configScript",
    "resolutionStrategy": "manual",
    "resolvedBy": { "userId": 10, "username": "pm_zhang" },
    "finalVersion": 6
  }
}
```

---

## 10. 归档事件

### 10.1 archive.completed - 归档完成

**主题**：`pms-archive-completed`
**生产者**：归档服务
**消费者**：报表服务、冷存储服务
**触发时机**：项目归档完成

```json
{
  "eventId": "evt-090",
  "eventType": "archive.completed",
  "topic": "pms-archive-completed",
  "timestamp": "2026-07-10T18:00:00Z",
  "source": "pms-archive-service",
  "payload": {
    "archiveId": "ar-001",
    "projectId": 10001,
    "archivedBy": { "userId": 1, "username": "admin" },
    "deliverablesCount": 25,
    "retention": "5y",
    "archivedAt": "2026-07-10T18:00:00Z"
  }
}
```

### 10.2 archive.cold-storage-moved - 移至冷存储

**主题**：`pms-archive-cold-storage-moved`
**生产者**：冷存储服务
**消费者**：归档服务、报表服务
**触发时机**：归档对象从热存储迁移至冷存储低频访问层

```json
{
  "eventId": "evt-091",
  "eventType": "archive.cold-storage-moved",
  "topic": "pms-archive-cold-storage-moved",
  "timestamp": "2026-07-10T19:00:00Z",
  "source": "pms-cold-storage-service",
  "payload": {
    "archiveId": "ar-001",
    "projectId": 10001,
    "objectCount": 25,
    "fromStorageClass": "STANDARD",
    "toStorageClass": "GLACIER",
    "totalSizeMB": 5120,
    "movedAt": "2026-07-10T19:00:00Z"
  }
}
```

---

## 主题汇总

| 主题 | 事件类型 | 生产者 | 主要消费者 |
|------|----------|--------|-----------|
| pms-project-created | project.created | project-service | 钉钉/报表/CRM |
| pms-project-status-changed | project.status-changed | project-service | 钉钉/报表/跟踪 |
| pms-project-sub-stage-changed | project.sub-stage-changed | delivery-service | 报表/跟踪 |
| pms-project-closed | project.closed | project-service | 归档/报表/维保/CRM |
| pms-project-overdue | project.overdue | delivery-service | 钉钉/报表/告警 |
| pms-approval-submitted | approval.submitted | workflow-service | 钉钉/待办 |
| pms-approval-approved | approval.approved | workflow-service | 业务模块/钉钉 |
| pms-approval-rejected | approval.rejected | workflow-service | 业务模块/钉钉 |
| pms-delivery-sub-stage-changed | delivery.sub-stage-changed | delivery-service | 跟踪/报表 |
| pms-delivery-overdue | delivery.overdue | delivery-service | 钉钉/告警 |
| pms-customer-synced | customer.synced | crm-sync-service | 资产库/项目 |
| pms-customer-service-level-changed | customer.service-level-changed | customer-service | 项目服务 |
| pms-device-config-updated | device.config-updated | deploy-service | 设备增强/资产库 |
| pms-device-info-enhanced | device.info-enhanced | device-service | 资产库/报表 |
| pms-cutover-initiated | cutover.initiated | cutover-service | 割接平台/钉钉 |
| pms-cutover-completed | cutover.completed | cutover-integration | cutover/归档/报表 |
| pms-cutover-failed | cutover.failed | cutover-integration | cutover/钉钉/告警 |
| pms-integration-d365-pushed | integration.d365-pushed | d365-integration | 转包/报表 |
| pms-integration-crm-synced | integration.crm-synced | crm-sync-service | 客户/报表 |
| pms-integration-itr-created | integration.itr-created | itr-integration | AI 排障/报表 |
| pms-integration-rma-invoked | integration.rma-invoked | rma-integration | ITR/资产库 |
| pms-migration-started | migration.started | migration-service | 报表/告警 |
| pms-migration-completed | migration.completed | migration-service | 报表/灰度切换 |
| pms-migration-rollback | migration.rollback | migration-service | 告警/报表 |
| pms-sync-started | sync.started | sync-service | 监控/报表 |
| pms-sync-completed | sync.completed | sync-service | 监控 |
| pms-sync-conflict-detected | sync.conflict-detected | sync-service | 监控/告警 |
| pms-sync-conflict-resolved | sync.conflict-resolved | sync-service | 监控 |
| pms-archive-completed | archive.completed | archive-service | 报表/冷存储 |
| pms-archive-cold-storage-moved | archive.cold-storage-moved | cold-storage-service | 归档/报表 |

**消费者幂等要求**：所有消费者必须基于 `eventId` 做幂等处理，避免重复消费导致数据不一致。消息顺序通过 RocketMQ 分区（key 为 projectId 或 recordId）保证同一业务记录事件有序。
