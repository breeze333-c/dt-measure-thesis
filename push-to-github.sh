#!/usr/bin/env bash
# 一键推送到 GitHub
# 用法：bash push-to-github.sh <你的GitHub用户名> [仓库名]
# 示例：bash push-to-github.sh zhangsan
#       bash push-to-github.sh zhangsan my-thesis
#
# 前置条件：已在 GitHub 网页端创建了对应的【空】仓库（不要勾选 README/gitignore/license）
set -e

USER_NAME="${1:-}"
REPO="${2:-dt-measure-thesis}"

if [ -z "$USER_NAME" ]; then
  echo "用法：bash push-to-github.sh <你的GitHub用户名> [仓库名]"
  echo "示例：bash push-to-github.sh zhangsan"
  exit 1
fi

cd "$(dirname "$0")"

echo "[1/3] 清理旧的远程地址（如有）"
git remote remove origin 2>/dev/null || true

echo "[2/3] 关联远程仓库 https://github.com/${USER_NAME}/${REPO}.git"
git remote add origin "https://github.com/${USER_NAME}/${REPO}.git"

echo "[3/3] 推送 main 分支（提示输入凭据时，Password 处请填 Personal Access Token，不是登录密码）"
git push -u origin main

echo ""
echo "完成！仓库地址：https://github.com/${USER_NAME}/${REPO}"
