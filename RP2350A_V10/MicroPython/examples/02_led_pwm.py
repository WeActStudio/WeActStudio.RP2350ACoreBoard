# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  02_led_pwm.py -- PWM 呼吸灯 / PWM breathing LED
#
#  功能 / Function:
#      LED2(GP25) 以 1kHz PWM 输出，占空比 0->100%->0 循环渐变，每 10 步打印一次。
#      LED2 (GP25) outputs 1 kHz PWM with the duty cycling 0 -> 100% -> 0 and
#      prints the duty every 10 steps.
# =============================================================================

from machine import Pin, PWM
import time
import weact_board as wb


def main():
    wb.banner("02 LED 呼吸灯 / Breathing LED")

    pwm = PWM(Pin(wb.PIN_LED2))
    pwm.freq(1000)          # 载波频率 / carrier frequency
    steps = 50
    step_ms = 20

    try:
        while True:
            # 渐亮 / fade in
            for i in range(steps + 1):
                duty = 65535 * i // steps
                pwm.duty_u16(duty)
                if i % 10 == 0:
                    print("渐亮/fade-in  duty={:5d}/65535 ({:3d}%)".format(
                        duty, duty * 100 // 65535))
                time.sleep_ms(step_ms)
            # 渐暗 / fade out
            for i in range(steps, -1, -1):
                duty = 65535 * i // steps
                pwm.duty_u16(duty)
                if i % 10 == 0:
                    print("渐暗/fade-out duty={:5d}/65535 ({:3d}%)".format(
                        duty, duty * 100 // 65535))
                time.sleep_ms(step_ms)
    finally:
        # 占空比归零并关闭 PWM，引脚恢复为普通输出低电平
        # zero the duty, stop PWM and restore the pin as a plain low output
        pwm.duty_u16(0)
        pwm.deinit()
        Pin(wb.PIN_LED2, Pin.OUT).value(0)


if __name__ == "__main__":
    wb.run_safely(main)
