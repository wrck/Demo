# 桌面客户端离线同步协议契约：PMS 项目交付管理系统

**Date**: 2026-07-10
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Research**: [research.md](../research.md)

## 概述

本契约定义 PMS 桌面客户端（Electron 28+ + better-sqlite3-multiple-cipher）离线模式下的同步协议。基于 research.md 决策，采用 **版本向量 + Oplog 混合方案 + per-field 三方比较 + Pull-Push + Three-way merge + 服务端 change_log 表** 的字段级合并同步协议。

### 设计目标

- 离线写操作本地响应 ≤200ms
- 联网后增量同步 ≤30 秒/项目
- 未冲突字段自动合并，冲突字段人工裁定，已审核锁定字段拒绝覆盖
- 字段级 diff，避免整记录覆盖
- 支持断点续传与幂等提交

### 核心约束

- 仅允许填写类写操作暂存草稿；强一致性操作离线禁用（审批/状态流转/割接发起/闭环/转包发起等）
- 本地缓存 SQLCipher AES-256-CBC 透明加密
- 7 天有效期，登出清除本地缓存

---

## 1. 同步协议概述

### 1.1 架构决策

| 决策项 | 方案 |
|--------|------|
| 变更追踪 | 版本向量 + Oplog 混合 |
| 字段级 diff | per-field version/hash 检测 + 精简 JSON Patch 传输 |
| 冲突检测 | per-field 三方比较 + 锁定字段强校验 |
| 交互模式 | Pull-Push + 客户端预合并 + 服务端乐观锁终裁 |
| 增量同步 | 服务端 change_log 表 + 客户端按 log_id 拉取 |
| 批量提交 | 记录级事务 + op_id 幂等 + last_acked_op_id 续传 |

### 1.2 同步流程

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│  桌面客户端  │                  │   PMS 服务端 │                  │  change_log │
│ (本地 SQLite)│                  │  (MySQL)    │                  │   (表)      │
└──────┬──────┘                  └──────┬──────┘                  └──────┬──────┘
       │                                │                                │
       │  1. Pull（last_consumed_log_id）│                                │
       │───────────────────────────────>│  查询 log_id > last            │
       │                                │───────────────────────────────>│
       │  2. 返回字段级变更（带 version）│<───────────────────────────────│
       │<───────────────────────────────│                                │
       │                                │                                │
       │  3. 本地 Three-way merge        │                                │
       │  (未冲突字段自动合并入草稿)     │                                │
       │  (冲突字段标记待裁定)           │                                │
       │                                │                                │
       │  4. 人工裁定冲突字段            │                                │
       │                                │                                │
       │  5. Push（base_version, resolved_value, op_id）                │
       │───────────────────────────────>│  6. 服务端乐观锁终裁            │
       │                                │  current_version == base?      │
       │                                │  - 是 → 写入                  │
       │                                │  - 否 → 返回最新值二次 merge   │
       │  7. 逐项 ACK（last_acked_op_id）│                                │
       │<───────────────────────────────│                                │
       │                                │                                │
```

### 1.3 冲突检测规则

每个被客户端修改的字段提交 `(field, base_value, base_version, new_value)`，服务端取该字段 `current_value, current_version`：

| 条件 | 判定 | 处理 |
|------|------|------|
| current_version == base_version | 仅客户端改了 | 直接应用 |
| current_version > base_version 且 current_value == new_value | 假冲突 | 自动合并 |
| current_version > base_version 且 current_value != new_value | 真冲突 | 进入人工裁定队列 |
| 字段标记为"已审核锁定" | 锁定字段 | 无论版本如何，拒绝离线覆盖，回退并提示 |

---

## 2. 同步端点

所有同步端点统一前缀 `/api/v1/sync/`。

### 2.1 POST /api/v1/sync/pull - 拉取服务端变更

客户端拉取服务端自上次同步后的字段级变更。

**权限要求**：`sync:pull`（登录用户）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lastConsumedLogId | long | 是 | 上次消费的 log_id（首次传 0） |
| entityTypes | array | 否 | 拉取的实体类型（不传则全量） |
| projectId | long | 否 | 限定项目范围 |
| batchSize | integer | 否 | 批量大小，默认 500 |

**响应数据**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "logs": [
      {
        "logId": 10001,
        "recordId": "impl-scheme-5001",
        "entityType": "implementation_scheme",
        "field": "configScript",
        "op": "replace",
        "oldValue": "...",
        "newValue": "...",
        "version": 3,
        "ts": "2026-07-10T10:00:00Z",
        "actor": { "userId": 10, "username": "pm_zhang", "nodeId": "server" }
      }
    ],
    "latestLogId": 10001,
    "hasMore": false,
    "serverTime": "2026-07-10T10:00:05Z"
  }
}
```

