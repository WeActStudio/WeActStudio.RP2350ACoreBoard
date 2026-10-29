# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  09_i2c_scan.py -- I2C 总线扫描 / I2C bus scan
#
#  功能 / Function:
#      每 2 秒在 I2C0（SDA=GP4，SCL=GP5，400kHz）上探测 0x08~0x77 的全部地址，
#      打印在线器件地址、扫描耗时，并尝试读取每个器件的首字节。
#      Every 2 seconds probe all addresses 0x08-0x77 on I2C0 (SDA=GP4, SCL=GP5,
#      400 kHz), print the devices found and the scan time, and try to read the
#      first byte from each device.
# =============================================================================

from machine import I2C, Pin
import time
import weact_board as wb


I2C_FREQ = 400000


def scan(i2c):
    """扫描 0x08~0x77 的所有地址，返回在线设备列表 / scan 0x08-0x77 and return the list of devices found."""
    found = []
    for addr in range(0x08, 0x78):
        try:
            i2c.writeto(addr, b"")
            found.append(addr)
        except OSError:
            pass
    return found


def main():
    wb.banner("09 I2C 总线扫描 / I2C bus scan")

    i2c = I2C(0, scl=Pin(wb.PIN_I2C0_SCL), sda=Pin(wb.PIN_I2C0_SDA),
              freq=I2C_FREQ)

    print("频率/frequency: {} Hz".format(I2C_FREQ))
    print("引脚/pins: SDA=GP{}  SCL=GP{}\n".format(
        wb.PIN_I2C0_SDA, wb.PIN_I2C0_SCL))

    while True:
        t0 = time.ticks_ms()
        devices = scan(i2c)
        elapsed = time.ticks_diff(time.ticks_ms(), t0)

        if devices:
            print("发现/found {} 个器件/devices（耗时/took {}ms）:".format(len(devices), elapsed))
            for addr in devices:
                try:
                    data = i2c.readfrom(addr, 1)
                    extra = "  首字节/first byte=0x{:02X}".format(data[0])
                except OSError:
                    extra = "  不支持直接读 / read not supported"
                print("  0x{:02X}{}".format(addr, extra))
        else:
            print("未发现器件 / no device found（耗时/took {}ms）".format(elapsed))

        print()
        time.sleep_ms(2000)


if __name__ == "__main__":
    wb.run_safely(main)
