# 什么值得挖 v2 — 静态化改造技术方案

> 版本：1.0
> 日期：2026-03-25
> 状态：Boss 已确认方向，待开发
> 编写：总管

---

## 一、改造目标

将「什么值得挖」从 **Next.js SSR + Supabase** 架构迁移为 **纯静态 + Cloudflare Pages + Workers** 架构，与数据站 (crypto3d.pro) 保持一致的部署模式。

**核心收益：**
- 零数据库运维、零连接问题
- 全球 CDN，访问速度快
- 部署简单可靠（push 即上线）
- 零托管成本（Cloudflare 免费额度）

---

## 二、架构对比

### 改造前（当前）
```
用户 → Vercel (SSR) → Supabase PostgreSQL
                     → RainbowKit + 服务端 Session
```

### 改造后
```
用户 → Cloudflare Pages（静态 HTML/JS/JSON）
     → Cloudflare Worker（验证签名 + 鉴权）
     → Cloudflare KV（白名单 + Token 存储）

本地管理：
Mac mini → 本地 dev server（后台管理）
        → 导出 JSON + build 静态站
        → git push → Cloudflare Pages 自动部署
```

---

## 三、模块拆解

### 3.1 数据层：Supabase → 本地 SQLite + JSON 导出

**现状：** Prisma + Supabase PostgreSQL，线上实时读写
**改后：** 本地 SQLite 做管理后台数据库，导出 JSON 给前端

#### 数据文件结构
```
data/
├── opportunities.json      # 全部机会数据（公开部分）
├── opportunities-full.json # 含 Boss 评价等受保护数据（需 token）
├── reviews.json            # 复盘数据
├── updates.json            # 动态更新流
└── stats.json              # 统计摘要（首页用）
```

#### 导出脚本
```bash
# scripts/export-data.ts
# 从本地 SQLite 读取 → 生成 JSON 文件到 data/ 目录
# 公开数据直接放 data/，受保护数据放 data/protected/
```

#### Prisma 改动
```prisma
datasource db {
  provider = "sqlite"
  url      = "file:./dev.db"
}
```

**迁移步骤：**
1. 导出 Supabase 现有数据为 SQL
2. 转换为 SQLite 格式导入
3. 验证数据完整性

---

### 3.2 认证层：服务端 Session → Cloudflare Workers + KV

**现状：** 钱包签名 → 服务端验证 → Supabase 存 Session → Cookie
**改后：** 钱包签名 → Worker 验证 → KV 存 Token → 前端 localStorage

#### Worker 端点设计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/challenge` | GET | 生成签名挑战（nonce + 过期时间） |
| `/api/auth/verify` | POST | 验证签名 + 检查白名单 + 发 token |
| `/api/auth/check` | GET | 验证 token 有效性 |
| `/api/data/*` | GET | 受保护数据代理（需 token） |

#### 认证流程
```
1. 用户连接钱包（RainbowKit，纯前端）
2. 前端请求 /api/auth/challenge → Worker 返回 nonce
3. 用户用钱包签名 nonce
4. 前端发送 { address, signature, nonce } 到 /api/auth/verify
5. Worker 验证：
   a. nonce 未过期且未使用
   b. ecrecover(signature) === address
   c. address 在白名单 KV 中
6. 验证通过 → 生成 token（JWT 或随机串）→ 存入 KV（30天TTL）
7. 前端存 token 到 localStorage
8. 后续请求受保护数据时带 Authorization: Bearer {token}
```

#### Worker 代码骨架
```typescript
// workers/auth.ts

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // CORS
    if (request.method === 'OPTIONS') return handleCORS();

    switch (url.pathname) {
      case '/api/auth/challenge':
        return handleChallenge(env);
      case '/api/auth/verify':
        return handleVerify(request, env);
      case '/api/auth/check':
        return handleCheck(request, env);
      default:
        if (url.pathname.startsWith('/api/data/'))
          return handleProtectedData(request, env);
        return new Response('Not found', { status: 404 });
    }
  }
};

interface Env {
  WHITELIST: KVNamespace;   // 白名单：key=address, value="1"
  SESSIONS: KVNamespace;    // Token：key=token, value=address, TTL=30天
  CHALLENGES: KVNamespace;  // Nonce：key=nonce, value="1", TTL=5分钟
  AUTH_SECRET: string;      // 签名密钥
}
```

#### KV 命名空间

