# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  12_key_led_fsm.py -- 按键切换 LED 工作模式（状态机）
#                       Key-driven LED mode state machine
#
#  功能 / Function:
#      外部按键（默认 GP15，另一端接 GND）短按不足 800ms，模式按
#      常亮 -> 呼吸 -> 快闪 -> 慢闪 -> 熄灭 循环切换；按住满 800ms 直接切到熄灭。
#      切换时打印当前模式序号与名称。
#      五种效果均通过 LED(GP25) 的单路 PWM 占空比输出：常亮 65535、熄灭 0、
#      快闪与慢闪 0/65535 翻转（半周期 100ms / 600ms）、呼吸 0~65535 渐变
#      （每步 25ms，共 40 步）。
#      A short press (under 800 ms) cycles through steady on -> breathing ->
#      fast blink -> slow blink -> off; holding for 800 ms jumps to off. Each
#      switch prints the mode index and name. All five effects drive LED (GP25)
#      through a single PWM duty: 65535 for steady on, 0 for off, 0/65535 toggle
#      for blinking (100 ms / 600 ms half period) and a 0-65535 ramp for
#      breathing (25 ms per step, 40 steps).
# =============================================================================

from machine import Pin, PWM
import time
import weact_board as wb


LONG_PRESS_MS = 800
BREATH_STEP_MS = 25
BREATH_STEPS = 40
TICK_MS = 5                 # 主循环节拍 / main loop tick

# 模式表：(名字, 效果类型, 参数)
MODES = (
    ("常亮/steady", "static", 1),
    ("呼吸/breath", "breath", 0),
    ("快闪/fast", "blink", 100),
    ("慢闪/slow", "blink", 600),
    ("熄灭/off", "static", 0),
)


class LedFx:
    """基于单路 PWM 的 LED 效果输出 / LED effects on a single PWM channel.

    所有效果均以占空比表示，step() 由主循环按 TICK_MS 调用推进。
    Every effect is expressed as a duty value; step() is called from the main
    loop every TICK_MS to advance it.
    """

    def __init__(self, pin, freq=1000):
        self.pin_no = pin
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self.duty(0)
        self.mode = 0
        self._kind = "static"
        self._arg = 0
        self._level = 0          # 呼吸当前档位 0..BREATH_STEPS
        self._dir = 1
        self._on = False         # 闪烁当前相位
        self._t_step = time.ticks_ms()
        self._t_flip = time.ticks_ms()

    def duty(self, d):
        self.pwm.duty_u16(0 if d < 0 else (65535 if d > 65535 else d))

    def set_mode(self, idx):
        """切换模式并复位内部相位 / switch mode and reset the internal phase."""
        self.mode = idx % len(MODES)
        name, kind, arg = MODES[self.mode]
        self._kind = kind
        self._arg = arg
        self._level = 0
        self._dir = 1
        self._on = False
        self._t_step = time.ticks_ms()
        self._t_flip = time.ticks_ms()
        if kind == "static":
            self.duty(65535 if arg else 0)
        else:
            self.duty(0)
        return name

    def step(self):
        """按当前效果推进一帧 / advance one frame of the current effect."""
        now = time.ticks_ms()

        if self._kind == "blink":
            if time.ticks_diff(now, self._t_flip) >= self._arg:
                self._t_flip = now
                self._on = not self._on
                self.duty(65535 if self._on else 0)

        elif self._kind == "breath":
            if time.ticks_diff(now, self._t_step) >= BREATH_STEP_MS:
                self._t_step = now
                self._level += self._dir
                if self._level >= BREATH_STEPS:
                    self._level = BREATH_STEPS
                    self._dir = -1
                elif self._level <= 0:
                    self._level = 0
                    self._dir = 1
                self.duty(65535 * self._level // BREATH_STEPS)

    def stop(self):
        self.duty(0)
        self.pwm.deinit()
        Pin(self.pin_no, Pin.OUT).value(0)


def main():
    wb.banner("12 按键切换 LED 模式 / Key-driven LED FSM")

    key = wb.Key(wb.PIN_KEY, debounce_ms=20)
    fx = LedFx(wb.PIN_LED)
    print("按键/key = GP{}（另一端接 GND / other leg to GND）".format(wb.PIN_KEY))
    print("短按切换模式，长按 {}ms 熄灭\n".format(LONG_PRESS_MS))

    name = fx.set_mode(0)
    print("模式/mode 0: {}".format(name))

    t_press = None           # 按下时刻 / moment of the press

    try:
        while True:
            # --- 按键状态机 / key state machine ---
            key.update()

            if key.pressed() and t_press is None:
                t_press = time.ticks_ms()
            elif not key.pressed() and t_press is not None:
                held = time.ticks_diff(time.ticks_ms(), t_press)
                t_press = None
                if held >= LONG_PRESS_MS:
                    name = fx.set_mode(len(MODES) - 1)      # 长按 -> 熄灭 / long press -> off
                    print("长按 {:<4d}ms -> 模式/mode {}: {}".format(held, fx.mode, name))
                else:
                    name = fx.set_mode(fx.mode + 1)
                    print("短按 {:<4d}ms -> 模式/mode {}: {}".format(held, fx.mode, name))

            # --- 效果推进 / advance the effect ---
            fx.step()
            time.sleep_ms(TICK_MS)
    finally:
        fx.stop()


if __name__ == "__main__":
    wb.run_safely(main)
