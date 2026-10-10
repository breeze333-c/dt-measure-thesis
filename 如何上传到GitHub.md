# 如何把本项目上传到 GitHub

**当前状态：本项目已完成推送** → https://github.com/breeze333-c/dt-measure-thesis

本文件保留作为操作参考：既可用于本项目未来的再次推送（更新内容后），也可照此把其他项目推上 GitHub。
下面三种方式任选其一。

---

## 方式一：把仓库交给 AI 推送（最快，推荐）

在本对话里发我两样东西中的任意一样：

1. 一个 GitHub Personal Access Token（classic），或者
2. 你的 GitHub 用户名 + 一个 Token

**Token 生成步骤**（约 30 秒）：

1. 登录 GitHub → 右上角头像 → **Settings**
2. 左侧最下方 → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. 右上 → **Generate new token** → **Generate new token (classic)**
5. 勾选 **repo**（完整仓库权限）；Expiration 建议选 7 days
6. 点 **Generate token**，复制 `ghp_` 开头的那串字符（**只显示一次**）

把 token 发我之后，我会自动完成：创建公开仓库 → 关联远程 → 推送全部材料 → 返回仓库地址。
推送完成后建议你立刻到同一页面 **Delete** 该 token，避免泄露风险。

> 安全提示：token 相当于密码。不要把它提交到仓库里，也不要在群里转发；
> 用完后删除即可。若担心安全，请用方式二。

---

## 方式二：自己在网页上创建仓库 + 本地推（不需要给任何人凭据）

### 第 1 步：在 GitHub 创建空仓库

1. 打开 https://github.com/new
2. **Repository name** 填 `dt-measure-thesis`
3. 可见性选 **Public**（公开）
4. **不要**勾选 "Add a README file"、"Add .gitignore"、"Choose a license"（必须是空仓库）
5. 点 **Create repository**

### 第 2 步：在本地执行推送命令

把下面的 `你的用户名` 替换成你的 GitHub 用户名，然后在 WorkBuddy 里让我执行，
或者自己打开 Git Bash 粘贴执行：

```bash
cd "C:/Users/zxt13/Desktop/work/dt-measure-thesis"
git remote add origin https://github.com/你的用户名/dt-measure-thesis.git
git push -u origin main
```

推送时会弹出登录窗口：**Username** 填 GitHub 用户名，**Password** 要填
**Personal Access Token**（不是登录密码，GitHub 早已禁用密码推送）。
Token 生成方法见方式一。

### 或者：用仓库里的一键脚本

```bash
cd "C:/Users/zxt13/Desktop/work/dt-measure-thesis"
bash push-to-github.sh 你的用户名
```

### 第 3 步：验证

刷新仓库页面，应能看到 `README.md`、`thesis/`、`code/`、`data/`、`results/` 等目录。
仓库地址形如：`https://github.com/你的用户名/dt-measure-thesis`

---

## 方式三：用 WorkBuddy 的 GitHub 连接器

1. 打开连接器管理页 → 搜索 **GitHub** → 点击安装
2. 按提示完成 GitHub 账号授权
3. 回到本对话告诉我"已授权"，我用连接器直接建仓库并推送

---

## 常见问题

**Q：推送报 `remote: Support for password authentication was removed`？**
A：说明你在密码框里填了登录密码。必须填 Personal Access Token。

**Q：`git push` 卡住不动？**
A：通常是网络问题。可尝试：
```bash
git config --global http.proxy http://127.0.0.1:7890   # 换成你自己的代理端口
```

**Q：创建仓库时勾了 README，导致 push 被拒（non-fast-forward）？**
A：先拉取合并再推送：
```bash
git pull --rebase origin main
git push -u origin main
```

**Q：我不小心把 token 发到公开的地方了？**
A：立即到 Settings → Developer settings → Personal access tokens 删除该 token，重新生成一个。
