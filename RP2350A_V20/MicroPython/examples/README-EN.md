# WeAct RP2350A Core V20 Examples

[中文版](README.md)

---

Works with the MicroPython v1.29.0 images in `firmware16M/` or `firmware4M/`.

## How to run

**USB drive** (recommended): copy the `.py` to the root of the `MicroPython`
drive and rename it `main.py` so it runs on power-up.

**REPL**: copy the file first, then

```python
exec(open("01_led_blink.py").read())
```

**mpremote**:

```bash
mpremote cp weact_board.py :
mpremote run 01_led_blink.py
```

`weact_board.py` holds the pin map plus the `Led` / `Key` helpers. Examples try to
import it; without it they still run, but you must keep the pin constants right.

## Pin map

| Function | V20 pin | Note |
|---|---|---|
| Onboard LED | **GP25** | single LED, active high |
| External key | **GP15** | **no onboard user key**, wire one to GND yourself |
| ADC | **GP26 / GP27 / GP28** | only these three reach the header |
| VSYS sense | **GP29** (ADC3) | onboard 100K/100K divider, `weact_board.vsys_voltage()` returns volts |
| VBUS sense | **GP24** | onboard 100K/100K divider, read as a digital input, `vbus_present()` returns a bool |
| UART0 | TX=GP0, RX=GP1 | 115200 8N1, no CTS/RTS |
| I2C0 | SDA=GP4, SCL=GP5 | weak internal pull-ups, add 4.7k for modules |
| SPI0 | SCK=GP18, TX=GP19, RX=GP16, CSn=GP17 | |
| PWM / servo | GP14 (example) | any GPIO works |
| BOOT | — | pulls QSPI_SS low (SW1), flashing only |
| RESET | — | pulls RUN low (SW2) |

> **V20 is a Pico 2** with a different Flash size, so these examples also run
> unchanged on Pico 2 and Pico 2 examples apply here. The one trap is V10:
> that is different hardware (LED1=GP24 + LED2=GP25, onboard key on GP23), and
> V10 examples land on entirely different behaviour at `Pin(23)` / `Pin(24)`.

## Examples

| File | Content | Pins |
|---|---|---|
| `weact_board.py` | board helpers: `Led` / `Key` / `banner()` / `run_safely()` | — |
| `01_led_blink.py` | 500ms blink with a counter | GP25 |
| `02_led_pwm.py` | PWM breathing LED at 1kHz | GP25 |
| `03_key_poll.py` | polling with software debounce | GP15 (external) |
| `04_key_irq.py` | falling-edge IRQ with debounce | GP15 (external) |
| `05_uart_echo.py` | UART0 echo | GP0/GP1 |
| `06_uart_command.py` | UART command line (`led`, `pwm`, `gpio`, `info`) | GP0/GP1 |
| `07_pwm_servo.py` | 50Hz servo sweep + buzzer | GP14 |
| `08_adc_read.py` | 3-channel ADC + VSYS via GP29 + die temperature | GP26/27/28, GP29 |
| `09_i2c_scan.py` | scan 0x08-0x77 on I2C0 | GP4/GP5 |
| `10_spi_loopback.py` | SPI loopback test | GP18/19/16/17 |
| `11_timer_irq.py` | periodic hardware timer callback | — |
| `12_key_led_fsm.py` | key + LED state machine (click / double / long) | GP15 / GP25 |
| `13_vsys_vbus_monitor.py` | VSYS voltage and VBUS plug/unplug monitor, 500 ms sampling | GP29 / GP24 |

## Wiring notes

- **03 / 04 / 12** need a push button between **GP15 and GND**. Left floating the
  internal pull-up reads high and the example says "no key detected".
- **05 / 06** need a USB-TTL adapter on GP0(TX) / GP1(RX) / GND at 115200 8N1.
  Adapter RX goes to the board's TX (GP0).
- **08** takes any 0-3.3V signal on GP26/27/28; floating inputs drift, which is
  normal. GP29 needs no wiring — it sits on the onboard VSYS divider (R23/R24,
  100K each) and reads half the rail, so the example scales it back by 2. GP29
  is hard-wired to the supply; do **not** drive it externally.
- **09** with no I2C device attached returns an empty scan; that is normal.
- **10** needs **GP19 shorted to GP16**, otherwise it reads all 0x00/0xFF and
  reports "not shorted".
- **12** uses GP15 by default; change `PIN_KEY` at the top of the file to move it.

## Relation to the firmware

The examples only use the standard MicroPython modules (`machine`, `time`,
`utime`, `rp2`). No frozen module is required. The firmware enables USB MSC, so
the drive shows up and you can drag files in; the REPL is a separate USB CDC port.

If you hit `MemoryError`, call `gc.collect()` first, or use `mpremote run`, which
streams the file instead of storing it in RAM.
