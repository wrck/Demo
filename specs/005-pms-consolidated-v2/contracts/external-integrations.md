# 外部系统集成契约：PMS 项目交付管理系统

**Date**: 2026-07-10
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Research**: [research.md](../research.md)

## 通用约定

### 集成方向说明

| 方向标识 | 说明 |
|----------|------|
| PMS → 对端 | PMS 主动调用对端系统 |
| 对端 → PMS | 对端系统主动调用 PMS |
| 双向 | 双向数据同步与调用 |

### 接口协议说明

| 协议 | 说明 |
|------|------|
| REST | HTTP RESTful API（JSON） |
| SOAP | SOAP Web Service（XML） |
| MQ | 消息队列（RocketMQ Topic） |
| DB | 数据库直连（多数据源动态路由） |
| LDAP | LDAP/AD 协议 |
| Webhook | HTTP 回调 |

### 通用降级策略

| 策略 | 说明 |
|------|------|
| 重试退避 | 失败后按指数退避重试（1s/2s/4s/8s/16s），最多 5 次 |
| 本地队列 | 集成失败时写入本地消息表，定时重投 |
| 熔断降级 | 连续失败超阈值触发熔断，降级为只读或缓存数据 |
| 人工补偿 | 熔断后通知运维人工介入，记录补偿日志 |

### 跨系统集成点同步成功率

全局约束：跨系统集成点同步成功率 ≥99%（SC-017）。

---

## 1. LDAP / AD（认证集成）

| 项 | 说明 |
|----|------|
| 对端系统 | 企业 LDAP/AD 目录服务 |
| 集成方向 | PMS → 对端 |
| 接口协议 | LDAP（LDAPv3 协议） |
| 触发时机 | 用户登录认证、联网瞬间账户状态联合校验 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| sAMAccountName / uid | string | 登录账号 |
| userPassword | string | 密码（绑定认证，不存储） |
| userAccountControl | int | 账户控制位（ACCOUNTDISABLE=0x0002、LOCKOUT=0x0010） |
| memberOf | string | 所属组（角色映射） |
| displayName | string | 显示名 |
| mail | string | 邮箱 |
| department | string | 部门 |

**集成流程**：
1. 用户提交账号密码，PMS 通过 LDAP bind 操作验证凭据
2. 认证成功后查询用户 userAccountControl 判断账户是否启用/锁定
3. 查询 memberOf 映射 RBAC 角色，同步组织架构数据
4. 数据权限按"办事处/项目归属"维度过滤

**失败降级策略**：
- LDAP 不可达：启用本地缓存用户（24 小时有效），降级为本地认证，记录降级日志
- 账户锁定：返回 401 并将离线令牌加入黑名单，客户端立即清除本地缓存

---

## 2. 钉钉（审批推送 / 待办推送）

| 项 | 说明 |
|----|------|
| 对端系统 | 钉钉开放平台 |
| 集成方向 | PMS → 对端 |
| 接口协议 | REST（钉钉开放 API） |
| 触发时机 | 审批流提交、待办生成、状态变更通知 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| userIds | array | 接收人钉钉用户 ID |
| title | string | 待办标题 |
| content | string | 待办内容 |
| url | string | 跳转 PMS 单据 URL |
| approvalTemplateId | string | 钉钉审批模板 ID |
| formComponents | array | 审批表单字段 |

**集成流程**：
1. PMS 提交施工计划审核 / 实施方案审核 / 转包审批时，推送钉钉待办
2. 调用钉钉审批流模板创建审批实例
3. 审批结果通过 Webhook 回调 PMS 更新状态

**失败降级策略**：
- 钉钉推送失败：写入本地消息表，重试退避，同时通过邮件兜底通知
- 审批回调失败：PMS 主动轮询审批状态兜底

---

## 3. CRM（客户信息双向同步 / 发货提醒）

| 项 | 说明 |
|----|------|
| 对端系统 | CRM 客户关系管理系统 |
| 集成方向 | 双向 |
| 接口协议 | REST + Webhook |
| 触发时机 | 客户信息变更、发货状态变更、PMS 客户维护变更反向同步 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| customerId | string | 客户编码 |
| customerName | string | 客户名称 |
| address | string | 客户地址 |
| industry | string | 行业 |
| serviceLevel | string | 服务等级 |
| contacts | array | 联系人列表 |
| shipStatus | string | 发货状态 |
| salesOffice | string | 销售处 |

