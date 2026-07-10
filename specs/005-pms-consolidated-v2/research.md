# Phase 0 Research: PMS 项目交付管理系统（归纳版）

**Date**: 2026-07-10
**Spec**: [spec.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/spec.md)
**Plan**: [plan.md](file:///d:/开发资料/PMS资料/优化/2026/阶段性汇报文件/specs/005-pms-consolidated-v2/plan.md)

## 概述

本研究针对 005 spec 引入的关键技术未知点进行选型分析，重点聚焦桌面客户端离线模式（FR-119a/b/c/d）带来的新技术决策。003 plan 已决定的核心技术栈（Spring Boot 3.2 + Vue 3.4 + MySQL 8.0 + Redis 7 + ES 8 + MinIO + Flowable + RocketMQ）沿用不重述，本研究仅补充新增技术决策与既有决策的增量验证。

---

## 1. 桌面客户端技术选型

### Decision: Electron 28+ + better-sqlite3-multiple-cipher + electron-builder 多架构出包

### Rationale
- **Vue 3 资产零改动复用**：已有 PC Web 前端（Vue 3.4 + Element Plus），Electron 内置 Chromium 渲染与浏览器一致，前端代码无任何改动即可嵌入，无需为不同 WebView 调样式
- **三端渲染一致性**：macOS/Windows/Linux 均使用同一 Chromium 引擎，规避 Tauri 依赖系统 WebView（macOS WKWebView / Linux WebKitGTK / Windows WebView2）导致的跨端差异。2026 年 4 月 Opencode 团队公开宣布从 Tauri 切回 Electron，核心理由即为 WebKit 跨端渲染不一致与 Linux WebKitGTK 版本碎片化
- **国产化适配**：Electron 自带 Chromium，渲染不依赖麒麟 V10 的 WebKitGTK 版本，规避国产 Linux 最大坑。按 CPU 架构分别出包（x64 / arm64 鲲鹏飞腾 / loongarch64 龙芯），loongarch64 通过社区工具链本地编译
- **better-sqlite3 原生模块**：Node 原生模块，Electron 主进程直接 require，同步 API 性能最优，通过 `@electron/rebuild` 针对目标架构重编译
- **生态成熟**：自动更新、崩溃上报、代码签名、安装包制作（electron-builder）企业级能力齐全
- **信创合规**：BSD 协议可商用、可私有化 fork、可本地化构建与私有 npm 源，满足"自主可控"的等保/信创审计要求

### Alternatives considered
- **Tauri 2.x**：放弃。包体积小（2-10MB）是唯一显著优势，但 Linux 端强依赖系统 WebKitGTK，麒麟 V10 不同 SP 版本、不同 CPU 架构的 WebKitGTK 版本参差不齐，部分 ES6+ 语法不支持；loongarch64 的 Rust target 支持尚不成熟；better-sqlite3 是 Node 模块无法直接使用。适合轻量工具类应用，不适合 PMS 这类 UI 密集型企业系统
- **CEF**：放弃。渲染一致性接近 Electron，但需 C++ 开发主进程，开发效率低；无内置 Node 运行时，数据层/自动更新等都要自造轮子；编译产物并不比 Electron 小；团队技能与前端栈脱节

---

## 2. 本地存储与加密方案

### Decision: SQLite + better-sqlite3-multiple-cipher（SQLCipher AES-256-CBC 透明加密）+ 库内 cache_meta 元数据表 + 会话密钥内存持有

### Rationale
- **结构化数据 SQL 查询**：业务数据（客户联系人、设备清单、实施方案、配置 Log）天然关系型，SQL 查询（按项目 ID 关联设备/联系人/日志）效率高，索引可覆盖热点查询
- **better-sqlite3-multiple-cipher**：better-sqlite3 的 drop-in 替换，API 完全兼容，仅编译时链接 SQLCipher，业务代码零改动，集成成本最低。支持 SQLCipher v4（AES-256-CBC + HMAC-SHA512），透明整库加密（WAL 日志同样加密，无明文残留）
- **同步 API 性能**：better-sqlite3 同步 API 在主进程调用，避免异步 IPC 往返，本地查询响应稳定在毫秒级，远低于 200ms 目标
- **单文件存储**：便于加密、备份、整体删除（退出登录清缓存只需删一个 .db 文件 + WAL/SHM）
- **库内 cache_meta 表**：记录 cache_version、download_time、last_refresh_time、expires_at（= last_refresh_time + 7d）、source_user_id。元数据与业务数据同库加密，避免元数据明文泄露缓存范围
- **会话密钥内存持有**：用户登录后服务端下发数据加密密钥（DEK，用用户口令或服务端主密钥包装传输），客户端保存在主进程内存，不写入磁盘/Keychain。换机登录同样能解密新下载的缓存，登出时丢弃密钥并删除库文件，即使文件残留也无法解密。缓存目录按 tenant/user_id 隔离，支持同机多账号切换

### Alternatives considered
- **IndexedDB + Web Crypto API**：放弃。仅存在于渲染进程，无 SQL 支持关系型业务查询需手动建索引/关联；异步 API 增加复杂度；字段级加密性能差且密钥管理分散
- **LevelDB / RocksDB**：放弃。纯 KV 存储，无 SQL，需自建查询层，对关系型业务是重复造轮子
- **RxDB / WatermelonDB**：放弃。离线优先封装层，但 PMS 同步逻辑由后端主导，引入会增加抽象层、依赖体积与学习成本，收益有限
- **OS 级加密（BitLocker / FileVault）**：放弃。依赖用户是否开启磁盘加密，企业 IT 环境不可控，仅作为补充纵深防御
- **机器指纹派生密钥**：放弃。典型设备绑定，违背"不绑定特定设备"需求
- **Keychain/Credential Manager 存密钥**：放弃。密钥持久化于本机，等同于设备绑定，登出后仍可被本地提取，不符合"登出清除"语义

### 7 天有效期与缓存元数据管理
- 库内 cache_meta 表记录：cache_version、download_time、last_refresh_time、expires_at（= last_refresh_time + 7d）、source_user_id、source_tenant
- 应用启动时主进程读取 expires_at 判定：未过期→直接用；已过期→标记 stale 并在显著位置提示"缓存已过期，请联网刷新"，超期不强制清除
- 草稿（离线写）单独记录 created_at，同样 7 天有效
- 所有写入更新 last_refresh_time 与 expires_at，实现"刷新即续期"

### 退出登录清除本地缓存
- 顺序：先 `db.close()` 释放文件锁 → 删除 .db / -wal / -shm 三个文件 → 调用 `session.defaultSession.clearStorageData({ storages: ['indexdb','localstorage','filesystem','appcache'] })` 清掉渲染进程残留
- 删除定位到 `app.getPath('userData')` 下该用户的缓存目录（按 user_id/tenant 隔离）
- 删除后做存在性校验，失败则标记下次启动重试

### 性能考量
- 5-20MB/项目对 SQLite 是极小数据量，配合索引单表查询通常 <10ms，复杂关联查询远低于 200ms
- SQLCipher 加密约 5-15% 性能开销，本地 IO 场景几乎无感
- 启用 WAL 模式提升并发读写；对设备序列号、项目 ID、客户手机号等热点查询字段建索引
- 大字段（配置 Log 文本）单独存表或用 BLOB，避免拖慢主表扫描

---

## 3. 离线同步协议设计

### Decision: 版本向量 + Oplog 混合方案 + per-field 三方比较 + Pull-Push + Three-way merge + 服务端 change_log 表

### Rationale

**变更追踪：版本向量 + Oplog**
- 客户端用 Oplog 精确记录离线期间字段级操作；每条记录携带简化 Version Vector（服务端版本号 + 客户端节点 ID + 本地计数器）用于因果判定
- VV 天然支持并发判定（两边计数器都推进即并发冲突），Oplog 提供操作可重放与可回溯，二者互补：VV 做冲突仲裁，Oplog 做变更内容传输

**字段级 diff：per-field version/hash 检测 + 精简 JSON Patch 传输**
- 业务对象（实施方案/施工计划/工勘/配置调试）schema 固定，采用 per-field version 检测开销最低：`client_field_version != server_field_version` 即变化
- 传输层用 JSON Patch 子集（仅 replace/add/remove）作为线上报文格式，标准化便于服务端校验与日志审计
- 字段哈希（xxhash64）用于快速比对"值是否真变"，避免 updated_at 被触发但值未变的假阳性

**冲突检测：per-field 三方比较 + 锁定字段强校验**
- 每个被客户端修改的字段提交 (field, base_value, base_version, new_value)；服务端取该字段 current_value, current_version：
  - current_version == base_version → 仅客户端改了，直接应用
  - current_version > base_version 且 current_value == new_value → 假冲突，自动合并
  - current_version > base_version 且 current_value != new_value → 真冲突，进入人工裁定队列
  - 字段标记为"已审核锁定" → 无论版本如何，拒绝离线覆盖，回退并提示

**交互模式：Pull-Push + 客户端预合并 + 服务端乐观锁终裁**
1. Pull：客户端拉取服务端自上次同步后的字段级变更（带 current_version）
2. 本地 Three-way merge：对每个本地修改字段执行三方比较，未冲突字段自动合并入本地草稿，冲突字段标记待裁定
3. 人工裁定：客户端 UI 列出冲突字段供用户选择
4. Push：客户端提交 (base_version, resolved_value)
5. 服务端终裁：再次校验 current_version == base_version（乐观锁），通过则写入，否则返回最新值触发二次 merge

**增量同步：服务端 change_log 表 + 客户端按 log_id 拉取**
- 服务端新增 change_log 表：(log_id, record_id, field, op, old_value, new_value, version, ts, actor)
- 客户端持久化 last_consumed_log_id，每次同步拉取 log_id > last_consumed_log_id 的变更流
- Oplog 天然记录删除、捕获所有中间变更、按单调递增 log_id 拉取无歧义，支持断点续传
- change_log 表设 TTL/归档策略（保留 90 天），客户端长期离线回归时触发"全量字段哈希对账"兜底

**批量提交：记录级事务 + op_id 幂等 + last_acked_op_id 续传**
- 事务粒度：按业务记录级原子（单条实施方案/工勘单多字段更新要么全成功要么全回滚）；跨记录批量不强制全局事务
- 幂等性：客户端为每个操作生成唯一 op_id（UUID + 客户端节点 ID），服务端去重
- 断点续传：客户端持久化 last_acked_op_id，批量提交后服务端逐项 ACK；中断后从 last_acked_op_id + 1 重传
- 冲突挂起：遇冲突字段该项挂起（不阻断后续项），其余字段继续提交；冲突项汇总后一次性回传客户端裁定

### Alternatives considered
- **纯向量时钟**：放弃。偏向事件全序排序，会产生虚假并发，且不区分读写语义
- **纯 Lamport 时间戳**：放弃。只给全序，无法区分真并发与因果先后，会把可并发字段误判为有序
- **纯 Wall Clock**：放弃。跨机器时钟漂移，断网更不可控
- **纯 RFC 6902 JSON Patch（含 move/copy/test）**：放弃。业务场景几乎用不到 move/copy
- **Merkle Tree**：放弃。适合海量记录集合层面的反熵比对，针对单条业务记录的字段级 diff 属于杀鸡用牛刀
- **纯 Last-Write-Wins**：放弃。会静默覆盖业务关键数据，违反"冲突字段提示用户选择"策略
- **CRDT 自动合并**：放弃。业务文本/枚举/结构化字段无法定义满足交换律的 merge 函数，仍需人工裁定
- **Push-only（客户端推、服务端裁）**：放弃。客户端无法预知服务端变更，无法做预合并，用户盲推后才发现冲突
- **updated_at 时间戳增量拉取**：放弃。无法捕获删除（需额外 tombstone）、时钟漂移导致漏拉/重拉、丢失中间版本
- **CDC（binlog 订阅）直接给客户端**：放弃。耦合数据库内部格式，应作为 Oplog 的底层实现来源而非直接暴露
- **全局大事务（整批原子）**：放弃。一个冲突回滚全批，与"字段级自动合并"目标矛盾
- **2PC 两阶段提交**：放弃。复杂度高、阻塞大，不符合最终一致模型

### 业界方案参考
- **CouchDB/PouchDB**：借鉴修订树 + 冲突标记思想，但其文档级冲突粒度需下沉到字段级
- **Firebase Offline**：借鉴透明写入队列 UX + 自动重试，但默认 last-write-wins 必须替换为字段级 VV + 三方合并
- **Linear**：本地优先架构 + Oplog 驱动 + 乐观 UI + 服务端协调，是整体范式参考
- **Notion**：离线能力较弱（多为缓存只读 + 受限编辑），非字段级同步范式，参考价值低

---

## 4. 离线登录态校验方案

### Decision: RS256 签名 JWT 离线令牌 + 7 天 TTL + 本地公钥验签 + 联网即校验 + OS 凭证库存储

### Rationale

**JWT 离线令牌**
- JWT 采用非对称签名（RS256/ES256），客户端内嵌服务端公钥，离线可独立验签，无需联网
- exp 声明为时间戳，客户端用本地系统时间比对即可判定是否过期
- 离线时无法做服务端吊销校验，只能依赖 exp 的硬过期

**离线时钟可信度**
- 限制性信任本地时钟 + 记录"最后联网时间"（last_online_at，已加密存储）作为兜底
- 离线时额外约束：`当前时间 - last_online_at <= 离线宽限期`，即使改钟也无法把"已离线 8 天"伪装成"刚断网"
- Windows 域控托管设备时钟通常由 NTP 同步，篡改概率低

**离线令牌有效期**
- 7 天，与本地业务缓存有效期对齐——缓存数据失效时令牌也失效，用户被强制联网重新认证，语义统一
- 7 天能覆盖常规出差/断网场景；高安全场景可配置缩短至 24/72 小时
- 滑动续期：每次联网即续 7 天（推荐作为增强项）

**Access Token vs Refresh Token**
- 离线期 Refresh Token 不可用（标准 OAuth2 中 RT 必须联网换取新 AT）
- 离线令牌 = 一个独立的 7 天 TTL Access Token（不依赖刷新）
- 联网后替换为标准短 AT + RT 组合

**LDAP/AD 账户变更感知**
- 离线时无法实时感知（物理限制，与 LDAP/AD 隔离）
- 联网瞬间（应用启动或网络恢复事件）立即向服务端发起"令牌 + 账户状态"联合校验，服务端转查 LDAP/AD 的 userAccountControl（ACCOUNTDISABLE=0x0002、LOCKOUT=0x0010）返回账户有效性
- 离线期间仅靠 7 天 exp 兜底，超过即拒绝访问
- 服务端黑名单：即便离线令牌未到期，联网校验发现账户已停用，服务端返回 401 并将离线令牌加入黑名单，客户端立即清除本地缓存

**令牌存储：OS 凭证库**
- Windows：DPAPI（CryptProtectData）或 Windows Credential Manager
- macOS：Keychain（配合 access group）
- Linux：libsecret / GNOME Keyring
- 严禁明文存储于配置文件、localStorage、SQLite 裸字段

**多设备登录**
- 每台设备独立持有离线令牌；服务端维护"设备-令牌"列表支持按设备吊销
- 令牌嵌入 password_version 声明，改密后版本号变更，旧令牌联网校验即判失效
- 令牌嵌入 device_id 声明，降低令牌被复制到其他设备的可用性

**风险窗口**
- 接受最长 7 天的风险窗口，通过"联网即校验 + 7 天硬过期"双重收敛
- 最坏情况（刚断网即被锁定）风险窗口为 7 天，但只要用户联网一次，风险窗口立即归零

### Alternatives considered
- **对称签名 HS256**：放弃。客户端需持有密钥，泄露后可伪造任意令牌
- **TPM Secure Clock**：放弃。最强方案但跨平台兼容性差、实现复杂，投入产出比低
- **纯在线校验**：放弃。违背"离线可用"核心需求
- **24 小时短令牌**：放弃。频繁要求联网，断网超 1 天的用户体验差
- **30 天长令牌**：放弃。安全窗口过大
- **OAuth2 Device Flow**：放弃。面向无键盘/无浏览器设备，与桌面客户端场景不符
- **CouchDB/PouchDB 离线认证**：放弃。基于 cookie session + 本地复制，对企业 PMS 的 LDAP/AD 鉴权链路不直接适用
- **应用自实现 AES 加密 + 硬编码密钥**：放弃。密钥随应用分发即可被提取，等同明文

---

## 5. 增量缓存刷新策略

### Decision: 服务端 change_log 表（与离线同步协议共用）+ 客户端 last_consumed_log_id 增量拉取 + 联网时自动后台刷新

### Rationale
- 与离线同步协议共用同一套 change_log 机制，避免重复建设
- 客户端联网时自动后台拉取 log_id > last_consumed_log_id 的变更，刷新本地缓存
- 刷新即续期：每次成功刷新更新 last_refresh_time 与 expires_at
- 超期不强制清除，仅在显著位置提示"缓存已过期，请联网刷新"

### Alternatives considered
- **基于 updated_at 时间戳增量拉取**：放弃。无法捕获删除、时钟漂移导致漏拉/重拉、丢失中间版本
- **CDC binlog 订阅直接给客户端**：放弃。耦合数据库内部格式

---

## 6. 网络拓扑自动生成

### Decision: 基于 Cytoscape.js + dagre 布局算法，从接口对照表生成拓扑数据结构

### Rationale
- Cytoscape.js 是成熟的图论可视化库，支持 DAG 布局、交互式操作、导出图片
- dagre 布局算法适合层级网络拓扑（上下游设备 + 接口互联）
- 接口对照表（FR-100）本身已是结构化数据，可直接映射为图节点（设备）与边（接口互联）
- 非 PNG 图片，支持标注上下游设备与接口互联（FR-101）

### Alternatives considered
- **ECharts Graph**：放弃。图论能力弱于 Cytoscape.js，不适合复杂网络拓扑
- **D3-force**：放弃。需自建布局逻辑，开发成本高
- **vis-network**：放弃。交互能力弱于 Cytoscape.js

---

## 7. AI 排障 RAG 架构

### Decision: Elasticsearch 8 kNN 向量检索 + 自研提示模板 + LLM 集成

### Rationale
- 复用已有 Elasticsearch 8.x 基础设施，无需额外引入 Milvus/PgVector
- ES 8.x 内置 kNN（k-Nearest Neighbors）向量检索能力，支持 dense_vector 字段类型
- 知识库（产品标准手册/命令行手册/典配手册/日志手册/Mib 节点手册/API 手册/技术公告/已知隐患/FAQ/经典案例/排障经验）向量化后存入 ES
- AI AGENT 工具集（命令解析/功能配置/日志解析/MIB 解析/API 解析/场景答疑）通过提示模板训练 Skill
- 排障经验转换模板产出（故障单号/现象/产品架构/触发因素/排查过程）沉淀为训练数据
- 诊断命中率目标 ≥70%（SC-010）

### Alternatives considered
- **Milvus 独立向量数据库**：放弃。增加运维成本，ES kNN 已满足需求
- **PgVector（PostgreSQL 扩展）**：放弃。未使用 PostgreSQL，且 ES kNN 性能更优
- **纯关键词检索**：放弃。无法理解故障语义，命中率不足

---

## 8. 多数据源动态路由

### Decision: dynamic-datasource-spring-boot-starter（苞米豆）

### Rationale
- 老系统依赖 9 个外部库（D365/CRM/SAP/MES 等直连查询），合并为单库需大量 ETL 且数据所有权分散
- dynamic-datasource-spring-boot-starter 是 Spring Boot 生态最成熟的多数据源方案，支持注解切换、分布式事务、读写分离
- 与 MyBatis-Plus 无缝集成
- 支持动态添加数据源（运行时）

### Alternatives considered
- **自研 AbstractRoutingDataSource**：放弃。重复造轮子，功能不如成熟方案
- **Spring Cloud 多数据源微服务**：放弃。一期采用模块化单体（Modulith），后续按需拆分

---

## 9. 工作流迁移：Activiti 5 → Flowable 7

### Decision: Flowable 7.x 重写流程定义，保留 BPMN 语义

### Rationale
- 老系统 Activiti 5.23 已 EOL，存在安全漏洞与 Java 17 兼容问题
- Flowable 7 是 Activiti 团队 fork 的现代继承者，BPMN 2.0 兼容，API 设计更现代
- 新系统 MUST 保留老系统业务流程语义（状态机、审批节点、角色指派），但 MUST NOT 复用老引擎与原流程定义文件
- 复杂审批流（售前/转包/回访/闭环多级审批、会签/或签/委派/超时升级）需要成熟工作流引擎
- Flowable 支持 DMN 决策表（用于割接等级评定规则）、CMMN 案例（用于巡检流程）

### Alternatives considered
- **Camunda 8**：放弃。Camunda 8 转向云原生 SaaS 模式，本地部署需 Camunda Platform 8 Self-Managed，复杂度高
- **自研状态机**：放弃。无法支持复杂审批流（会签/或签/委派/超时升级）

---

## 10. 数据迁移与灰度切换

### Decision: Python ETL（自研脚本）+ Debezium CDC 增量同步 + 按办事处灰度切换

### Rationale
- 老系统 286 表 + 43 视图，仅核心业务表需迁移（项目/售前/转包/回访/维保 + 基础数据 + 用户/部门）
- Python ETL 脚本灵活，可处理老系统 iBATIS/MyBatis 双 ORM 产生的数据冗余
- Debezium CDC（基于 MySQL binlog 订阅）实现新老系统增量数据双向同步，延迟 ≤5 分钟
- 灰度切换：按办事处或项目类型分批切换，先试点后推广；切换失败可回滚至老系统
- 迁移完整性校验：记录数对比 + 关键字段抽样核对，校验失败告警并阻塞切换

### Alternatives considered
- **Bonobo/Petl ETL 框架**：放弃。功能限制多，不如自研脚本灵活
- **全量切换**：放弃。风险过高，违背"不可中断业务"约束
- **不迁移，老系统继续运行**：放弃。违反系统升级目标

---

## 11. 安全架构

### Decision: Spring Security + LDAP/AD 绑定认证 + RBAC + 数据权限拦截器 + 本地缓存加密 + JWT 离线令牌

### Rationale
- **认证**：LDAP/AD 绑定认证（非钉钉 SSO），复用企业目录服务
- **授权**：RBAC 角色权限 + 数据权限按"办事处/项目归属"维度过滤
- **本地缓存加密**：SQLCipher AES-256-CBC 透明加密
- **离线令牌**：RS256 JWT + 7 天 TTL + OS 凭证库存储
- **Web 安全**：XSS 转义 + CSRF Token + SQL 预编译 + 安全日志
- **审计**：操作日志 + 登录日志 + 集成调用日志

### Alternatives considered
- **钉钉 SSO**：放弃。项目明确要求 LDAP/AD
- **OAuth2 + 自建用户中心**：放弃。增加用户管理复杂度，企业已有 LDAP/AD
- **本地缓存明文**：放弃。业务敏感数据泄露风险

---

## 12. 可观测性

### Decision: SkyWalking 链路追踪 + Prometheus 指标 + ELK 日志 + 离线同步专项监控

### Rationale
- **链路追踪**：SkyWalking 8.x 支持 Spring Boot 3 + Spring Cloud，自动埋点，对业务代码零侵入
- **指标**：Prometheus + Grafana，监控 JVM/DB/Redis/ES/接口性能/业务指标
- **日志**：Logback + ELK（Elasticsearch + Logstash + Kibana），集中日志查询与分析
- **离线同步专项监控**：同步成功率、冲突率、缓存命中率、同步延迟、令牌过期率等专项指标
- **告警**：Prometheus AlertManager + 钉钉/邮件通知

### Alternatives considered
- **Zipkin**：放弃。功能弱于 SkyWalking，无 APM
- **Datadog**：放弃。商业 SaaS，数据出境合规风险
- **Pinpoint**：放弃。社区活跃度低于 SkyWalking

---

## 研究结论汇总

| 研究项 | 决策 | 关键理由 |
|--------|------|----------|
| 桌面客户端框架 | Electron 28+ | Vue 3 零改动复用，三端渲染一致，国产化多架构编译 |
| 本地存储 | SQLite + better-sqlite3 | 同步 API 性能最优，关系型业务 SQL 查询 |
| 本地加密 | better-sqlite3-multiple-cipher（SQLCipher AES-256） | 透明整库加密，API 兼容，集成成本最低 |
| 缓存元数据 | 库内 cache_meta 表 | 元数据同库加密，避免明文泄露 |
| 密钥管理 | 会话密钥内存持有，不绑设备 | 换机可用，登出即清除 |
| 离线同步协议 | 版本向量 + Oplog + per-field 三方合并 + Pull-Push | 字段级合并 + 人工裁定，避免静默覆盖 |
| 增量同步 | 服务端 change_log 表 + log_id 拉取 | 支持删除/中间版本/断点续传 |
| 批量提交 | 记录级事务 + op_id 幂等 + last_acked_op_id 续传 | 冲突挂起不阻断后续项 |
| 离线认证 | RS256 JWT + 7 天 TTL + 联网即校验 + OS 凭证库 | 风险窗口 7 天，联网即收敛 |
| 增量缓存刷新 | change_log 共用 + 联网后台自动刷新 | 刷新即续期 |
| 网络拓扑 | Cytoscape.js + dagre | 成熟图论可视化，支持 DAG 布局 |
| AI 排障 | ES 8 kNN + 自研提示模板 + LLM | 复用 ES 基础设施，命中率 ≥70% |
| 多数据源 | dynamic-datasource-spring-boot-starter | 苞米豆成熟方案，注解切换 |
| 工作流 | Flowable 7.x 重写 | Activiti 5 EOL，BPMN 兼容 |
| 数据迁移 | Python ETL + Debezium CDC + 灰度切换 | 增量同步延迟 ≤5 分钟，可回滚 |
| 安全 | Spring Security + LDAP/AD + RBAC + 本地加密 + JWT | 企业目录服务，数据权限过滤 |
| 可观测性 | SkyWalking + Prometheus + ELK + 离线专项监控 | 零侵入埋点，集中日志 |

所有 NEEDS CLARIFICATION 项已解决，可进入 Phase 1 设计阶段。
