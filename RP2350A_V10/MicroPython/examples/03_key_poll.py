# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  03_key_poll.py -- 按键轮询 / Key polling
#
#  功能 / Function:
#      每 1ms 轮询一次 KEY(GP23)，确认按下后翻转 LED2(GP25)，
#      并打印累计按下次数与当前是否仍按住。
#      Polls KEY (GP23) every 1 ms, toggles LED2 (GP25) on each confirmed press
#      and prints the press count and whether the key is still held.
# =============================================================================

from machine import Pin
import time
import weact_board as wb


def main():
    wb.banner("03 按键轮询 / Key polling")

    led = wb.Led(wb.PIN_LED2, "LED2(绿/green)")
    key = wb.Key(wb.PIN_KEY, debounce_ms=20)

    print("初始电平 / initial level = {}".format(key.pin.value()))

    while True:
        # 确认按下时返回 True / returns True on a confirmed press
        if key.update():
            led.toggle()
            print("第 {:3d} 次按下 / press #{:d}  ->  LED={}  按住/held={}".format(
                key.count, key.count, led.value(),
                "是/yes" if key.pressed() else "否/no"))
        time.sleep_ms(1)


if __name__ == "__main__":
    wb.run_safely(main)
