# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  04_key_irq.py -- 按键中断 / Key interrupt
#
#  功能 / Function:
#      把外部按键（默认 GP15）配成下降沿中断，中断服务程序只置标志位，
#      主循环检测到标志后做 20ms 软件消抖、翻转 LED(GP25) 并打印次数。
#      这样既避免在 ISR 里做耗时操作，也能滤掉机械抖动造成的重复触发。
#      Configure the external key (default GP15) as a falling-edge interrupt. The
#      ISR only sets a flag; the main loop debounces for 20 ms, toggles LED (GP25)
#      and prints the count. This keeps the ISR short and filters contact bounce.
# =============================================================================

from machine import Pin
import time
import weact_board as wb


DEBOUNCE_MS = 20


def main():
    wb.banner("04 按键中断 / Key interrupt")

    led = wb.Led(wb.PIN_LED, "LED(GP25)")

    flag = {"hit": False, "t": 0}

    def on_falling(pin):
        """中断服务程序：只记录事件 / ISR: record the event only."""
        flag["hit"] = True
        flag["t"] = time.ticks_ms()

    key = wb.Key(wb.PIN_KEY, debounce_ms=DEBOUNCE_MS)
    key.irq(on_falling, Pin.IRQ_FALLING)

    print("按键/key = GP{}  触发/trigger = 下降沿/falling".format(wb.PIN_KEY))
    print("等待按键 / waiting for a press ...\n")

    n = 0
    try:
        while True:
            if flag["hit"]:
                flag["hit"] = False
                # 抖动可能在同一毫秒内产生多次中断，用 20ms 窗口合并
                # bounce can fire several IRQs within a millisecond; merge them
                time.sleep_ms(DEBOUNCE_MS)
                if key.pin.value() == 0:
                    n += 1
                    led.toggle()
                    print("中断 {}/irq #{:<3d} LED={}  距上次/flags t={}ms".format(
                        n, n, led.value(), flag["t"]))
            time.sleep_ms(1)
    finally:
        key.irq_off()


if __name__ == "__main__":
    wb.run_safely(main)