### 2.2 POST /api/v1/sync/push - 推送本地变更

客户端提交离线期间的字段级变更（带 base_version 用于乐观锁）。

**权限要求**：`sync:push`（登录用户）

**请求参数**：

```json
{
  "deviceId": "client-node-001",
  "operations": [
    {
      "opId": "op-uuid-001",
      "recordId": "impl-scheme-5001",
      "entityType": "implementation_scheme",
      "field": "configScript",
      "op": "replace",
      "baseValue": "原值...",
      "baseVersion": 3,
      "newValue": "新值...",
      "clientVersionVector": { "server": 10001, "client": "node-001", "count": 5 },
      "fieldHash": "xxhash64-of-newvalue",
      "ts": "2026-07-09T15:00:00Z"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| deviceId | string | 是 | 客户端节点 ID（设备标识） |
| operations | array | 是 | 操作列表（记录级事务，单条多字段原子） |
| operations[].opId | string | 是 | 操作唯一 ID（UUID + 客户端节点 ID，幂等去重） |
| operations[].recordId | string | 是 | 业务记录 ID |
| operations[].entityType | string | 是 | 实体类型 |
| operations[].field | string | 是 | 字段名 |
| operations[].op | string | 是 | replace / add / remove |
| operations[].baseValue | any | 是 | 客户端基准值 |
| operations[].baseVersion | long | 是 | 客户端基准版本号 |
| operations[].newValue | any | 是 | 新值 |
| operations[].clientVersionVector | object | 是 | 简化版本向量（服务端版本号 + 客户端节点 ID + 本地计数器） |
| operations[].fieldHash | string | 是 | xxhash64 字段哈希（快速比对值是否真变） |
| operations[].ts | datetime | 是 | 本地操作时间戳 |

**响应数据**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "results": [
      {
        "opId": "op-uuid-001",
        "status": "applied",
        "newVersion": 4,
        "logId": 10002
      },
      {
        "opId": "op-uuid-002",
        "status": "auto_merged",
        "reason": "fake_conflict",
        "newVersion": 4
      },
      {
        "opId": "op-uuid-003",
        "status": "conflict",
        "reason": "real_conflict",
        "currentValue": "服务端当前值...",
        "currentVersion": 5,
        "currentActor": { "userId": 20, "username": "sm_li" }
      },
      {
        "opId": "op-uuid-004",
        "status": "rejected",
        "reason": "field_locked",
        "message": "该字段已审核锁定，不可离线覆盖"
      }
    ],
    "lastAckedOpId": "op-uuid-002",
    "conflicts": [
      {
        "opId": "op-uuid-003",
        "recordId": "impl-scheme-5001",
        "entityType": "implementation_scheme",
        "field": "configScript",
        "baseValue": "客户端基准值",
        "clientValue": "客户端新值",
        "serverValue": "服务端当前值",
        "baseVersion": 3,
        "currentVersion": 5
      }
    ]
  }
}
```

### 2.3 POST /api/v1/sync/ack - 确认消费

客户端确认已消费的 log_id，更新 last_consumed_log_id。

