# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  11_timer_irq.py -- 定时器中断 / Timer interrupt
#
#  功能 / Function:
#      用软件定时器 Timer(-1) 每 500ms 触发一次回调，回调内翻转 LED(GP25)
#      并累加计数；主循环每 1300ms 打印已运行时间、理论触发次数、实际触发次数与偏差。
#      A software timer Timer(-1) fires every 500 ms; the callback toggles LED
#      (GP25) and increments a counter. The main loop prints, every 1300 ms, the
#      elapsed time, the expected count, the actual count and the difference.
# =============================================================================

from machine import Pin, Timer
import time
import weact_board as wb


PERIOD_MS = 500


def main():
    wb.banner("11 定时器中断 / Timer interrupt")

    led = wb.Led(wb.PIN_LED, "LED(GP25)")

    state = {"count": 0, "t0": time.ticks_ms()}

    def tick(t):
        """定时器回调函数 / timer callback."""
        state["count"] += 1
        led.toggle()

    tim = Timer(-1)
    tim.init(period=PERIOD_MS, mode=Timer.PERIODIC, callback=tick)

    print("周期/period = {}ms\n".format(PERIOD_MS))

    try:
        while True:
            time.sleep_ms(1300)
            elapsed = time.ticks_diff(time.ticks_ms(), state["t0"])
            expect = elapsed // PERIOD_MS
            got = state["count"]
            err = got - expect
            print("已运行/elapsed {:5d}ms  理论/expect {:3d}  实际/actual {:3d}  偏差/diff {:+d}".format(
                elapsed, expect, got, err))
    finally:
        tim.deinit()
        print("定时器已停止 / timer stopped")


if __name__ == "__main__":
    wb.run_safely(main)
