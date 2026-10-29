#!/usr/bin/env python3
"""mpy_sim.py -- 在 PC 上模拟这块板子跑一遍 fw_test.py
                Run fw_test.py on a simulated board.

用途 / Purpose:
    手边没有板子时，验证测试套件本身的逻辑（统计、协议输出、失败判定）；
    也可以放进 CI，防止改测试脚本时改坏解析格式。
    Verify the suite logic (counting, protocol output, failure detection) without
    a board, or run it in CI to catch broken parsing.

    不测任何硬件 / no hardware is tested：machine / rp2 / _thread 都换成假实现，
    "/" 开头的路径重定向到临时目录，不写入本机文件系统。
    machine / rp2 / _thread are replaced by stubs and absolute paths are
    redirected to a temporary directory.

用法 / Usage:
    python3 tools/mpy_sim.py --mb 16            # 16MB 板，全部正常 / all good
    python3 tools/mpy_sim.py --mb 4             # 4MB 板
    python3 tools/mpy_sim.py --mb 16 --flash 4  # 板名 16MB、实际 4MB → 应 FAIL
    python3 tools/mpy_sim.py --mb 16 --no-lcd   # 预留：外设缺失 / missing peripherals
"""

import argparse
import builtins
import os
import shutil
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
FW_TEST_DIR = os.path.dirname(HERE)


