#!/usr/bin/env python3
# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
"""
Off-board simulator for the WeAct RP2350A Core V20 self-test suite.
无板模拟器：替换 machine / rp2 / _thread，让 fw_test.py 能在 PC 上跑通。

It is NOT a substitute for a real board. It only proves the test logic and the
output protocol work; every electrical property is faked.
不能替代上板验证，只保证测试逻辑与输出协议正确。

Usage / 用法
    python3 tools/mpy_sim.py --mb 16
    python3 tools/mpy_sim.py --mb 4
    python3 tools/mpy_sim.py --mb 16 --flash 4     # capacity mismatch -> T03 FAIL
    python3 tools/mpy_sim.py --mb 16 --uart-loop --spi-loop --i2c --key
    python3 tools/mpy_sim.py --mb 16 --out sim.log # also write the log
"""

import argparse
import io
import os
import shutil
import sys
import tempfile
import time
import types

# ---------------------------------------------------------------------------
# Fake hardware state / 模拟硬件状态
# ---------------------------------------------------------------------------

PIN_KEY_SIM = 15    # GP15, the external key pin in fw_test
PIN_VBUS_SIM = 24   # GP24, VBUS divider tap / VBUS 分压中点
PIN_VSYS_SIM = 29   # GP29, VSYS divider tap / VSYS 分压中点

STATE = {
    "mb": 16,
    "flash_mb": 16,
    "uart_loop": False,
    "spi_loop": False,
    "i2c": False,
    "key": False,
    "temp_c": 32.0,
    "reset_cause": 1,
    "sd": False,
    "freq": 150_000_000,
    "vbus": True,      # board powered over USB by default / 默认 USB 供电
    "vsys": 5.0,       # VSYS rail in volts / VSYS 电压
}


# ---------------------------------------------------------------------------
# machine / rp2 modules
# ---------------------------------------------------------------------------

class Pin:
    IN = 0
    OUT = 1
    OPEN_DRAIN = 2
    PULL_UP = 1
    PULL_DOWN = 2
    # rp2 的中断触发常量 / IRQ trigger constants as on the rp2 port
    IRQ_RISING = 1
    IRQ_FALLING = 2
    IRQ_HIGH_LEVEL = 3
    IRQ_LOW_LEVEL = 4

    _values = {}

    def __init__(self, gpio, mode=-1, pull=None, value=None):
        self.id = gpio
        self.mode = mode
        self.pull = pull
        self.out = 0
        if value is not None:
            self.value(value)

    def value(self, v=None):
        if v is None:
            if self.mode == Pin.OUT:
                return self.out
            # VBUS tap is a plain digital input with an external 100K
            # pull-down, so it reads 0 unless USB power is present.
            # VBUS 分压中点外接 100K 下拉，没插 USB 时读 0。
            if self.id == PIN_VBUS_SIM:
                return 1 if STATE.get("vbus") else 0
            # input: pull decides, unless the pin is the simulated key
            if self.pull == Pin.PULL_UP:
                if self.id == PIN_KEY_SIM and STATE.get("key"):
                    # fw_test opens T10 with a 1.5s stuck-key check and only
                    # then waits 3s for a press. A real user leaves the key
                    # alone until they see the prompt, so: stay high for the
                    # first 1.6s, then press for 0.5s and release.
                    # fw_test 进入 T10 先做 1.5 秒卡键检查，再等 3 秒。
                    # 真实用户看到提示才按下，所以：前 1.6 秒保持高，
                    # 之后按下 0.5 秒再松开。
                    if "key_t" not in STATE:
                        STATE["key_t"] = time.monotonic()
                    dt = time.monotonic() - STATE["key_t"]
                    if 1.6 <= dt < 2.1:
                        return 0
                    if dt >= 2.1:
                        STATE["key"] = False
                return 1
            if self.pull == Pin.PULL_DOWN:
                return 0
            return 1
        self.out = 1 if v else 0
        Pin._values[self.id] = self.out

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def toggle(self):
        self.value(0 if self.out else 1)

    def deinit(self):
        pass


class PWM:
    def __init__(self, pin):
        self.pin = pin
        self._freq = 1000
        self._duty = 0

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = f

    def duty_u16(self, d=None):
        if d is None:
            return self._duty
        self._duty = d

    def duty_ns(self, d=None):
        if d is None:
            return self._duty * 1000000 // max(1, self._freq) // 65535
        self._duty = d

    def deinit(self):
        pass


