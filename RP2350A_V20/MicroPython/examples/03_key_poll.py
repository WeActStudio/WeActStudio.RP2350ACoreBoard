# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  03_key_poll.py -- 外部按键轮询 / External key polling
#
#  功能 / Function:
#      每 1ms 轮询一次外部按键（默认 GP15），确认按下后翻转 LED(GP25)，
#      并打印累计按下次数与当前是否仍按住。
#      V20 板上没有用户按键，需要把按键一端接 GP15、另一端接 GND；
#      未接线时内部上拉使读数恒为 1，不会误触发。
#      Polls an external key (default GP15) every 1 ms, toggles LED (GP25) on
#      each confirmed press and prints the press count and whether it is still
#      held. V20 has no onboard user key: wire one leg to GP15 and the other to
#      GND. With nothing connected the internal pull-up keeps the pin at 1.
# =============================================================================

from machine import Pin
import time
import weact_board as wb


def main():
    wb.banner("03 外部按键轮询 / External key polling")

    led = wb.Led(wb.PIN_LED, "LED(GP25)")
    key = wb.Key(wb.PIN_KEY, debounce_ms=20)

    print("按键引脚/key pin = GP{}（另一端接 GND / other leg to GND）".format(wb.PIN_KEY))
    print("初始电平/initial level = {}".format(key.pin.value()))

    if not key.connected():
        print("提示/note: GP{} 读数不随上下拉变化，可能没有接按键。".format(wb.PIN_KEY))
        print("           the pin does not respond to pull-up/pull-down, no key wired.")

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
