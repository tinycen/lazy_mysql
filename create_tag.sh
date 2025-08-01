#!/bin/bash

# bash create_tag.sh

# 定义要创建的标签
TAG_NAME="v0.1.1"

# 创建本地标签
git tag $TAG_NAME
# 推送标签到远程仓库
git push origin $TAG_NAME

# 显示最新的3个本地标签
echo "Latest 3 local tags:"
git tag -l | sort -V | tail -n 3

# 显示最新的3个远程标签
echo "Latest 3 remote tags:"
git ls-remote --tags origin | awk '{print $2}' | sed 's/refs\/tags\///' | sort -V | tail -n 3
