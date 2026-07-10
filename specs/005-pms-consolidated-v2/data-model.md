# PMS 项目交付管理系统 - 数据模型文档

**Feature Branch**: `005-pms-consolidated-v2`

**文档说明**：本文档基于 spec.md 中"### Key Entities"章节定义的 38 个业务实体，按业务域分组组织，并新增 3 个离线同步实体（响应桌面客户端离线能力 FR-119a/b/c/d）。包含实体字段定义、关系映射、状态机与校验规则。

**业务域组织原则**：以"项目交付生命周期"为主线（立项 / 工前 / 计划 / 方案 / 部署 / 验收 / 割接 / 归档），老系统模块作为子能力嵌入对应阶段（转包嵌入"部署"、回访嵌入"验收"、维保嵌入"归档"、售前作为独立业务场景复用生命周期）；横切模块（客户资产库 / 系统管理 / 工作流 / 集成 / 离线同步等）独立。

---

## 目录

- [一、业务实体总览](#一业务实体总览)
- [二、项目交付核心生命周期](#二项目交付核心生命周期)
- [三、工前准备](#三工前准备)
- [四、制定施工计划与审批](#四制定施工计划与审批)
- [五、编写实施方案与审核](#五编写实施方案与审核)
- [六、实施部署](#六实施部署)
- [七、验收交维](#七验收交维)
- [八、闭环与回访管理](#八闭环与回访管理)
- [九、维保管理](#九维保管理)
- [十、售前测试管理](#十售前测试管理)
- [十一、项目转包（代施）管理](#十一项目转包代施管理)
- [十二、技术公告与修复任务](#十二技术公告与修复任务)
- [十三、项目周报与文件管理](#十三项目周报与文件管理)
- [十四、客户资产库与客户管理](#十四客户资产库与客户管理)
- [十五、割接管理与平台集成](#十五割接管理与平台集成)
- [十六、ITR 故障处理与 RMA 联动](#十六itr-故障处理与-rma-联动)
- [十七、AI 排障与知识库管理](#十七ai-排障与知识库管理)
- [十八、系统管理与权限控制](#十八系统管理与权限控制)
- [十九、工作流引擎](#十九工作流引擎)
- [二十、跨系统数据集成](#二十跨系统数据集成)
- [二十一、离线同步（新增）](#二十一离线同步新增)
- [二十二、关键状态机汇总](#二十二关键状态机汇总)
- [二十三、校验规则（按业务域分组）](#二十三校验规则按业务域分组)

---

## 一、业务实体总览

### 1.1 业务实体清单（38 个，按业务域分组）

| 序号 | 业务域 | 实体中文名 | 实体英文名 | 是否存储实体 |
|------|--------|------------|-----------|-------------|
| 1 | 项目交付核心生命周期 | 项目 | Project | 是 |
| 2 | 项目交付核心生命周期 | 项目成员 | Member | 是 |
| 3 | 项目交付核心生命周期 | 项目合同 | Contract | 是 |
| 4 | 项目交付核心生命周期 | 产品信息清单 | ProductList | 是 |
| 5 | 项目交付核心生命周期 | 设备序列号 | DeviceSerial | 是 |
| 6 | 工前准备 | 客户联系人 | CustomerContact | 是 |
| 7 | 工前准备 | 工勘记录 | SiteSurvey | 是 |
| 8 | 工前准备 | 需求分析 | Requirement | 是 |
| 9 | 工前准备 | 物料换货记录 | MaterialExchange | 是 |
| 10 | 制定施工计划与审批 | 施工计划 | ConstructionPlan | 是 |
| 11 | 编写实施方案与审核 | 实施方案 | ImplementationPlan | 是 |
| 12 | 实施部署 | 配置 Log | ConfigLog | 是 |
| 13 | 实施部署 | 割接单 | CutOverOrder | 是 |
| 14 | 实施部署 | 割接资源 | CutOverResource | 是 |
| 15 | 实施部署 | 备件 | SparePart | 是 |
| 16 | 实施部署 | 巡检任务 | InspectionTask | 是 |
| 17 | 验收交维 | 交付件 | Deliverable | 是 |
| 18 | 验收交维 | 移动端评价记录 | MobileEvaluation | 是 |
| 19 | 闭环与回访管理 | 回访申请 | Callback | 是 |
| 20 | 维保管理 | 维护记录 | Maintenance | 是 |
| 21 | 售前测试管理 | 售前测试项目 | Presales Project | 是 |
| 22 | 售前测试管理 | 临时授权 | TemporaryLicense | 是 |
| 23 | 项目转包（代施）管理 | 转包项目 | Subcontract Project | 是 |
| 24 | 项目转包（代施）管理 | 服务商 | Facilitator | 是 |
| 25 | 技术公告与修复任务 | 技术公告 | Prob | 是 |
| 26 | 项目周报与文件管理 | 项目周报 | Weekly | 是 |
| 27 | 客户资产库与客户管理 | 客户 | Customer | 是 |
| 28 | 客户资产库与客户管理 | 客户资产库视图 | CustomerAssetLibraryView | 否（整合性视图） |
| 29 | 客户资产库与客户管理 | 客户档案 | CustomerArchive | 是 |
| 30 | ITR 故障处理与 RMA 联动 | ITR 问题单 | ITRTicket | 是 |
| 31 | ITR 故障处理与 RMA 联动 | RMA 工单 | RMAOrder | 是 |
| 32 | AI 排障与知识库管理 | AI 排障知识库 | KnowledgeBase | 是 |
| 33 | 系统管理与权限控制 | 角色 | Role | 是 |
| 34 | 系统管理与权限控制 | 部门 | Department | 是 |
| 35 | 系统管理与权限控制 | 基础数据 | BasicData | 是 |
| 36 | 系统管理与权限控制 | 操作日志 | OperateLog | 是 |
| 37 | 工作流引擎 | 工作流任务 | Workflow Task | 是 |
| 38 | 跨系统数据集成 | 跨系统集成点 | IntegrationPoint | 是 |

### 1.2 新增离线同步实体清单（3 个）

| 序号 | 业务域 | 实体中文名 | 实体英文名 | 说明 |
|------|--------|------------|-----------|------|
| 39 | 离线同步 | 本地缓存元数据 | LocalCacheMeta | 桌面客户端本地缓存元数据（FR-119c/d） |
| 40 | 离线同步 | 同步队列 | SyncQueue | 离线期间待同步变更（FR-119a/b） |
| 41 | 离线同步 | 冲突记录 | ConflictRecord | 同步冲突人工裁定（FR-119a） |

---

## 二、项目交付核心生命周期

### 2.1 项目（Project）

**所属业务域**：项目交付核心生命周期
**实体说明**：项目信息主表，状态机驱动生命周期。支持主子项目层级。项目阶段采用双层并行模型（顶层生命周期状态机 + "40 实施中"内嵌套 8 个交付子阶段）。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_no | VARCHAR(64) | UNIQUE, NOT NULL | 项目编号（系统生成，唯一） |
| contract_no | VARCHAR(64) | UNIQUE, NOT NULL | 合同号（唯一性校验，FR-001） |
| project_name | VARCHAR(255) | NOT NULL | 项目名称 |
| status_code | INT | NOT NULL | 生命周期状态码（30/31/32/36/38/40/42/100/20） |
| delivery_sub_phase | VARCHAR(32) | NULL | 交付子阶段（status_code=40 时生效） |
| parent_project_id | BIGINT | FK, NULL | 父项目 ID（主子项目层级） |
| sm_id | BIGINT | FK, NULL | 服务经理 ID（系统自动指派） |
| pm_id | BIGINT | FK, NULL | 项目经理 ID（手动指派） |
| office_id | BIGINT | FK, NOT NULL | 办事处 ID（数据权限过滤维度） |
| product_line | VARCHAR(64) | NULL | 实际产品线 |
| planned_product_line | VARCHAR(64) | NULL | 计划产品线 |
| project_type | VARCHAR(32) | NOT NULL | 项目类型（直签/非直签） |
| project_level | VARCHAR(16) | NULL | 项目级别（逻辑自动判断） |
| scenario_template_id | BIGINT | FK, NULL | 业务场景模板 ID |
| template_version_snapshot | VARCHAR(32) | NULL | 模板版本快照 |
| stakeholders | JSON | NULL | 相关方（渠道商/代理商/服务商） |
| project_groups | JSON | NULL | 项目组（多归属） |
| version | INT | NOT NULL, DEFAULT 0 | 乐观锁版本号（FR-021） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | BIGINT | NOT NULL | 创建人 |

**关系映射**：
- `parent_project_id` → Project（自关联，主子项目层级）
- `sm_id` / `pm_id` → Member
- `office_id` → Department
- `scenario_template_id` → BasicData
- 1:N → ProductList, DeviceSerial, SiteSurvey, Requirement, ConstructionPlan, ImplementationPlan, Deliverable, Weekly, Member, Contract

**状态机**：见 [22.1 项目生命周期状态机](#221-项目生命周期状态机)

### 2.2 项目成员（Member）

**所属业务域**：项目交付核心生命周期
**实体说明**：项目成员表，记录服务经理、项目经理、安装地址、实施状态；支持可编辑增加其他办事处人员。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| user_id | BIGINT | FK, NULL | 用户 ID（我司角色） |
| role_type | VARCHAR(32) | NOT NULL | 角色类型（服务经理/项目经理/销售代表/团队成员/客户主联系人） |
| name | VARCHAR(64) | NOT NULL | 姓名（模糊匹配） |
| phone | VARCHAR(32) | NULL | 联系方式 |
| install_address | VARCHAR(512) | NULL | 安装地址 |
| impl_status | VARCHAR(16) | NULL | 实施状态 |
| office_id | BIGINT | FK, NULL | 所属办事处（可跨办事处增加） |
| remark | VARCHAR(512) | NULL | 备注 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `project_id` → Project
- `user_id` → 用户（LDAP/AD）
- `office_id` → Department

### 2.3 项目合同（Contract）

**所属业务域**：项目交付核心生命周期
**实体说明**：项目合同关联表，支持合并与拆分。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| contract_no | VARCHAR(64) | UNIQUE, NOT NULL | 合同号 |
| project_id | BIGINT | FK, NOT NULL | 关联项目 ID |
| merged_from | JSON | NULL | 合并来源合同号列表 |
| split_to | JSON | NULL | 拆分目标合同号列表 |
| order_data | JSON | NULL | 订单数据（一致性校验） |
| acceptance_time | DATETIME | NULL | 合同验收时间（PMS 导入） |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `project_id` → Project

### 2.4 产品信息清单（ProductList）

**所属业务域**：项目交付核心生命周期
**实体说明**：项目下产品明细。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| product_code | VARCHAR(64) | NOT NULL | 产品编码 |
| product_model | VARCHAR(128) | NULL | 产品型号 |
| product_desc | VARCHAR(512) | NULL | 产品描述 |
| planned_qty | INT | NOT NULL | 项目数量 |
| shipped_qty | INT | DEFAULT 0 | 发货数量 |
| unshipped_qty | INT | DEFAULT 0 | 未发货数量（= 计划 - 发货） |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `project_id` → Project
- 1:N → DeviceSerial

### 2.5 设备序列号（DeviceSerial）

**所属业务域**：项目交付核心生命周期
**实体说明**：设备唯一标识，含配置历史、部署风险、运行业务档案、启用功能、接口对照表、网络拓扑等增强维度。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| serial_no | VARCHAR(64) | UNIQUE, NOT NULL | 序列号（唯一） |
| product_code | VARCHAR(64) | NOT NULL | 产品编码 |
| product_name | VARCHAR(128) | NULL | 产品名称 |
| project_id | BIGINT | FK, NULL | 所属项目 ID |
| install_location | VARCHAR(256) | NULL | 安装位置（一码通定位填写，FR-103） |
| factory_sw_version | VARCHAR(32) | NULL | 出厂软件版本 |
| factory_conboot_version | VARCHAR(32) | NULL | 出厂 conboot 版本 |
| factory_cpld_version | VARCHAR(32) | NULL | 出厂 cpld 版本 |
| official_version | VARCHAR(32) | NULL | 官网版本（出厂匹配，供应链导入，FR-102） |
| online_sw_version | VARCHAR(32) | NULL | 在网软件版本（show version，对客户） |
| online_conboot_version | VARCHAR(32) | NULL | 在网 conboot 版本 |
| online_cpld_version | VARCHAR(32) | NULL | 在网 cpld 版本 |
| branch_version | VARCHAR(32) | NULL | 分支版本（特殊版本，对内） |
| affected_prob_ids | JSON | NULL | 受影响技术公告 ID 列表 |
| warranty_duration | INT | NULL | 维保时长（月） |
| warranty_start | DATE | NULL | 维保开始时间 |
| warranty_end | DATE | NULL | 维保结束时间 |
| renew_count | INT | DEFAULT 0 | 续保次数（MES 只读集成） |
| config_history | JSON | NULL | 配置历史（支持历史对比，FR-099） |
| deploy_risk | JSON | NULL | 部署风险描述（单机/单点/冗余，FR-099） |
| running_business_archive | JSON | NULL | 运行业务档案（FR-099） |
| enabled_features | JSON | NULL | 启用功能（命令获取，FR-100） |
| interface_mapping | JSON | NULL | 接口对照表（FR-100） |
| network_topology | JSON | NULL | 网络拓扑（自动生成，非图片，FR-101） |
| device_photos | JSON | NULL | 设备照片（一码通上传，FR-103） |
| customer_id | BIGINT | FK, NULL | 客户 ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- `customer_id` → Customer
- 1:N → ConfigLog
- N:N → Prob（通过 affected_prob_ids）

---

## 三、工前准备

### 3.1 客户联系人（CustomerContact）

**所属业务域**：工前准备
**实体说明**：客户方联系人（项目交付环境实际使用设备的最终客户方联系人）。客户基础信息与默认联系人由 CRM 带入；服务等级由客户资产库带入。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| customer_id | BIGINT | FK, NOT NULL | 客户 ID |
| contact_type | VARCHAR(16) | NOT NULL | 联系人属性（主联系人/其他联系人） |
| name | VARCHAR(64) | NOT NULL | 姓名 |
| phone | VARCHAR(32) | NULL | 电话 |
| customer_unit | VARCHAR(128) | NULL | 客户单位名称 |
| service_level | VARCHAR(16) | NULL | 服务等级（客户资产库带入） |
| department | VARCHAR(128) | NULL | 部门 |
| position | VARCHAR(64) | NULL | 职务 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态（active/invalid） |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `customer_id` → Customer
- 项目页面仅显示主联系人，其他联系人仅在详情页展示

### 3.2 工勘记录（SiteSurvey）

**所属业务域**：工前准备
**实体说明**：工勘分工确认结果。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| deadline_requirement | DATETIME | NULL | 工期要求（项目结束时间） |
| power_supply | VARCHAR(32) | NULL | 机房供电确认 |
| power_mode | VARCHAR(32) | NULL | 供电方式 |
| port_type | VARCHAR(32) | NULL | 网口类型确认 |
| cabinet_resource | VARCHAR(32) | NULL | 机柜资源 |
| fiber_cable | VARCHAR(32) | NULL | 光纤网线 |
| optical_module | VARCHAR(32) | NULL | 光模块 |
| oem_optical_module | VARCHAR(32) | NULL | 原厂光模块 |
| rack_powerup_need_oem | VARCHAR(16) | NULL | 上架加电需原厂实施（是/否） |
| rack_powerup_need_outsource | VARCHAR(16) | NULL | 需外包（是/否，触发发起外包流程链接） |
| need_rail_tray | VARCHAR(16) | NULL | 需要导轨托盘（是/否，触发物料领用/外采链接） |
| material_conformity | VARCHAR(16) | NULL | 发货物料符合性（符合/不符合，触发物料选择页面） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project

### 3.3 需求分析（Requirement）

**所属业务域**：工前准备
**实体说明**：项目需求采集。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| background | TEXT | NULL | 项目背景 |
| objective | TEXT | NULL | 项目目标 |
| network_topology_file | VARCHAR(512) | NULL | 网络拓扑文件（上传） |
| transmission_status | JSON | NULL | 传输现状（IPv6/分片/MTU/Jumbo/隧道多选） |
| traffic_status | JSON | NULL | 流量现状（新建/并发/吞吐） |
| running_business | JSON | NULL | 运行业务情况表 |
| ip_resources | JSON | NULL | IP 资源（管理IP/公网IP） |
| redundancy_backup | TEXT | NULL | 冗余备份要求 |
| local_protection | TEXT | NULL | 本机防护要求 |
| ops_management | JSON | NULL | 运维管理要求（带内/带外/SNMP/UMC/第三平台/堡垒机多选） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- 实施方案引用此实体数据

### 3.4 物料换货记录（MaterialExchange）

**所属业务域**：工前准备
**实体说明**：物料选择与换货流程实体。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| device_serial_id | BIGINT | FK, NULL | 设备序列号 ID |
| product_code | VARCHAR(64) | NOT NULL | 产品编码 |
| product_name | VARCHAR(128) | NULL | 产品名称 |
| checked | BOOLEAN | DEFAULT FALSE | 勾选状态（是否需换货） |
| nonconformity_desc | TEXT | NULL | 不符合项说明 |
| exchange_status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 换货流程状态 |
| push_target_crm | VARCHAR(128) | NULL | 推送目标（CRM 对应销售） |
| pushed_at | DATETIME | NULL | 推送时间 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `project_id` → Project
- `device_serial_id` → DeviceSerial
- 推送至 CRM 对应销售（FR-029）

---

## 四、制定施工计划与审批

### 4.1 施工计划（ConstructionPlan）

**所属业务域**：制定施工计划与审批
**实体说明**：项目各阶段时间安排，采用三层时间模型。工期建议计划时间按项目类型倒推逻辑自动计算。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| contract_acceptance_time | DATETIME | NULL | 合同验收时间（PMS 导入，只读） |
| deadline_requirement | DATETIME | NULL | 工期要求（工前准备带入，不可调整） |
| arrival_signoff_plan | JSON | NULL | 到货签收（阶段计划时间：开始/结束） |
| hardware_impl_plan | JSON | NULL | 硬件实施（阶段计划时间） |
| device_config_plan | JSON | NULL | 设备配置（阶段计划时间） |
| business_integration_plan | JSON | NULL | 业务联通（阶段计划时间） |
| cutover_online_plan | JSON | NULL | 割接-上线（阶段计划时间） |
| initial_acceptance_plan | JSON | NULL | 初验（阶段计划时间，直签项目必填） |
| final_acceptance_plan | JSON | NULL | 终验（阶段计划时间，直签项目必填） |
| suggested_arrival_signoff | DATETIME | NULL | 建议到货签收时间（倒推计算） |
| suggested_hardware_impl | DATETIME | NULL | 建议硬件实施时间 |
| suggested_device_config | DATETIME | NULL | 建议设备配置时间 |
| suggested_business_integration | DATETIME | NULL | 建议业务联通时间 |
| suggested_cutover_online | DATETIME | NULL | 建议割接上线时间 |
| suggested_initial_acceptance | DATETIME | NULL | 建议初验时间 |
| suggested_final_acceptance | DATETIME | NULL | 建议终验时间 |
| audit_status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 审核状态（draft/submitted/approved/rejected） |
| version | INT | NOT NULL, DEFAULT 0 | 乐观锁版本号 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- 实施方案引用此实体数据

**校验规则**：
- 直签项目（含初验环节）：到货签收、初验、终验 MUST 必填
- 非直签项目：工期建议时间倒推 = 工期时间 - 2 周（割接上线）
- 直签项目：割接上线 = 初验时间 - 3 个月 - 2 周

---

## 五、编写实施方案与审核

### 5.1 实施方案（ImplementationPlan）

**所属业务域**：编写实施方案与审核
**实体说明**：项目实施方案文档，含多章节。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| has_customer_plan | BOOLEAN | DEFAULT FALSE | 是否已有客户方案 |
| uploaded_plan_file | VARCHAR(512) | NULL | 上传的客户方案文件 |
| overview | TEXT | NULL | 项目概述（引用工前准备） |
| current_network_analysis | TEXT | NULL | 现网现状分析 |
| overall_design | JSON | NULL | 总体方案设计（部署位置/接口互联/IP-VLAN/软件版本，同步至序列号） |
| config_scripts | TEXT | NULL | 配置脚本 |
| implementation_steps | TEXT | NULL | 实施步骤 |
| other_plans | JSON | NULL | 其他方案（质量保障/风险管控/运维交付/问题闭环，模板勾选） |
| training_plan | TEXT | NULL | 培训 |
| after_sales | TEXT | NULL | 售后服务 |
| audit_status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 审核状态（draft/generated/submitted/approved/rejected/locked） |
| generated_file | VARCHAR(512) | NULL | 生成的实施方案文件 |
| version | INT | NOT NULL, DEFAULT 0 | 乐观锁版本号 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- 引用 SiteSurvey, Requirement, Member, ProductList, ConstructionPlan 等前序数据
- 总体方案设计同步更新至 DeviceSerial

**校验规则**：已提交审核的实施方案锁定不可编辑（audit_status = locked）

---

## 六、实施部署

### 6.1 配置 Log（ConfigLog）

**所属业务域**：实施部署
**实体说明**：设备配置时上传或自动读取产生的 Log 文件记录。每生成一次 Log 记录一条。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| device_serial_id | BIGINT | FK, NOT NULL | 设备序列号 ID |
| log_file_path | VARCHAR(512) | NOT NULL | Log 文件路径 |
| read_mode | VARCHAR(16) | NOT NULL | 读取方式（auto 自动读取 / manual 本地上传） |
| config_read_path | VARCHAR(512) | NULL | 配置读取路径（自动读取时设置） |
| uploaded_by | BIGINT | FK, NULL | 上传人（系统自动带入或手动） |
| uploaded_at | DATETIME | NOT NULL | 上传时间 |
| parse_status | VARCHAR(16) | NULL | 解析状态（success/partial/failed） |
| parsed_config | JSON | NULL | 解析出的配置信息（解析失败字段保留空） |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `device_serial_id` → DeviceSerial（多对一）
- `uploaded_by` → 用户

**校验规则**：
- 自动读取失败 MUST 回退至手动上传模式
- 手动上传后仍尝试自动解析，解析失败字段保留为空待人工填写

### 6.2 割接单（CutOverOrder）

**所属业务域**：实施部署
**实体说明**：割接管理平台核心实体。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NULL | 关联项目 ID（工程交付来源） |
| cutover_source | VARCHAR(32) | NOT NULL | 割接来源（工程交付/维保主动服务/ITR故障/RMA） |
| cutover_type | VARCHAR(32) | NOT NULL | 割接类型（友商替换/新建入网/搬迁入网/配置组网变更/补丁升级/版本升级/RMA好件替换） |
| cutover_level | VARCHAR(8) | NULL | 割接等级（A/B 类，固定规则自动匹配） |
| cutover_objects | JSON | NULL | 割接对象 |
| network_config | JSON | NULL | 割接组网 |
| operation_impact | TEXT | NULL | 操作影响 |
| cutover_team | JSON | NULL | 割接小组 |
| cutover_plan | JSON | NULL | 割接计划 |
| cutover_solution | JSON | NULL | 割接方案（模板库生成） |
| operation_orders | JSON | NULL | 操作单（准备/割接/割接后/回退） |
| checklist | JSON | NULL | checklist（自动生成） |
| closure_status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 闭环状态 |
| archived_data | JSON | NULL | 闭环归档数据（tech-support/版本/CPLD/conboot/备件序列号） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- 1:N → CutOverResource, SparePart
- 关联 ITR 待闭环问题、客户资产库、RMA 流程信息

### 6.3 割接资源（CutOverResource）

**所属业务域**：实施部署
**实体说明**：割接所需资源（人员与备件）。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| cutover_order_id | BIGINT | FK, NOT NULL | 割接单 ID |
| resource_type | VARCHAR(16) | NOT NULL | 资源类型（person 人员 / spare_part 备件） |
| role | VARCHAR(32) | NULL | 人员角色（操作人/复核人/验证人/割接保障人） |
| user_id | BIGINT | FK, NULL | 人员用户 ID |
| spare_part_id | BIGINT | FK, NULL | 备件 ID |
| return_status | VARCHAR(16) | NULL | 退回状态（备件割接后退回闭环） |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `cutover_order_id` → CutOverOrder
- `user_id` → 用户
- `spare_part_id` → SparePart

### 6.4 备件（SparePart）

**所属业务域**：实施部署
**实体说明**：割接与运维备件实体，与割接单关联。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| spare_part_no | VARCHAR(64) | UNIQUE, NOT NULL | 备件编号 |
| serial_no | VARCHAR(64) | NULL | 序列号 |
| product_code | VARCHAR(64) | NOT NULL | 产品编码 |
| product_name | VARCHAR(128) | NULL | 产品名称 |
| cutover_order_id | BIGINT | FK, NULL | 关联割接单 ID |
| apply_status | VARCHAR(16) | NOT NULL | 申请状态 |
| return_status | VARCHAR(16) | NULL | 退回状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `cutover_order_id` → CutOverOrder
- 与 SPMS 备件系统集成（标准 API，解耦，FR-127）

### 6.5 巡检任务（InspectionTask）

**所属业务域**：实施部署
**实体说明**：服务平台巡检实体，输出同步至 PMS。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| device_type | VARCHAR(64) | NOT NULL | 设备类型 |
| target_ip | VARCHAR(64) | NOT NULL | 目标 IP |
| scenario_library | VARCHAR(128) | NULL | 场景库 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | 状态 |
| inspection_log | TEXT | NULL | 巡检 log |
| inspection_report | VARCHAR(512) | NULL | 巡检报告路径 |
| synced_to_pms | BOOLEAN | DEFAULT FALSE | 是否已同步至 PMS |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：与迪普服务平台集成（FR-091/092/093）

---

## 七、验收交维

### 7.1 交付件（Deliverable）

**所属业务域**：验收交维
**实体说明**：项目交付物电子档。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| deliverable_type | VARCHAR(32) | NOT NULL | 交付件类型（到货签收单/实施方案/初验报告/终验报告/现场培训记录/满意度调查报告） |
| file_path | VARCHAR(512) | NOT NULL | 文件路径 |
| file_name | VARCHAR(255) | NULL | 文件名 |
| generated_by | VARCHAR(32) | NULL | 产生方式（线上操作产生/上传） |
| uploaded_by | BIGINT | FK, NULL | 上传人 |
| uploaded_at | DATETIME | NOT NULL | 上传时间 |
| archive_status | VARCHAR(16) | NULL | 归档状态（随项目归档保留 ≥ 5 年） |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `project_id` → Project
- PMS 线上操作产生，保存至总部数据中心（FR-072/073）

### 7.2 移动端评价记录（MobileEvaluation）

**所属业务域**：验收交维
**实体说明**：移动端推送与回传的评价记录。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| evaluation_type | VARCHAR(32) | NOT NULL | 评价类型（现场培训服务评价/服务评价） |
| customer_contact_id | BIGINT | FK, NULL | 推送目标（客户联系人） |
| customer_feedback | TEXT | NULL | 客户反馈内容 |
| customer_signature | VARCHAR(512) | NULL | 客户签字 |
| push_status | VARCHAR(16) | NOT NULL | 推送状态（pushed/opened/replied） |
| reply_status | VARCHAR(16) | NULL | 回传状态（pending/received/failed） |
| deliverable_id | BIGINT | FK, NULL | 关联交付件 ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| replied_at | DATETIME | NULL | 回传时间 |

**关系映射**：
- `project_id` → Project
- `customer_contact_id` → CustomerContact
- `deliverable_id` → Deliverable

---

## 八、闭环与回访管理

### 8.1 回访申请（Callback）

**所属业务域**：闭环与回访管理
**实体说明**：回访申请主表，归属子项目。主项目闭环前 MUST 确认全部子项目回访已完成。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 关联项目 ID（归属子项目） |
| parent_project_id | BIGINT | FK, NULL | 主项目 ID（汇总用） |
| questionnaire_template_id | BIGINT | FK, NULL | 回访问卷模板 ID |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 状态（draft/submitted/approved/completed/rejected） |
| score | DECIMAL(5,2) | NULL | 评分（计算得出） |
| questionnaire_result | JSON | NULL | 问卷结果（头表 + 行表） |
| evaluation_records | JSON | NULL | 评价记录（评价头表） |
| custom_approval_opinions | JSON | NULL | 自定义审批意见 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- `parent_project_id` → Project（主项目汇总）
- 回访通过 → 闭环流程状态回到 10（FR-064）

---

## 九、维保管理

### 9.1 维护记录（Maintenance）

**所属业务域**：维保管理
**实体说明**：维护记录主表，按 projectType 关联对应项目主表。归属子项目，主项目可按子项目维度汇总。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 关联项目 ID |
| project_type | VARCHAR(32) | NOT NULL | 项目类型（售后/售前/非业务/自定义） |
| questionnaire_result | JSON | NULL | 维护问卷结果（头表 + 行表） |
| deliverables | JSON | NULL | 维护交付件 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project（按 projectType 关联）

---

## 十、售前测试管理

### 10.1 售前测试项目（Presales Project）

**所属业务域**：售前测试管理
**实体说明**：售前测试信息主表，复用标准项目管理能力但范围限定为售前测试业务环境。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_no | VARCHAR(64) | UNIQUE, NOT NULL | 售前测试项目编号 |
| status_code | INT | NOT NULL | 状态码（10/31/32/33/100/20） |
| product_details | JSON | NULL | 产品明细 |
| rma_info | JSON | NULL | RMA 信息 |
| stage_durations | JSON | NULL | 各阶段耗时统计（视图） |
| callback_questionnaire_id | BIGINT | FK, NULL | 回访问卷关联 ID |
| deliverables | JSON | NULL | 交付件明细 |
| version | INT | NOT NULL, DEFAULT 0 | 乐观锁版本号 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `callback_questionnaire_id` → Callback
- 工作流驱动审批流：申请 → SM 审批指定 PM → PM 跟踪 → EM 回访 → 闭环

**状态机**：见 [22.3 售前测试状态机](#223-售前测试状态机)

### 10.2 临时授权（TemporaryLicense）

**所属业务域**：售前测试管理
**实体说明**：售前测试首次临时授权，设备发货后自动获取并下发。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| presales_project_id | BIGINT | FK, NOT NULL | 售前测试项目 ID |
| device_serial_id | BIGINT | FK, NOT NULL | 设备序列号 ID |
| license_key | VARCHAR(256) | NOT NULL | 授权密钥 |
| auto_acquired | BOOLEAN | DEFAULT TRUE | 是否自动获取（发货后自动） |
| issued_at | DATETIME | NOT NULL | 下发时间 |
| expires_at | DATETIME | NULL | 授权到期时间 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `presales_project_id` → Presales Project
- `device_serial_id` → DeviceSerial

---

## 十一、项目转包（代施）管理

### 11.1 转包项目（Subcontract Project）

**所属业务域**：项目转包（代施）管理
**实体说明**：转包项目主表，归属子项目，主项目可汇总。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 关联主项目 ID（归属子项目） |
| parent_project_id | BIGINT | FK, NULL | 主项目 ID（汇总用） |
| subcontract_no | VARCHAR(64) | UNIQUE, NOT NULL | 转包项目编号 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 状态（草稿/审批中/合同执行/付款/回访/验收/闭环） |
| device_list | JSON | NULL | 设备清单 |
| prices | JSON | NULL | 价格信息 |
| payment_info | JSON | NULL | 付款信息 |
| payment_view | JSON | NULL | 付款视图 |
| callback_records | JSON | NULL | 回访记录 |
| deliverables | JSON | NULL | 交付件/附件 |
| facilitator_id | BIGINT | FK, NULL | 服务商 ID |
| d365_purchase_order | VARCHAR(64) | NULL | D365 采购订单号 |
| d365_receipt_no | VARCHAR(64) | NULL | D365 采购收货号 |
| invoice_info | JSON | NULL | 发票信息（OCR 识别） |
| version | INT | NOT NULL, DEFAULT 0 | 乐观锁版本号 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- `facilitator_id` → Facilitator
- 向 D365 推送采购订单与采购收货（FR-060）

**状态机**：见 [22.4 转包状态机](#224-转包状态机)

### 11.2 服务商（Facilitator）

**所属业务域**：项目转包（代施）管理
**实体说明**：服务商/代理商信息表，承接转包业务。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| facilitator_code | VARCHAR(64) | UNIQUE, NOT NULL | 服务商编码 |
| name | VARCHAR(128) | NOT NULL | 服务商名称 |
| type | VARCHAR(32) | NULL | 类型（服务商/代理商） |
| contact_person | VARCHAR(64) | NULL | 联系人 |
| contact_phone | VARCHAR(32) | NULL | 联系电话 |
| address | VARCHAR(256) | NULL | 地址 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- 1:N → Subcontract Project

---

## 十二、技术公告与修复任务

### 12.1 技术公告（Prob）

**所属业务域**：技术公告与修复任务
**实体说明**：技术公告主表，用于割接已知隐患自动匹配与 ITR 故障关联。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| prob_no | VARCHAR(64) | UNIQUE, NOT NULL | 技术公告编号 |
| title | VARCHAR(255) | NOT NULL | 标题 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 状态（草稿/待确认/已确认/解决中/已关闭/已拒绝） |
| content | TEXT | NULL | 公告内容 |
| software_version | VARCHAR(32) | NULL | 软件版本 |
| affected_products | JSON | NULL | 受影响产品型号 |
| repair_tasks | JSON | NULL | 修复任务（子任务表） |
| process_records | JSON | NULL | 流程过程记录 |
| weekly_reports | JSON | NULL | 进展周报 |
| read_records | JSON | NULL | 阅读记录（阅读确认表） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- N:N → DeviceSerial（受影响设备）
- N:N → ITRTicket（ITR 故障关联技术公告编号）
- 割接执行风险确认时自动匹配（FR-068）

**状态机**：见 [22.5 技术公告状态机](#225-技术公告状态机)

---

## 十三、项目周报与文件管理

### 13.1 项目周报（Weekly）

**所属业务域**：项目周报与文件管理
**实体说明**：周报头表 + 内容表 + 反馈表，继承上期数据。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| project_id | BIGINT | FK, NOT NULL | 项目 ID |
| week_no | VARCHAR(16) | NOT NULL | 周报期号 |
| inherited_from_id | BIGINT | FK, NULL | 继承上期周报 ID |
| header_data | JSON | NULL | 周报头表数据 |
| content_data | JSON | NULL | 周报内容表数据 |
| feedback_data | JSON | NULL | 周报反馈表数据 |
| attachments | JSON | NULL | 周报附件 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'draft' | 状态（draft/submitted/feedback） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `project_id` → Project
- `inherited_from_id` → Weekly（自关联，继承上期）

---

## 十四、客户资产库与客户管理

### 14.1 客户（Customer）

**所属业务域**：客户资产库与客户管理
**实体说明**：指设备最终使用方，按客户维度做资产管理。与 CRM 双向同步。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| customer_code | VARCHAR(64) | UNIQUE, NOT NULL | 客户编码 |
| name | VARCHAR(128) | NOT NULL | 客户名称 |
| address | VARCHAR(256) | NULL | 客户地址 |
| industry | VARCHAR(64) | NULL | 客户行业 |
| service_level | VARCHAR(16) | NULL | 客户服务等级（资产库统一维护） |
| belonging_unit | VARCHAR(128) | NULL | 客户所属单位 |
| department | VARCHAR(128) | NULL | 客户所属部门 |
| position | VARCHAR(64) | NULL | 客户职位 |
| is_final_customer | BOOLEAN | DEFAULT FALSE | 是否最终客户（区别下单客户，FR-082） |
| crm_sync_status | VARCHAR(16) | NULL | CRM 同步状态 |
| crm_synced_at | DATETIME | NULL | 最后同步时间 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- 1:N → CustomerContact, Project, DeviceSerial, CustomerArchive
- 与 CRM 双向同步（FR-083）
- 客户服务等级修改后对所有关联项目生效（FR-078）

### 14.2 客户资产库视图（CustomerAssetLibraryView）

**所属业务域**：客户资产库与客户管理
**实体说明**：**非实体**，以客户信息为中心的整合性管理与查询界面。聚合客户联系人、项目、发货设备明细、服务记录、故障记录、续保记录等数据。不存储独立数据，来源于各业务模块实时查询聚合；续保记录来源于外部系统 MES 集成，仅展示只读。

| 维度 | 数据来源 | 说明 |
|------|----------|------|
| 客户单位信息 | Customer | 客户编码/名称/地址/行业（PMS 导入） |
| 客户服务等级 | Customer | PMS 导入可修改，统一维护 |
| 客户联系人 | CustomerContact | 联系人姓名/电话/服务等级/部门/职务 |
| 归属项目清单 | Project | 项目名称（超链接至项目跟踪页）/合同号/办事处等 |
| 归属设备清单 | DeviceSerial | 序列号/产品编码/版本信息/维保信息/配置 Log |
| 服务记录 | CustomerArchive | 一期可仅提供框架 |
| 故障记录 | CustomerArchive / ITRTicket | 一期可仅提供框架 |
| 续保记录 | MES（外部集成） | 维保时长/维保起止时间/续保次数，仅展示只读 |

**访问权限分级**：
- 服务经理：全局访问
- 交付管理人员：按办事处访问
- 项目经理：按项目归属访问
- 其他角色：不可访问

### 14.3 客户档案（CustomerArchive）

**所属业务域**：客户资产库与客户管理
**实体说明**：客户维度档案，含故障档案与服务档案。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| customer_id | BIGINT | FK, NOT NULL | 客户 ID |
| archive_type | VARCHAR(32) | NOT NULL | 档案类型（fault 故障档案 / service 服务档案） |
| content | JSON | NULL | 档案内容（一期可仅提供框架） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `customer_id` → Customer
- 故障档案关联 ITRTicket

---

## 十五、割接管理与平台集成

> 割接单（CutOverOrder）、割接资源（CutOverResource）、备件（SparePart）实体定义见 [六、实施部署](#六实施部署)。

割接管理平台集成要点：
- 割接闭环归档后 PMS 刷新版本/CPLD/conboot 与备件序列号（FR-090）
- 割接方案基于模板库（7 类模板）生成
- 7 个工具集：信息分析、配置对比、配置翻译、脚本制作/验证、拓扑生成、方案输出、业务指标判定

---

## 十六、ITR 故障处理与 RMA 联动

### 16.1 ITR 问题单（ITRTicket）

**所属业务域**：ITR 故障处理与 RMA 联动
**实体说明**：故障处理工单。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| ticket_no | VARCHAR(64) | UNIQUE, NOT NULL | 工单号 |
| caller_info | JSON | NULL | 来电人信息 |
| problem_desc | TEXT | NOT NULL | 问题描述 |
| device_info | JSON | NULL | 设备信息（客户名称/序列号/维保状态/版本信息） |
| occur_time | DATETIME | NULL | 发生时间 |
| impact_duration | INT | NULL | 影响时长（分钟） |
| problem_level | VARCHAR(8) | NOT NULL | 问题级别（一/二/三级） |
| root_cause | TEXT | NULL | 问题根因 |
| solution | TEXT | NULL | 解决方案 |
| resolved_version | VARCHAR(32) | NULL | 解决问题版本 |
| bug_no | VARCHAR(64) | NULL | Bug 单号 |
| prob_no | VARCHAR(64) | FK, NULL | 技术公告编号 |
| product_line | VARCHAR(64) | NULL | 归属产线 |
| cause_category | JSON | NULL | 原因大小类 |
| current_official_version | VARCHAR(32) | NULL | 当前官网版本号 |
| is_official_version | BOOLEAN | NULL | 是否官网版本 |
| is_internal_tracking | BOOLEAN | NULL | 是否转内部跟踪 |
| references | JSON | NULL | 参考资料/资料来源 |
| device_serial_id | BIGINT | FK, NULL | 关联 PMS 设备 ID |
| customer_id | BIGINT | FK, NULL | 关联客户 ID |
| status | VARCHAR(16) | NOT NULL | 状态（受理/处理中/已解决/已关闭） |
| rma_order_id | BIGINT | FK, NULL | 关联 RMA 工单 ID（硬件故障触发） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `device_serial_id` → DeviceSerial
- `customer_id` → Customer
- `prob_no` → Prob
- `rma_order_id` → RMAOrder
- 故障报告归档至 ITR（FR-108）

### 16.2 RMA 工单（RMAOrder）

**所属业务域**：ITR 故障处理与 RMA 联动
**实体说明**：硬件故障处理工单，由 ITR 硬件故障解决方案触发调用。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| rma_no | VARCHAR(64) | UNIQUE, NOT NULL | RMA 工单号 |
| itr_ticket_id | BIGINT | FK, NOT NULL | 触发的 ITR 问题单 ID |
| device_serial_id | BIGINT | FK, NULL | 设备序列号 ID |
| status | VARCHAR(16) | NOT NULL | 状态（处理中/已闭环） |
| progress | JSON | NULL | 处理进展 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| closed_at | DATETIME | NULL | 闭环时间 |

**关系映射**：
- `itr_ticket_id` → ITRTicket
- `device_serial_id` → DeviceSerial

---

## 十七、AI 排障与知识库管理

### 17.1 AI 排障知识库（KnowledgeBase）

**所属业务域**：AI 排障与知识库管理
**实体说明**：AI 排障数据基础，含多种手册与排障经验。含公共 KB。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| kb_type | VARCHAR(32) | NOT NULL | 知识类型（产品标准手册/命令行手册/典配手册/日志手册/Mib节点手册/API手册/技术公告/已知隐患/FAQ/经典案例/排障经验） |
| title | VARCHAR(255) | NOT NULL | 标题 |
| content | TEXT | NULL | 内容 |
| product_line | VARCHAR(64) | NULL | 归属产品线 |
| is_public_kb | BOOLEAN | DEFAULT FALSE | 是否公共 KB |
| troubleshooting_template | JSON | NULL | 排障经验转换模板（故障单号/现象/产品架构/触发因素/排查过程） |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- 公共 KB 含产品典型故障对照表、功能模块与产品对照表、硬件定位处理手册（FR-097）
- 排障经验沉淀为训练数据（脱敏后长期保留，FR-133）

---

## 十八、系统管理与权限控制

### 18.1 角色（Role）

**所属业务域**：系统管理与权限控制
**实体说明**：角色表，关联菜单权限、按钮权限、数据权限。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| role_code | VARCHAR(64) | UNIQUE, NOT NULL | 角色编码 |
| role_name | VARCHAR(64) | NOT NULL | 角色名称 |
| menu_permissions | JSON | NULL | 菜单权限 |
| button_permissions | JSON | NULL | 按钮权限 |
| data_permissions | JSON | NULL | 数据权限（办事处/项目归属维度） |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- N:N → 用户（通过 LDAP/AD 同步）

### 18.2 部门（Department）

**所属业务域**：系统管理与权限控制
**实体说明**：部门信息表，树形结构。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| dept_code | VARCHAR(64) | UNIQUE, NOT NULL | 部门编码 |
| dept_name | VARCHAR(128) | NOT NULL | 部门名称 |
| parent_id | BIGINT | FK, NULL | 父部门 ID（树形结构） |
| is_office | BOOLEAN | DEFAULT FALSE | 是否办事处（数据权限过滤维度） |
| ldap_dn | VARCHAR(256) | NULL | LDAP/AD DN |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- `parent_id` → Department（自关联，树形）
- 从 LDAP/AD 同步（FR-112）

### 18.3 基础数据（BasicData）

**所属业务域**：系统管理与权限控制
**实体说明**：字典数据，支撑项目类型、产品线、区域等枚举。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| dict_type | VARCHAR(64) | NOT NULL | 字典类型（项目类型/产品线/区域/设备类别/任务类型等） |
| dict_code | VARCHAR(64) | NOT NULL | 字典编码 |
| dict_value | VARCHAR(255) | NULL | 字典值 |
| sort_order | INT | DEFAULT 0 | 排序 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- 字典类型 + 字典编码联合唯一

### 18.4 操作日志（OperateLog）

**所属业务域**：系统管理与权限控制
**实体说明**：记录用户操作行为。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| user_id | BIGINT | FK, NOT NULL | 操作用户 ID |
| operation | VARCHAR(128) | NOT NULL | 操作行为 |
| target_type | VARCHAR(64) | NULL | 操作对象类型 |
| target_id | VARCHAR(64) | NULL | 操作对象 ID |
| detail | TEXT | NULL | 操作详情 |
| ip_address | VARCHAR(64) | NULL | IP 地址 |
| created_at | DATETIME | NOT NULL | 操作时间 |

**关系映射**：
- `user_id` → 用户

---

## 十九、工作流引擎

### 19.1 工作流任务（Workflow Task）

**所属业务域**：工作流引擎
**实体说明**：运行时任务表 + 历史任务表，驱动审批流转。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| process_instance_id | VARCHAR(64) | NOT NULL | 流程实例 ID |
| task_no | VARCHAR(64) | UNIQUE, NOT NULL | 任务编号 |
| business_type | VARCHAR(32) | NOT NULL | 业务类型（售前/转包/回访/闭环/施工计划/实施方案等） |
| business_id | BIGINT | NOT NULL | 业务对象 ID |
| task_name | VARCHAR(128) | NULL | 任务名称（审批节点） |
| assignee_id | BIGINT | FK, NULL | 办理人 ID |
| candidate_roles | JSON | NULL | 候选角色 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | 状态（pending/completed/rejected/cancelled） |
| is_history | BOOLEAN | DEFAULT FALSE | 是否历史任务 |
| comment | TEXT | NULL | 审批意见 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| completed_at | DATETIME | NULL | 完成时间 |

**关系映射**：
- `assignee_id` → 用户
- 与业务状态机联动（售前/转包/回访/闭环等流程，FR-115）

---

## 二十、跨系统数据集成

### 20.1 跨系统集成点（IntegrationPoint）

**所属业务域**：跨系统数据集成
**实体说明**：系统与外部系统的集成关系。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| integration_code | VARCHAR(64) | UNIQUE, NOT NULL | 集成点编码 |
| direction | VARCHAR(16) | NOT NULL | 方向（inbound/outbound/bidirectional） |
| target_system | VARCHAR(64) | NOT NULL | 对端系统（CRM/D365/SMS/OA/EHR/SAP/MES/ITR/RMA/服务平台/供应链/割接平台/SPMS/钉钉等） |
| data_elements | JSON | NULL | 数据元 |
| trigger_timing | VARCHAR(128) | NULL | 触发时机 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |

**关系映射**：
- 40+ 集成点（FR-132），数据同步成功率 ≥ 99%

---

## 二十一、离线同步（新增）

> 以下 3 个实体为响应桌面客户端离线能力（FR-119a/b/c/d）新增。

### 21.1 本地缓存元数据（LocalCacheMeta）

**所属业务域**：离线同步
**实体说明**：记录桌面客户端本地缓存元数据。对应 FR-119c（加密存储/登录态校验）与 FR-119d（7 天有效期/增量刷新/过期提示）。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| user_id | BIGINT | FK, NOT NULL | 用户 ID |
| device_id | VARCHAR(128) | NOT NULL | 设备标识（不绑定特定设备，记录当前缓存所在设备） |
| cache_version | VARCHAR(64) | NOT NULL | 缓存版本 |
| download_time | DATETIME | NOT NULL | 缓存下载时间 |
| last_refresh_time | DATETIME | NOT NULL | 最后刷新时间 |
| expires_at | DATETIME | NOT NULL | 过期时间（= last_refresh_time + 7 天） |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'active' | 状态（active/expired/stale） |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**关系映射**：
- `user_id` → 用户
- 1:N → SyncQueue

**校验规则**：
- 本地缓存 MUST 加密存储（FR-119c）
- 每次启动 MUST 校验 LDAP/AD 登录态（离线时校验上次登录令牌有效期）
- 账户锁定/变更后本地缓存不可用
- 退出登录 MUST 清除本地缓存
- 缓存超期（expires_at < 当前时间）MUST 在显著位置提示"缓存已过期，请联网刷新"
- 超期不强制清除，超期后离线填写数据仍可暂存为本地草稿

### 21.2 同步队列（SyncQueue）

**所属业务域**：离线同步
**实体说明**：记录离线期间产生的待同步变更。对应 FR-119a（联网自动同步/字段级合并）与 FR-119b（离线填写暂存本地草稿/联网批量提交）。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| user_id | BIGINT | FK, NOT NULL | 用户 ID |
| device_id | VARCHAR(128) | NOT NULL | 设备标识 |
| entity_type | VARCHAR(64) | NOT NULL | 实体类型（ImplementationPlan/ConstructionPlan/SiteSurvey/ConfigLog 等） |
| entity_id | BIGINT | NOT NULL | 实体 ID |
| field_path | VARCHAR(256) | NOT NULL | 字段路径 |
| base_value | TEXT | NULL | 基础值（离线时服务端值快照） |
| base_version | INT | NOT NULL | 基础版本号（乐观锁基线） |
| new_value | TEXT | NOT NULL | 离线修改后的新值 |
| op_id | VARCHAR(64) | UNIQUE, NOT NULL | 操作 ID（UUID 幂等键，防重复同步） |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | 状态（pending/synced/conflict/rejected） |
| last_acked_op_id | VARCHAR(64) | NULL | 最后确认的操作 ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| synced_at | DATETIME | NULL | 同步完成时间 |

**关系映射**：
- `user_id` → 用户
- 1:N → ConflictRecord（冲突时产生）

**校验规则**：
- 强一致性写操作（审批提交/状态流转/割接发起/闭环申请/转包发起）离线禁用
- 实施方案/施工计划/工勘/配置调试等填写内容可离线暂存为本地草稿
- 联网后自动同步，失败时支持手动触发同步
- 已审核锁定字段拒绝离线覆盖

### 21.3 冲突记录（ConflictRecord）

**所属业务域**：离线同步
**实体说明**：记录同步冲突待人工裁定。对应 FR-119a（冲突字段提示用户人工裁定）。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, NOT NULL | 主键 |
| sync_queue_id | BIGINT | FK, NOT NULL | 同步队列 ID |
| user_id | BIGINT | FK, NOT NULL | 用户 ID |
| field_path | VARCHAR(256) | NOT NULL | 冲突字段路径 |
| base_value | TEXT | NULL | 基础值（离线时基线） |
| client_value | TEXT | NULL | 客户端值（离线修改后） |
| server_value | TEXT | NULL | 服务端值（联网同步时服务端当前值） |
| server_version | INT | NOT NULL | 服务端版本号 |
| resolution | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | 裁定结果（pending/client/server/merged） |
| resolved_by | BIGINT | FK, NULL | 裁定人 ID |
| resolved_at | DATETIME | NULL | 裁定时间 |
| resolved_value | TEXT | NULL | 裁定后的最终值 |

**关系映射**：
- `sync_queue_id` → SyncQueue
- `user_id` → 用户
- `resolved_by` → 用户

**校验规则**：
- 未冲突字段自动合并
- 冲突字段提示用户选择保留哪一方
- 已审核锁定字段拒绝离线覆盖（复用既有"乐观锁 + 字段级合并"机制）

---

## 二十二、关键状态机汇总

### 22.1 项目生命周期状态机

**实体**：Project（status_code 字段）
**说明**：顶层生命周期状态机，与"40 实施中"内嵌套交付子阶段分层并行（双层并行模型，FR-020）。

| 状态码 | 状态名称 | 说明 |
|--------|----------|------|
| 30 | 已创建 | 项目创建初始状态（FR-001） |
| 31 | 待指派 PM | 待服务经理指派项目经理 |
| 32 | 已指派 PM | 项目经理已指派，进入实施准备 |
| 40 | 实施中 | 项目实施中，内嵌套交付子阶段状态机 |
| 100 | 已闭环 | 项目闭环（终态） |
| 20 | 不予跟踪 | 终止状态（终态） |
| 36 | SM 回退 | 回退分支：服务经理回退 |
| 38 | PM 回退至服务经理 | 回退分支：项目经理回退至服务经理 |
| 42 | PM 回退实施 | 回退分支：项目经理回退实施 |

**状态流转**：
```
30 已创建 → 31 待指派PM → 32 已指派PM → 40 实施中 → 100 已闭环
                                                   ↓
                                               20 不予跟踪（终态）

回退分支（每次回退 MUST 记录日志并发送邮件通知，FR-002）：
- 36 SM 回退
- 38 PM 回退至服务经理
- 42 PM 回退实施
```

### 22.2 项目交付子阶段状态机

**实体**：Project（delivery_sub_phase 字段，status_code=40 时生效）
**说明**：采用"已完成上一阶段所有工作和产出则自动进入下一阶段"模式；割接上线、验收交维等关键节点需人工触发；子阶段回退 MUST 受控（需审批）。超期子阶段单独标红体现（FR-013）。

| 子阶段 | 说明 |
|--------|------|
| 未开始 | 初始子阶段 |
| 工前准备 | 客户联系人/工勘/需求分析/物料换货 |
| 编写实施方案 | 实施方案编写与审核 |
| 制定施工计划 | 施工计划制定与审核 |
| 实施部署 | 到货签收/硬件安装/配置调试/业务联调/割接上线 |
| 验收交维 | 现场培训/满意度调查/初验终验/交付件 |
| 超期 | 施工阶段超期，标红体现 |

**状态流转（自动流转为主）**：
```
未开始 → 工前准备 → 编写实施方案 → 制定施工计划 → 实施部署 → 验收交维
                                                              ↓
                                                          [超期标红]

- 自动流转：已完成上一阶段所有工作和产出时系统自动进入下一阶段
- 人工触发：割接上线、验收交维等关键节点需人工触发
- 受控回退：子阶段回退 MUST 审批
```

### 22.3 售前测试状态机

**实体**：Presales Project（status_code 字段）
**说明**：工作流驱动审批流（申请 → SM 审批指定 PM → PM 跟踪 → EM 回访 → 闭环），FR-051。

| 状态码 | 状态名称 | 说明 |
|--------|----------|------|
| 10 | 申请 | 售前测试申请 |
| 31 | SM 审批指定 PM | 服务经理审批并指定项目经理 |
| 32 | PM 跟踪 | 项目经理跟踪 |
| 33 | EM 回访 | 工程管理部回访 |
| 100 | 闭环 | 售前测试闭环 |
| 20 | 终止/驳回 | 终止或驳回（终态） |

**状态流转**：
```
10 申请 → 31 SM审批指定PM → 32 PM跟踪 → 33 EM回访 → 100 闭环
                                                        ↓
                                                    20 终止/驳回
```

### 22.4 转包状态机

**实体**：Subcontract Project（status 字段）
**说明**：工作流驱动转包多级审批（受益部门服务经理 → 通用审批节点 → 工程管理部 → 主任 → 合同执行），FR-055。

| 状态 | 说明 |
|------|------|
| 草稿 | 转包项目创建初始状态 |
| 审批中 | 多级审批流转中（100% 完成全部节点方可进入合同执行） |
| 合同执行 | 合同执行阶段 |
| 付款 | 付款审批流（记录付款信息与付款视图） |
| 回访 | 转包回访记录与回访问卷 |
| 验收 | 验收阶段 |
| 闭环 | 转包闭环（终态） |

**状态流转**：
```
草稿 → 审批中 → 合同执行 → 付款 → 回访 → 验收 → 闭环

- 审批流：受益部门服务经理 → 通用审批节点 → 工程管理部 → 主任 → 合同执行
- 审批流 100% 完成全部节点方可进入合同执行，无跳过（SC-004）
- D365 接口调用成功率 ≥ 99%
```

### 22.5 技术公告状态机

**实体**：Prob（status 字段）
**说明**：技术公告创建、编辑、审批，FR-067。

| 状态 | 说明 |
|------|------|
| 草稿 | 创建初始状态 |
| 待确认 | 提交确认 |
| 已确认 | 确认通过 |
| 解决中 | 修复任务发布与跟踪中 |
| 已关闭 | 关闭（终态） |
| 已拒绝 | 拒绝（终态） |

**状态流转**：
```
草稿 → 待确认 → 已确认 → 解决中 → 已关闭
                ↓
            已拒绝（终态）
```

### 22.6 离线同步状态机

**实体**：SyncQueue（status 字段）
**说明**：离线期间产生的待同步变更状态流转，对应 FR-119a/b。

| 状态 | 说明 |
|------|------|
| pending | 待同步（离线产生，待联网同步） |
| synced | 已同步成功 |
| conflict | 同步冲突（服务端字段已被他人修改，待人工裁定） |
| rejected | 已拒绝（已审核锁定字段拒绝离线覆盖） |

**状态流转**：
```
pending → synced（未冲突字段自动合并，同步成功）
       → conflict（冲突字段，进入人工裁定 → ConflictRecord）
                      ↓
               resolution: client / server / merged → synced
       → rejected（已审核锁定字段拒绝离线覆盖，终态）

- 联网后自动同步，失败时支持手动触发同步
- op_id（UUID 幂等键）防重复同步
```

---

## 二十三、校验规则（按业务域分组）

### 23.1 项目立项

| 校验项 | 规则 | 关联 FR |
|--------|------|---------|
| 合同号唯一性 | contract_no MUST 全局唯一，创建时校验 | FR-001 |
| 状态流转合法性 | status_code MUST 遵循生命周期状态机（30→31→32→40→100，回退 36/38/42，终态 20），禁止非法跳转 | FR-002 |
| 主子项目闭环前置 | 主项目闭环（100）MUST 以全部子项目闭环为前置条件 | FR-025 |
| 项目编号唯一性 | project_no 系统生成且全局唯一 | FR-001 |
| 乐观锁版本控制 | 并发编辑保存时检测 version，不一致提示冲突字段并支持字段级合并 | FR-021 |
| 已审核文档锁定 | 已提交审核的施工计划/实施方案等文档 MUST 锁定不可编辑 | FR-021 |

### 23.2 工期倒推

| 校验项 | 规则 | 关联 FR |
|--------|------|---------|
| 直签项目必填初验/终验时间 | 直签项目（含初验环节）的到货签收、初验、终验 MUST 必填，按合同规定试运行 | FR-034 |
| 非直签工期倒推规则 | 非直签项目：工前准备 = 硬件实施时间 - 2 周；硬件实施 = 设备配置时间 - 2 周；设备配置 = 割接上线时间 - 1~2 个月；割接上线 = 工期时间 - 2 周 | FR-033 |
| 直签工期倒推规则 | 直签项目：割接上线 = 初验时间 - 3 个月 - 2 周 | FR-033 |
| 初验/终验时间来源 | 初验/终验时间由 PMS 导入，不可手动调整 | FR-034 |
| 工期紧张提示 | 工期要求离当前时间不足 3 个月时提示"当前项目工期紧张"，若同时未发货/部分发货提示"请与销售确认发货时间" | FR-035 |
| 三层时间模型 | 阶段计划时间（PM 填写）/ 工期要求时间（工前准备带入，不可调整）/ 工期建议计划时间（系统自动计算） | FR-033 |

### 23.3 配置 Log

| 校验项 | 规则 | 关联 FR |
|--------|------|---------|
| 自动读取失败回退手动 | 自动读取失败时 MUST 提示失败原因并回退至手动上传模式 | FR-044 |
| 解析失败字段保留空 | 手动上传后仍尝试自动解析，解析失败字段保留为空待人工填写 | FR-044 |
| 自动与手动并行 | 自动读取与手动上传并行可用，实施人员可选其一 | FR-044 |
| 配置读取路径可配置 | 自动读取需设置 Log 读取路径 | FR-044 |
| 按序列号解析 | 自动读取的配置信息可按序列号解析 | FR-044 |

### 23.4 离线同步

| 校验项 | 规则 | 关联 FR |
|--------|------|---------|
| 强一致性写操作离线禁用 | 审批提交/状态流转/割接发起/闭环申请/转包发起等强一致性写操作 MUST 联机执行，离线时禁用 | FR-119b |
| 字段级合并冲突裁定 | 未冲突字段自动合并；冲突字段提示用户选择保留哪一方；裁定结果记录于 ConflictRecord | FR-119a |
| 已审核锁定字段拒绝覆盖 | 已审核锁定的施工计划/实施方案等字段拒绝离线覆盖（复用既有"乐观锁 + 字段级合并"机制） | FR-119a |
| 幂等键防重复同步 | op_id（UUID）作为幂等键，防止重复同步 | FR-119a |
| 本地缓存加密存储 | 本地缓存数据 MUST 加密存储 | FR-119c |
| 登录态校验 | 每次启动 MUST 校验 LDAP/AD 登录态（离线时校验上次登录令牌有效期），账户锁定/变更后本地缓存不可用 | FR-119c |
| 退出清除缓存 | 退出登录 MUST 清除本地缓存 | FR-119c |
| 不绑定特定设备 | 本地缓存不绑定特定设备 | FR-119c |
| 7 天有效期 | 本地缓存默认有效期 7 天（expires_at = last_refresh_time + 7 天） | FR-119d |
| 联网自动增量刷新 | 联网时 MUST 自动拉取增量变更刷新缓存 | FR-119d |
| 过期提示 | 缓存超期时 MUST 在显著位置提示"缓存已过期，请联网刷新"，超期不强制清除 | FR-119d |
| 超期后草稿可暂存 | 超期后离线填写数据仍可暂存为本地草稿，同步时按字段级合并冲突机制处理 | FR-119d |
| 手动触发同步 | 同步失败时 MUST 支持手动触发同步 | FR-119a |

### 23.5 数据权限

| 校验项 | 规则 | 关联 FR |
|--------|------|---------|
| 按办事处/项目归属过滤 | 数据权限按"办事处/项目归属"维度过滤：项目经理仅见自己项目，实施人员仅见自己参与的项目，交付管理人员见全局，服务经理见所辖项目 | FR-113 |
| 代理商数据隔离 | 代理商仅可见本公司数据，不可见其他代理商/客户/成本敏感数据 | FR-113 |
| 客户资产库分级访问 | 服务经理全局访问、交付管理人员按办事处访问、项目经理按项目归属访问、其他角色不可访问 | FR-079 |
| 越权访问拦截 | 越权访问拦截率 100%（SC-019） | FR-113 |
| RBAC 权限模型 | 角色 + 菜单权限 + 按钮权限 + 数据权限 | FR-109 |
| LDAP/AD 统一认证 | 对接企业 LDAP/AD 实现统一认证，用户角色与组织架构从 LDAP/AD 同步 | FR-112 |

---

**文档结束**

> 注：本文档实体类名与数据库表的详细映射（字段类型精度、索引策略、分区策略等）在 plan 阶段补充。spec 假设中明确"实体类名映射：spec 的核心实体仅列中文名，具体实体类名与数据库表的映射在 plan 阶段补充"。