class ADC:
    # rp2 上 CORE_TEMP = ADC_TEMPERATURE_CHANNEL_NUM = NUM_ADC_CHANNELS - 1
    # on rp2, CORE_TEMP is the last channel: 5 - 1 = 4
    CORE_TEMP = 4

    def __init__(self, pin):
        self.ch = pin.id if isinstance(pin, Pin) else pin

    def read_u16(self):
        if self.ch == 4:   # internal temperature sensor
            volt = 0.706 + (27 - STATE["temp_c"]) * 0.001721
            return int(volt / 3.3 * 65535)
        if self.ch == PIN_VSYS_SIM:
            # 100K/100K divider: the pin sees half of VSYS.
            # 100K/100K 分压：引脚上是 VSYS 的一半。
            volt = STATE.get("vsys", 5.0) / 2.0
            raw = int(volt / 3.3 * 65535)
            return max(0, min(65535, raw))
        # a plausible divider value on the header pins
        return 32768 + (self.ch - 26) * 100

    def read_uv(self):
        return self.read_u16() * 3300 * 1000 // 65535


class Timer:
    PERIODIC = 1
    ONE_SHOT = 0

    def init(self, *, freq=None, period=None, mode=PERIODIC, callback=None):
        # A real 1kHz ISR on a 150MHz core lands in this window.
        # 真实硬件的回调次数落在这个区间。
        n = int((freq or 1000) * 0.2)
        for _ in range(n + 5):
            if callback:
                callback(self)

    def deinit(self):
        pass


class _UARTBuffer:
    """Loopback byte buffer; empty when the pins are not shorted."""

    def __init__(self):
        self.buf = bytearray()

    def write(self, data):
        if STATE["uart_loop"]:
            self.buf += data
        return len(data)

    def read(self, n=None):
        if n is None:
            n = len(self.buf)
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def any(self):
        return len(self.buf)


class UART:
    def __init__(self, idx, baudrate=115200, tx=None, rx=None, **kw):
        self.buf = _UARTBuffer()

    def write(self, data):
        return self.buf.write(data)

    def read(self, n=None):
        return self.buf.read(n)

    def any(self):
        return self.buf.any()

    def deinit(self):
        pass


class I2C:
    def __init__(self, idx, scl=None, sda=None, freq=400000):
        pass

    def scan(self):
        return [0x3C, 0x68] if STATE["i2c"] else []


class SPI:
    def __init__(self, idx, baudrate=1000000, polarity=0, phase=0, **pins):
        pass

    def write_readinto(self, tx, rx):
        data = bytes(x for x in tx) if not isinstance(tx, (bytes, bytearray)) else bytes(tx)
        if STATE["spi_loop"]:
            fill = data
        else:
            fill = bytes(len(data))
        if isinstance(rx, memoryview):
            rx[:len(fill)] = fill
        else:
            rx[:] = fill
        return len(fill)

    def write(self, data):
        return len(data)

    def deinit(self):
        pass


