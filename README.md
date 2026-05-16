<<<<<<< HEAD
# Pana ERV

Home Assistant 自定义集成：通过**有人 USR** 等 Modbus TCP（RTU 透传）网关控制松下新风（ERV）。

## 功能

| 功能 | 说明 |
|------|------|
| 开关 | 寄存器 `1`：`0` 关 / `1` 开 |
| 模式 | 寄存器 `2`：`0` 热交换 / `1` 普通模式 |
| 风量 | 寄存器 `3`：`1` 弱 / `3` 强（真机仅两档） |

以 `fan` 实体接入，支持 HA 风速滑条（50% / 100%）与模式预设。

## 安装

### HACS（推荐）

1. HACS → 集成 → 自定义仓库 → 添加 `https://github.com/sakraming/pana_erv`
2. 类别选 **Integration**，安装 **Pana ERV**
3. 重启 Home Assistant

### 手动安装

将 `custom_components/pana_erv/` 复制到 HA 配置目录：

```text
config/custom_components/pana_erv/
```

重启后：**设置 → 设备与服务 → 添加集成 → Pana ERV**，填写有人模块 **IP** 与 **端口**（默认 `8899`）。

## 配置要求

- Home Assistant 与有人模块在同一局域网（或路由可达）
- 集成域名为 `pana_erv`；若曾安装 `panasonic_erv` / `panasonic_xinfeng`，请先删除旧目录与旧集成条目

## 开发 / 本机测试

不安装 Home Assistant 也可验证 Modbus 逻辑：

```bash
./scripts/run-python-tests.sh
source .venv/bin/activate
python scripts/test_modbus.py --host <有人模块IP> --port 8899
python scripts/test_modbus.py --host <IP> --test-controls
```

## 已知限制

- 湿度、温度、滤网剩余时间等**状态寄存器**偏移尚未在真机确认，当前版本仅可靠支持开关 / 模式 / 风量控制。
- 无效 Modbus 值（如 `65535`）不会显示在实体属性中。

## 许可证

个人项目，按「现状」提供，不保证适配所有机型。
=======
# pana_erv
>>>>>>> 9e01305b82774fe424f96b3e32288b63ced9d6cd