| KV | Key | Value | TTL |
|----|-----|-------|-----|
| WHITELIST | `0xabc...` | `1` | 永久 |
| SESSIONS | `tok_xxxx` | `0xabc...` | 30天 |
| CHALLENGES | `nonce_xxxx` | `1` | 5分钟 |

#### 白名单管理
```bash
# 添加白名单地址
wrangler kv:key put --binding WHITELIST "0xabc..." "1"

# 批量导入
scripts/sync-whitelist.ts  # 从本地 SQLite 读取 → 写入 KV

# 删除
wrangler kv:key delete --binding WHITELIST "0xabc..."
```

---

### 3.3 前端改造

#### 页面渲染策略

| 页面 | 数据来源 | 是否需要认证 |
|------|---------|-------------|
| 首页 `/` | `data/opportunities.json` | ❌ 公开浏览 |
| 详情页 `/opportunity/[id]` | `data/opportunities-full.json` | ✅ 需要 token |
| 复盘 `/reviews` | `data/reviews.json` | ❌ 公开 |
| 全部机会 `/all` | `data/opportunities.json` | ❌ 公开 |
| 收藏 `/favorites` | localStorage | ✅ 需要连接钱包 |

**分级策略：**
- **公开数据**：机会名称、平台、APR、标签、倒计时 → 任何人可见
- **受保护数据**：Boss 评价、参与指南、退出信号、收益计算器 → 需验证

#### 前端认证 Hook
```typescript
// hooks/useAuth.ts
export function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [address, setAddress] = useState<string | null>(null);

  // 初始化：从 localStorage 恢复
  useEffect(() => {
    const saved = localStorage.getItem('wtm_auth');
    if (saved) {
      const { token, address, expiresAt } = JSON.parse(saved);
      if (Date.now() < expiresAt) {
        setToken(token);
        setAddress(address);
      } else {
        localStorage.removeItem('wtm_auth');
      }
    }
  }, []);

  // 验证流程
  async function verify(address: string, signMessage: Function) {
    // 1. 获取 challenge
    const { nonce } = await fetch('/api/auth/challenge').then(r => r.json());
    // 2. 签名
    const message = `什么值得挖 登录验证\n\nNonce: ${nonce}`;
    const signature = await signMessage({ message });
    // 3. 验证
    const res = await fetch('/api/auth/verify', {
      method: 'POST',
      body: JSON.stringify({ address, signature, nonce }),
    });
    const { token } = await res.json();
    // 4. 存储
    const auth = { token, address, expiresAt: Date.now() + 30 * 86400000 };
    localStorage.setItem('wtm_auth', JSON.stringify(auth));
    setToken(token);
    setAddress(address);
  }

  // 获取受保护数据
  async function fetchProtected(path: string) {
    return fetch(`/api/data/${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.json());
  }

  return { token, address, isAuthenticated: !!token, verify, fetchProtected };
}
```

#### 收藏功能
```typescript
// 改为 localStorage，不跨设备但零后端
// hooks/useFavorites.ts
export function useFavorites() {
  const [ids, setIds] = useState<string[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem('wtm_favorites');
    if (saved) setIds(JSON.parse(saved));
  }, []);

  function toggle(id: string) {
    const next = ids.includes(id)
      ? ids.filter(x => x !== id)
      : [...ids, id];
    setIds(next);
    localStorage.setItem('wtm_favorites', JSON.stringify(next));
  }

  return { ids, isFavorite: (id: string) => ids.includes(id), toggle };
}
```

---

### 3.4 后台管理（本地）

**保持现有 Next.js admin 页面**，但只在本地运行：

```bash
# 本地启动后台
cd what-to-mine
npm run dev
# 访问 http://localhost:3000/admin
```

- 后台读写本地 SQLite
- 编辑完成后执行导出：
```bash
npm run export    # 导出 JSON 到 data/
npm run build     # 构建静态站
npm run deploy    # git push（触发 Cloudflare Pages 部署）
```

#### 一键发布脚本
```bash
# scripts/publish.sh
#!/bin/bash
set -e

echo "📦 导出数据..."
npx tsx scripts/export-data.ts

echo "🔨 构建静态站..."
npm run build

echo "📤 提交并推送..."
git add data/ out/
git commit -m "data: update $(date +%Y-%m-%d_%H:%M)"
git push origin main

