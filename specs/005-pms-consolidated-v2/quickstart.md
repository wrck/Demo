# Quickstart: PMS 项目交付管理系统（归纳版）

**Date**: 2026-07-10
**Spec**: [spec.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/spec.md)
**Plan**: [plan.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/plan.md)

本文档定义 PMS 系统的端到端验证场景，证明核心业务流程与桌面客户端离线能力可运行。仅作为验证/运行指南，不包含完整实现代码。

---

## 前置条件

### 环境依赖

| 组件 | 版本 | 用途 |
|------|------|------|
| JDK | 17 LTS | 后端运行时 |
| Node.js | 20 LTS | 前端与桌面客户端构建 |
| Python | 3.11+ | 数据迁移脚本 |
| MySQL | 8.0 | 主数据库 |
| Redis | 7.x | 缓存/分布式锁 |
| Elasticsearch | 8.x | 全文检索/向量检索 |
| MinIO | 最新 | 对象存储 |
| RocketMQ | 5.x | 消息队列 |
| LDAP/AD | 企业现有 | 统一认证 |
| Flowable | 7.x | 工作流引擎 |

### 服务清单

| 服务 | 端口 | 说明 |
|------|------|------|
| pms-backend | 8080 | 后端 API 服务 |
| pms-frontend | 5173 | PC Web 前端（Vite dev） |
| pms-desktop | - | 桌面客户端（Electron） |
| pms-mobile | 5174 | 移动端 H5（Vite dev） |
| MySQL | 3306 | 主数据库 |
| Redis | 6379 | 缓存 |
| Elasticsearch | 9200 | 搜索 |
| MinIO | 9000/9001 | 对象存储 |
| RocketMQ NameServer | 9876 | 消息队列 |

---

## 场景 1：项目生命周期与总体跟踪

**验证目标**：项目从创建到闭环的完整生命周期流转（FR-001~FR-020）

**关联契约**：[rest-api.md 项目交付核心生命周期](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/contracts/rest-api.md)

### 步骤

1. **登录认证**：通过 LDAP/AD 绑定认证登录，获取 JWT 令牌
   ```bash
   POST /api/v1/auth/login
   { "username": "pm_zhang", "password": "***", "authSource": "LDAP" }
   ```
   预期：返回 `{ code: 0, data: { token, refreshToken, user, roles } }`

2. **创建项目**：通过合同号创建项目
   ```bash
   POST /api/v1/projects
   { "contractNo": "HT-2026-001", "projectName": "某省政务网项目" }
   ```
   预期：项目创建，状态码 30（已创建）

3. **指派服务经理**：管理员指定 SM
   ```bash
   PUT /api/v1/projects/{projectId}/assign-sm
   { "smId": "sm_li" }
   ```
   预期：状态流转 30→31，SM 收到钉钉通知

4. **指派项目经理**：SM 指定 PM
   ```bash
   PUT /api/v1/projects/{projectId}/assign-pm
   { "pmId": "pm_zhang" }
   ```
   预期：状态流转 31→32，PM 收到钉钉通知

5. **进入实施**：PM 启动实施
   ```bash
   PUT /api/v1/projects/{projectId}/start-delivery
   ```
   预期：状态流转 32→40（实施中），进入交付子阶段"未开始"

6. **总体跟踪页面**：查看 8 阶段统计卡片
   ```bash
   GET /api/v1/projects/tracking?office=&phase=40&keyword=
   ```
   预期：返回 8 阶段统计卡片数据，搜索响应 ≤2 秒

7. **闭环**：PM 发起闭环申请，通过审批后状态流转至 100

---

## 场景 2：工前准备与工期倒推

**验证目标**：客户联系人录入、工勘问卷填写、施工计划三层时间模型与工期倒推（FR-026~FR-036）

**关联数据模型**：[data-model.md 工前准备实体](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/data-model.md)

### 步骤

1. **录入客户联系人**（客户基础信息由 CRM 带入）
   ```bash
   POST /api/v1/projects/{projectId}/customer-contacts
   { "name": "王主任", "phone": "138****1234", "isPrimary": true }
   ```
   预期：主联系人显示在项目页面

2. **填写工勘问卷**：机房供电、网口、机柜、光模块、上架加电等
   ```bash
   POST /api/v1/projects/{projectId}/site-survey
   { "powerSupply": "ok", "outletType": "PDU", "needOutsource": true }
   ```
   预期：选择"需要外包"时展示"发起外包流程"链接

3. **填写施工计划**（非直签项目工期倒推）
   ```bash
   POST /api/v1/projects/{projectId}/construction-plan
   { "deadline": "2026-12-31" }
   ```
   预期：系统按倒推逻辑自动计算工期建议计划时间（割接-上线=工期时间-2周，设备配置=割接上线-1~2个月...）

