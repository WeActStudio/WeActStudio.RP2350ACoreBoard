# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  10_spi_loopback.py -- SPI 自发自收回环测试 / SPI loopback test
#
#  功能 / Function:
#      在 SPI0（SCK=GP18，MOSI=GP19，MISO=GP16，CSN=GP17，Mode 0，MSB 先行）上，
#      分别以 100k / 1M / 4M 三种速率发送 32 字节 0x00~0x1F 并读回，
#      统计正确字节数并打印 PASS / FAIL。需用杜邦线短接 GP19 与 GP16。
#      On SPI0 (SCK=GP18, MOSI=GP19, MISO=GP16, CSN=GP17, mode 0, MSB first) send
#      32 bytes 0x00-0x1F at 100k / 1M / 4M, read them back, count the matching
#      bytes and print PASS / FAIL. GP19 must be wired to GP16.
# =============================================================================

from machine import SPI, Pin
import time
import weact_board as wb


TEST_SPEEDS = (100000, 1000000, 4000000)


def make_spi(freq):
    return SPI(
        0,
        baudrate=freq,
        polarity=0,          # CPOL=0
        phase=0,             # CPHA=0，即 Mode 0 / mode 0
        sck=Pin(wb.PIN_SPI0_SCK),
        mosi=Pin(wb.PIN_SPI0_MOSI),
        miso=Pin(wb.PIN_SPI0_MISO),
        firstbit=SPI.MSB,
    )


def test_speed(freq):
    """在指定速率下做一次 32 字节回环 / one 32-byte loopback at the given rate.

    返回 (成功字节数, 总字节数, 异常信息) / returns (matched, total, error).
    """
    spi = make_spi(freq)
    pattern = bytes(range(32))
    rx = bytearray(32)

    try:
        spi.write_readinto(pattern, rx)
    except Exception as e:
        return 0, 32, str(e)

    ok = sum(1 for a, b in zip(pattern, rx) if a == b)
    spi.deinit()
    return ok, 32, None


def main():
    wb.banner("10 SPI 回环测试 / SPI loopback")

    print("引脚/pins: SCK=GP{} MOSI=GP{} MISO=GP{}".format(
        wb.PIN_SPI0_SCK, wb.PIN_SPI0_MOSI, wb.PIN_SPI0_MISO))
    print("测试前请短接 GP{} 与 GP{} / wire GP{} to GP{} before running\n".format(
        wb.PIN_SPI0_MOSI, wb.PIN_SPI0_MISO,
        wb.PIN_SPI0_MOSI, wb.PIN_SPI0_MISO))

    while True:
        for freq in TEST_SPEEDS:
            ok, total, err = test_speed(freq)
            if err:
                print("{:8d} Hz : 异常/error {}".format(freq, err))
            elif ok == total:
                print("{:8d} Hz : PASS  {}/{} 字节正确/bytes ok".format(freq, ok, total))
            else:
                print("{:8d} Hz : FAIL  {}/{} 字节正确/bytes ok".format(freq, ok, total))
        print()
        time.sleep_ms(3000)


if __name__ == "__main__":
    wb.run_safely(main)
