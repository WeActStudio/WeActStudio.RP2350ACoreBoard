# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  weact_board.py -- WeAct Studio RP2350A Core V10 板级资源定义
#                    Board resources for WeAct Studio RP2350A Core V10
#
#  功能 / Function:
#      集中定义板载资源引脚编号，并提供 Led（GPIO 输出）、Key（按键消抖）、
#      leds_off（全部熄灭）、banner（打印板卡信息）、run_safely（异常保护）
#      等公共对象与函数，供所有例程引用。
#      Define the onboard pin numbers once and provide the shared helpers used by
#      every example: Led (GPIO output), Key (debounced key), leds_off, banner
#      and run_safely.
#
#  引脚定义 / Pin map:
#      LED1 = GP24（蓝/blue）  LED2 = GP25（绿/green） 高电平点亮 / active high
#      KEY  = GP23             低电平有效 / active low, internal pull-up
#      UART0: TX=GP0   RX=GP1
#      I2C0 : SDA=GP4  SCL=GP5
#      SPI0 : SCK=GP18 MOSI=GP19 MISO=GP16 CSN=GP17
#      ADC  : GP26 / GP27 / GP28 / GP29
# =============================================================================

from machine import Pin, PWM
import time

# ------------------------------------------------- 引脚编号 / pin numbers

PIN_LED1 = 24
PIN_LED2 = 25
PIN_KEY = 23

PIN_UART0_TX = 0
PIN_UART0_RX = 1

PIN_I2C0_SDA = 4
PIN_I2C0_SCL = 5

PIN_SPI0_SCK = 18
PIN_SPI0_MOSI = 19
PIN_SPI0_MISO = 16
PIN_SPI0_CSN = 17

ADC_PINS = (26, 27, 28, 29)

BOARD_NAME = "WeAct Studio RP2350A Core V10"

# 板载 LED 引脚 / onboard LED pins
LED_PINS = (PIN_LED1, PIN_LED2)


# ------------------------------------------------- LED 封装 / LED wrapper

class Led:
    """板载 LED 封装（高电平点亮）/ onboard LED wrapper (active high).

    方法 / methods: on(), off(), toggle(), value(),
    blink(times, period_ms) 闪烁 / blink N times, breath() PWM 渐变一次 / one PWM ramp.
    """

    def __init__(self, pin, name=None, active_high=True):
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
        pwm = PWM(self.pin)
        pwm.freq(1000)
        step_ms = period_ms // (steps * 2)
        for i in range(steps):
            pwm.duty_u16(int(65535 * i / steps))
            time.sleep_ms(step_ms)
        for i in range(steps, -1, -1):
            pwm.duty_u16(int(65535 * i / steps))
            time.sleep_ms(step_ms)
        pwm.deinit()
        self.off()
        return self

    def __repr__(self):
        return "<Led {} pin=GP{} state={}>".format(
            self.name, self.pin.id() if hasattr(self.pin, "id") else "?", self.value())


# ------------------------------------------------- KEY 封装 / key wrapper

class Key:
    """板载按键封装 / onboard key wrapper（GP23，低电平有效 / active low，20ms 消抖 / debounce）.

    方法 / methods: update() 推进消抖并返回是否新按下 / poll and report a new press,
    pressed() 当前是否按住 / is the key held, wait_press(timeout_ms) 阻塞等待 /
    block until pressed, irq() / irq_off() 挂载与卸载中断 / attach or detach the IRQ.
    属性 / attribute: count 为累计按下次数 / total press count.
    """

    def __init__(self, pin=PIN_KEY, debounce_ms=20, pull=Pin.PULL_UP):
        self.pin = Pin(pin, Pin.IN, pull)
        self.debounce_ms = debounce_ms
        self._last = self._raw()
        self._stable = self._last
        self._t_change = time.ticks_ms()
        self.count = 0

    def _raw(self):
        return self.pin.value()

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
                if self._stable == 0:      # 拉低为按下
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

def leds_off():
    """熄灭全部板载 LED / turn off every onboard LED."""
    for p in LED_PINS:
        Pin(p, Pin.OUT).value(0)


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
    """运行 fn / run fn，捕获 Ctrl-C 与异常 / catch Ctrl-C and exceptions，退出时熄灭 LED / LEDs off on exit."""
    try:
        fn()
    except KeyboardInterrupt:
        print("\n[已停止] 用户按下 Ctrl-C")
    except Exception as e:
        print("\n[异常] {}: {}".format(type(e).__name__, e))
    finally:
        leds_off()
