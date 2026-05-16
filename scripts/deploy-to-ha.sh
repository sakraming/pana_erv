#!/usr/bin/env bash
# 通过 SSH 将 pana_erv 同步到已有 Home Assistant 的 config 目录
#
# 用法示例:
#   export HA_SSH="root@192.168.30.33"
#   export HA_CONFIG_PATH="/config"          # HA OS / Supervised 一般为 /config
#   ./scripts/deploy-to-ha.sh
#
# 部署后请在 HA 中: 开发者工具 → YAML → 重新启动
# 或: ha core restart（SSH 终端里若有 ha 命令）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${ROOT}/custom_components/pana_erv"
HA_SSH="${HA_SSH:?请设置 HA_SSH，例如 root@192.168.30.33}"
HA_CONFIG_PATH="${HA_CONFIG_PATH:-/config}"
TARGET="${HA_CONFIG_PATH}/custom_components/pana_erv"

if [[ ! -d "${SOURCE}" ]]; then
  echo "错误: 未找到 ${SOURCE}"
  exit 1
fi

echo "同步到 ${HA_SSH}:${TARGET}"
ssh "${HA_SSH}" "mkdir -p ${HA_CONFIG_PATH}/custom_components"
rsync -av --delete \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "${SOURCE}/" "${HA_SSH}:${TARGET}/"

echo ""
echo "已上传。请在 Home Assistant 中执行:"
echo "  1. 删除旧集成目录（若存在）: panasonic_erv、panasonic_xinfeng"
echo "  2. 设置 → 设备与服务 → 删除旧版集成配置（若有）"
echo "  3. 重启 Home Assistant"
echo "  4. 添加集成 → 搜索「Pana ERV」"