class Sim:
    def __init__(self, mb, flash_mb, uart_loop, spi_loop, i2c_dev):
        self.t_start = time.time()
        self.mb = mb
        self.flash_mb = flash_mb
        self.uart_loop = uart_loop
        self.spi_loop = spi_loop
        self.i2c_dev = i2c_dev
        self.tmp = tempfile.mkdtemp(prefix="mpysim_")
        self._orig = {}
        self.key_pressed = False

    # ---------------- 路径重定向 ----------------
    def _map(self, p):
        if isinstance(p, str) and p.startswith("/"):
            return os.path.join(self.tmp, p.lstrip("/"))
        return p

    def _key_down(self):
        # 0.3 秒后才"按下"，模拟人手按键而不是上电就按住
        return self.key_pressed and (time.time() - self.t_start) > 0.3

    def install(self):
        s = self

        # ---- time ----
        t0 = time.perf_counter()

        def ticks_us():
            return int((time.perf_counter() - t0) * 1e6)

        def ticks_ms():
            return int((time.perf_counter() - t0) * 1e3)

        time.ticks_us = ticks_us
        time.ticks_ms = ticks_ms
        time.ticks_diff = lambda a, b: a - b
        time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)

        # ---- sys.implementation ----
        # 只改属性，不整体替换，否则 importlib 的 cache_tag 会丢
        sys.implementation.version = (1, 29, 0)
        sys.implementation._mpy = 6

        # ---- os ----
        real = {
            "statvfs": os.statvfs, "remove": os.remove, "mkdir": os.mkdir,
            "rmdir": os.rmdir, "rename": os.rename, "listdir": os.listdir,
        }
        self._orig = dict(real)
        self._orig["open"] = builtins.open

        def fake_statvfs(path):
            total = (s.mb - 1) * 1024 * 1024
            bs = 512
            return (bs, bs, total // bs, (total // 2) // bs, (total // 2) // bs,
                    255, 0, 0, 0, 255)

        def fake_uname():
            return types.SimpleNamespace(
                sysname="rp2",
                nodename="rp2",
                release="1.29.0",
                version="v1.29.0 on 2026-10-29",
                machine="WeAct Studio RP2350A Core V10 ({}MB) with RP2350".format(s.mb))

        os.uname = fake_uname
        os.statvfs = fake_statvfs
        os.remove = lambda p: real["remove"](s._map(p))
        os.mkdir = lambda p: real["mkdir"](s._map(p))
        os.rmdir = lambda p: real["rmdir"](s._map(p))
        os.rename = lambda a, b: real["rename"](s._map(a), s._map(b))
        os.listdir = lambda p="/": [
            x for x in real["listdir"](s._map(p))
        ]

        # ---- open ----
        real_open = builtins.open

        def fake_open(file, *a, **kw):
            return real_open(s._map(file), *a, **kw)

        builtins.open = fake_open

        # ---- gc（CPython 没有 mem_free/mem_alloc）----
        import gc as _gc
        _gc.mem_free = lambda: 380 * 1024
        _gc.mem_alloc = lambda: 140 * 1024

        # ---- machine ----
        machine = types.ModuleType("machine")

        class Pin:
            OUT = 1
            IN = 0
            PULL_UP = 2
            PULL_DOWN = 3
            _state = {}

            def __init__(self, gp, mode=-1, pull=None):
                self.gp = gp
                self.mode = mode
                self.pull = pull
                if gp == 23 and pull == Pin.PULL_UP:
                    Pin._state[gp] = 0 if s._key_down() else 1

            def value(self, v=None):
                if v is not None:
                    Pin._state[self.gp] = v
                    return None
                if self.pull == Pin.PULL_UP:
                    return 1 if self.gp != 23 else (0 if s._key_down() else 1)
                if self.pull == Pin.PULL_DOWN:
                    return 0
                return Pin._state.get(self.gp, 0)

            def init(self, mode=-1, pull=None, **kw):
                self.mode = mode
                self.pull = pull

            def __call__(self, v=None):
                return self.value(v)

        class ADC:
            CORE_TEMP = 4

            def __init__(self, ch):
                self.ch = ch

            def read_u16(self):
                if self.ch == ADC.CORE_TEMP:
                    return int((0.706 + 0.02) / 3.3 * 65535)
                return [21000, 33000, 47000, 52000][self.ch % 4]

        class PWM:
            def __init__(self, pin):
                self._f = 1000
                self._d = 0

            def freq(self, v=None):
                if v is not None:
                    self._f = v
                    return None
                return self._f

            def duty_u16(self, v=None):
                if v is not None:
                    self._d = v
                    return None
                return self._d

            def deinit(self):
                pass

        class Timer:
            PERIODIC = 1
            ONE_SHOT = 0

            def __init__(self, id=-1, **kw):
                self._cb = None
                self._freq = 0
                self._on = False

            def init(self, mode=1, freq=1000, callback=None, **kw):
                self._cb = callback
                self._freq = freq
                self._on = True
                # 由 sleep 驱动：这里直接给个合理计数
                import threading

                def ticker():
                    period = 1.0 / max(1, freq)
                    while self._on:
                        time.sleep(period)
                        if not self._on:
                            break
                        if self._cb:
                            self._cb(self)

                threading.Thread(target=ticker, daemon=True).start()

            def deinit(self):
                self._on = False

        class UART:
            def __init__(self, id, **kw):
                pass

            def write(self, b):
                pass

            def read(self, n=None):
                return b"FWLOOP" if s.uart_loop else None

            def deinit(self):
                pass

        class SPI:
            def __init__(self, id, **kw):
                pass

            def write_readinto(self, tx, rx):
                if s.spi_loop:
                    rx[:] = bytes(tx)
                else:
                    for i in range(len(rx)):
                        rx[i] = 0

            def deinit(self):
                pass

        class I2C:
            def __init__(self, id, **kw):
                pass

            def scan(self):
                return [0x3C, 0x68] if s.i2c_dev else []

            def deinit(self):
                pass

        class USBDevice:
            BUILTIN_DEFAULT = 0

            def active(self, v=None):
                return True

        machine.Pin = Pin
        machine.ADC = ADC
        machine.PWM = PWM
        machine.Timer = Timer
        machine.UART = UART
        machine.SPI = SPI
        machine.I2C = I2C
        machine.USBDevice = USBDevice
        machine.freq = lambda: 150000000
        machine.unique_id = lambda: b"\xe6\x60\x38\x12\x34\x56\x78\x90"
        machine.reset_cause = lambda: 1
        sys.modules["machine"] = machine

        # ---- rp2 ----
        rp2 = types.ModuleType("rp2")

        class Flash:
            # 与真实固件语义对齐（rp2_flash.c）：
            #   rp2.Flash() = 文件系统分区，不是整片 Flash
            #   flash_size = 实际Flash - 1MB(固件预留)
            #   ioctl(4)*ioctl(5) 返回这个分区大小
            FS_RESERVE = 1024 * 1024

            def __init__(self, start=-1, length=-1):
                self.total = s.flash_mb * 1024 * 1024
                self.size = self.total - Flash.FS_RESERVE
                self.base = Flash.FS_RESERVE

            def ioctl(self, cmd, arg):      # 与固件一致：arg 必须传
                if cmd == 4:
                    return self.size // 4096
                if cmd == 5:
                    return 4096
                return 0

            def readblocks(self, blk, buf):
                off = blk * 4096
                n = len(buf)
                if off >= 4096:
                    # 第 0 块以外的数据区：填充可辨识内容
                    for i in range(n):
                        buf[i] = (0xA5 + i) & 0xFF
                    return 0
                # 第 0 块：生成一个合法 FAT16 引导扇区，供 T03/T04 解析
                boot = bytearray(4096)
                boot[0:3] = b"\xEB\xFE\x90"          # jmp + nop
                boot[3:11] = b"MSDOS5.0"             # OEM 名
                bps = 4096
                spc = 1
                tot = self.size // bps              # 分区总扇区数（与本模拟分区一致）
                boot[11:13] = bps.to_bytes(2, "little")
                boot[13] = spc
                boot[14:16] = (32).to_bytes(2, "little")     # 保留扇区
                boot[16] = 2                                  # FAT 数
                boot[17:19] = (512).to_bytes(2, "little")    # 根目录项数
                boot[19:21] = (0).to_bytes(2, "little")      # TotSec16=0 → 用 TotSec32
                boot[21] = 0xF8                               # 介质描述符
                boot[22:24] = (0).to_bytes(2, "little")
                boot[24:26] = (32).to_bytes(2, "little")     # 每道扇区数
                boot[26:28] = (64).to_bytes(2, "little")     # 磁头数
                boot[28:32] = (0).to_bytes(4, "little")
                boot[32:36] = tot.to_bytes(4, "little")      # TotSec32
                boot[36] = 0x80                               # 驱动器号
                boot[510] = 0x55
                boot[511] = 0xAA
                for i in range(n):
                    buf[i] = boot[i] if i < len(boot) else 0
                return 0

        rp2.Flash = Flash
        sys.modules["rp2"] = rp2

        # ---- _thread ----
        import threading
        th = types.ModuleType("_thread")
        th.start_new_thread = lambda fn, args: threading.Thread(
            target=fn, args=args, daemon=True).start()
        th.stack_size = lambda n: None
        sys.modules["_thread"] = th

    def cleanup(self):
        o = getattr(self, "_orig", {})
        for k in ("statvfs", "remove", "mkdir", "rmdir", "rename", "listdir"):
            if k in o:
                setattr(os, k, o[k])
        if "open" in o:
            builtins.open = o["open"]
        shutil.rmtree(self.tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mb", type=int, default=16, help="固件标称 Flash(MB) / nominal Flash size")
    ap.add_argument("--flash", type=int, default=None, help="实际 Flash(MB)，默认同 --mb / actual Flash size")
    ap.add_argument("--uart-loop", action="store_true", help="模拟 GP0-GP1 已短接 / simulate the GP0-GP1 jumper")
    ap.add_argument("--spi-loop", action="store_true", help="模拟 GP19-GP16 已短接 / simulate the GP19-GP16 jumper")
    ap.add_argument("--i2c", action="store_true", help="模拟 I2C 上有器件 / simulate an I2C device")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--key", action="store_true", help="模拟 3 秒内按键被按下 / simulate a key press")
    ap.add_argument("--key-stuck", action="store_true", help="模拟按键卡死 / simulate a stuck key (low at boot)")
    args = ap.parse_args()

    sim = Sim(args.mb, args.flash or args.mb, args.uart_loop,
              args.spi_loop, args.i2c)
    sim.key_pressed = args.key or args.key_stuck
    if args.key_stuck:
        sim.t_start = time.time() - 10      # 一上电就是按下状态
    sim.install()
    try:
        sys.path.insert(0, FW_TEST_DIR)
        import fw_test
        rc = fw_test.run(quick=args.quick, save=True)
    finally:
        sim.cleanup()
    return rc


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