**性能约束**：CRM 双向同步延迟 ≤5 分钟，客户服务等级同步延迟 ≤1 分钟（SC-012）。

**集成流程**：
1. CRM 客户信息变更 → Webhook 通知 PMS → PMS 拉取最新客户信息
2. PMS 客户服务等级 / 联系人维护变更 → PMS 推送至 CRM
3. 工期不足且未发货时，PMS 发起 CRM 发货提醒推送至对应销售处
4. 物料换货流程勾选物料推送至 CRM 对应销售处

**失败降级策略**：
- 同步失败：写入 sync_queue 表，按 1/2/4/8 分钟重试
- 服务等级同步延迟超 1 分钟告警，人工补偿

---

## 4. D365（采购订单 / 采购收货 / 合同验收）

| 项 | 说明 |
|----|------|
| 对端系统 | Microsoft Dynamics 365 |
| 集成方向 | PMS → 对端 + 对端 → PMS |
| 接口协议 | REST（OData） |
| 触发时机 | 转包审批通过推送采购订单、采购收货状态回传、合同验收 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| purchaseOrderNo | string | 采购订单号 |
| vendorId | string | 供应商（代理商）ID |
| lineItems | array | 行项目 |
| lineItems[].productCode | string | 产品编码 |
| lineItems[].quantity | int | 数量 |
| lineItems[].amount | decimal | 金额 |
| receiveStatus | string | 收货状态 |
| contractNo | string | 合同号 |
| acceptanceResult | string | 验收结果 |

**集成流程**：
1. 转包审批通过 → PMS 推送采购订单至 D365
2. D365 采购收货 → Webhook 回传收货状态至 PMS
3. 合同验收 → PMS 推送验收结果至 D365

**失败降级策略**：
- 推送失败：本地消息表重投，超 3 次失败通知运维
- D365 不可用：转包流程暂停在"采购订单待推送"状态，标记需人工补推

---

## 5. MES（续保记录只读集成）

| 项 | 说明 |
|----|------|
| 对端系统 | MES 制造执行系统 |
| 集成方向 | 对端 → PMS（只读） |
| 接口协议 | DB（数据库直连，多数据源动态路由） |
| 触发时机 | 客户资产库查询续保记录 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| warrantyId | string | 续保记录 ID |
| customerId | string | 客户编码 |
| deviceId | string | 设备序列号 |
| startDate | date | 续保开始日期 |
| endDate | date | 续保结束日期 |
| warrantyType | string | 续保类型 |

**集成流程**：
- PMS 通过 dynamic-datasource-spring-boot-starter 直连 MES 库只读视图
- 客户资产库页面展示续保记录（只读，不写入）

**失败降级策略**：
- MES 库不可达：客户资产库续保记录区显示"数据源不可用"，不影响其他资产视图

---

## 6. SAP（财务数据）

| 项 | 说明 |
|----|------|
| 对端系统 | SAP ERP |
| 集成方向 | 对端 → PMS（只读） |
| 接口协议 | DB（数据库直连） + REST |
| 触发时机 | 财务报表查询、转包付款状态查询 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| financeDocNo | string | 财务凭证号 |
| amount | decimal | 金额 |
| costCenter | string | 成本中心 |
| paymentStatus | string | 付款状态 |
| postingDate | date | 记账日期 |

**失败降级策略**：
- SAP 不可达：财务数据展示"暂不可用"，报表降级为缓存数据

---

## 7. ITR（故障工单 / 待闭环问题）

| 项 | 说明 |
|----|------|
| 对端系统 | ITR 故障管理系统 |
| 集成方向 | 双向 |
| 接口协议 | REST |
| 触发时机 | PMS 创建故障工单、ITR 待闭环问题同步、AI 排障诊断关联 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| ticketNo | string | 故障工单号 |
| customerId | string | 客户编码 |
| deviceId | string | 设备序列号 |
| faultType | string | 故障类型 |
| faultDescription | string | 故障描述 |
| status | string | 工单状态 |
| pendingClosureIssues | array | 待闭环问题列表 |

**集成流程**：
1. PMS 创建 ITR 故障工单 → 推送至 ITR 系统
2. ITR 工单状态变更 → Webhook 回传 PMS
3. 待闭环问题定期同步至 PMS 待办列表

