# WeAct RP2350A Core V20 示例代码

[English Version](README-EN.md)

---

配套固件：`firmware16M/` 或 `firmware4M/` 中的 MicroPython v1.29.0。

## 运行方式

**U 盘方式**（推荐）：把 `.py` 拷到 `MicroPython` 盘根目录，改名为 `main.py` 即可上电自动运行。

**REPL 方式**：拷到盘里后，在 REPL 里执行

```python
exec(open("01_led_blink.py").read())
```

**mpremote 方式**：

```bash
mpremote cp weact_board.py :                      # 板级封装，多数例程会 import 它
mpremote run 01_led_blink.py
```

`weact_board.py` 提供引脚定义与 `Led` / `Key` 封装，例程会优先导入它；没有该文件时例程可独立运行，但引脚常量需自己确认。

## 引脚对照

| 功能 | V20 引脚 | 说明 |
|---|---|---|
| 板载 LED | **GP25** | 单颗，高电平点亮 |
| 外接按键 | **GP15** | **板上没有用户按键**，需自行在 GP15 与 GND 之间接键 |
| ADC | **GP26 / GP27 / GP28** | 排针上只有这 3 路 |
| VSYS 检测 | **GP29**（ADC3） | 板载 100K/100K 分压，`weact_board.vsys_voltage()` 直接给伏特 |
| VBUS 检测 | **GP24** | 板载 100K/100K 分压，当数字输入读，`vbus_present()` 给布尔值 |
| UART0 | TX=GP0，RX=GP1 | 115200 8N1，CTS/RTS 未连接 |
| I2C0 | SDA=GP4，SCL=GP5 | 内部上拉较弱，外接模块建议并 4.7k |
| SPI0 | SCK=GP18，TX=GP19，RX=GP16，CSn=GP17 | |
| PWM/舵机 | GP14（示例） | 任意 GPIO 均可做 PWM |
| BOOT | — | 拉低 QSPI_SS（SW1），仅用于下载 |
| RESET | — | 拉低 RUN（SW2） |

> **V20 就是 Pico 2**，只有 Flash 容量不同。所以这些例程在 Pico 2 上也能原样跑，Pico 2 的例程同样适用于这里。唯一要留心的是 V10：那是另一套硬件（LED1=GP24 + LED2=GP25 双灯、板载按键 GP23），V10 的例程搬到 V20 上会在 `Pin(23)` / `Pin(24)` 处得到完全不同的行为。

## 例程清单

| 文件 | 内容 | 关键引脚 |
|---|---|---|
| `weact_board.py` | 板级封装：`Led` / `Key` / `banner()` / `run_safely()` | — |
| `01_led_blink.py` | LED 500ms 闪烁，打印计数 | GP25 |
| `02_led_pwm.py` | PWM 呼吸灯，1kHz | GP25 |
| `03_key_poll.py` | 按键轮询 + 软件消抖 | GP15 外接 |
| `04_key_irq.py` | 按键下降沿中断 + 延时消抖 | GP15 外接 |
| `05_uart_echo.py` | UART0 回显 | GP0/GP1 |
| `06_uart_command.py` | UART 命令行（`led on/off/toggle/blink`、`pwm`、`gpio`、`info`） | GP0/GP1 |
| `07_pwm_servo.py` | 50Hz 舵机扫角 + 蜂鸣器 | GP14 |
| `08_adc_read.py` | ADC 三通道电压 + GP29 读 VSYS + 片内温度 | GP26/27/28、GP29 |
| `09_i2c_scan.py` | I2C 总线扫描 0x08–0x77 | GP4/GP5 |
| `10_spi_loopback.py` | SPI 自环测试 | GP18/19/16/17 |
| `11_timer_irq.py` | 硬件定时器周期回调 | — |
| `12_key_led_fsm.py` | 按键 + LED 状态机（单击/双击/长按） | GP15 / GP25 |
| `13_vsys_vbus_monitor.py` | VSYS 电压 + VBUS 插拔监测，500ms 采样 | GP29 / GP24 |

## 接线提示

- **03 / 04 / 12**：需要在 **GP15 与 GND** 之间接一个轻触按键。悬空时内部上拉读到高电平，例程会提示“未检测到按键”。
- **05 / 06**：需要一个 USB-TTL 模块接到 GP0(TX) / GP1(RX) / GND，115200 8N1。注意 USB-TTL 的 RX 接板子的 TX（GP0）。
- **08**：GP26/27/28 接 0~3.3V 信号即可，悬空读数会飘属正常。GP29 不需要接线——它是板上 VSYS 分压（R23/R24 各 100K），读数为 VSYS 的一半，例程会乘 2 还原。GP29 固定接电源，**不要**外接信号去驱动它。
- **09**：未接 I2C 器件时扫描结果为空，这是正常的。
- **10**：需要把 **GP19 与 GP16 直接短接**，否则读回全 0/全 FF，例程会提示未短接。
- **12**：状态机默认按键接 GP15；若改用其它引脚，修改文件顶部的 `PIN_KEY`。
- **13**：不需要接线。VSYS 与 VBUS 的分压都在板上，插拔 USB 就能看到 `[事件] VBUS` 提示。

## 与固件的关系

例程只依赖 MicroPython 标准库（`machine`、`time`、`utime`、`rp2`），不需要额外冻结模块。固件已打开 USB MSC，所以盘符可见、可直接拖放文件；REPL 走 USB CDC，是独立的第二个串口。

如果例程报 `MemoryError`，先 `gc.collect()`，或用 `mpremote run`（不占板内 RAM 保存文件）。
