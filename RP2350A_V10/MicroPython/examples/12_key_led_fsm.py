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
#      短按 KEY(GP23) 不足 800ms，模式按 常亮 -> 呼吸 -> 快闪 -> 慢闪 -> 熄灭
#      循环切换；按住满 800ms 直接切到熄灭。切换时打印当前模式序号与名称。
#      五种效果均通过 LED2(GP25) 的 PWM 占空比输出：常亮 65535、熄灭 0、
#      快闪与慢闪 0/65535 翻转（半周期 100ms / 600ms）、呼吸 0~65535 渐变
#      （每步 25ms，共 40 步）。
#      A short press (under 800 ms) cycles through steady on -> breathing ->
#      fast blink -> slow blink -> off; holding for 800 ms jumps to off. Each
#      switch prints the mode index and name. All five effects drive LED2 (GP25)
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

# 模式表：(名字, 效果类型, 参数)
MODES = (
    ("常亮", "static", 1),
    ("呼吸", "breath", 0),
    ("快闪", "blink", 100),
    ("慢闪", "blink", 600),
    ("熄灭", "static", 0),
)


class LedFx:
    """基于单路 PWM 的 LED 效果输出 / LED effects on a single PWM channel.

    所有效果均以占空比表示 / every effect is expressed as a duty value.
    """

    def __init__(self, pin, freq=1000):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self.pwm.duty_u16(0)
        self._level = 0          # 呼吸当前档位 0..BREATH_STEPS
        self._dir = 1
        self._on = False         # 闪烁当前相位
        self._t_step = time.ticks_ms()
        self._t_flip = time.ticks_ms()

    def _duty(self, d):
        self.pwm.duty_u16(d if d <= 65535 else 65535)

    def static(self, on):
        self._on = bool(on)
        self._duty(65535 if on else 0)

    def reset(self):
        """清零相位与输出 / reset phase and output."""
        self._level = 0
        self._dir = 1
        self._on = False
        self._t_step = self._t_flip = time.ticks_ms()
        self._duty(0)

    def step_breath(self, step_ms=BREATH_STEP_MS, steps=BREATH_STEPS):
        """推进一档呼吸亮度 / advance the breathing level by one step."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self._t_step) < step_ms:
            return
        self._t_step = now

        self._level += self._dir
        if self._level >= steps:
            self._level = steps
            self._dir = -1
        elif self._level <= 0:
            self._level = 0
            self._dir = 1

        # 按平方曲线输出，使亮度变化更均匀 / square-law curve for a smoother ramp
        lv = self._level * 100 // steps
        self._duty(65535 * lv * lv // 10000)

    def step_blink(self, half_ms):
        """按半周期翻转亮灭 / toggle on and off every half period."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self._t_flip) >= half_ms:
            self._t_flip = now
            self._on = not self._on
            self._duty(65535 if self._on else 0)

    def close(self):
        self._duty(0)
        self.pwm.deinit()


def main():
    wb.banner("12 按键切换 LED 模式 / LED mode switch")

    fx = LedFx(wb.PIN_LED2)
    key = wb.Key(wb.PIN_KEY, debounce_ms=20)

    st = {
        "idx": -1,
        "pending": False,        # 是否有一次按下尚未结算
        "t_down": 0,
    }

    def enter_mode(i):
        """切换到第 i 个模式。"""
        fx.reset()
        st["idx"] = i
        name, kind, param = MODES[i]

        if kind == "static":
            fx.static(param)

        print(">>> [{}/{}] {}".format(i + 1, len(MODES), name))

    enter_mode(0)

    while True:
        now = time.ticks_ms()

        # 按键：记录按下，结算短按 / 长按 · key: record press, settle short or long
        if key.update():
            st["pending"] = True
            st["t_down"] = now

        if st["pending"]:
            if not key.pressed():           # 已松开 / released
                held = time.ticks_diff(time.ticks_ms(), st["t_down"])
                st["pending"] = False
                if held < LONG_PRESS_MS:
                    enter_mode((st["idx"] + 1) % len(MODES))
            elif time.ticks_diff(now, st["t_down"]) >= LONG_PRESS_MS:
                st["pending"] = False
                print("长按/long press >= {}ms -> 熄灭/off".format(LONG_PRESS_MS))
                enter_mode(len(MODES) - 1)

        # 按当前模式刷新 LED / refresh the LED for the current mode
        name, kind, param = MODES[st["idx"]]
        if kind == "breath":
            fx.step_breath()
        elif kind == "blink":
            fx.step_blink(param)

        time.sleep_ms(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[已停止/stopped] 用户按下 Ctrl-C")
    finally:
        # 关闭 PWM，并把引脚恢复为普通输出低电平
        # stop PWM and restore the pin as a plain low output
        try:
            Pin(wb.PIN_LED2, Pin.OUT).value(0)
        except Exception:
            pass