**失败降级策略**：
- ITR 不可达：工单暂存本地队列，联网后补推

---

## 8. RMA（硬件故障流程调用）

| 项 | 说明 |
|----|------|
| 对端系统 | RMA 返修管理系统 |
| 集成方向 | PMS → 对端 |
| 接口协议 | REST |
| 触发时机 | ITR 故障判定为硬件故障时调用 RMA 流程 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| rmaNo | string | RMA 单号 |
| deviceId | string | 故障设备序列号 |
| faultType | string | 硬件故障类型 |
| description | string | 故障描述 |
| shipStatus | string | 返修物流状态 |
| replacementSerialNo | string | 替换设备序列号 |

**集成流程**：
1. ITR 故障工单判定硬件故障 → PMS 调用 RMA 创建返修单
2. RMA 返修完成 → 回传替换设备序列号至 PMS
3. PMS 更新客户资产库设备清单

**失败降级策略**：
- RMA 调用失败：工单标记"RMA 待调用"，人工介入

---

## 9. 迪普服务平台（巡检 / 设备信息解析）

| 项 | 说明 |
|----|------|
| 对端系统 | 迪普服务平台 |
| 集成方向 | 双向 |
| 接口协议 | REST |
| 触发时机 | 定期巡检同步、设备信息解析回传、CRT log 读取 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| inspectionId | string | 巡检记录 ID |
| deviceId | string | 设备序列号 |
| inspectionDate | date | 巡检日期 |
| inspectionResult | object | 巡检结果 |
| deviceInfo | object | 解析的设备信息 |
| crtLog | string | CRT log 内容 |

**集成流程**：
1. 定时任务拉取服务平台巡检数据
2. PMS 发起设备信息解析请求 → 服务平台返回解析结果回传
3. CRT log 读取通过服务平台接口

**失败降级策略**：
- 服务平台不可达：巡检数据降级为上次缓存，标记"巡检数据可能过期"

---

## 10. 供应链系统（出厂产品信息 / 官网版本导入）

| 项 | 说明 |
|----|------|
| 对端系统 | 供应链管理系统 |
| 集成方向 | 对端 → PMS |
| 接口协议 | REST + MQ |
| 触发时机 | 设备出厂、产品版本发布 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| serialNo | string | 设备序列号 |
| productCode | string | 产品编码 |
| productName | string | 产品名称 |
| factoryDate | date | 出厂日期 |
| softwareVersion | string | 软件版本 |
| officialVersion | string | 官网发布版本 |

**集成流程**：
1. 设备出厂 → 供应链 MQ 推送至 PMS，更新设备出厂信息
2. 官网版本发布 → PMS 拉取版本信息更新设备版本库

**失败降级策略**：
- MQ 消费失败：死信队列 + 人工重投
- 版本拉取失败：标记版本"待同步"，下次定时重试

---

## 11. 割接管理平台（割接闭环刷新 PMS）

| 项 | 说明 |
|----|------|
| 对端系统 | 割接管理平台 |
| 集成方向 | 双向 |
| 接口协议 | REST + Webhook |
| 触发时机 | PMS 发起割接、割接平台闭环刷新 PMS |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| cutoverNo | string | 割接单号 |
| projectId | long | PMS 项目 ID |
| cutoverPlan | object | 割接计划 |
| checklistResult | object | checklist 执行结果 |
| closureStatus | string | 闭环状态 |
| closureTime | datetime | 闭环时间 |

**集成流程**：
1. PMS 发起割接 → 同步割接操作单至割接管理平台
2. 割接平台执行 checklist → Webhook 回传进度
3. 割接平台闭环 → 刷新 PMS 割接状态

**失败降级策略**：
- 割接平台不可达：割接流程阻塞（强一致性，不可离线降级），告警人工介入
- Webhook 回调失败：PMS 主动轮询割接状态兜底

---

## 12. SPMS 备件系统（备件领用 / 归还 / 返修 / 替换）

| 项 | 说明 |
|----|------|
| 对端系统 | SPMS 备件管理系统 |
| 集成方向 | PMS → 对端 |
| 接口协议 | REST |
| 触发时机 | 实施部署备件领用、归还、返修、替换 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| sparePartNo | string | 备件编号 |
| sparePartName | string | 备件名称 |
| operationType | string | 操作类型（borrow/return/repair/replace） |
| projectId | long | 关联项目 ID |
| quantity | int | 数量 |
| operatorId | long | 操作人 |
| returnDeadline | date | 归还截止日期 |