4. **工期紧张提醒**：工期要求离当前时间不足 3 个月
   预期：提示"当前项目工期紧张，请详细落实好工期计划"

5. **提交施工计划审核**：推送到服务经理钉钉审批
   ```bash
   POST /api/v1/projects/{projectId}/construction-plan/submit
   ```
   预期：审批任务创建，SM 收到钉钉推送

---

## 场景 3：实施部署与配置 Log

**验证目标**：到货签收、硬件安装、配置 Log 自动读取与手动回退、业务联调（FR-042~FR-046）

### 步骤

1. **配置 Log 自动读取**
   ```bash
   POST /api/v1/projects/{projectId}/config-debug/read-log
   { "logPath": "/tmp/config-logs/" }
   ```
   预期：系统自动读取对应路径下配置 Log 文件，按序列号解析配置信息回填

2. **自动读取失败回退手动上传**
   预期：自动读取失败时提示失败原因，回退手动上传模式；手动上传后仍尝试自动解析，解析失败字段保留为空待人工填写

3. **业务联调一键收集**
   ```bash
   POST /api/v1/projects/{projectId}/business-debug/collect
   { "devices": [{ "ip": "192.168.1.1", "username": "admin", "loginType": "SSH" }] }
   ```
   预期：采集设备配置，设备清单展示设备型号、序列号、运行业务描述

---

## 场景 4：桌面客户端离线模式（005 新增关键场景）

**验证目标**：FR-119a/b/c/d 桌面客户端离线写操作、缓存、同步、冲突解决

**关联契约**：[desktop-sync.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/contracts/desktop-sync.md)

### 步骤

1. **下载与登录桌面客户端**
   - 安装桌面客户端（Windows/macOS/麒麟 V10）
   - 通过 LDAP/AD 登录，获取离线令牌（7 天 TTL）
   - 预期：离线令牌存入 OS 凭证库，本地 SQLite 加密库初始化

2. **提前缓存项目数据**
   ```bash
   POST /api/v1/cache/download
   { "projectIds": ["proj_001", "proj_002"] }
   ```
   预期：项目信息/设备清单/实施方案/配置 Log 等下载至本地 SQLite（加密），cache_meta 记录 expires_at = now + 7d

3. **断网离线操作**
   - 断开网络连接
   - 进入实施方案页面，填写方案内容
   - 预期：填写内容暂存为本地草稿，强一致性操作（审批提交/状态流转/割接发起）按钮禁用并提示"该操作需联机执行"

4. **联网自动同步**
   - 恢复网络连接
   - 预期：自动触发 delta-sync，本地草稿通过 Pull-Push 流程同步至服务端

5. **冲突解决（如有）**
   - 假设离线期间服务端实施方案已被他人修改
   - 预期：未冲突字段自动合并，冲突字段弹出人工裁定 UI（显示 base_value/client_value/server_value），已审核锁定字段拒绝覆盖

6. **缓存过期提示**
   - 模拟缓存超过 7 天
   - 预期：显著位置提示"缓存已过期，请联网刷新"，但不强制清除；离线填写数据仍可暂存

7. **退出登录清除缓存**
   - 退出登录
   - 预期：本地 SQLite 文件（.db/.wal/.shm）删除，渲染进程 session 存储清除

---

## 场景 5：客户资产库与 CRM 同步

**验证目标**：FR-074~FR-083 客户资产库整合查询与 CRM 双向同步

### 步骤

1. **从项目跟踪页进入客户资产库**
   - 在项目总体跟踪页面点击"客户单位"超链接
   - 预期：跳转至客户资产库页面，展示客户单位信息、联系人、归属项目、归属设备

2. **修改客户服务等级**
   ```bash
   PUT /api/v1/customers/{customerId}/service-level
   { "serviceLevel": "VIP" }
   ```
   预期：关联项目联系人服务等级同步更新（延迟 ≤1 分钟）

3. **MES 续保记录只读展示**
   - 预期：续保记录由 MES 集成获取，仅展示只读，MES 不可达时提示"续保记录暂不可用"但不阻塞其他资产信息

---

## 场景 6：割接管理与平台集成

**验证目标**：FR-085~FR-090 割接发起、等级评定、方案生成、闭环归档

### 步骤

1. **发起割接**：前期流程完成后点击"发起流程"
   ```bash
   POST /api/v1/cutover/orders
   { "projectId": "proj_001", "source": "ENGINEERING", "type": "NEW_NETWORK" }
   ```
   预期：进入割接平台，按类型建单

2. **自动评定等级**
   - 预期：依据评定办法自动评定 A/B 类，按类发起分级审批

3. **生成割接方案与操作单**
   - 预期：基于模板库生成方案，自动生成准备/割接/割接后/回退操作单及 checklist

