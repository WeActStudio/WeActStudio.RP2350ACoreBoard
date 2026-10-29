# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  07_pwm_servo.py -- PWM 输出：舵机与蜂鸣器 / PWM output: servo and buzzer
#
#  功能 / Function:
#      在 GP20 上先输出 50Hz PWM，依次把舵机转到 0/45/90/135/180/90/0°；
#      再切换为 2~4kHz 方波，驱动无源蜂鸣器播放 8 个音阶。
#      脉宽与角度换算：0°=500us，180°=2500us，周期 20ms。
#      Drive a servo through 0/45/90/135/180/90/0 deg with 50 Hz PWM on GP20,
#      then output a 2-4 kHz square wave to play 8 notes on a passive buzzer.
#      Pulse width: 0 deg = 500 us, 180 deg = 2500 us, period 20 ms.
# =============================================================================

from machine import Pin, PWM
import time
import weact_board as wb


SERVO_PIN = 20          # 舵机/蜂鸣器信号脚 / servo and buzzer signal pin


def servo_duty(pulse_us, period_us=20000):
    """把脉宽（微秒）换算成 16 位占空比 / convert pulse width (us) to 16-bit duty."""
    return int(65535 * pulse_us // period_us)


def servo_angle(pwm, deg):
    """舵机转到指定角度 0~180° / move the servo to 0-180 deg."""
    deg = max(0, min(180, deg))
    pulse = 500 + (2500 - 500) * deg // 180      # 500us ~ 2500us
    pwm.duty_u16(servo_duty(pulse))
    return pulse


def demo_servo():
    pwm = PWM(Pin(SERVO_PIN))
    pwm.freq(50)                    # 舵机控制频率 50Hz / servo control frequency
    try:
        for deg in (0, 45, 90, 135, 180, 90, 0):
            pulse = servo_angle(pwm, deg)
            print("角度/angle {:3d}°  脉宽/pulse {}us  duty={}".format(
                deg, pulse, servo_duty(pulse)))
            time.sleep_ms(800)      # 等待舵机转到位 / wait for the servo to settle
    finally:
        pwm.deinit()


def demo_buzzer():
    pwm = PWM(Pin(SERVO_PIN))
    try:
        for f in (262, 294, 330, 349, 392, 440, 494, 523):   # 中音 Do~高音 Do / middle C to high C
            pwm.freq(f)
            pwm.duty_u16(32768)     # 50% 占空比 / 50% duty
            print("蜂鸣器/buzzer {} Hz".format(f))
            time.sleep_ms(300)
        pwm.duty_u16(0)
    finally:
        pwm.deinit()


def main():
    wb.banner("07 PWM 输出 / PWM output")
    print("信号脚/signal pin: GP{}\n".format(SERVO_PIN))

    print("--- 舵机扫描 / servo sweep ---")
    demo_servo()

    print("\n--- 蜂鸣器音阶 / buzzer scale ---")
    demo_buzzer()

    print("\n演示结束 / demo finished")


if __name__ == "__main__":
    wb.run_safely(main)
