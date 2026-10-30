# WeAct RP2350A Core V20 固件自检套件

[English Version](README-EN.md)

---

配套固件：`firmware16M/` 或 `firmware4M/` 中的 MicroPython v1.29.0。

用途：烧完固件后确认板级软硬件正常，并生成可归档的报告。

## 文件

| 文件 | 作用 |
|---|---|
| `fw_test.py` | 测试套件本体，26 个用例，输出 `@@TEST` / `@@SUM` 协议 |
| `main.py` | 上电自动运行入口，同时保存 `/fwtest_report.txt` |
| `host_test.py` | PC 端驱动与报告生成（Markdown + JSON） |
| `tools/mpy_sim.py` | 无板时模拟运行 |

## 运行方式

**① 拷到 U 盘，上电自动运行**

把 `main.py` 与 `fw_test.py` 放到 `MicroPython` 盘根目录，按 RESET 或重新上电。板子等待 2 秒（USB 枚举完成）后自动运行，输出在串口可见，结果同时写入 `/fwtest_report.txt`。

**② PC 端一条命令**

```bash
pip install pyserial

python3 host_test.py --port /dev/ttyACM0             # Linux
python3 host_test.py --port COM7                     # Windows
python3 host_test.py --port /dev/ttyACM0 --quick     # 跳过性能项
python3 host_test.py --port /dev/ttyACM0 --fetch     # 取回板端已存结果
```

产物：`fwtest_report_YYYYmmdd_HHMMSS.md` 与同名 `.json`。

退出码：0 全通过（允许 SKIP）、1 有 FAIL、2 环境或连接错误。

**③ REPL 手动运行**

```python
import fw_test
fw_test.run()                  # 全部用例
fw_test.run(quick=True)        # 跳过 T18/T19
fw_test.run(only="T01,T03")    # 只跑指定用例
```

## 26 个用例

| 编号 | 用例 | 判定 |
|---|---|---|
| T01 | 系统信息 | `sysname=rp2`、板名含 `WeAct Studio RP2350A Core V20`、主频 ≥48MHz |
| T02 | 固件版本 | MicroPython ≥1.25，打印 mpy 版本 |
| T03 | Flash 分区容量 | `ioctl(4)*ioctl(5)` = 容量−1MB，并与 FAT BPB 交叉校验 |
| T04 | Flash 只读读取 | 扇区 0 含 `EB xx 90`、OEM 名与 `55AA` 签名 |
| T05 | 文件系统容量 | `statvfs("/")` 总量 ≈ 容量−1MB |
| T06 | 文件读写校验 | 64KB 写入后逐字节比对，顺带记录读写速度 |
| T07 | 目录与重命名 | mkdir / rename / rmdir |
| T08 | LED GP25 输出 | 输出回读 1/0 |
| T09 | GPIO 内部上下拉 | GP22 上拉=1、下拉=0 |
| T10 | 外接按键 GP15 | 持续低 1.5 秒判故障；3 秒内按下判 PASS，否则 SKIP |
| T11 | PWM 输出 | GP25 1kHz、25% 占空比回读 |
| T12 | ADC 与片内温度 | GP26/27/28 读数；温度在 −40~125℃ |
| T13 | 软件定时器回调 | 1kHz 运行 200ms，触发 120~320 次 |
| T14 | 时间基准 | `time_ns` 与 `ticks_ms` 500ms 内一致 |
| T15 | UART0 自环 | 需短接 GP0–GP1，否则 SKIP |
| T16 | SPI0 自环 | 需短接 GP19–GP16，否则 SKIP |
| T17 | I2C0 总线扫描 | GP4/GP5，无器件 SKIP |
| T18 | 内存拷贝带宽 | >5MB/s |
| T19 | Flash 文件吞吐 | 512KB，写 >20KB/s 读 >40KB/s |
| T20 | 外部存储探测 | `/sd`、`/sdcard` 挂载则报容量 |
| T21 | GC 堆与分配 | 可用堆 >64KB，50 次 4KB 分配无泄漏 |
| T22 | 双核 `_thread` | core1 计算结果正确 |
| T23 | USB 设备接口 | `rp2.Flash`、`machine.bootloader` 可用 |
| T24 | 复位原因 | 打印 PWRON / WDT / SOFT 等 |
| T25 | VSYS 电压 | GP29 分压值 ×2，应在 2.8–5.8V；3V3 反灌供电时 SKIP |
| T26 | VBUS 检测 | GP24 数字读，并与 VSYS 交叉校验电源通路 |

