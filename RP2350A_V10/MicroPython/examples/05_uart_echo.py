# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  05_uart_echo.py -- UART 回显 / UART echo
#
#  功能 / Function:
#      UART0（TX=GP0，RX=GP1，115200 8N1）收到多少字节就原样发回多少字节，
#      每次收发打印本次字节数、本次内容与累计收发量。
#      UART0 (TX=GP0, RX=GP1, 115200 8N1) sends back every byte it receives.
#      Each transfer prints the byte count, the data and the running totals.
# =============================================================================

from machine import UART, Pin
import time
import weact_board as wb


BAUD = 115200


def main():
    wb.banner("05 UART 回显 / UART echo")

    uart = UART(
        0,
        baudrate=BAUD,
        tx=Pin(wb.PIN_UART0_TX),
        rx=Pin(wb.PIN_UART0_RX),
        timeout=100,
    )
    print("配置/config: UART0 {} 8N1".format(BAUD))

    total_rx = 0
    total_tx = 0

    while True:
        n = uart.any()
        if n:
            data = uart.read(n)
            if data:
                uart.write(data)
                total_rx += len(data)
                total_tx += len(data)
                print("RX {:3d} 字节/bytes: {}   累计/accum RX={} TX={}".format(
                    len(data), repr(data), total_rx, total_tx))
        time.sleep_ms(10)


if __name__ == "__main__":
    wb.run_safely(main)
