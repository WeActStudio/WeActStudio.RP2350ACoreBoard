# WeAct Studio RP2350A Core V10 示例代码

[English Version](./README-EN.md)

---

WeAct Studio Official Link

| 项目 | 地址 |
|---|---|
| taobao | weactstudio.taobao.com |
| aliexpress | weactstudio.aliexpress.com |
| github | github.com/WeActStudio |
| gitee | gitee.com/WeAct-TC |
| blog | www.weact-tc.cn |

## 环境

- 固件：本工程编译的 MicroPython v1.29.0（16MB / 4MB 版均可）
- 板卡：WeAct Studio RP2350A Core V10

## 文件说明

| 文件 | 功能 | 外部接线 |
|---|---|---|
| `weact_board.py` | 引脚定义，`Led` / `Key` 封装，`banner` / `run_safely` | 否 |
| `01_led_blink.py` | LED1、LED2 每 500ms 同时翻转，交替亮灭 | 否 |
| `02_led_pwm.py` | LED2 以 1kHz PWM 输出，占空比 0→100%→0 循环 | 否 |
| `03_key_poll.py` | 每 1ms 轮询 KEY，按下翻转 LED2 并累计次数 | 否 |
| `04_key_irq.py` | KEY 下降沿中断，中断内翻转 LED2 并计数 | 否 |
| `05_uart_echo.py` | UART0 收多少字节回发多少字节，打印收发统计 | USB-TTL 或短接 GP0-GP1 |
| `06_uart_command.py` | UART0 按行解析命令控制 LED1/LED2，回发结果 | USB-TTL |
| `07_pwm_servo.py` | GP20 输出 50Hz PWM 驱动舵机扫描，再输出方波驱动蜂鸣器 | 舵机 / 蜂鸣器 |
| `08_adc_read.py` | 采集 GP26-29 的 ADC 值并换算电压，读取片内温度 | 否 |
| `09_i2c_scan.py` | 每 2 秒扫描 I2C0 上 0x08~0x77 的器件地址 | I2C 器件 |
| `10_spi_loopback.py` | SPI0 以 100k/1M/4M 发送 32 字节并读回比对 | 短接 GP19-GP16 |
| `11_timer_irq.py` | Timer(-1) 每 500ms 回调翻转 LED2，打印计数偏差 | 否 |
| `12_key_led_fsm.py` | 短按循环切换五种灯效，长按 800ms 切到熄灭 | 否 |
| `weact_link.h` | C 语言版权头与板级引脚宏 | — |

## 运行方法

`weact_board.py` 必须与例程放在同一目录。

文件名以数字开头，不能直接 `import`，在 REPL 中执行：

```python
exec(open("01_led_blink.py").read())
```

或用 mpremote 直接运行：

```bash
mpremote run 01_led_blink.py
```

需要上电自动运行，把例程重命名为 `main.py` 后复位。

## 引脚定义

| 资源 | 引脚 |
|---|---|
| LED1（蓝） | GP24，高电平点亮 |
| LED2（绿） | GP25，高电平点亮 |
| KEY | GP23，低电平有效 |
| UART0 | TX=GP0，RX=GP1 |
| I2C0 | SDA=GP4，SCL=GP5 |
| SPI0 | SCK=GP18，MOSI=GP19，MISO=GP16，CSN=GP17 |
| ADC | GP26、GP27、GP28、GP29 |
| 舵机 / 蜂鸣器（07） | GP20 |

## 各例程说明

### 01 LED 闪烁

LED1 与 LED2 同时翻转电平，因此两灯交替亮灭，每次翻转打印计数与当前电平。

### 02 PWM 呼吸灯

`PWM(Pin(25))`，`freq(1000)`，占空比从 0 增至 65535 再降回 0，每步 20ms、共 50 步，
每 10 步打印一次。退出时占空比归零并 `deinit()`。

### 03 按键轮询

`Key.update()` 内置 20ms 消抖，确认按下时返回 `True`。主循环每 1ms 调用一次，
按下则翻转 LED2，并打印 `key.count` 与 `key.pressed()`。

### 04 按键中断

`key.irq(handler, Pin.IRQ_FALLING)` 把按键挂到下降沿中断。中断服务函数内累加
`counter[0]` 并翻转 LED2；主循环每 50ms 一轮，每 20 轮打印一次心跳与计数。

