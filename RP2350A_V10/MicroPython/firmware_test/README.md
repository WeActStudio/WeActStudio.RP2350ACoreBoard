# WeAct RP2350A_V10 固件自检套件

[English Version](./README-EN.md)

---

配套固件：`firmware16M/` 或 `firmware4M/` 中的 MicroPython v1.29.0。

用途：烧完固件后确认板级软硬件正常，并生成可归档的报告。

## 文件

| 文件 | 作用 |
|---|---|
| `fw_test.py` | 测试套件本体，24 个用例，输出 `@@TEST` / `@@SUM` 协议 |
| `main.py` | 上电自动运行入口，同时保存 `/fwtest_report.txt` |
| `host_test.py` | PC 端驱动与报告生成（Markdown + JSON） |
| `tools/mpy_sim.py` | 无板时模拟运行 |

## 运行方式

**① 拷到 U 盘，上电自动运行**

把 `main.py` 与 `fw_test.py` 放到 `MicroPython` 盘根目录，按 RUN 或复位。板子等待 2 秒
（USB 枚举完成）后自动运行，输出在串口可见，结果同时写入 `/fwtest_report.txt`。

**② PC 端一条命令**

```bash
pip install mpremote pyserial

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
fw_test.run()            # quick=True 跳过性能项
```

## 24 个用例

| 编号 | 用例 | 判定 |
|---|---|---|
| T01 | 系统信息 | `sysname=rp2`、板名含 `WeAct RP2350A Core V10`、主频 ≥48MHz |
| T02 | 固件版本 | MicroPython ≥1.25、mpy ≥6 |
| T03 | Flash 分区容量 | `ioctl(4)*ioctl(5)` = 容量-1MB，与 FAT BPB 交叉校验 |
| T04 | Flash 只读读取 | 扇区 0 含 `EB xx 90`、OEM 名与 `55AA` 签名 |
| T05 | 文件系统挂载与容量 | `statvfs` 总量 ≈ 容量-1MB |
| T06 | 文件读写校验 | 64KB 写入后逐字节比对 |
| T07 | 目录与重命名 | mkdir / rename / rmdir |
| T08 | LED GP24/GP25 输出 | 输出回读 1/0 |
| T09 | GPIO 内部上下拉 | GP22 上拉=1、下拉=0 |
| T10 | 按键 GP23 电平 | 持续低 200ms 判故障；3 秒内按下判 PASS，否则 SKIP |
| T11 | PWM 输出 | GP25 1kHz、25% 占空比回读 |
| T12 | ADC 与片内温度 | GP26-29 读数，温度在 -40~125℃ |
| T13 | 软件定时器回调 | 1kHz 运行 200ms，触发 120~320 次 |
| T14 | 时间基准 | `time_ns` 与 `ticks_ms` 500ms 内一致 |
| T15 | UART0 自环 | 需短接 GP0-GP1，否则 SKIP |
| T16 | SPI0 自环 | 需短接 GP19-GP16，否则 SKIP |
| T17 | I2C0 总线扫描 | GP4/GP5，无器件 SKIP |
| T18 | 内存拷贝带宽 | 自适应迭代，>5MB/s |
| T19 | Flash 文件写入速度 | 512KB，写>20KB/s 读>40KB/s |
| T20 | 外部存储探测 | `/sd`、`/sdcard` 挂载则报容量 |
| T21 | GC 堆与分配 | 可用堆 >64KB，50 次 4KB 分配无泄漏 |
| T22 | 双核 _thread | core1 计算结果正确 |
| T23 | USB 设备状态 | `USBDevice()` 存在，`rp2` 相关接口可用 |
| T24 | 复位原因 | 打印 PWRON / WDT |

SKIP 不等于失败：T15/T16 未短接、T17 无 I2C 器件、T20 未插 SD、T10 未按键均属正常。

## 结果判读

| 结果 | 含义 |
|---|---|
| 全部 PASS，少量 SKIP | 板子可用 |
| T03 FAIL | 固件与 Flash 容量不匹配，换对应容量固件重烧 |
| T10 FAIL | GP23 持续为低，检查按键是否卡住或缺少上拉 |
| T19 明显偏低 | 检查 Flash 焊接与 QSPI 走线 |
| T21 FAIL | 反复分配后堆不恢复 |

## 无板时自检套件

```bash
python3 tools/mpy_sim.py --mb 16                        # 16MB 板
python3 tools/mpy_sim.py --mb 4                         # 4MB 板
python3 tools/mpy_sim.py --mb 16 --flash 4              # 容量不符 → T03 失败
python3 tools/mpy_sim.py --mb 16 --uart-loop --spi-loop --i2c --key
python3 host_test.py --log /tmp/sim.log                 # 用日志生成报告
```

模拟器只替换 `machine` / `rp2` / `_thread`，并把 `/` 开头的路径重定向到临时目录，
不写入本机文件系统，也不能替代上板验证。

## 已知边界

1. T23 只反映设备侧状态。内建 USB（REPL + MSC）由 TinyUSB 内建描述符驱动，脚本侧的
   `USBDevice().active()` 为 `False` 属正常；MSC 是否工作需在主机侧看盘符。
2. 套件不包含复位、WDT、deepsleep 测试，避免中途断开 USB。复位行为由 T24 与人工
   断电验证。

## 实测基线

v1.29.0 / 16MB 板：

| 指标 | 实测 |
|---|---|
| 内存拷贝带宽 | 161 MB/s |
| 文件系统写（512KB） | 228 KB/s |
| 文件系统读（512KB） | 3403 KB/s |
| 64KB 文件写/读 | 193 / 1104 KB/s |
| 文件系统容量 | 15332KB 总 / 15292KB 可用 |
| GC 空闲堆 | 445KB |