echo "✅ 已推送，Cloudflare Pages 会自动部署"
```

---

### 3.5 部署架构

```
GitHub (what-to-mine)
├── main 分支 → Cloudflare Pages（静态站）
│                ├── HTML/JS/CSS（公开）
│                └── data/*.json（公开部分）
│
└── Workers（独立部署）
     ├── /api/auth/*（认证端点）
     └── /api/data/*（受保护数据代理）

Cloudflare KV
├── WHITELIST（白名单地址）
├── SESSIONS（登录 token）
└── CHALLENGES（签名 nonce）
```

#### Cloudflare Pages 配置
```toml
# wrangler.toml (Pages)
name = "what-to-mine"
compatibility_date = "2026-03-25"

[site]
bucket = "./out"
```

#### Workers 路由
```
what-to-mine.crypto3d.pro/api/* → Worker
what-to-mine.crypto3d.pro/*     → Pages（静态）
```

---

## 四、改造步骤（执行计划）

### Phase 1：数据层切换（预估 2-3 小时）
1. Prisma datasource 改为 SQLite
2. 从 Supabase 导出现有数据
3. 导入 SQLite
4. 编写 export-data.ts 脚本
5. 验证导出的 JSON 和现有 API 返回一致

### Phase 2：Worker 认证服务（预估 2-3 小时）
1. 创建 Cloudflare Worker 项目
2. 实现 challenge/verify/check 端点
3. 配置 KV 命名空间
4. 导入现有白名单
5. 本地测试完整认证流程

### Phase 3：前端改造（预估 3-4 小时）
1. 首页改为读 JSON 文件（去掉 Prisma 调用）
2. 详情页改为 fetchProtected
3. 登录改为 Worker 认证流程
4. 收藏改为 localStorage
5. 后台保留，仅本地运行
6. 去掉 SSR 相关配置，改为 `next export` 静态导出

### Phase 4：部署切换（预估 1 小时）
1. Cloudflare Pages 项目创建
2. Worker 部署
3. 域名绑定（子域名 or 主域名）
4. 验证全链路
5. 下线 Vercel

### Phase 5：运维脚本（预估 1 小时）
1. publish.sh 一键发布
2. sync-whitelist.ts 白名单同步
3. 本地 dev 启动脚本

---

## 五、需要保留的现有代码

| 模块 | 保留 | 改动 |
|------|------|------|
| RainbowKit 钱包连接 | ✅ | 签名后改调 Worker |
| 所有前端组件 | ✅ | 数据来源从 API 改为 JSON |
| admin 后台页面 | ✅ | 仅本地运行 |
| Prisma schema | ✅ | datasource 改 SQLite |
| 机会卡片/详情页/复盘页 | ✅ | 不变 |
| 筛选/排序逻辑 | ✅ | 不变（已是前端逻辑） |
| 倒计时/角标系统 | ✅ | 不变（纯前端） |
| CEX 监控代码 | ✅ | 独立运行，不影响 |

**需要删除的：**
- Vercel 配置（`vercel.json`、`.vercel/`）
- 服务端 Session 逻辑（`src/lib/session.ts` 中的 DB 部分）
- API Routes 中直接查 DB 的逻辑（改为读 JSON 或删除）

---

## 六、安全评估

| 风险 | 评估 | 防护 |
|------|------|------|
| 签名伪造 | ❌ 不可能 | ECDSA 密码学保证 |
| 重放攻击 | ❌ | Nonce 一次性 + 5分钟过期 |
| 白名单泄露 | ✅ 安全 | 存在 KV，不暴露给前端 |
| 数据被爬 | ✅ 安全 | 受保护数据需 token |
| Token 被盗 | ⚠️ 低风险 | localStorage 仅当前设备 |
| DDoS | ✅ 安全 | Cloudflare 自带防护 |
| Worker 被绕过 | ❌ | 受保护 JSON 不在 Pages 上，由 Worker 代理 |

---

## 七、成本

| 资源 | 免费额度 | 预估用量 |
|------|---------|---------|
| Cloudflare Pages | 无限请求 | 足够 |
| Cloudflare Workers | 10万次/天 | 远够（认证请求很少） |
| Cloudflare KV | 10万次读/天 | 足够 |
| 域名 | 已有 crypto3d.pro | 0 |
| **总成本** | | **$0** |

---

## 八、后续扩展预留

- **公告雷达**：CEX 监控结果导出为 `data/radar.json`，前端展示
- **日历**：导出 `data/calendar.json`，前端渲染日历视图
- **多用户收藏同步**：如需跨设备，可在 Worker + KV 中实现
- **运营后台在线化**：如需多人协作，可以后加回线上后台

---

**最后更新**: 2026-03-25 21:45