**权限要求**：`sync:ack`（登录用户）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| consumedLogId | long | 是 | 已消费到的 log_id |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "ackedLogId": 10001,
    "serverTime": "2026-07-10T10:00:10Z"
  }
}
```

### 2.4 POST /api/v1/sync/conflicts - 提交冲突裁定结果

客户端人工裁定后提交解决值。

**权限要求**：`sync:resolve`（登录用户）

**请求参数**：

```json
{
  "resolutions": [
    {
      "conflictId": "conflict-001",
      "recordId": "impl-scheme-5001",
      "entityType": "implementation_scheme",
      "field": "configScript",
      "resolvedValue": "用户裁定后的最终值",
      "baseVersion": 5,
      "resolutionStrategy": "manual"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| resolutions | array | 是 | 裁定结果列表 |
| resolutions[].conflictId | string | 是 | 冲突 ID |
| resolutions[].resolvedValue | any | 是 | 裁定后的最终值 |
| resolutions[].baseVersion | long | 是 | 服务端当前版本（二次乐观锁校验） |
| resolutions[].resolutionStrategy | string | 是 | manual（人工）/ auto（自动合并回放） |

**响应**：同 push 响应结构，含终裁结果（可能二次冲突需再次裁定）。

### 2.5 GET /api/v1/sync/status - 同步状态

**权限要求**：`sync:status`（登录用户）

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "lastSyncAt": "2026-07-10T10:00:00Z",
    "lastConsumedLogId": 10001,
    "pendingOps": 5,
    "pendingConflicts": 1,
    "syncState": "idle"
  }
}
```

---

## 3. 数据结构

### 3.1 SyncQueue（同步队列，客户端本地）

客户端本地 SQLite 表，存储待推送的离线操作。

```sql
CREATE TABLE sync_queue (
  op_id          TEXT PRIMARY KEY,       -- UUID + 客户端节点 ID
  record_id      TEXT NOT NULL,           -- 业务记录 ID
  entity_type    TEXT NOT NULL,           -- 实体类型
  field          TEXT NOT NULL,           -- 字段名
  op             TEXT NOT NULL,           -- replace / add / remove
  base_value     TEXT,                    -- 基准值（JSON）
  base_version   INTEGER NOT NULL,        -- 基准版本号
  new_value      TEXT,                    -- 新值（JSON）
  field_hash     TEXT,                    -- xxhash64 字段哈希
  client_node    TEXT NOT NULL,           -- 客户端节点 ID
  local_count    INTEGER NOT NULL,        -- 本地计数器
  server_version INTEGER,                 -- 服务端版本号（版本向量）
  status         TEXT NOT NULL DEFAULT 'pending',  -- pending / pushing / acked / conflict / rejected
  created_at     TEXT NOT NULL,           -- 本地操作时间
  pushed_at      TEXT,                     -- 推送时间
  acked_at       TEXT,                     -- 确认时间
  conflict_id    TEXT                      -- 冲突 ID（如产生冲突）
);
```

### 3.2 ConflictRecord（冲突记录）

```sql
CREATE TABLE conflict_record (
  conflict_id    TEXT PRIMARY KEY,        -- 冲突 ID
  op_id          TEXT NOT NULL,            -- 关联操作 ID
  record_id      TEXT NOT NULL,            -- 业务记录 ID
  entity_type    TEXT NOT NULL,            -- 实体类型
  field          TEXT NOT NULL,            -- 字段名
  base_value     TEXT,                     -- 基准值（JSON）
  client_value   TEXT,                     -- 客户端新值（JSON）
  server_value   TEXT,                     -- 服务端当前值（JSON）
  base_version   INTEGER NOT NULL,         -- 基准版本号
  current_version INTEGER NOT NULL,        -- 服务端当前版本号
  current_actor  TEXT,                     -- 服务端最后修改人
  conflict_type  TEXT NOT NULL,            -- real_conflict / field_locked
  status         TEXT NOT NULL DEFAULT 'pending',  -- pending / resolved / discarded
  resolved_value TEXT,                     -- 裁定后最终值（JSON）
  resolution_strategy TEXT,                -- manual / auto / discard_client / discard_server
  resolved_at    TEXT,
  created_at     TEXT NOT NULL
);
```

### 3.3 ChangeLog（服务端变更日志表）

服务端 MySQL 表，记录所有字段级变更，客户端按 log_id 增量拉取。

```sql
CREATE TABLE change_log (
  log_id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  record_id       VARCHAR(64) NOT NULL,    -- 业务记录 ID
  entity_type     VARCHAR(64) NOT NULL,    -- 实体类型
  field           VARCHAR(128) NOT NULL,   -- 字段名
  op              VARCHAR(16) NOT NULL,    -- replace / add / remove
  old_value       TEXT,                    -- 旧值（JSON）
  new_value       TEXT,                    -- 新值（JSON）
  version         BIGINT NOT NULL,         -- 变更后版本号
  field_hash      VARCHAR(32),             -- xxhash64 字段哈希
  actor_user_id   BIGINT,                  -- 操作人 ID
  actor_node_id   VARCHAR(64),             -- 操作节点 ID（server / client-node-xxx）
  ts              DATETIME NOT NULL,       -- 变更时间
  ttl_expire_at   DATETIME NOT NULL,      -- TTL 过期时间（保留 90 天）
  INDEX idx_entity (entity_type, record_id),
  INDEX idx_ts (ts),
  INDEX idx_ttl (ttl_expire_at)
) ENGINE=InnoDB;
```

**TTL/归档策略**：保留 90 天，超期归档至冷存储；客户端长期离线回归时触发"全量字段哈希对账"兜底。

### 3.4 VersionVector（版本向量）

简化版本向量，每条 Oplog 记录携带，用于因果判定。

```json
{
  "server": 10001,           // 服务端版本号（change_log 的 latest log_id）
  "client": "node-001",      // 客户端节点 ID
  "count": 5                 // 本地计数器（单调递增）
}
```

**因果判定规则**：VV 天然支持并发判定（两边计数器都推进即并发冲突）。

### 3.5 cache_meta（缓存元数据表，客户端本地）

```sql
CREATE TABLE cache_meta (
  meta_key        TEXT PRIMARY KEY,        -- 元数据键
  meta_value      TEXT NOT NULL,           -- 元数据值
  updated_at      TEXT NOT NULL
);

-- 关键元数据项：
-- cache_version        缓存版本号
-- download_time        首次下载时间
-- last_refresh_time   最后刷新时间
-- expires_at           过期时间（= last_refresh_time + 7d）
-- last_consumed_log_id 最后消费的 log_id
-- last_acked_op_id     最后确认的 op_id
-- source_user_id       缓存来源用户
-- source_tenant        缓存来源租户
-- last_online_at       最后联网时间（加密存储，兜底校验）
```

---

## 4. 冲突解决流程

### 4.1 冲突类型

| 类型 | 说明 | 处理方式 |
|------|------|----------|
| 假冲突（fake_conflict） | current_version > base_version 且 current_value == new_value | 自动合并，无需人工 |
| 真冲突（real_conflict） | current_version > base_version 且 current_value != new_value | 进入人工裁定队列 |
| 字段锁定（field_locked） | 字段标记为"已审核锁定" | 无论版本，拒绝离线覆盖，回退并提示 |

### 4.2 冲突解决流程

```
┌─────────────────────────────────────────────────────────────┐
│                    客户端检测到冲突                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  冲突类型判定            │
              └──────────┬─────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│ 假冲突        │ │ 真冲突        │ │ 字段锁定      │
│ (auto_merged) │ │ (conflict)   │ │ (rejected)   │
└───────┬───────┘ └──────┬───────┘ └──────┬───────┘
        │                │                │
        ▼                ▼                ▼
  自动合并入草稿   列入冲突裁定 UI    回退并提示用户
  更新本地版本    展示三方值         "字段已锁定"
                  供用户选择
                         │
                         ▼
              ┌────────────────────────┐
              │  用户人工裁定            │
              │  - 采用客户端值          │
              │  - 采用服务端值          │
              │  - 手动输入新值          │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │  提交裁定结果            │
              │  POST /sync/conflicts   │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │  服务端二次乐观锁终裁    │
              │  current_version==base? │
              └──────────┬─────────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼                           ▼
    ┌──────────────┐          ┌──────────────┐
    │ 通过 → 写入   │          │ 二次冲突      │
    │ 更新版本      │          │ 返回最新值     │
    └──────────────┘          │ 触发二次 merge │
                              └──────────────┘
```

### 4.3 自动合并策略

对于可定义合并函数的字段（如追加型文本、数组追加），支持自动合并：

| 字段类型 | 自动合并策略 |
|----------|--------------|
| 追加型文本（配置 Log） | 客户端值追加至服务端值末尾，标记合并来源 |
| 数组追加（附件列表） | 并集合并，去重 |
| 标量字段（枚举/数字） | 不自动合并，必须人工裁定 |

---

## 5. 离线令牌端点

### 5.1 POST /api/v1/auth/offline-token - 获取离线令牌

联网时获取 RS256 签名 JWT 离线令牌，7 天 TTL。

**权限要求**：登录用户

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| deviceId | string | 是 | 设备标识（嵌入令牌 device_id 声明） |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "offlineToken": "eyJ...",
    "publicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
    "expiresAt": "2026-07-17T10:00:00Z",
    "passwordVersion": 2,
    "issuedAt": "2026-07-10T10:00:00Z"
  }
}
```

**JWT 离线令牌声明**：

| 声明 | 说明 |
|------|------|
| iss | 签发方（PMS） |
| sub | 用户 ID |
| device_id | 设备 ID（降低令牌复制可用性） |
| password_version | 改密版本号（改密后变更，旧令牌失效） |
| exp | 过期时间（7 天） |
| iat | 签发时间 |
| tenant | 租户 ID |

### 5.2 离线令牌校验流程

**离线时**：
1. 客户端从 OS 凭证库读取离线令牌
2. 客户端内嵌服务端公钥（RS256）本地验签
3. 校验 exp（本地系统时间比对）
4. 校验 `当前时间 - last_online_at <= 离线宽限期`（last_online_at 加密存储）
5. 通过则允许访问本地缓存数据

**联网瞬间**：
1. 应用启动或网络恢复事件触发
2. 客户端向服务端发起"令牌 + 账户状态"联合校验
3. 服务端转查 LDAP/AD 的 userAccountControl（ACCOUNTDISABLE=0x0002、LOCKOUT=0x0010）
4. 账户停用 → 服务端返回 401，离线令牌加入黑名单，客户端立即清除本地缓存
5. 账户正常 → 续期 7 天（滑动续期）

### 5.3 POST /api/v1/auth/offline-token/verify - 联网校验离线令牌

**权限要求**：登录用户

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| offlineToken | string | 是 | 离线令牌 |
| deviceId | string | 是 | 设备 ID |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "valid": true,
    "accountActive": true,
    "newOfflineToken": "eyJ...",
    "newExpiresAt": "2026-07-17T11:00:00Z"
  }
}
```

**错误响应**：

```json
{
  "code": 40102,
  "message": "离线令牌已失效（账户已停用）",
  "data": null
}
```

### 5.4 POST /api/v1/auth/offline-token/revoke - 吊销离线令牌

服务端将离线令牌加入黑名单（账户停用 / 改密 / 多设备管理）。

**权限要求**：`system:user:manage`（管理员）/ 系统自动触发

---

## 6. 缓存元数据端点

### 6.1 GET /api/v1/cache/meta - 缓存元数据

**权限要求**：登录用户

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "cacheVersion": "v1.2",
    "downloadTime": "2026-07-08T10:00:00Z",
    "lastRefreshTime": "2026-07-10T09:00:00Z",
    "expiresAt": "2026-07-17T09:00:00Z",
    "sourceUserId": 10,
    "sourceTenant": "default",
    "lastConsumedLogId": 10001,
    "stale": false
  }
}
```

