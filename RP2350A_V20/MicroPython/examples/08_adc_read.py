# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  08_adc_read.py -- ADC 读取 / ADC reading
#
#  功能 / Function:
#      每 500ms 采集一次 GP26/GP27/GP28 的 16 位 ADC 值并换算电压；
#      同时采集 GP29（板载 VSYS 分压）算回供电电压，读取片内温度传感器，
#      按手册公式 T = 27 - (V - 0.706) / 0.001721 换算成摄氏度。
#      Sample the 16-bit ADC on GP26/GP27/GP28 every 500 ms and convert it to
#      volts; also sample GP29 (the onboard VSYS divider) to derive the supply
#      rail, and read the internal temperature sensor with
#      T = 27 - (V - 0.706) / 0.001721.
#
#  关于 GP29 / About GP29:
#      排针上只有 GP26/GP27/GP28 三路自由 ADC。GP29_ADC3 在板上被 VSYS 检测
#      分压占用：R23/R24 两个 100K 串联分压，GP29 上得到的正好是 VSYS 的一半，
#      所以读出的电压要乘 2 才是真正的 VSYS。
#      GP29 不是"第 4 路排针 ADC"，它是固定接到电源上的，不要外接信号去推它。
#      Only GP26/GP27/GP28 are free ADC channels on the header. GP29_ADC3 is
#      wired to the VSYS sense divider (R23/R24, 100K each), so it always sees
#      exactly half of VSYS — multiply by 2 to get the rail. It is not a fourth
#      general-purpose channel; do not drive it externally.
#
#      量程余量：GP29 满量程 3.3V 对应 VSYS 6.6V，而 VSYS 正常工作范围是
#      2.8~5.8V，所以 5V USB 供电时读数约 2.5V（满量程的 76%），既没触顶也留了
#      余量；电池 3.7V 时约 1.85V，位置更靠中间。
#      Headroom: 3.3V full scale maps to 6.6V of VSYS, so a 5V USB rail reads
#      about 2.5V (76% of full scale) — not clipping, with margin to spare. On a
#      3.7V battery it reads about 1.85V, sitting closer to mid-scale.
#
#  接线 / Wiring:
#      GP26 / GP27 / GP28 接 0~3.3V 之间的信号，悬空时读数会飘属正常。
#      GP29 不需要接线，它测的是板子自己的供电。
#      Feed GP26/27/28 with anything between 0 and 3.3V; floating inputs drift,
#      which is expected. GP29 needs no wiring — it measures the board's own
#      supply rail.
# =============================================================================

from machine import ADC, Pin
import time
import weact_board as wb


VREF = wb.ADC_VREF_MV / 1000.0     # ADC 满量程，3.3V / full scale in volts


def read_avg(adc, samples=8):
    """多次采样取平均，压一点噪声 / average several samples to cut noise."""
    total = 0
    for _ in range(samples):
        total += adc.read_u16()
    return total // samples


def read_voltage(adc, samples=8):
    """读 ADC 并换算成电压 / read the ADC and convert it to volts."""
    raw = read_avg(adc, samples)      # 0~65535
    return raw, raw * VREF / 65535


def read_core_temp(adc):
    """读片内温度（摄氏度）/ read the internal temperature in Celsius."""
    raw = read_avg(adc)
    volts = raw * VREF / 65535
    temp = 27 - (volts - 0.706) / 0.001721
    return raw, volts, temp


def main():
    wb.banner("08 ADC 读取 / ADC reading")

    adcs = [ADC(Pin(p)) for p in wb.ADC_PINS]
    adc_vsys = ADC(Pin(wb.PIN_VSYS))
    adc_temp = ADC(ADC.CORE_TEMP)

    print("排针通道/header channels: {}".format(
        ", ".join("GP{}".format(p) for p in wb.ADC_PINS)))
    print("供电通道/supply channel : GP{} (VSYS, R23/R24 100K 分压, 比 {:g})".format(
        wb.PIN_VSYS, wb.VSYS_DIVIDER))
    print("参考电压/VREF           : {:.2f}V\n".format(VREF))

    while True:
        # --- 三路自由 ADC / three free channels -------------------------
        line = []
        for pin, adc in zip(wb.ADC_PINS, adcs):
            raw, v = read_voltage(adc)
            line.append("GP{}={:5d}({:.2f}V)".format(pin, raw, v))
        print("  ".join(line))

        # --- GP29：先算脚上电压，再乘分压比还原 VSYS --------------------
        # --- GP29: pin voltage first, then scale back to the VSYS rail ---
        raw_s, v_pin = read_voltage(adc_vsys)
        v_sys = v_pin * wb.VSYS_DIVIDER
        print("  GP{}= {:5d}({:.2f}V) x{:g} -> VSYS {:.2f}V  电源/{}".format(
            wb.PIN_VSYS, raw_s, v_pin, wb.VSYS_DIVIDER, v_sys,
            "USB" if wb.vbus_present() else "外部/external"))

        # --- 片内温度 / die temperature --------------------------------
        raw_t, v_t, temp = read_core_temp(adc_temp)
        print("  片内温度/core temp: raw={:5d} {:.3f}V -> {:.1f}℃".format(raw_t, v_t, temp))
        print()

        time.sleep_ms(500)


if __name__ == "__main__":
    wb.run_safely(main)
