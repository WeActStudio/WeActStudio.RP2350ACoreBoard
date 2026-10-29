# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  01_led_blink.py -- 板载 LED 交替闪烁 / Onboard LED alternating blink
#
#  功能 / Function:
#      LED1(GP24) 与 LED2(GP25) 每 500ms 同时翻转电平，两灯交替亮灭，
#      每次翻转打印一次计数与当前电平。
#      LED1 (GP24) and LED2 (GP25) toggle together every 500 ms, so the two LEDs
#      alternate on and off. Each toggle prints the tick count and current levels.
# =============================================================================

from machine import Pin
import time
import weact_board as wb


def main():
    wb.banner("01 LED 闪烁 / LED blink")

    led1 = wb.Led(wb.PIN_LED1, "LED1(蓝/blue)")
    led2 = wb.Led(wb.PIN_LED2, "LED2(绿/green)")

    n = 0
    while True:
        led1.toggle()
        led2.toggle()
        n += 1
        print("tick {:3d}  LED1={}  LED2={}".format(n, led1.value(), led2.value()))
        time.sleep_ms(500)


if __name__ == "__main__":
    wb.run_safely(main)
