# WeAct Studio RP2350A Core V10 Example Code

[简体中文](./README.md)

---

WeAct Studio Official Link

| Item | Link |
|---|---|
| taobao | weactstudio.taobao.com |
| aliexpress | weactstudio.aliexpress.com |
| github | github.com/WeActStudio |
| gitee | gitee.com/WeAct-TC |
| blog | www.weact-tc.cn |

## Environment

- Firmware: MicroPython v1.29.0 built from this project (16 MB or 4 MB image)
- Board: WeAct Studio RP2350A Core V10

## Files

| File | Function | Wiring |
|---|---|---|
| `weact_board.py` | pin map, `Led` / `Key` wrappers, `banner` / `run_safely` | no |
| `01_led_blink.py` | LED1 and LED2 toggle together every 500 ms | no |
| `02_led_pwm.py` | 1 kHz PWM on LED2, duty cycles 0 to 100% and back | no |
| `03_key_poll.py` | poll KEY every 1 ms, toggle LED2 and count presses | no |
| `04_key_irq.py` | falling-edge IRQ on KEY toggles LED2 and counts | no |
| `05_uart_echo.py` | UART0 echoes every byte received and prints totals | USB-TTL or jumper GP0-GP1 |
| `06_uart_command.py` | line-based UART commands drive LED1/LED2 | USB-TTL |
| `07_pwm_servo.py` | 50 Hz PWM sweeps a servo on GP20, then a square wave drives a buzzer | servo / buzzer |
| `08_adc_read.py` | read GP26-29 ADC values and the internal temperature | no |
| `09_i2c_scan.py` | scan I2C0 addresses 0x08-0x77 every 2 s | I2C device |
| `10_spi_loopback.py` | SPI0 loopback of 32 bytes at 100k / 1M / 4M | jumper GP19-GP16 |
| `11_timer_irq.py` | Timer(-1) toggles LED2 every 500 ms and prints the count drift | no |
| `12_key_led_fsm.py` | short press cycles five LED effects, 800 ms hold turns off | no |
| `weact_link.h` | C copyright header and pin macros | — |

## How to Run

`weact_board.py` must be in the same directory as the example.

File names start with a digit and cannot be imported; run them in the REPL:

```python
exec(open("01_led_blink.py").read())
```

Or run directly with mpremote:

```bash
mpremote run 01_led_blink.py
```

To run automatically at power-up, rename the example to `main.py` and reset.

## Pin Map

| Resource | Pin |
|---|---|
| LED1 (blue) | GP24, active high |
| LED2 (green) | GP25, active high |
| KEY | GP23, active low |
| UART0 | TX = GP0, RX = GP1 |
| I2C0 | SDA = GP4, SCL = GP5 |
| SPI0 | SCK = GP18, MOSI = GP19, MISO = GP16, CSN = GP17 |
| ADC | GP26, GP27, GP28, GP29 |
| Servo / buzzer (07) | GP20 |

## Example Details

### 01 LED blink

LED1 and LED2 toggle together, so the two LEDs alternate. Each toggle prints the
tick count and the current levels.

### 02 Breathing LED

`PWM(Pin(25))` with `freq(1000)`; the duty ramps from 0 up to 65535 and back down,
20 ms per step, 50 steps, printing every 10 steps. On exit the duty is zeroed and
`deinit()` is called.

### 03 Key polling

`Key.update()` applies 20 ms of debounce and returns `True` on a confirmed press.
The loop calls it every 1 ms, toggles LED2 and prints `key.count` and `key.pressed()`.

### 04 Key interrupt

`key.irq(handler, Pin.IRQ_FALLING)` attaches the key to a falling-edge IRQ. The ISR
increments `counter[0]` and toggles LED2. The main loop runs every 50 ms and prints
a heartbeat with the counter every 20 rounds.

### 05 UART echo

`UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))`. `uart.any()` gives the readable
byte count; the data is read and written back unchanged, printing the payload and
the running totals. The REPL uses USB CDC and does not occupy GP0/GP1.

### 06 UART command line

Input is received character by character; `\r` or `\n` ends a line, backspace
deletes the last character, and a line is limited to 64 bytes. Each complete line
is parsed by `handle()` and the response is sent back.

| Command | Function |
|---|---|
| `help` | list the commands |
| `led1 on\|off\|toggle` | drive LED1 |
| `led2 on\|off\|toggle` | drive LED2 |
| `both on\|off` | drive both LEDs |
| `blink <times> <period>` | blink LED2, 1-20 times, 20-2000 ms period |
| `status` | report levels and clock |

### 07 Servo and buzzer

The servo is driven at 50 Hz (20 ms period); 500 us maps to 0 deg and 2500 us to
180 deg, sweeping 0/45/90/135/180/90/0 deg. The buzzer then gets a 2-4 kHz square
wave at 50% duty for eight notes from 262 to 523 Hz.

### 08 ADC reading

`ADC(Pin(26..29))` returns 0-65535 from `read_u16()`, converted to volts against the
3.3 V reference. The internal temperature uses `ADC(ADC.CORE_TEMP)` with
`T = 27 - (V - 0.706) / 0.001721`. Printed every 500 ms.

### 09 I2C scan

`I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)`. Each address 0x08-0x77 is probed with
`writeto(addr, b"")`; no exception means the device is present. The first byte is
then read with `readfrom(addr, 1)`.

### 10 SPI loopback

`SPI(0, baudrate, polarity=0, phase=0, firstbit=SPI.MSB)`; `write_readinto()` sends
and receives 32 bytes (0x00-0x1F) which are compared byte by byte. GP19 (MOSI) must
be wired to GP16 (MISO); without the jumper the result is FAIL.

### 11 Timer interrupt

The rp2 port only supports the software timer `Timer(-1)`; `Timer(0)` raises
`ValueError: bad timer number`.

`tim.init(period=500, mode=Timer.PERIODIC, callback=tick)` calls the callback every
500 ms. After sleeping 1300 ms the main loop prints the elapsed time, the expected
count, the actual count and the difference.

### 12 Key-driven LED modes

Mode order: steady on, breathing, fast blink, slow blink, off. A short press (under
800 ms) advances to the next mode; holding for 800 ms jumps to off.

All five effects drive one PWM channel on LED2, expressed as a duty value:

| Mode | Output |
|---|---|
| steady on | `duty_u16(65535)` |
| off | `duty_u16(0)` |
| fast blink | toggle 0 / 65535, 100 ms half period |
| slow blink | toggle 0 / 65535, 600 ms half period |
| breathing | ramp 0 to 65535, 25 ms per step, 40 steps |

Press detection uses the debounced `Key.update()` and `Key.pressed()`. On a mode
change the output and phase are cleared first, then the new effect is set up.

## FAQ

| Symptom | Fix |
|---|---|
| `ImportError: no module named 'weact_board'` | keep `weact_board.py` in the same directory as the example |
| `SyntaxError` on `import 01_xxx` | file names start with a digit; use `exec(open("01_xxx.py").read())` |
| one press fires twice | debounce the key with `Key(pin, debounce_ms=20)` |
| hang after `print` in an ISR | only set flags in the ISR, print from the main loop |
| `ValueError: bad timer number` | use `Timer(-1)` |
| `Pin.value()` has no effect after PWM | rp2 `PWM.deinit()` does not restore the pin; rebuild `Pin(p, Pin.OUT)` or use PWM only |
| every SPI loopback fails | check the GP19-GP16 jumper |
| board resets when the servo moves | power the servo from a separate 5 V supply and share GND |