**SKIP 不等于失败**：T10 未接按键、T15/T16 未短接、T17 无 I2C 器件、T20 未插 SD 均属正常。

## V20 与 V10 的用例差异

V20 与 Pico 2 硬件一致，所以下表里 V20 列应处处等于 Pico 2 列——不等就是 bug。

| 用例 | V10 | Pico 2 | V20 |
|---|---|---|---|
| T08 LED | GP24 蓝 + GP25 绿 | GP25 单颗 | **同 Pico 2** |
| T10 按键 | 板载 GP23 | 无按键 | **同 Pico 2**（需在 GP15–GND 外接） |
| T12 ADC | GP26–GP29 | GP26/27/28，GP29 给 VSYS | **同 Pico 2** |
| T25 VSYS | 无 | GP29 + 100K/100K | **同 Pico 2** |
| T26 VBUS | 无 | GP24 + 100K/100K | **同 Pico 2** |
| T01 板名 | `WeAct RP2350A Core V10` | `Raspberry Pi Pico2` | `WeAct Studio RP2350A Core V20` |

## 结果判读

| 结果 | 含义 |
|---|---|
| 全部 PASS，少量 SKIP | 板子可用 |
| T03 FAIL | 固件与 Flash 容量不匹配，换对应容量固件重烧 |
| T05/T06 FAIL | 文件系统未正确挂载，检查是否烧了带 `-msc` 的固件 |
| T10 FAIL | GP15 持续为低，检查是否短路到 GND |
| T25 FAIL | VSYS 超出 2.8–5.8V，检查供电或 R23/R24 分压 |
| T26 FAIL | VBUS 为高但 VSYS 无电，电源通路（二极管/理想二极管）异常 |
| T19 明显偏低 | 检查 Flash 焊接与 QSPI 走线 |
| T21 FAIL | 反复分配后堆不恢复 |

## 无板时自检套件

```bash
python3 tools/mpy_sim.py --mb 16                       # 16MB 板，默认接线
python3 tools/mpy_sim.py --mb 4                        # 4MB 板
python3 tools/mpy_sim.py --mb 16 --uart-loop --spi-loop --i2c --key --sd
python3 tools/mpy_sim.py --mb 16 --quick               # 跳过性能项
python3 tools/mpy_sim.py --mb 16 --vsys 3.7 --no-vbus   # 电池供电
python3 tools/mpy_sim.py --mb 16 --vsys 0 --no-vbus     # 3V3 引脚反灌
python3 tools/mpy_sim.py --mb 16 --out sim.log
python3 host_test.py --log sim.log                     # 用日志生成报告
```

模拟器把 `machine` / `rp2` / `_thread` / `time.ticks_*` 替换为桩实现，并把 `/` 开头的路径重定向到临时目录，不写入本机文件系统。它只能验证测试逻辑与输出协议，**不能替代上板验证**。

默认 16MB 配置（USB 供电）下的预期结果：`@@SUM 21 0 5 26`（5 个 SKIP 为按键、UART、SPI、I2C、SD）。
带全部外设开关时：`@@SUM 26 0 0 26`。
3V3 引脚反灌供电（`--vsys 0 --no-vbus`）时 T25/T26 一并 SKIP，结果 `@@SUM 19 0 7 26`。

## 已知边界

1. T23 只反映设备侧 API 是否存在。内建 USB（REPL + MSC）由 TinyUSB 内建描述符驱动，MSC 是否工作需在主机侧看盘符。
2. 套件不包含复位、WDT、deepsleep 测试，避免中途断开 USB。复位行为由 T24 与人工断电验证。
3. T10 需要人为在 3 秒窗口内按下外接按键，无人值守时会得到 SKIP，这是预期行为。
