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
#      每 500ms 采集一次 GP26/GP27/GP28/GP29 的 16 位 ADC 值并换算电压，
#      同时读取片内温度传感器，按手册公式 T = 27 - (V - 0.706) / 0.001721
#      换算成摄氏度，一并打印。
#      Sample the 16-bit ADC on GP26/GP27/GP28/GP29 every 500 ms and convert it
#      to volts; also read the internal temperature sensor and convert it with
#      T = 27 - (V - 0.706) / 0.001721. All values are printed together.
# =============================================================================

from machine import ADC, Pin
import time
import weact_board as wb


VREF = 3.3          # ADC 参考电压 / reference voltage


def read_voltage(adc):
    """读 ADC 并换算成电压 / read the ADC and convert to volts."""
    raw = adc.read_u16()            # 0~65535
    return raw, raw * VREF / 65535


def read_core_temp():
    """读片内温度（摄氏度）/ read the internal temperature in Celsius."""
    adc = ADC(ADC.CORE_TEMP)
    raw = adc.read_u16()
    volts = raw * VREF / 65535
    temp = 27 - (volts - 0.706) / 0.001721
    return raw, volts, temp


def main():
    wb.banner("08 ADC 读取 / ADC reading")

    adcs = [ADC(Pin(p)) for p in wb.ADC_PINS]

    while True:
        line = []
        for pin, adc in zip(wb.ADC_PINS, adcs):
            raw, v = read_voltage(adc)
            line.append("GP{}={:5d}({:.2f}V)".format(pin, raw, v))
        print("  ".join(line))

        raw_t, v_t, temp = read_core_temp()
        print("  片内温度/core temp: raw={:5d} {:.3f}V -> {:.1f}℃".format(raw_t, v_t, temp))
        print()

        time.sleep_ms(500)


if __name__ == "__main__":
    wb.run_safely(main)
