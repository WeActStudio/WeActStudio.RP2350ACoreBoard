# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  04_key_irq.py -- 按键硬件中断 / Key hardware interrupt
#
#  功能 / Function:
#      KEY(GP23) 下降沿触发中断，中断服务函数内累计次数并翻转 LED2(GP25)；
#      主循环每 50ms 一轮，定期打印心跳与计数。
#      The falling edge on KEY (GP23) triggers an ISR that counts the event and
#      toggles LED2 (GP25). The main loop runs every 50 ms and prints a heartbeat
#      with the counter.
# =============================================================================

from machine import Pin
import time
import weact_board as wb


def main():
    wb.banner("04 按键中断 / Key interrupt")

    led = wb.Led(wb.PIN_LED2, "LED2(绿/green)")
    key = wb.Key(wb.PIN_KEY)

    # 用 list 保存中断内需要修改的计数 / list keeps the counter mutable inside the ISR
    counter = [0]

    def on_press(pin):
        counter[0] += 1
        led.toggle()

    key.irq(on_press, Pin.IRQ_FALLING)

    last = 0
    tick = 0
    while True:
        tick += 1
        now = counter[0]
        if now != last:
            print("中断触发 {} 次（累计）/ ISR count {}  LED={}".format(now, now, led.value()))
            last = now
        if tick % 20 == 0:
            print("  [主循环心跳/heartbeat {}] LED={} 计数/count={}".format(
                tick, led.value(), counter[0]))
        time.sleep_ms(50)


if __name__ == "__main__":
    wb.run_safely(main)
