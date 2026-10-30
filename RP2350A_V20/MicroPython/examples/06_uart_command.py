# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  06_uart_command.py -- UART 命令行控制 / UART command line
#
#  功能 / Function:
#      UART0（TX=GP0，RX=GP1，115200 8N1）按行接收命令，解析后控制 LED(GP25)，
#      并把执行结果回发。接收时逐字符本地回显，支持退格，单行最多 64 字节。
#      支持命令：help / led / blink / status / gpio / info。
#      UART0 (TX=GP0, RX=GP1, 115200 8N1) receives one command per line, parses
#      it, drives LED (GP25) and sends the result back. Input is echoed per
#      character, backspace is supported, 64 bytes per line.
#      Commands: help / led / blink / status / gpio / info.
# =============================================================================

from machine import UART, Pin
import time
import weact_board as wb


BAUD = 115200

HELP_TEXT = """
---------------- 可用命令 / commands ----------------
  help                     显示本帮助 / show this help
  led on|off|toggle        LED (GP25)
  blink <次数/times> <间隔ms/period>   闪烁 / blink, e.g. blink 3 200
  status                   查询状态 / query status
  gpio <pin>               读一个 GPIO 电平 / read one GPIO level
  info                     板卡与固件信息 / board and firmware info
-----------------------------------------------------
"""


def main():
    wb.banner("06 UART 命令行 / UART command line")

    uart = UART(0, baudrate=BAUD,
                tx=Pin(wb.PIN_UART0_TX), rx=Pin(wb.PIN_UART0_RX), timeout=100)

    led = wb.Led(wb.PIN_LED, "LED")

    def send(msg):
        uart.write((msg + "\r\n").encode())

    def do_status():
        return "STATUS led={} freq={}MHz key=GP{} adc={}".format(
            led.value(), wb._freq_mhz(), wb.PIN_KEY, wb.ADC_PINS)

    def do_gpio(arg):
        try:
            gp = int(arg)
        except (TypeError, ValueError):
            return "ERR 用法/usage: gpio <pin>"
        if gp not in wb.HEADER_GPIOS:
            return "ERR GP{} 不在排针上 / not on the header，可用/use {}".format(
                gp, list(wb.HEADER_GPIOS))
        # 读之前先给内部上拉，悬空引脚不会读到随机值
        # enable pull-up first so a floating pin does not read randomly
        p = Pin(gp, Pin.IN, Pin.PULL_UP)
        time.sleep_ms(2)
        v = p.value()
        p.init(Pin.IN)
        return "OK GP{}={}".format(gp, v)

    def do_info():
        import os
        u = os.uname()
        st = os.statvfs("/")
        total = st[0] * st[2] // 1024
        free = st[0] * st[3] // 1024
        return "INFO {} / {} / 文件系统 {}KB 可用 {}KB".format(
            u.machine, u.version, total, free)

    def handle(line):
        """解析一行命令并返回响应字符串 / parse one line and return the reply."""
        parts = line.split()
        if not parts:
            return ""

        cmd = parts[0].lower()

        if cmd == "help":
            return HELP_TEXT

        if cmd == "led":
            if len(parts) < 2:
                return "ERR 用法/usage: led on|off|toggle"
            action = parts[1].lower()
            if action == "on":
                led.on()
            elif action == "off":
                led.off()
            elif action == "toggle":
                led.toggle()
            else:
                return "ERR 未知动作/unknown action '{}'，可用/use on/off/toggle".format(action)
            return "OK led -> {} (value={})".format(action, led.value())

        if cmd == "blink":
            if len(parts) < 3:
                return "ERR 用法/usage: blink <次数/times> <间隔ms/period>"
            try:
                times = int(parts[1])
                period = int(parts[2])
            except ValueError:
                return "ERR 参数必须是整数 / arguments must be integers"
            if not (1 <= times <= 20) or not (20 <= period <= 2000):
                return "ERR 范围/range: 次数/times 1~20，间隔/period 20~2000ms"
            led.blink(times, period)
            return "OK blink {} x {}ms".format(times, period)

        if cmd == "status":
            return do_status()

        if cmd == "gpio":
            return do_gpio(parts[1] if len(parts) > 1 else None)

        if cmd == "info":
            return do_info()

        return "ERR 未知命令/unknown command '{}'，发/send help".format(cmd)

    send("")
    send("WeAct RP2350A V20 UART 命令行就绪 / command line ready")
    send("发 help 查看命令 / send help to list commands")

    buf = b""
    while True:
        n = uart.any()
        if not n:
            time.sleep_ms(5)
            continue

        data = uart.read(n)
        if not data:
            continue

        for b in data:
            ch = bytes([b])
            if ch in (b"\r", b"\n"):
                # 行结束，按整行解析 / end of line, parse the whole line
                if buf:
                    line = buf.decode().strip()
                    buf = b""
                    if line:
                        print("CMD: {}".format(line))
                        resp = handle(line)
                        if resp:
                            send(resp)
            elif ch == b"\x08" or ch == b"\x7f":
                # 退格 / backspace
                buf = buf[:-1]
                send("\b \b")
            else:
                if len(buf) < 64:
                    buf += ch
                    send(ch.decode() if b < 128 else "?")


if __name__ == "__main__":
    wb.run_safely(main)
