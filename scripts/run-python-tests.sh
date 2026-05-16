#!/usr/bin/env bash
# 在本机跑通 Python 测试，无需 Home Assistant
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.venv"
cd "${ROOT}"

if [[ ! -d "${VENV}" ]]; then
  echo "创建虚拟环境 ${VENV} ..."
  python3 -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

if ! python -c "import pymodbus" 2>/dev/null; then
  echo "安装测试依赖..."
  pip install -q -r scripts/requirements-test.txt
fi

echo ">>> 1/3 集成静态检查"
./scripts/validate-integration.sh

echo ""
echo ">>> 2/3 离线 Modbus 自检（mock）"
python scripts/test_modbus.py --self-test

echo ""
echo ">>> 3/3 单元测试"
python scripts/test_modbus.py --unit-test

echo ""
echo "全部本机 Python 测试通过。"
echo "连接真机: source .venv/bin/activate && python scripts/test_modbus.py --host <有人模块IP> --port 8899"
echo "控制测试: source .venv/bin/activate && python scripts/test_modbus.py --host <IP> --test-controls"