class Flash:
    """rp2.Flash(): reports the partition geometry, backed by a temp file."""

    _size = 512

    def __init__(self):
        self.path = "_flash.bin"
        total = STATE["flash_mb"] * 1024 * 1024
        if not os.path.exists(self.path):
            with _real_open(self.path, "wb") as f:
                f.truncate(total)
                boot = bytearray(512)
                boot[0:3] = b"\xEB\x3C\x90"
                boot[3:11] = b"MSDOS5.0"
                boot[11] = 0x00
                boot[12] = 0x02          # 512 bytes per sector
                boot[13] = 1             # 1 sector per cluster (512B)
                boot[14] = 0x08          # 8 reserved sectors
                boot[16] = 2             # 2 FATs
                boot[17] = 0x00          # root entries 512
                boot[18] = 0x02
                tot_sectors = total // 512
                if tot_sectors < 0x10000:
                    boot[19] = tot_sectors & 0xFF
                    boot[20] = tot_sectors >> 8
                else:
                    boot[32:36] = tot_sectors.to_bytes(4, "little")
                # size the FAT so the data area lands just under the
                # declared file system, like a real mkfs would
                # 按真实 mkfs 的方式反推 FAT 大小
                fs_target = (STATE["flash_mb"] - 1) * 1024 * 1024
                data_sectors = fs_target // 512
                reserved, nfat_sim, root_sectors = 8, 2, 32
                fat_sectors = max(32, (tot_sectors - data_sectors - reserved - root_sectors) // nfat_sim)
                fat_sectors = int(fat_sectors)
                boot[22] = fat_sectors & 0xFF
                boot[23] = fat_sectors >> 8
                boot[510] = 0x55
                boot[511] = 0xAA
                f.seek(0)
                f.write(boot)

    def ioctl(self, cmd, arg):
        total = STATE["flash_mb"] * 1024 * 1024
        if cmd == 4:
            return total // Flash._size
        if cmd == 5:
            return Flash._size
        return 0

    def readblocks(self, block, buf, off=0):
        with _real_open(self.path, "rb") as f:
            f.seek(block * Flash._size + off)
            data = f.read(len(buf))
        buf[:len(data)] = data
        return 0

    def writeblocks(self, block, buf, off=0):
        with _real_open(self.path, "r+b") as f:
            f.seek(block * Flash._size + off)
            f.write(bytes(buf))
        return 0

    def eraseblocks(self, block, n):
        return 0


def _make_machine():
    m = types.ModuleType("machine")
    m.Pin = Pin
    m.PWM = PWM
    m.ADC = ADC
    m.Timer = Timer
    m.UART = UART
    m.I2C = I2C
    m.SPI = SPI
    m.freq = lambda f=None: STATE["freq"] if f is None else None
    m.reset = lambda: None
    m.reset_cause = lambda: STATE["reset_cause"]
    m.bootloader = lambda: None
    m.soft_reset = lambda: None
    m.PWRON_RESET = 1
    m.HARD_RESET = 2
    m.WDT_RESET = 3
    m.DEEPSLEEP_RESET = 4
    m.SOFT_RESET = 6


    class USBDevice:
        def __init__(self, *a, **kw):
            pass

        def active(self, *a):
            return False

    m.USBDevice = USBDevice
    return m


def _make_rp2():
    r = types.ModuleType("rp2")
    r.Flash = Flash
    r.PIO = object
    r.StateMachine = object
    return r


def _patch_time():
    """Add the MicroPython tick API onto the standard time module."""
    t = time
    if not hasattr(t, "ticks_ms"):
        def ticks_ms():
            return int(t.monotonic() * 1000) & 0x3FFFFFFF

        def ticks_us():
            return int(t.monotonic() * 1000000) & 0x3FFFFFFF

        def ticks_diff(a, b):
            return ((a - b + 0x20000000) & 0x3FFFFFFF) - 0x20000000

        t.ticks_ms = ticks_ms
        t.ticks_us = ticks_us
        t.ticks_diff = ticks_diff
        t.ticks_add = lambda a, b: (a + b) & 0x3FFFFFFF
        t.sleep_ms = lambda ms: t.sleep(ms / 1000)
        t.sleep_us = lambda us: t.sleep(us / 1000000)
    return t


# ---------------------------------------------------------------------------
# Sandboxed file system / 沙箱文件系统
# ---------------------------------------------------------------------------

_real_open = open


def _sandbox_open(path, mode="r", *a, **kw):
    if isinstance(path, str) and path.startswith("/"):
        path = os.path.join(STATE["root"], path.lstrip("/"))
    return _real_open(path, mode, *a, **kw)


def _fix_paths():
    """Redirect os.* path arguments into the sandbox / 把 os 路径参数重定向"""
    root = STATE["root"]

    def wrap(fn):
        def inner(path, *a, **kw):
            if isinstance(path, str) and path.startswith("/"):
                path = os.path.join(root, path.lstrip("/"))
            return fn(path, *a, **kw)
        return inner

    def wrap2(fn):
        def inner(src, dst, *a, **kw):
            if isinstance(src, str) and src.startswith("/"):
                src = os.path.join(root, src.lstrip("/"))
            if isinstance(dst, str) and dst.startswith("/"):
                dst = os.path.join(root, dst.lstrip("/"))
            return fn(src, dst, *a, **kw)
        return inner

    for name in ("stat", "remove", "unlink", "mkdir", "rmdir", "listdir"):
        if hasattr(os, name):
            setattr(os, name, wrap(getattr(os, name)))
    for name in ("rename", "replace"):
        if hasattr(os, name):
            setattr(os, name, wrap2(getattr(os, name)))


def _sandbox_statvfs(path):
    name = path.rstrip("/") if isinstance(path, str) else ""
    # /sd and /sdcard only exist when the simulator was told to fake an SD card
    # 只有显式 --sd 时才假装插了卡
    if name in ("/sd", "/sdcard"):
        if not STATE.get("sd"):
            raise OSError(2)
    total = STATE["flash_mb"] * 1024 * 1024 - 1024 * 1024
    bs = 512
    blocks = total // bs
    free = int(blocks * 0.996)
    return (bs, 512, blocks, free, free, 0, 0, 0, 0, 255)


def _patch_gc():
    """gc.mem_free/mem_alloc are MicroPython-only / 这两个接口只有 MicroPython 有"""
    import gc as g
    if not hasattr(g, "mem_free"):
        limit = 445 * 1024
        g.mem_free = lambda: limit - 16384
        g.mem_alloc = lambda: 16384


_real_listdir = os.listdir


# ---------------------------------------------------------------------------
# Entry / 入口
# ---------------------------------------------------------------------------

def _fake_uname():
    from collections import namedtuple
    U = namedtuple("uname_result", "sysname nodename release version machine")
    return U("rp2", "rp2350",
             "MicroPython v1.29.0 (simulator)",
             "v1.29.0 on 2025-01-01 (simulator)",
             "WeAct Studio RP2350A Core V20 (%dMB) with RP2350" % STATE["mb"])


def main(argv=None):
    ap = argparse.ArgumentParser(description="off-board simulator for fw_test.py")
    ap.add_argument("--mb", type=int, default=16, choices=(4, 16),
                    help="board Flash size the firmware targets (default 16)")
    ap.add_argument("--flash", type=int, default=None, choices=(4, 16),
                    help="actual chip size, to simulate a mismatch")
    ap.add_argument("--uart-loop", action="store_true", help="pretend GP0-GP1 are shorted")
    ap.add_argument("--spi-loop", action="store_true", help="pretend GP19-GP16 are shorted")
    ap.add_argument("--i2c", action="store_true", help="pretend two I2C devices answer")
    ap.add_argument("--key", action="store_true", help="pretend a key on GP15 is pressed")
    ap.add_argument("--sd", action="store_true", help="pretend an SD card is mounted")
    ap.add_argument("--vsys", type=float, default=5.0,
                    help="simulated VSYS rail in volts (0 = fed from the 3V3 pin)")
    ap.add_argument("--no-vbus", action="store_true",
                    help="pretend USB power is absent")
    ap.add_argument("--temp", type=float, default=32.0, help="simulated die temperature")
    ap.add_argument("--quick", action="store_true", help="skip T18/T19")
    ap.add_argument("--only", default=None, help="comma separated case ids")
    ap.add_argument("--out", default=None, help="also write the raw log here")
    args = ap.parse_args(argv)

    STATE["mb"] = args.mb
    STATE["flash_mb"] = args.flash if args.flash is not None else args.mb
    STATE["uart_loop"] = args.uart_loop
    STATE["spi_loop"] = args.spi_loop
    STATE["i2c"] = args.i2c
    STATE["key"] = args.key
    STATE["sd"] = args.sd
    STATE["vsys"] = args.vsys
    STATE["vbus"] = not args.no_vbus
    STATE.pop("key_t", None)
    STATE.pop("key_reads", None)
    STATE["temp_c"] = args.temp

    root = tempfile.mkdtemp(prefix="mpysim_")
    STATE["root"] = root
    # MicroPython gives the user root; the sandbox root plays that role.
    # MicroPython 的进程工作目录就是 "/"，这里把沙箱目录设成它。
    os.chdir(root)
    # Pre-create /sd so T20 exercises the PASS branch only when asked
    # 默认不创建 /sd，T20 走 SKIP

    sys.modules["machine"] = _make_machine()
    sys.modules["rp2"] = _make_rp2()

    # _thread: run the worker synchronously, result is identical
    # _thread：同步执行 worker，计算结果一致
    th = types.ModuleType("_thread")

    def start_new_thread(fn, args=(), kwargs=None):
        fn(*args, **(kwargs or {}))
        return 1

    def allocate_lock():
        import threading
        return threading.Lock()

    th.start_new_thread = start_new_thread
    th.allocate_lock = allocate_lock
    th.get_ident = lambda: 1
    sys.modules["_thread"] = th

    # Patch os.open/os.statvfs for the sandbox
    # 把 os 的路径相关接口重定向到沙箱
    os.open = _sandbox_open
    _fix_paths()
    os.statvfs = _sandbox_statvfs
    os.getcwd = lambda: STATE["root"]
    os.chdir = lambda p: None
    _patch_time()
    _patch_gc()
    # os.uname is a normal Python function, so patch it here rather than
    # hanging it off the fake machine module.
    # os.uname 是普通函数，直接替换。
    os.uname = _fake_uname

    # fw_test is imported from the firmware_test folder one level up
    # 从上一级 firmware_test 目录导入 fw_test
    here = os.path.dirname(os.path.abspath(__file__))
    fwdir = os.path.dirname(here)
    sys.path.insert(0, fwdir)

    for mod in ("fw_test",):
        sys.modules.pop(mod, None)
    # sys.implementation._mpy only exists on MicroPython
    # sys.implementation._mpy 只有 MicroPython 才有
    if not hasattr(sys.implementation, "_mpy"):
        sys.implementation._mpy = 6
    import fw_test  # noqa: E402
    fw_test.__builtins__  # touch, keeps linters quiet

    # Redirect builtins.open used by fw_test to the sandbox too
    # fw_test 里的 open() 同样走沙箱
    import builtins
    builtins.open = _sandbox_open

    log = io.StringIO()
    real_write = sys.stdout.write

    def tee(s):
        log.write(s)
        return real_write(s)

    sys.stdout.write = tee
    try:
        p, f, s = fw_test.run(quick=args.quick, only=args.only)
    finally:
        sys.stdout.write = real_write
        builtins.open = _real_open

    if args.out:
        with _real_open(args.out, "w", encoding="utf-8") as fp:
            fp.write(log.getvalue())
        print("log written to %s" % args.out)

    shutil.rmtree(root, ignore_errors=True)
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
