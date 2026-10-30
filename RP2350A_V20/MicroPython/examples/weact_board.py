# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  weact_board.py -- WeAct Studio RP2350A Core V20 板级资源定义
#                    Board resources for WeAct Studio RP2350A Core V20
#
#  功能 / Function:
#      集中定义板载资源引脚编号，并提供 Led（GPIO/PWM 输出）、Key（外部按键
#      消抖）、led_off（熄灭）、banner（打印板卡信息）、run_safely（异常保护）
#      等公共对象与函数，供所有例程引用。
#      Define the onboard pin numbers once and provide the shared helpers used by
#      every example: Led (GPIO/PWM output), Key (debounced external key),
#      led_off, banner and run_safely.
#
#  与 V10 的差异 / differences from V10:
#      V20 是 Pico 2 尺寸的板子，只引出一颗 LED，没有板载用户按键。
#      LED  = GP25（高电平点亮 / active high）
#      KEY  = 无板载按键；例程默认使用外接按键接 GP15 与 GND
#             no onboard key; the examples use an external key on GP15 to GND
#      UART0: TX=GP0   RX=GP1
#      I2C0 : SDA=GP4  SCL=GP5
#      SPI0 : SCK=GP18 MOSI=GP19 MISO=GP16 CSN=GP17
#      ADC  : GP26 / GP27 / GP28 引到排针 / on the header
#      VSYS : GP29_ADC3，100K/100K 分压（分压比 2）/ 100K-100K divider, ratio 2
#      VBUS : GP24，100K/100K 分压，当数字输入读，高 = USB 供电在
#             100K-100K divider, read as a digital input, high = USB power present
# =============================================================================

from machine import Pin, PWM
import time

# ------------------------------------------------- 引脚编号 / pin numbers

PIN_LED = 25

# 外部按键默认接 GP15（40 pin 排针第 20 脚），另一端接 GND
# external key defaults to GP15 (header pin 20), the other leg goes to GND
PIN_KEY = 15

PIN_UART0_TX = 0
PIN_UART0_RX = 1

PIN_I2C0_SDA = 4
PIN_I2C0_SCL = 5

PIN_SPI0_SCK = 18
PIN_SPI0_MOSI = 19
PIN_SPI0_MISO = 16
PIN_SPI0_CSN = 17

# V20 排针上只有 3 路 ADC / only 3 ADC channels reach the header
ADC_PINS = (26, 27, 28)

# GP29_ADC3 被板载 VSYS 分压占用，不再引出到排针
# GP29_ADC3 is taken by the onboard VSYS divider, so it is not on the header
PIN_VSYS = 29
PIN_VBUS = 24

# 两个监测电路都是 100K/100K，引脚电压 = 实际电压 / 2
# both monitors are 100K/100K, so pin voltage = rail voltage / 2
VSYS_DIVIDER = 2.0
VBUS_DIVIDER = 2.0

# ADC 参考电压 / ADC full-scale voltage, in millivolts
ADC_VREF_MV = 3300

# 排针引出的全部 GPIO / every GPIO available on the 40-pin header
HEADER_GPIOS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                16, 17, 18, 19, 20, 21, 22, 26, 27, 28)

BOARD_NAME = "WeAct Studio RP2350A Core V20"

# 板载 LED 引脚 / onboard LED pins
LED_PINS = (PIN_LED,)


# ------------------------------------------------- LED 封装 / LED wrapper