### 6.2 POST /api/v1/cache/refresh - 刷新缓存

联网时自动后台刷新，刷新即续期（更新 last_refresh_time 与 expires_at）。

**权限要求**：登录用户

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lastConsumedLogId | long | 是 | 当前消费到的 log_id |
| projectIds | array | 否 | 限定刷新项目范围 |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "refreshed": true,
    "newExpiresAt": "2026-07-17T10:00:00Z",
    "latestLogId": 10050,
    "updatedRecords": 15
  }
}
```

### 6.3 POST /api/v1/cache/download - 全量下载缓存

首次登录或长期离线回归时全量下载项目数据。

**权限要求**：登录用户

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | long | 是 | 项目 ID |

**响应**：返回项目相关全量数据（实施方案/工勘/施工计划/配置 Log 等）。

### 6.4 DELETE /api/v1/cache - 清除本地缓存（登出）

客户端本地执行：先 `db.close()` → 删除 .db / -wal / -shm → 清渲染进程残留。

---

## 7. 强一致性操作清单（离线禁用列表）

以下操作为强一致性操作，离线模式下禁用，仅联网可执行。前端通过 `v-offline-disabled` 指令禁用相关按钮。

| 操作 | 权限标识 | 禁用原因 |
|------|----------|----------|
| 项目闭环申请 | `project:closure:request` | 涉及状态机强一致流转 |
| 项目闭环审批 | `project:closure:approve` | 审批强一致 |
| 割接发起 | `project:cutover:initiate` | 割接强一致，需同步割接平台 |
| 割接平台同步 | `cutover:operation:sync` | 跨系统强一致 |
| 项目状态流转（指派 SM/PM） | `project:project:assign` | 状态机强一致 |
| 项目闭环 | `project:project:close` | 状态机强一致 |
| 转包申请发起 | `subcontract:submit` | 多级审批强一致 |
| 转包审批 | `subcontract:approve` | 审批强一致 |
| 实施方案审核 | `project:scheme:review` | 审核锁定强一致 |
| 实施方案提交审核 | `project:scheme:submit` | 触发审批强一致 |
| 施工计划提交审核 | `project:plan:submit` | 触发审批强一致 |
| 售前测试审批 | `presales:application:approve` | 审批强一致 |
| 数据迁移操作 | `migration:*` | 迁移强一致 |
| 系统管理写操作 | `system:*:create/update/delete` | 系统配置强一致 |
| 工作流任务完成 | `workflow:task:complete` | 流程强一致 |
| 集成推送（D365/CRM/RMA） | `integration:*` | 跨系统强一致 |

**离线允许操作**：填写类写操作暂存草稿（实施方案草稿、工勘填写、需求分析填写、硬件安装记录、配置 Log 上传本地、业务联调记录、客户联系人录入等），联网后增量同步。

---

## 8. 同步状态机

```
                  ┌──────────┐
                  │  IDLE    │ ← 初始状态 / 同步完成
                  └────┬─────┘
                       │ 触发同步（联网/手动）
                       ▼
                  ┌──────────┐
                  │ PULLING  │ ← 拉取服务端变更
                  └────┬─────┘
                       │ pull 完成
                       ▼
                  ┌──────────┐
                  │ MERGING  │ ← 本地 Three-way merge
                  └────┬─────┘
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
     ┌────────────┐       ┌────────────┐
     │ CONFLICT_  │       │ PUSHING    │ ← 推送本地变更
     │ DETECTED   │       └────┬───────┘
     └─────┬──────┘            │
           │                     │ push 响应
           ▼                     ▼
     ┌────────────┐       ┌────────────┐
     │ RESOLVING  │       │ ACKING     │ ← 确认消费
     │ (人工裁定) │       └────┬───────┘
     └─────┬──────┘            │
           │ 裁定完成           │
           ▼                     ▼
     ┌────────────┐       ┌────────────┐
     │ PUSHING    │──────►│  IDLE      │
     │ (提交裁定) │       │ (completed)│
     └────────────┘       └────────────┘