**集成流程**：
1. 实施部署领用备件 → PMS 调用 SPMS 创建领用记录
2. 备件归还 → PMS 调用 SPMS 更新归还状态
3. 备件返修 / 替换 → PMS 调用 SPMS 创建返修/替换流程

**失败降级策略**：
- SPMS 不可达：备件操作暂存本地队列，联网后补推，标记"待同步"

---

## 13. OA / EHR（审批 / 人事数据）

| 项 | 说明 |
|----|------|
| 对端系统 | OA 办公系统 / EHR 人事系统 |
| 集成方向 | 对端 → PMS |
| 接口协议 | REST + DB |
| 触发时机 | 人事变动同步、OA 审批结果回传 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| userId | string | 用户工号 |
| userName | string | 姓名 |
| department | string | 部门 |
| position | string | 躯位 |
| employeeStatus | string | 在职状态 |
| oaApprovalNo | string | OA 审批单号 |
| approvalResult | string | 审批结果 |

**集成流程**：
1. EHR 人事变动 → 定时同步组织架构至 PMS
2. OA 审批完成 → 回传审批结果至 PMS 更新业务单据状态

**失败降级策略**：
- EHR 不可达：使用上次缓存组织架构，标记"组织数据可能过期"
- OA 回调失败：PMS 主动查询 OA 审批状态兜底

---

## 14. FP 平台（发票 OCR / 合同数据校验）

| 项 | 说明 |
|----|------|
| 对端系统 | FP 财务平台 |
| 集成方向 | 双向 |
| 接口协议 | REST |
| 触发时机 | 转包付款发票识别、合同数据校验 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| invoiceNo | string | 发票号 |
| invoiceDate | date | 开票日期 |
| amount | decimal | 发票金额 |
| buyer | string | 购方 |
| seller | string | 销方 |
| contractNo | string | 合同号 |
| verifyResult | string | 校验结果 |

**集成流程**：
1. 转包付款上传发票 → PMS 调用 FP 平台 OCR 识别发票信息
2. 合同数据校验 → PMS 推送合同信息至 FP 平台比对

**失败降级策略**：
- FP 平台不可达：发票识别降级为百度/阿里云 OCR 兜底，合同校验降级为人工核对

---

## 15. 客户资产库（设备资产数据元）

| 项 | 说明 |
|----|------|
| 对端系统 | 客户资产库 |
| 集成方向 | 双向 |
| 接口协议 | REST |
| 触发时机 | 设备部署、资产信息变更、客户资产库视图查询 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| assetId | string | 资产 ID |
| customerId | string | 客户编码 |
| deviceId | string | 设备序列号 |
| productName | string | 产品名称 |
| deployLocation | string | 部署位置 |
| installDate | date | 安装日期 |
| serviceLevel | string | 服务等级 |
| warrantyStatus | string | 维保状态 |

**集成流程**：
1. PMS 设备部署完成 → 同步设备资产数据至客户资产库
2. 客户资产库服务等级变更 → 同步至 PMS 所有关联项目

**失败降级策略**：
- 资产库不可达：资产视图降级为 PMS 本地缓存数据

---

## 16. 冷存储（对象存储分层归档）

| 项 | 说明 |
|----|------|
| 对端系统 | MinIO 冷存储（低频访问层） |
| 集成方向 | PMS → 对端 |
| 接口协议 | S3 API |
| 触发时机 | 归档操作、冷数据取回 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| objectId | string | 对象 ID |
| bucket | string | 存储桶 |
| storageClass | string | 存储类（STANDARD / GLACIER） |
| archiveDate | date | 归档日期 |
| retention | int | 保留年限（交付件 ≥5 年、巡检/割接 ≥3 年） |

**集成流程**：
1. 归档触发 → 热存储对象迁移至冷存储低频访问层
2. 冷数据取回 → 发起取回请求（延迟取回，非实时）

**失败降级策略**：
- 冷存储不可达：归档操作写入重试队列，不影响主业务读写

---

## 17. 一码通（设备安装地址定位）

| 项 | 说明 |
|----|------|
| 对端系统 | 一码通定位平台 |
| 集成方向 | PMS → 对端 |
| 接口协议 | REST |
| 触发时机 | 硬件安装记录地址定位 |

