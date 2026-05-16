#!/usr/bin/env bash
# 不启动 HA，仅做静态检查（语法、manifest、目录结构）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INTEGRATION="${ROOT}/custom_components/pana_erv"

echo "==> 检查集成目录结构"
required=(
  "__init__.py"
  "manifest.json"
  "config_flow.py"
  "const.py"
  "fan.py"
  "hub.py"
  "state.py"
)
for f in "${required[@]}"; do
  if [[ ! -f "${INTEGRATION}/${f}" ]]; then
    echo "缺少文件: ${f}"
    exit 1
  fi
  echo "  OK ${f}"
done

echo ""
echo "==> Python 语法检查"
python3 -m py_compile \
  "${INTEGRATION}/hub.py" \
  "${INTEGRATION}/state.py" \
  "${INTEGRATION}/config_flow.py" \
  "${INTEGRATION}/const.py" \
  "${INTEGRATION}/fan.py"
echo "  OK 语法通过"

echo ""
echo "==> manifest.json"
python3 -c "
import json, sys
m = json.load(open('${INTEGRATION}/manifest.json'))
assert m.get('domain') == 'pana_erv', 'domain 应为 pana_erv'
assert m.get('config_flow') is True, 'manifest 需 config_flow: true'
print('  OK domain=%s version=%s' % (m['domain'], m.get('version')))
"

echo ""
echo "==> 检查 PLATFORMS 与 fan 模块一致"
python3 -c "
import ast, pathlib
src = pathlib.Path('${INTEGRATION}/__init__.py').read_text()
tree = ast.parse(src)
for node in ast.walk(tree):
    target = None
    value = None
    if isinstance(node, ast.Assign):
        target, value = node.targets[0], node.value
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        target, value = node.target, node.value
    if getattr(target, 'id', None) == 'PLATFORMS' and value is not None:
        names = [e.attr for e in value.elts if isinstance(e, ast.Attribute)]
        assert names == ['FAN'], 'PLATFORMS 应为 [Platform.FAN]，当前: %s' % names
        print('  OK PLATFORMS =', names)
        raise SystemExit(0)
raise SystemExit('未找到 PLATFORMS 定义')
"

echo ""
echo "全部静态检查通过。真机测试: ./scripts/run-python-tests.sh 后执行 test_modbus.py"