class Led:
    """板载 LED 封装（高电平点亮）/ onboard LED wrapper (active high).

    方法 / methods: on(), off(), toggle(), value(),
    blink(times, period_ms) 闪烁 / blink N times, breath() PWM 渐变一次 / one PWM ramp.
    """

    def __init__(self, pin=PIN_LED, name=None, active_high=True):
        self.pin_no = pin
        self.pin = Pin(pin, Pin.OUT)
        self.name = name or "LED@GP{}".format(pin)
        self._on_level = 1 if active_high else 0
        self.off()

    def on(self):
        self.pin.value(self._on_level)
        return self

    def off(self):
        self.pin.value(1 - self._on_level)
        return self

    def toggle(self):
        self.pin.value(1 - self.pin.value())
        return self

    def value(self, v=None):
        if v is None:
            return 1 if self.pin.value() == self._on_level else 0
        return self.on() if v else self.off()

    def blink(self, times=1, period_ms=200):
        """闪 times 次 / blink N times，亮灭各 period_ms，结束后熄灭 / ends off."""
        for _ in range(times):
            self.on()
            time.sleep_ms(period_ms)
            self.off()
            time.sleep_ms(period_ms)
        return self

    def breath(self, period_ms=2000, steps=40):
        """PWM 由暗到亮再到暗渐变一次 / one PWM ramp up and down，结束后熄灭 / ends off."""
        pwm = PWM(Pin(self.pin_no))
        pwm.freq(1000)
        step_ms = max(1, period_ms // (steps * 2))
        for i in range(steps):
            pwm.duty_u16(int(65535 * i / steps))
            time.sleep_ms(step_ms)
        for i in range(steps, -1, -1):
            pwm.duty_u16(int(65535 * i / steps))
            time.sleep_ms(step_ms)
        pwm.deinit()
        self.pin = Pin(self.pin_no, Pin.OUT)
        self.off()
        return self

    def __repr__(self):
        return "<Led {} pin=GP{} state={}>".format(self.name, self.pin_no, self.value())


# ------------------------------------------------- KEY 封装 / key wrapper

class Key:
    """外部按键封装 / external key wrapper（默认 GP15，低电平有效 / active low，20ms 消抖 / debounce）.

    V20 没有板载用户按键，需要把按键一端接 GP15、另一端接 GND。
    内部上拉保证未接线时读到 1，不会产生假触发。
    V20 has no onboard user key: wire one leg to GP15 and the other to GND. The
    internal pull-up keeps the pin at 1 when nothing is connected, so an open
    header never produces phantom presses.

    方法 / methods: update() 推进消抖并返回是否新按下 / poll and report a new press,
    pressed() 当前是否按住 / is the key held, wait_press(timeout_ms) 阻塞等待 /
    block until pressed, irq() / irq_off() 挂载与卸载中断 / attach or detach the IRQ.
    属性 / attribute: count 为累计按下次数 / total press count.
    """

    def __init__(self, pin=PIN_KEY, debounce_ms=20, pull=Pin.PULL_UP):
        self.pin_no = pin
        self.pin = Pin(pin, Pin.IN, pull)
        self.debounce_ms = debounce_ms
        self._last = self._raw()
        self._stable = self._last
        self._t_change = time.ticks_ms()
        self.count = 0

    def _raw(self):
        return self.pin.value()

    def connected(self, probe_ms=30):
        """粗测按键是否接着 / rough check whether a key is wired.

        把引脚切成上拉再切下拉：接了按键到 GND 时两种模式读数不同；
        悬空引脚两次都是 1。返回值只作提示，不作为唯一判据。
        Switch pull-up then pull-down: a key to GND changes the reading, a
        floating pin reads 1 both times. The result is a hint, not a verdict.
        """
        p = Pin(self.pin_no, Pin.IN, Pin.PULL_UP)
        time.sleep_ms(probe_ms)
        up = p.value()
        p = Pin(self.pin_no, Pin.IN, Pin.PULL_DOWN)
        time.sleep_ms(probe_ms)
        dn = p.value()
        self.pin = Pin(self.pin_no, Pin.IN, Pin.PULL_UP)
        return up != dn

    def update(self):
        """推进一次消抖判断 / one debounce step，返回是否有新的按下事件 / returns True on a new press."""
        raw = self._raw()
        now = time.ticks_ms()
        if raw != self._last:
            self._last = raw
            self._t_change = now
        elif time.ticks_diff(now, self._t_change) >= self.debounce_ms:
            if raw != self._stable:
                self._stable = raw
                if self._stable == 0:      # 拉低为按下 / low means pressed
                    self.count += 1
                    return True
        return False

    def pressed(self):
        """当前是否处于按下状态 / whether the key is held（消抖后 / after debounce）."""
        return self._stable == 0

    def wait_press(self, timeout_ms=None):
        """阻塞等待按下 / block until pressed. 返回 True，超时返回 False / False on timeout."""
        t0 = time.ticks_ms()
        while True:
            if self.update():
                return True
            if timeout_ms is not None and \
                    time.ticks_diff(time.ticks_ms(), t0) >= timeout_ms:
                return False
            time.sleep_ms(1)

    def irq(self, handler, trigger=Pin.IRQ_FALLING):
        """把按键挂到硬件中断 / attach the key to a hardware IRQ，下降沿为按下 / falling edge."""
        self.pin.irq(handler=handler, trigger=trigger)
        return self

    def irq_off(self):
        self.pin.irq(handler=None)
        return self


# ------------------------------------------------- 便捷函数 / helpers

def led_off():
    """熄灭板载 LED / turn off the onboard LED."""
    Pin(PIN_LED, Pin.OUT).value(0)


# 兼容 V10 的命名 / keep the V10 name working
def leds_off():
    led_off()


# ------------------------------------------------- 电源监测 / power monitors

def vsys_raw(samples=8):
    """读 VSYS 分压后的 ADC 原始值（多次平均）/ averaged raw ADC of the VSYS divider."""
    from machine import ADC
    adc = ADC(PIN_VSYS)
    total = 0
    for _ in range(samples):
        total += adc.read_u16()
    return total // samples


def vsys_voltage(samples=8):
    """VSYS 实际电压，单位 V / VSYS rail voltage in volts.

    GP29 上只有 VSYS 的一半（100K/100K），所以要乘回分压比。
    GP29 sees half of VSYS through the 100K/100K divider, so scale it back up.
    """
    raw = vsys_raw(samples)
    return raw * (ADC_VREF_MV / 1000.0) * VSYS_DIVIDER / 65535


def vbus_present(samples=3):
    """VBUS 是否有电，即 USB 是否插着 / True when USB power is present on VBUS.

    GP24 不是 ADC 引脚，只能当数字输入：分压后的 2.5V 远高于 VIH。
    GP24 is not an ADC pin, so it is read as a digital input; the divided
    2.5V sits well above VIH.
    """
    p = Pin(PIN_VBUS, Pin.IN)
    high = 0
    for _ in range(samples):
        if p.value():
            high += 1
    return high > samples // 2


def power_report(samples=8):
    """返回 (VSYS 电压, VBUS 是否存在) / returns (vsys_volts, vbus_present)."""
    return vsys_voltage(samples), vbus_present()


def banner(title=""):
    """打印标题与板卡信息 / print the title and board information."""
    line = "=" * 56
    print()
    print(line)
    if title:
        print(" " + title)
        print(line)
    print(" 板卡: {}".format(BOARD_NAME))
    print(" 主频: {} MHz".format(_freq_mhz()))
    print(line)


def _freq_mhz():
    try:
        from machine import freq
        return freq() // 1000000
    except Exception:
        return 0


def run_safely(fn):
    """运行 fn / run fn，捕获 Ctrl-C 与异常 / catch Ctrl-C and exceptions，退出时熄灭 LED / LED off on exit."""
    try:
        fn()
    except KeyboardInterrupt:
        print("\n[已停止] 用户按下 Ctrl-C")
    except Exception as e:
        print("\n[异常] {}: {}".format(type(e).__name__, e))
    finally:
        led_off()