**数据元**：

| 字段 | 类型 | 说明 |
|------|------|------|
| locationCode | string | 一码通编码 |
| address | string | 安装地址 |
| longitude | decimal | 经度 |
| latitude | decimal | 纬度 |
| region | string | 区域 |

**集成流程**：
1. 硬件安装录入地址 → PMS 调用一码通解析地址坐标
2. 一码通返回定位信息 → PMS 存储设备部署位置

**失败降级策略**：
- 一码通不可达：地址降级为手动填写，标记"定位待补"

---

## 18. CAS（老系统认证基线，仅记录）

| 项 | 说明 |
|----|------|
| 对端系统 | CAS 老系统认证 |
| 集成方向 | 仅记录（迁移参考） |
| 接口协议 | CAS 协议 |
| 触发时机 | 数据迁移期间老系统认证兼容 |

**说明**：
- CAS 为老系统认证基线，新系统已切换为 LDAP/AD 绑定认证 + JWT
- 数据迁移与灰度切换期间，CAS 仅作为老系统兼容记录保留，新系统不再依赖
- 灰度切换完成后 CAS 下线

**失败降级策略**：
- 迁移期间 CAS 故障：老系统降级，加速切换至新系统 LDAP/AD 认证

---

## 集成监控与健康检查

### GET /api/v1/integration/health - 集成健康检查

返回所有外部系统连通状态与延迟，详见 [rest-api.md](./rest-api.md) 第 29 章。

**监控指标**：

| 指标 | 说明 |
|------|------|
| system | 系统名称 |
| status | healthy / degraded / down |
| latency | 探测延迟（ms） |
| lastSuccessAt | 最后成功时间 |
| failureRate | 近 1 小时失败率 |

### 告警阈值

| 指标 | 阈值 | 告警动作 |
|------|------|----------|
| 同步失败率 | >1% | 钉钉 + 邮件告警 |
| 同步延迟（CRM） | >5 分钟 | 告警 |
| 同步延迟（服务等级） | >1 分钟 | 紧急告警 |
| 系统状态 | down | 立即告警 + 降级策略触发 |

---

## 集成架构总览

```
                          ┌─────────────────────────────────────────┐
                          │              PMS 项目交付管理系统          │
                          │  (Spring Boot 3.2 + 多数据源动态路由)     │
                          └──────────────┬──────────────────────────┘
                                         │
        ┌────────────────┬───────────────┼───────────────┬────────────────┐
        │                │               │               │                │
   ┌────▼────┐    ┌─────▼─────┐   ┌────▼────┐    ┌──────▼──────┐   ┌────▼────┐
   │ LDAP/AD │    │  钉钉     │   │  CRM    │    │    D365     │   │  MES    │
   │ (认证)  │    │ (审批)   │   │(客户同步)│    │ (采购/验收) │   │(续保只读)│
   └─────────┘    └───────────┘   └─────────┘    └─────────────┘   └─────────┘
   ┌─────────┐    ┌───────────┐   ┌─────────┐    ┌─────────────┐   ┌─────────┐
   │   SAP   │    │   ITR     │   │  RMA    │    │ 迪普服务平台 │   │ 供应链  │
   │ (财务)  │    │ (故障)   │   │ (返修)  │    │ (巡检/解析) │   │(出厂信息)│
   └─────────┘    └───────────┘   └─────────┘    └─────────────┘   └─────────┘
   ┌─────────┐    ┌───────────┐   ┌─────────┐    ┌─────────────┐   ┌─────────┐
   │割接平台 │    │  SPMS    │   │ OA/EHR  │    │   FP 平台   │   │ 冷存储  │
   │(割接闭环)│   │ (备件)   │   │(审批/人事)│   │(发票/合同)  │   │(分层归档)│
   └─────────┘    └───────────┘   └─────────┘    └─────────────┘   └─────────┘
   ┌─────────┐    ┌───────────┐
   │客户资产库│   │  一码通  │
   │(设备资产)│   │(地址定位) │
   └─────────┘    └───────────┘
                          ┌───────────┐
                          │   CAS     │
                          │(老系统,仅记录)│
                          └───────────┘
```

**多数据源动态路由**：D365/CRM/SAP/MES 等直连查询通过 dynamic-datasource-spring-boot-starter 注解切换，保留 9 个数据源。