异常分支：
  - 任意状态 → ERROR（同步失败）→ RETRY（指数退避）→ 重新进入对应状态
  - 任意状态 → OFFLINE（断网）→ 等待联网 → IDLE
```

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| idle | 空闲/同步完成 | 初始、同步完成 |
| pulling | 拉取服务端变更 | 联网触发、手动触发 |
| merging | 本地三方合并 | pull 完成 |
| conflict_detected | 检测到冲突 | merge 发现真冲突 |
| resolving | 人工裁定中 | 冲突待裁定 |
| pushing | 推送本地变更 | merge 完成 / 裁定完成 |
| acking | 确认消费 | push 完成 |
| error | 同步失败 | 网络错误/服务端错误 |
| retry | 重试中 | 指数退避重试 |
| offline | 离线 | 断网检测 |

---

## 9. 错误码定义

### 9.1 同步错误码

| code | HTTP Status | 错误 | 说明 | 客户端处理 |
|------|-------------|------|------|-----------|
| 40901 | 409 | OPTIMISTIC_LOCK_FAILED | 乐观锁失败（current_version != base_version） | 触发二次 merge |
| 40902 | 409 | SYNC_FIELD_CONFLICT | 离线同步字段冲突（需人工裁定） | 加入冲突裁定队列 |
| 40903 | 409 | SYNC_FIELD_LOCKED | 离线覆盖锁定字段被拒绝 | 回退并提示用户 |
| 42201 | 422 | SYNC_VALIDATION_FAILED | 业务规则校验失败 | 标记操作失败，不入队列 |
| 42301 | 423 | SYNC_OP_DUPLICATED | op_id 重复（幂等去重） | 忽略，视为已成功 |
| 40002 | 400 | SYNC_LOG_ID_INVALID | last_consumed_log_id 无效 | 重置为 0 全量拉取 |
| 40003 | 400 | SYNC_BATCH_TOO_LARGE | 批量过大 | 减小 batchSize 重试 |

### 9.2 离线令牌错误码

| code | HTTP Status | 错误 | 说明 | 客户端处理 |
|------|-------------|------|------|-----------|
| 40101 | 401 | TOKEN_EXPIRED | 令牌过期 | 提示重新登录 |
| 40102 | 401 | OFFLINE_TOKEN_INVALID | 离线令牌已失效（账户变更/黑名单） | 立即清除本地缓存 |
| 40103 | 401 | PASSWORD_VERSION_MISMATCH | 改密后版本号变更 | 旧令牌失效，重新登录 |
| 40104 | 401 | DEVICE_REVOKED | 设备已被吊销 | 清除缓存并提示 |
| 42302 | 423 | OFFLINE_GRACE_PERIOD_EXCEEDED | 离线宽限期超限 | 拒绝访问，要求联网 |

### 9.3 缓存错误码

| code | HTTP Status | 错误 | 说明 | 客户端处理 |
|------|-------------|------|------|-----------|
| 41001 | 410 | CACHE_EXPIRED | 缓存已过期（>7 天） | 标记 stale，提示联网刷新 |
| 41002 | 410 | CACHE_STALE | 缓存已过期但未超期 | 显著位置提示，超期不强制清除 |
| 40004 | 400 | CACHE_DECRYPT_FAILED | 缓存解密失败（密钥不匹配） | 提示重新登录获取密钥 |

### 9.4 客户端本地错误

| 错误码 | 说明 | 客户端处理 |
|--------|------|-----------|
| LOCAL_DB_LOCKED | 本地数据库锁定 | 重试或重启应用 |
| LOCAL_DISK_FULL | 本地磁盘空间不足 | 提示清理空间 |
| LOCAL_CRYPTO_ERROR | 本地加密错误 | 提示重新登录 |
| NETWORK_OFFLINE | 网络离线 | 进入离线模式，同步队列暂存 |
| SYNC_CONFLICT_UNRESOLVED | 存在未裁定冲突 | 阻断后续 push，提示用户裁定 |

---

## 10. 批量提交与断点续传

### 10.1 记录级事务

- 事务粒度：按业务记录级原子（单条实施方案/工勘单多字段更新要么全成功要么全回滚）
- 跨记录批量不强制全局事务
- 单次 push 批量建议 ≤100 条操作

### 10.2 op_id 幂等

- 客户端为每个操作生成唯一 op_id（UUID + 客户端节点 ID）
- 服务端去重：相同 op_id 视为已处理，返回 42301

### 10.3 断点续传

- 客户端持久化 `last_acked_op_id`
- 批量提交后服务端逐项 ACK
- 中断后从 `last_acked_op_id + 1` 重传
- 冲突挂起：遇冲突字段该项挂起（不阻断后续项），其余字段继续提交；冲突项汇总后一次性回传客户端裁定

### 10.4 全量字段哈希对账（兜底）

客户端长期离线回归（change_log 已 TTL 归档）时触发：

1. 客户端拉取全量业务记录字段哈希清单
2. 本地逐字段比对 xxhash64
3. 不一致字段标记需重新拉取
4. 重建 last_consumed_log_id 为当前最新 log_id

---

## 附录：实体类型清单

支持离线同步的实体类型（仅填写类业务对象）：

| entityType | 说明 | 离线可写字段示例 |
|------------|------|-----------------|
| implementation_scheme | 实施方案 | overview/content/configScript 等 |
| site_survey | 工勘 | powerSupply/networkPort 等 |
| requirement_analysis | 需求分析 | projectBackground/goal 等 |
| construction_plan | 施工计划 | planTime（草稿） |
| hardware_installation | 硬件安装 | installLocation/photoFileIds |
| config_log | 配置 Log | configInfo（本地上传） |
| integration_test | 业务联调 | connectionInfo/devices |
| customer_contact | 客户联系人 | name/phone/email |
| training_record | 培训记录 | content/trainees |
| weekly_report | 周报 | content（草稿） |
