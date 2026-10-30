# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  01_led_blink.py -- 板载 LED 闪烁 / Onboard LED blink
#
#  功能 / Function:
#      LED(GP25) 每 500ms 翻转一次电平，每次翻转打印计数与当前电平。
#      V20 只有一颗板载 LED，所以这里是单灯闪，不是 V10 的双灯交替。
#      LED (GP25) toggles every 500 ms; each toggle prints the tick count and the
#      current level. V20 has a single onboard LED, so this is a single-LED blink
#      rather than the alternating pair used on V10.
# =============================================================================

from machine import Pin
import time
import weact_board as wb


def main():
    wb.banner("01 LED 闪烁 / LED blink")

    led = wb.Led(wb.PIN_LED, "LED(GP25)")

    n = 0
    while True:
        led.toggle()
        n += 1
        print("tick {:3d}  LED={}".format(n, led.value()))
        time.sleep_ms(500)


if __name__ == "__main__":
    wb.run_safely(main)
