# task-004《新闻监控雷达》验收清单

> 用途：仅用于 review 阶段验收新闻质量与输出质量
> 数据文件：`data/news.json`
> 预览页面：`review/news-radar.html`

---

## A. 产物存在性

- [ ] `data/news.json` 存在
- [ ] JSON 可正常解析
- [ ] 顶层字段完整：`updated_at` / `count` / `news`
- [ ] `count` 在 20-30 之间
- [ ] 每条新闻都包含：
  - [ ] `id`
  - [ ] `title_en`
  - [ ] `title_zh`
  - [ ] `summary_zh`
  - [ ] `category`
  - [ ] `importance`
  - [ ] `source`
  - [ ] `source_url`
  - [ ] `published_at`

## B. 数据质量

- [ ] 没有空标题
- [ ] 没有空摘要
- [ ] 所有 `title_zh` / `summary_zh` 为中文输出
- [ ] 没有明显英文 fallback
- [ ] `importance` 范围都在 1-10
- [ ] `category` 都在枚举范围内：
  - `markets`
  - `policy`
  - `defi`
  - `macro`
  - `business`
  - `security`
  - `technology`

## C. 选题质量（人工抽查）

抽查前 10 条重点看：

- [ ] 是否都是过去 24 小时内值得关注的新闻
- [ ] 是否避免大量重复事件
- [ ] 是否兼顾：加密市场 / 政策 / 宏观 / 公司动态 / 安全事件
- [ ] 是否有明显“水文 / 教程 / 广告 / 合集”混入
- [ ] Top 5 是否确实是当天更重要的事件

## D. 中文标题质量（人工抽查）

- [ ] 标题通顺，不像机翻
- [ ] 标题不夸张、不标题党
- [ ] 保留必要专有名词（如 Bitcoin / SEC / ETF / Fed）
- [ ] 没有明显错译
- [ ] 不出现大段英文直接复制

## E. 中文摘要质量（人工抽查）

- [ ] 每条摘要能说明“发生了什么”
- [ ] 每条摘要能说明“为什么重要”
- [ ] 摘要长度基本在 50-100 字附近
- [ ] 语言自然，像人写的，不像提示词残留
- [ ] 没有明显幻觉或补充原文没有的信息

## F. importance / category 合理性

抽查前 10 条：

- [ ] `importance` 与新闻重要程度大体匹配
- [ ] 市场大事件分数明显高于普通快讯
- [ ] `category` 分类基本合理
- [ ] 宏观新闻不会被误分到 defi / technology
- [ ] 安全攻击类不会被误分到 markets

## G. 页面 review 体验

- [ ] 页面可直接打开查看
- [ ] 能看到更新时间 / 总条数
- [ ] 能按卡片浏览新闻
- [ ] 每条能看到：中文标题、中文摘要、importance、category、source、时间、原文链接
- [ ] 页面加载失败时有错误提示

## H. Git / 分支规则

- [ ] 仅推送到 `dev`
- [ ] 未 merge 到 `main`
- [ ] review 页面不影响正式站主入口

---

## 建议验收顺序

1. 先打开 review 页面快速通读前 10 条
2. 再对照 `data/news.json` 抽查字段
3. 最后确认 git 仅在 `dev`

---

## 本轮 review 结论

- [ ] 通过：可进入下一步（前端正式接入 / cron）
- [ ] 不通过：需回炉修改

### 备注

- 
