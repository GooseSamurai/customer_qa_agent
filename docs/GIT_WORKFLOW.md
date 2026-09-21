# Git 与 GitHub 工作流

本文用于记录本项目实际采用的 Git、GitHub 和 CI 规则。

## 1. Git 的四个区域

```text
工作区 -> 暂存区 -> 本地仓库 -> 远端仓库
```

- 工作区：当前正在编辑的文件。
- 暂存区：准备放入下一次 commit 的文件。
- 本地仓库：已经提交到本机 `.git/` 的历史。
- 远端仓库：GitHub 上的团队副本。

对应命令：

```powershell
git status
git add <文件>
git commit -m "<提交信息>"
git push
```

## 2. 开始一个 Task

不要直接在 `main` 上开发。

```powershell
git switch main
git pull --rebase origin main
git switch -c feature/t002-conversation-schema
```

分支命名：

```text
feature/<task>
fix/<problem>
docs/<topic>
chore/<topic>
```

## 3. 开发过程中的常用检查

```powershell
git status
git diff
git diff --staged
```

解释：

- `git status`：查看当前有哪些修改。
- `git diff`：查看还没有进入暂存区的修改。
- `git diff --staged`：查看下一次 commit 将包含的内容。

## 4. 运行测试并提交

```powershell
python -m pytest
git add schemas/conversation.py tests/schemas/test_conversation.py
git commit -m "feat: add conversation schema"
```

提交信息类型：

```text
feat: 新功能
fix: 修复问题
test: 测试
docs: 文档
refactor: 重构
chore: 工程配置
```

## 5. 推送与 Pull Request

```powershell
git push -u origin feature/t002-conversation-schema
```

然后在 GitHub 上创建 Pull Request。

Pull Request 的作用：

1. 展示本次修改；
2. 触发 CI；
3. 允许其他人 review；
4. CI 和 review 通过后再合并到 main。

## 6. 合并后同步本地 main

```powershell
git switch main
git pull --rebase origin main
git branch -d feature/t002-conversation-schema
```

## 7. 查看历史

```powershell
git log --oneline --decorate --graph
git show <commit-id>
```

## 8. 安全的撤销方式

取消暂存但保留文件修改：

```powershell
git restore --staged <文件>
```

放弃未暂存的本地修改：

```powershell
git restore <文件>
```

已经推送到远端的提交应优先使用：

```powershell
git revert <commit-id>
```

不要在不理解影响时使用 `git reset --hard`。

## 9. GitHub Actions CI

配置文件：

```text
.github/workflows/ci.yml
```

触发条件：

- push 到 main；
- Pull Request 目标为 main；
- GitHub 网页手动触发。

执行过程：

```text
下载代码
→ 安装 Python 3.10 和 3.12
→ 安装项目及 dev 依赖
→ 运行 pytest
```

只有测试通过，CI 才是绿色。

## 10. 不应提交到 Git 的内容

- `.env` 和真实密钥；
- 虚拟环境；
- `__pycache__`；
- pytest 缓存；
- 构建产物；
- 大型模型权重；
- 企业敏感数据。

大型数据或模型后续应使用对象存储、DVC 或模型仓库，不直接进入 Git。