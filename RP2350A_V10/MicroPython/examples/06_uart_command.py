# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
#  06_uart_command.py -- UART 命令行控制 LED / UART command line for LEDs
#
#  功能 / Function:
#      UART0（TX=GP0，RX=GP1，115200 8N1）按行接收命令，解析后控制
#      LED1(GP24) / LED2(GP25)，并把执行结果回发。
#      支持命令：help / led1 / led2 / both / blink / status。
#      接收时逐字符本地回显，支持退格，单行最多 64 字节。
#      UART0 (TX=GP0, RX=GP1, 115200 8N1) receives one command per line, parses
#      it, drives LED1 (GP24) / LED2 (GP25) and sends the result back.
#      Commands: help / led1 / led2 / both / blink / status.
#      Input is echoed per character, backspace is supported, 64 bytes per line.
# =============================================================================

from machine import UART, Pin
import time
import weact_board as wb


BAUD = 115200

HELP_TEXT = """
---------------- 可用命令 / commands ----------------
  help                     显示本帮助 / show this help
  led1 on|off|toggle       LED1 (GP24 蓝/blue)
  led2 on|off|toggle       LED2 (GP25 绿/green)
  both on|off              两颗一起 / both LEDs
  blink <次数/times> <间隔ms/period>   闪烁 / blink, e.g. blink 3 200
  status                   查询状态 / query status
-----------------------------------------------------
"""


def main():
    wb.banner("06 UART 命令行 / UART command line")

    uart = UART(0, baudrate=BAUD,
                tx=Pin(wb.PIN_UART0_TX), rx=Pin(wb.PIN_UART0_RX), timeout=100)

    led1 = wb.Led(wb.PIN_LED1, "LED1")
    led2 = wb.Led(wb.PIN_LED2, "LED2")
    leds = {"led1": led1, "led2": led2, "both": None}

    def send(msg):
        uart.write((msg + "\r\n").encode())

    def do_status():
        return "STATUS led1={} led2={} freq={}MHz".format(
            led1.value(), led2.value(), wb._freq_mhz())

    def apply_led(name, action):
        targets = [led1, led2] if name == "both" else [leds[name]]
        for d in targets:
            if action == "on":
                d.on()
            elif action == "off":
                d.off()
            elif action == "toggle":
                d.toggle()
            else:
                return "ERR 未知动作/unknown action '{}'，可用/use on/off/toggle".format(action)
        return "OK {} -> {}".format(name, action)

    def handle(line):
        """解析一行命令并返回响应字符串。"""
        parts = line.split()
        if not parts:
            return ""

        cmd = parts[0].lower()

        if cmd == "help":
            return HELP_TEXT

        if cmd in ("led1", "led2", "both"):
            if len(parts) < 2:
                return "ERR 用法/usage: {} on|off|toggle".format(cmd)
            return apply_led(cmd, parts[1].lower())

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
            led2.blink(times, period)
            return "OK blink {} x {}ms".format(times, period)

        if cmd == "status":
            return do_status()

        return "ERR 未知命令/unknown command '{}'，发/send help".format(cmd)

    send("")
    send("WeAct RP2350A V10 UART 命令行就绪 / command line ready")
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
                # 行结束，按整行解析
                if buf:
                    line = buf.decode().strip()
                    buf = b""
                    if line:
                        print("CMD: {}".format(line))
                        resp = handle(line)
                        if resp:
                            send(resp)
            elif ch == b"\x08" or ch == b"\x7f":
                # 退格
                buf = buf[:-1]
                send("\b \b")
            else:
                if len(buf) < 64:
                    buf += ch
                    send(ch.decode() if b < 128 else "?")


if __name__ == "__main__":
    wb.run_safely(main)
