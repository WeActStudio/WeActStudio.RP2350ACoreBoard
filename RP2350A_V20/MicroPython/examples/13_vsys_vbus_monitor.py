# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  13_vsys_vbus_monitor.py -- 监测 VSYS 电压与 VBUS 供电
#                             Monitor the VSYS rail and VBUS presence
#
#  功能 / Function:
#      V20 上这两路电源都有 100K/100K 分压网络，因此都能被 MCU 读到：
#      Both rails on V20 have a 100K/100K divider, so the MCU can observe them:
#        VSYS -> GP29_ADC3，ADC 读分压值 ×2 还原实际电压
#                VSYS -> GP29_ADC3, ADC reading x2 gives the rail voltage
#        VBUS -> GP24，当数字输入读，高电平 = USB 供电存在
#                VBUS -> GP24, read as a digital input, high = USB power present
#
#      程序每 500ms 采样一次，打印 VSYS 电压（V）与 VBUS 状态（插入/未插入），
#      并在插拔瞬间与电压越界时给出提示。LED 作为 1Hz 心跳，说明程序还活着。
#      Every 500 ms it prints the VSYS voltage and whether VBUS is present, and
#      flags plug/unplug events plus out-of-range readings. The LED blinks at
#      1 Hz as a heartbeat so you can tell the loop is still running.
#
#  接线 / Wiring:
#      无需外部接线。VSYS 分压接 GP29，VBUS 分压接 GP24，都在板上。
#      Nothing to wire: both dividers are on the board.
#
#  提示 / Notes:
#      GP29 被 VSYS 占用后不再是通用 IO，GP24 同理只做 VBUS 检测。
#      GP29 is no longer a free GPIO once the VSYS divider is fitted, and GP24
#      is dedicated to VBUS sensing.
# =============================================================================

import time
import weact_board as wb

SAMPLE_MS = 500
HEARTBEAT_MS = 500

# 电压门限 / voltage thresholds
VSYS_LOW = 3.0      # 低于此值认为供电不足 / below this the rail is sagging
VSYS_USB_MAX = 4.5  # USB 供电时 VSYS 约为 4.4-4.7V / VSYS sits near 4.4-4.7V on USB
VSYS_HIGH = 5.6     # 高于此值不正常 / anything above this is suspicious


def _verdict(vsys, vbus):
    """给出电压状态的文字结论 / plain-language verdict for the readings."""
    if vsys < 0.3:
        return "无供电 / no supply"
    if vsys < VSYS_LOW:
        return "低压 / low"
    if vsys > VSYS_HIGH:
        return "过高 / over-voltage"
    if vbus and vsys < VSYS_USB_MAX:
        return "USB 供电 / on USB power"
    if vbus:
        return "USB 供电 + 外部电源 / USB and external supply"
    return "电池或外部电源 / battery or external supply"


def main():
    wb.banner("13 VSYS / VBUS 电源监测")
    print(" VSYS: GP{} (ADC, 分压比 {:g})".format(wb.PIN_VSYS, wb.VSYS_DIVIDER))
    print(" VBUS: GP{} (数字输入, 分压比 {:g})".format(wb.PIN_VBUS, wb.VBUS_DIVIDER))
    print()

    led = wb.Led()
    last_vbus = None
    last_beat = time.ticks_ms()

    while True:
        vsys, vbus = wb.power_report()

        # 插拔事件单独提示，方便对照 / flag plug events so they are easy to spot
        if last_vbus is not None and vbus != last_vbus:
            print(" [事件] VBUS {}".format("插入 / plugged in" if vbus else "拔出 / unplugged"))
        last_vbus = vbus

        print(" VSYS = {:.3f} V   VBUS = {:<3}  {}".format(
            vsys, "ON" if vbus else "OFF", _verdict(vsys, vbus)))

        # 心跳 / heartbeat
        now = time.ticks_ms()
        if time.ticks_diff(now, last_beat) >= HEARTBEAT_MS:
            led.toggle()
            last_beat = now

        time.sleep_ms(SAMPLE_MS)


if __name__ == "__main__":
    wb.run_safely(main)
