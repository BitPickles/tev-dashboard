# BMRI and BTC.D 页面调试报告

## 问题总结

### 1. BMRI 页面一直显示 "加载中"

#### 根本原因
部署的站点使用的是旧版本代码（来自 dev 分支），该版本尝试加载不存在的 `mcap.json` 文件。

#### 详细分析
**本地 main 分支代码**（正确版本）:
```javascript
const bmriRes = await fetch('/indicators/data/bmri.json');
const mcapRes = await fetch('/indicators/data/marketcap.json');
```

**远程 dev 分支/部署的站点代码**（有问题的版本）:
```javascript
fetch('../indicators/data/bmri.json'),
fetch('../indicators/data/mcap.json').catch(() => null),  // 404!
fetch('../indicators/data/shared/btc-price.json')
```

#### 文件状态检查
- ✅ `/indicators/data/bmri.json` - 存在，大小 ~608KB
- ✅ `/indicators/data/shared/btc-price.json` - 存在，大小 ~361KB
- ❌ `/indicators/data/mcap.json` - **404 Not Found**
- ✅ `/indicators/data/marketcap.json` - 存在，大小 ~399KB（正确的文件名）

#### 控制台错误（预期）
```
GET ../indicators/data/mcap.json 404 (Not Found)
```

虽然代码中有 `.catch(() => null)` 来捕获这个错误，但这可能不是唯一的问题。需要进一步检查：
1. `btc-price.json` 文件在本地仓库中不存在（只存在于部署的站点上）
2. 可能还有其他运行时错误导致页面卡在 loading 状态

### 2. BTC.D 页面没有显示数据

#### 根本原因
**访问了错误的 URL！**

用户访问的是: `https://bitpickles.github.io/tev-dashboard/btcd/`
正确的 URL 是: `https://bitpickles.github.io/tev-dashboard/btc-dominance/`

#### 页面状态
- ❌ `/btcd/` - 404 Page Not Found
- ✅ `/btc-dominance/` - 正常页面，数据加载正常

#### btc-dominance 页面数据文件
- ✅ `/indicators/data/btc-dominance.json` - 存在，大小 ~185KB
- ✅ `/indicators/data/shared/btc-price.json` - 存在

## 解决方案

### 修复 BMRI 页面

1. **立即修复 - 更新部署代码**:
   ```bash
   # 切换到 main 分支（正确的版本）
   git checkout main
   git push origin main

   # 确保 GitHub Pages 从 main 分支部署
   # 在 GitHub 仓库设置中: Settings > Pages > Source = main branch
   ```

2. **检查 btc-price.json 文件**:
   - `shared/btc-price.json` 在本地仓库中不存在
   - 需要创建这个文件或移除对它的依赖

3. **统一文件命名**:
   - 将 `mcap.json` 改为 `marketcap.json` 以匹配实际文件
   - 或者创建符号链接: `ln -s marketcap.json mcap.json`

### 修复 BTC.D 页面

1. **用户端修复**:
   - 使用正确的 URL: `https://bitpickles.github.io/tev-dashboard/btc-dominance/`
   - 首页导航链接是正确的

2. **可选 - 添加重定向**:
   - 在 `_redirects` 文件中添加:
     ```
     /btcd/ /btc-dominance/ 301
     ```

## 建议

1. **立即行动**: 部署 main 分支的最新代码到 GitHub Pages
2. **代码审查**: 检查 main 和 dev 分支的差异，确定应该部署哪个版本
3. **文件完整性**: 确保 `shared/btc-price.json` 要么存在，要么移除依赖
4. **监控**: 添加错误监控以捕获部署后的 JavaScript 错误

## 文件结构

```
indicators/data/
├── ahr999.json ✅
├── bmri.json ✅
├── btc-dominance.json ✅
├── marketcap.json ✅
├── mvrv.json ✅
└── shared/
    └── btc-price.json ✅ (仅存在于部署站点)
```

## Git 分支状态

- **当前分支**: main
- **main 分支**: 使用 `marketcap.json`，绝对路径 `/indicators/data/`
- **dev 分支**: 使用 `mcap.json`，相对路径 `../indicators/data/`
- **部署的站点**: 似乎使用的是 dev 分支的旧代码