### 05 UART 回显

`UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))`。`uart.any()` 判断可读字节数，
`read()` 后原样 `write()` 回发，打印本次内容与累计收发量。REPL 走 USB CDC，
不占用 GP0/GP1。

### 06 UART 命令行

逐字符接收，`\r` 或 `\n` 表示一行结束，退格键删除最后一个字符，单行上限 64 字节。
整行交给 `handle()` 解析并把响应回发。

| 命令 | 功能 |
|---|---|
| `help` | 显示命令列表 |
| `led1 on\|off\|toggle` | 控制 LED1 |
| `led2 on\|off\|toggle` | 控制 LED2 |
| `both on\|off` | 同时控制两颗 |
| `blink <次数> <间隔ms>` | LED2 闪烁，次数 1~20，间隔 20~2000ms |
| `status` | 返回两颗电平与主频 |

### 07 PWM 舵机与蜂鸣器

舵机以 50Hz、周期 20ms 输出，脉宽 500us 对应 0°、2500us 对应 180°，依次转
0/45/90/135/180/90/0°。蜂鸣器改为 2~4kHz 方波、50% 占空比，播放 262~523Hz 八个音阶。

### 08 ADC 读取

`ADC(Pin(26..29))`，`read_u16()` 得到 0~65535，按 3.3V 参考换算电压。片内温度用
`ADC(ADC.CORE_TEMP)`，公式 `T = 27 - (V - 0.706) / 0.001721`。每 500ms 打印一次。

### 09 I2C 扫描

`I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)`。向 0x08~0x77 逐地址
`writeto(addr, b"")`，无异常即视为在线，随后 `readfrom(addr, 1)` 读取首字节。

### 10 SPI 回环

`SPI(0, baudrate, polarity=0, phase=0, firstbit=SPI.MSB)`，用 `write_readinto()`
同时收发 32 字节（0x00~0x1F），逐字节比对。需短接 GP19(MOSI) 与 GP16(MISO)，
未短接时结果为 FAIL。

### 11 定时器中断

rp2 端口只支持软件定时器 `Timer(-1)`，写 `Timer(0)` 会抛 `ValueError: bad timer number`。

`tim.init(period=500, mode=Timer.PERIODIC, callback=tick)` 每 500ms 调用一次回调。
主循环睡眠 1300ms 后打印已运行时间、理论次数、实际次数与偏差。

### 12 按键切换 LED 模式

模式顺序：常亮 → 呼吸 → 快闪 → 慢闪 → 熄灭。短按（不足 800ms）切下一个，
按住满 800ms 直接切到熄灭。

五种效果统一由 LED2 的一路 PWM 输出，以占空比表示：

| 模式 | 输出 |
|---|---|
| 常亮 | `duty_u16(65535)` |
| 熄灭 | `duty_u16(0)` |
| 快闪 | 0 / 65535 翻转，半周期 100ms |
| 慢闪 | 0 / 65535 翻转，半周期 600ms |
| 呼吸 | 0~65535 渐变，每步 25ms，共 40 步 |

按键判定使用消抖后的 `Key.update()` 与 `Key.pressed()`。切换到新模式时先清零输出
与相位，再按类型建立效果。

## 常见问题

| 现象 | 处理 |
|---|---|
| `ImportError: no module named 'weact_board'` | 把 `weact_board.py` 与例程放同一目录 |
| `SyntaxError`，提示 `import 01_xxx` | 文件名以数字开头，改用 `exec(open("01_xxx.py").read())` |
| 按键按一次触发多次 | 使用 `Key(pin, debounce_ms=20)` 消抖 |
| 中断内 `print` 后卡死 | 中断内只改标志位，打印放主循环 |
| `ValueError: bad timer number` | 定时器改用 `Timer(-1)` |
| PWM 之后 `Pin.value()` 无法控制该引脚 | rp2 的 `PWM.deinit()` 不恢复引脚功能，需重新 `Pin(p, Pin.OUT)`，或全程只用 PWM |
| SPI 回环全部 FAIL | 检查 GP19 与 GP16 是否短接 |
| 舵机转动时板子复位 | 舵机单独 5V 供电并与板子共地 |