4. **闭环归档**
   - 预期：采集设备信息、承诺书签字后闭环，归档刷新 PMS 版本/CPLD/conboot/备件序列号

---

## 场景 7：数据迁移与灰度切换

**验证目标**：FR-124~FR-126 老系统数据迁移与并行运行

### 步骤

1. **执行全量迁移**
   ```bash
   python scripts/migration/full_migration.py --source legacy --target pms --tables core
   ```
   预期：迁移核心业务表（项目/售前/转包/回访/维保 + 基础数据 + 用户/部门）

2. **完整性校验**
   ```bash
   python scripts/migration/verify.py
   ```
   预期：记录数对比 + 关键字段抽样核对，校验失败告警并阻塞切换

3. **启动增量同步**
   - 启动 Debezium CDC，监控老系统 MySQL binlog
   - 预期：增量数据双向同步，延迟 ≤5 分钟

4. **灰度切换**
   - 按办事处试点切换
   - 预期：切换失败可回滚至老系统

---

## 场景 8：多终端访问

**验证目标**：FR-119~FR-123 五类终端覆盖

### 步骤

1. **PC Web**：Chrome 访问 `https://pms.example.com`，全功能操作
2. **桌面客户端**：Electron 客户端登录，在线/离线模式切换（见场景 4）
3. **工程师移动端 H5**：手机浏览器访问 `https://pms.example.com/m/engineer`，GPS 签到、拍照记录
4. **代理商 H5**：代理商工程师访问 `https://pms.example.com/m/agent`，接单、上报、交付
5. **客户 H5**：客户手机号+短信验证码登录，进度查看、割接审批、验收签核
   - 预期：仅暴露极有限只读字段，数据权限隔离

---

## 验证检查清单

| 场景 | 验证项 | 关联 FR | 预期结果 |
|------|--------|---------|----------|
| 1 | 项目状态流转 30→31→32→40→100 | FR-002 | 流转成功，日志与通知发送 |
| 1 | 总体跟踪 8 阶段卡片 | FR-011 | 卡片数字与项目列表一致 |
| 2 | 非直签项目工期倒推 | FR-033 | 建议计划时间按倒推逻辑计算 |
| 2 | 工期紧张提醒 | FR-035 | 不足 3 个月时提示 |
| 3 | 配置 Log 自动读取失败回退 | FR-044 | 回退手动上传，解析失败字段为空 |
| 4 | 桌面客户端离线写草稿 | FR-119b | 实施方案/施工计划/工勘草稿暂存 |
| 4 | 强一致性操作离线禁用 | FR-119b | 审批/状态流转按钮禁用 |
| 4 | 联网自动同步 | FR-119a | delta-sync 自动触发 |
| 4 | 字段级合并冲突解决 | FR-119a | 未冲突自动合并，冲突人工裁定 |
| 4 | 本地缓存加密 | FR-119c | SQLCipher AES-256 透明加密 |
| 4 | 7 天缓存过期 | FR-119d | 过期提示，不强制清除 |
| 4 | 退出登录清除缓存 | FR-119c | .db/.wal/.shm 文件删除 |
| 5 | 客户资产库整合查询 | FR-074 | 客户单位/联系人/项目/设备聚合展示 |
| 5 | 客户服务等级同步 | FR-078 | 修改后关联项目同步（≤1 分钟） |
| 5 | MES 续保记录只读 | FR-080 | 仅展示，MES 不可达时降级 |
| 6 | 割接等级评定 | FR-086 | A/B 类自动评定 |
| 6 | 操作单与 checklist 自动生成 | FR-088 | 准备/割接/割接后/回退操作单 |
| 7 | 数据迁移完整性校验 | FR-125 | 记录数对比 + 抽样核对 |
| 7 | 灰度切换与回滚 | FR-126 | 失败可回滚 |
| 8 | 五类终端覆盖 | FR-119~123 | PC Web/桌面/工程师 H5/代理商 H5/客户 H5 |

---

## 性能基线

| 指标 | 目标 | 关联 SC |
|------|------|---------|
| 1000 并发用户 | 无 degradation | SC-021 |
| 报表 P95 响应 | ≤2 秒 | SC-021 |
| CRM 同步延迟 | ≤5 分钟 | SC-012 |
| 客户服务等级同步 | ≤1 分钟 | SC-012 |
| 物料换货推送 CRM | ≤1 分钟 | SC-014 |
| 跨系统集成成功率 | ≥99% | SC-017 |
| 系统可用性 | ≥99.9% | SC-023 |
| 桌面客户端本地查询 | ≤200ms | - |
| 桌面客户端增量同步 | ≤30 秒/项目 | - |

---

## 下一步

完成 quickstart 验证后，可进入 `/speckit-tasks` 阶段生成实施任务清单。
