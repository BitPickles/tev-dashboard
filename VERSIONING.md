# 版本管理

## 当前版本

**v0.0.0.1** - 测试 0.0.0.1

## 版本命名规范

```
v{主版本}.{次版本}.{修订}.{构建}

主版本: 重大架构变更
次版本: 新功能
修订: Bug 修复
构建: 测试迭代
```

## 版本历史

| 版本 | 日期 | 说明 |
|-----|------|-----|
| v0.0.0.1 | 2026-02-13 | 测试 0.0.0.1 - 初始稳定版本 |

## 回滚方法

### 快速回滚到指定版本

```bash
# 查看所有版本
git tag -l

# 回滚到指定版本
git checkout v0.0.0.1

# 如需在该版本上修复，创建分支
git checkout -b hotfix/issue-xxx v0.0.0.1
```

### 生产环境回滚

```bash
# 1. 切换到 main 分支
git checkout main

# 2. 硬重置到指定版本
git reset --hard v0.0.0.1

# 3. 强制推送（谨慎）
git push origin main --force
```

### 保守回滚（推荐）

```bash
# 创建回滚提交，保留历史
git revert HEAD~n..HEAD
git push origin main
```

## 发版流程

1. dev 分支开发测试
2. 测试通过后打 tag
3. 合并到 main
4. 推送 tag 到远程

```bash
# 打版本标签
git tag -a v0.0.0.2 -m "版本说明"
git push origin v0.0.0.2

# 合并到 main
git checkout main
git merge dev
git push origin main
```
