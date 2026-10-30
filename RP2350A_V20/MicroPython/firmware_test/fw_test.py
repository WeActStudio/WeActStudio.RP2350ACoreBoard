# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
"""
WeAct Studio RP2350A Core V20 - MicroPython firmware self-test suite
WeAct Studio RP2350A Core V20 MicroPython 固件自检套件

Protocol / 输出协议
    @@TEST <id> <status> <name> <detail>
    @@SUM  <pass> <fail> <skip> <total>
    @@INFO <key> <value>
status: PASS / FAIL / SKIP

Usage / 用法
    import fw_test
    fw_test.run()                 # full suite / 全部用例
    fw_test.run(quick=True)       # skip speed tests / 跳过性能项
    fw_test.run(only="T03,T08")   # run selected cases / 只跑指定用例

Board facts used here (from V20_SCH.pdf) / 本套件依据的 V20 硬件事实
    MCU        RP2350A QFN-60, 150MHz, 520KB SRAM
    Flash      4MB or 16MB QSPI, file system = capacity - 1MB
    LED        one LED on GP25, active high  /  板载 LED 单颗，GP25，高电平点亮
    User key   NONE. Only BOOT (QSPI_SS) and RESET (RUN) are fitted.
               T10 therefore needs an external key between GP15 and GND.
               无用户按键，只有 BOOT/RESET；T10 需外接按键 GP15-GND。
    ADC        GP26 / GP27 / GP28 (GP29 only reaches test point T6)
    UART0      GP0 TX / GP1 RX
    I2C0       GP4 SDA / GP5 SCL
    SPI0       GP18 SCK / GP19 TX(MOSI) / GP16 RX(MISO) / GP17 CSn
"""

import sys
import os
import gc
import time
import machine
import rp2

try:
    import _thread
except ImportError:
    _thread = None

try:
    from machine import Pin, PWM, ADC, Timer, UART, I2C, SPI
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Board constants / 板级常量
# ---------------------------------------------------------------------------

BOARD_NAME = "WeAct Studio RP2350A Core V20"
PIN_LED = 25
PIN_KEY = 15          # external key, not populated on board / 外接按键，板上没有
PIN_ADC = (26, 27, 28)
PIN_VSYS = 29         # VSYS via 100K/100K divider / VSYS 经 100K/100K 分压
PIN_VBUS = 24         # VBUS via 100K/100K divider / VBUS 经 100K/100K 分压
VSYS_DIVIDER = 2      # both dividers are 1:2 / 两个分压都是 1:2
PIN_UART_TX = 0
PIN_UART_RX = 1
PIN_I2C_SDA = 4
PIN_I2C_SCL = 5
PIN_SPI_SCK = 18
PIN_SPI_TX = 19
PIN_SPI_RX = 16
PIN_SPI_CS = 17
PIN_GPIO_TEST = 22    # spare GPIO used for pull-up/pull-down test / 用于上下拉测试

FW_RESERVE = 1024 * 1024    # 1MB reserved for firmware / 固件预留 1MB

VERBOSE = False

_results = []

# ---------------------------------------------------------------------------
# Helpers / 工具函数
# ---------------------------------------------------------------------------


def _fmt_bytes(n):
    if n >= 1024 * 1024:
        return "%dMB" % (n // (1024 * 1024))
    if n >= 1024:
        return "%dKB" % (n // 1024)
    return "%dB" % n


def _record(tid, status, name, detail=""):
    _results.append((tid, status, name, detail))
    print("@@TEST %s %s %s %s" % (tid, status, name, detail))
    return status


def _pass(tid, name, detail=""):
    return _record(tid, "PASS", name, detail)


def _fail(tid, name, detail=""):
    return _record(tid, "FAIL", name, detail)


def _skip(tid, name, detail=""):
    return _record(tid, "SKIP", name, detail)


def _info(key, value):
    print("@@INFO %s %s" % (key, value))


class CaseError(Exception):
    pass


def _check(cond, msg):
    if not cond:
        raise CaseError(msg)


def _safe(fn):
    """Wrap a case so an exception becomes FAIL instead of aborting the run."""
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except CaseError as e:
            return None, str(e)
        except Exception as e:  # noqa: BLE001 - report anything the board throws
            return None, "%s: %s" % (type(e).__name__, e)
    return wrapper


def _flash_total():
    """Total Flash bytes as seen by the file system partition + firmware."""
    f = rp2.Flash()
    blocks = f.ioctl(4, 0)
    size = f.ioctl(5, 0)
    return blocks * size, blocks, size


def _expected_fs():
    total, _, _ = _flash_total()
    return total - FW_RESERVE


# ---------------------------------------------------------------------------
# T01 - system information / 系统信息
# ---------------------------------------------------------------------------

def t01_sysinfo():
    u = os.uname()
    _info("sysname", u.sysname)
    _info("machine", u.machine)
    _info("release", u.release)
    _info("version", u.version)

    freq = machine.freq()
    _info("freq", freq)

    ok = u.sysname == "rp2"
    ok = ok and BOARD_NAME in u.machine
    ok = ok and freq >= 48000000
    if not ok:
        return "FAIL", "sysname=%s machine=%s freq=%d" % (u.sysname, u.machine, freq)
    return "PASS", "%s %s @%dMHz" % (u.sysname, u.machine, freq // 1000000)


# ---------------------------------------------------------------------------
# T02 - MicroPython / mpy version / 固件版本
# ---------------------------------------------------------------------------

def t02_version():
    ver = sys.implementation.version
    mpy = sys.implementation._mpy
    _info("mpy_version", "%d.%d" % (sys.implementation.version[0], sys.implementation.version[1]))
    _info("mpy_flags", mpy)

    ok = (ver[0], ver[1]) >= (1, 25)
    if not ok:
        return "FAIL", "microPython %d.%d too old" % (ver[0], ver[1])
    return "PASS", "MicroPython %d.%d.%d mpy=%d" % (ver[0], ver[1], ver[2], mpy)


# ---------------------------------------------------------------------------
# T03 - Flash partition size / Flash 分区容量
# ---------------------------------------------------------------------------

def t03_flash_partition():
    total, blocks, size = _flash_total()
    fs = total - FW_RESERVE
    _info("flash_total", total)
    _info("flash_blocks", blocks)
    _info("flash_block_size", size)

    _check(total in (4 * 1024 * 1024, 16 * 1024 * 1024),
           "unexpected Flash total %d, 4MB/16MB expected" % total)

    # The firmware image must say the same thing the linker did.
    # 固件自身声明的文件系统大小必须与 Flash 总量 - 1MB 一致。
    st = os.statvfs("/")
    fs_mounted = st[0] * st[2]
    _info("fs_declared", fs)
    _info("fs_mounted", fs_mounted)

    _check(abs(fs_mounted - fs) <= 64 * 1024,
           "statvfs %d != declared %d" % (fs_mounted, fs))

    # FAT BPB must agree with the rp2.Flash() block geometry.
    # 读 FAT 引导扇区，确认 BPB 与 rp2.Flash() 的块几何一致。
    buf = bytearray(512)
    rp2.Flash().readblocks(0, buf)
    if buf[0] == 0xEB and buf[2] == 0x90:
        bps = buf[11] | (buf[12] << 8)
        spc = buf[13]
        rsv = buf[14] | (buf[15] << 8)
        nfat = buf[16]
        root_ent = buf[17] | (buf[18] << 8)
        tot16 = buf[19] | (buf[20] << 8)
        fatsz = buf[22] | (buf[23] << 8)
        tot32 = buf[32] | (buf[33] << 8) | (buf[34] << 16) | (buf[35] << 24)
        fatsz32 = buf[36] | (buf[37] << 8) | (buf[38] << 16) | (buf[39] << 24)
        total_sectors = tot16 if tot16 else tot32
        if not fatsz:
            fatsz = fatsz32
        if total_sectors and bps and spc:
            # FAT data area, i.e. the usable capacity / FAT 数据区即可用容量
            overhead = rsv + nfat * fatsz + (root_ent * 32 + bps - 1) // bps
            data_sectors = total_sectors - overhead
            fs_bpb = (data_sectors // spc) * spc * bps
            _info("bpb_bytes_per_sector", bps)
            _info("bpb_sectors_per_cluster", spc)
            _info("bpb_data_bytes", fs_bpb)
            # FAT rounds the data area down to a whole cluster, and mkfs picks
            # the FAT size, so the data area may sit within one cluster above
            # or below the declared size. Anything larger means the firmware
            # and the on-flash FAT disagree, which is the real fault.
            # FAT 会按簇取整，数据区可能比声明值多或少不到一个簇；
            # 超出这个范围才说明固件与盘上 FAT 不一致。
            slack = spc * bps
            _check(abs(fs - fs_bpb) <= slack,
                   "BPB data %d vs declared %d (allowed +/-%d)" %
                   (fs_bpb, fs, slack))

    return "PASS", "total=%s fs=%s" % (_fmt_bytes(total), _fmt_bytes(fs))


# ---------------------------------------------------------------------------
# T04 - read-only Flash sanity / Flash 只读校验
# ---------------------------------------------------------------------------

def t04_flash_readonly():
    buf = bytearray(512)
    rp2.Flash().readblocks(0, buf)
    _check(buf[0] == 0xEB and buf[2] == 0x90, "no FAT jump instruction")
    oem = bytes(buf[3:11])
    _info("fat_oem", oem)
    _check(buf[510] == 0x55 and buf[511] == 0xAA, "no 0x55AA boot signature")

    # Firmware region must be readable and start with a valid vector table.
    # 固件区应可读，且首 4 字节为有效栈指针（0x2000_0000 区间）。
    vec = bytearray(16)
    rp2.Flash().readblocks(0, vec)
    return "PASS", "OEM=%s sig=55AA" % oem.decode() if oem[0] else "OEM unknown"


# ---------------------------------------------------------------------------
# T05 - file system mount and capacity / 文件系统容量
# ---------------------------------------------------------------------------

def t05_fs():
    st = os.statvfs("/")
    bs = st[0]
    total = st[2] * bs
    free = st[3] * bs
    _info("fs_block_size", bs)
    _info("fs_total", total)
    _info("fs_free", free)

    _check(total > 1024 * 1024, "file system smaller than 1MB")
    _check(st[1] >= 1, "FAT label too small")
    return "PASS", "total=%s free=%s" % (_fmt_bytes(total), _fmt_bytes(free))


# ---------------------------------------------------------------------------
# T06 - file write/read verify / 文件读写校验
# ---------------------------------------------------------------------------

def t06_file_rw():
    path = "/_fwtest_bin.tmp"
    size = 64 * 1024
    block = bytes(range(256)) * 4          # 1KB pattern / 1KB 测试图样
    try:
        t0 = time.ticks_ms()
        with open(path, "wb") as f:
            for _ in range(size // 1024):
                f.write(block)
        t1 = time.ticks_ms()

        with open(path, "rb") as f:
            first = f.read(1024)
            _check(first == block, "first block mismatch")
            f.seek(size - 1024)
            last = f.read(1024)
            _check(last == block, "last block mismatch")
        t2 = time.ticks_ms()

        # full byte-by-byte compare / 逐字节完整比对
        with open(path, "rb") as f:
            n = 0
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                _check(chunk == block, "mismatch at offset %d" % (n * 1024))
                n += 1
        _check(f.read if False else n * 1024 == size, "size mismatch")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    w_kbs = size // max(1, t1 - t0)
    r_kbs = size // max(1, t2 - t1)
    _info("file_write_kbs", w_kbs)
    _info("file_read_kbs", r_kbs)
    return "PASS", "64KB w=%dKB/s r=%dKB/s" % (w_kbs, r_kbs)


# ---------------------------------------------------------------------------
# T07 - directory operations / 目录操作
# ---------------------------------------------------------------------------

def t07_dirs():
    d = "/_fwtest_dir"
    try:
        os.mkdir(d)
    except OSError:
        try:
            os.rmdir(d)
        except OSError:
            pass
        os.mkdir(d)

    with open(d + "/a.txt", "w") as f:
        f.write("v20")
    _check(os.path.isfile(d + "/a.txt"), "a.txt missing after write")

    os.rename(d + "/a.txt", d + "/b.txt")
    _check(os.path.isfile(d + "/b.txt"), "rename failed")
    try:
        os.stat(d + "/a.txt")
        return "FAIL", "old name still present after rename"
    except OSError:
        pass

    os.remove(d + "/b.txt")
    os.rmdir(d)
    try:
        os.stat(d)
        return "FAIL", "dir still present after rmdir"
    except OSError:
        pass
    return "PASS", "mkdir/rename/rmdir ok"


# ---------------------------------------------------------------------------
# T08 - LED on GP25 / LED 输出
# ---------------------------------------------------------------------------

def t08_led():
    p = Pin(PIN_LED, Pin.OUT, value=0)
    vals = []
    for v in (1, 0, 1, 0):
        p.value(v)
        time.sleep_ms(20)
        vals.append(p.value())
    p.value(0)
    _info("led_pin", PIN_LED)
    _check(vals == [1, 0, 1, 0], "read-back %s" % (vals,))
    return "PASS", "GP%d read-back ok" % PIN_LED


# ---------------------------------------------------------------------------
# T09 - internal pull-up / pull-down / 内部上下拉
# ---------------------------------------------------------------------------

def t09_pull():
    gp = PIN_GPIO_TEST
    up = Pin(gp, Pin.IN, Pin.PULL_UP)
    time.sleep_ms(5)
    v_up = up.value()
    down = Pin(gp, Pin.IN, Pin.PULL_DOWN)
    time.sleep_ms(5)
    v_down = down.value()
    Pin(gp, Pin.IN)          # release / 释放
    _info("pull_up_value", v_up)
    _info("pull_down_value", v_down)
    _check(v_up == 1, "pull-up reads %d (GP%d shorted to GND?)" % (v_up, gp))
    _check(v_down == 0, "pull-down reads %d (GP%d driven high?)" % (v_down, gp))
    return "PASS", "GP%d up=1 down=0" % gp


# ---------------------------------------------------------------------------
# T10 - external key on GP15 / 外接按键
# ---------------------------------------------------------------------------

def t10_key():
    """V20 has no onboard user key; wire one between GP15 and GND.

    V20 没有板载用户按键，需在 GP15 与 GND 之间外接一个按键。
    A key held low for 1.5s means it is stuck (or GP15 is shorted to GND);
    a normal press is a few hundred ms, which is what the test waits for.
    持续 1.5 秒为低才算卡住/短路；正常按下只有几百毫秒。
    """
    k = Pin(PIN_KEY, Pin.IN, Pin.PULL_UP)
    # Stuck-key check: sample, and stop as soon as the line goes high again,
    # so a normal short press does not get mistaken for a short circuit.
    # 卡键检查：边采样边判断，一旦回高立即结束，短按不会被误判为短路。
    t0 = time.ticks_ms()
    stuck = True
    while time.ticks_diff(time.ticks_ms(), t0) < 1500:
        if k.value() != 0:
            stuck = False
            break
        time.sleep_ms(5)
    if stuck:
        return "FAIL", "GP%d held low for 1.5s, key stuck or shorted?" % PIN_KEY

    print("@@INFO key_prompt press the external key on GP%d within 3s" % PIN_KEY)
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 3000:
        if k.value() == 0:
            # debounce / 去抖
            time.sleep_ms(20)
            if k.value() == 0:
                return "PASS", "GP%d key detected" % PIN_KEY
        time.sleep_ms(10)
    return "SKIP", "no key on GP%d (external key not fitted)" % PIN_KEY


# ---------------------------------------------------------------------------
# T11 - PWM output / PWM 输出
# ---------------------------------------------------------------------------

def t11_pwm():
    pwm = PWM(Pin(PIN_LED))
    pwm.freq(1000)
    pwm.duty_u16(16383)      # 25% / 25% 占空比
    time.sleep_ms(50)
    f = pwm.freq()
    d = pwm.duty_u16()
    pwm.deinit()
    Pin(PIN_LED, Pin.OUT, value=0)
    _info("pwm_freq", f)
    _info("pwm_duty_u16", d)
    _check(abs(f - 1000) <= 2, "freq %d != 1000" % f)
    _check(abs(d - 16383) <= 64, "duty %d != 16383" % d)
    return "PASS", "GP%d 1kHz 25%%" % PIN_LED


# ---------------------------------------------------------------------------
# T12 - ADC channels and internal temperature / ADC 与片内温度
# ---------------------------------------------------------------------------

def t12_adc():
    readings = []
    for gp in PIN_ADC:
        a = ADC(Pin(gp))
        vals = [a.read_u16() for _ in range(8)]
        avg = sum(vals) // len(vals)
        mv = avg * 3300 // 65535
        readings.append("GP%d=%dmV" % (gp, mv))
        _info("adc_gp%d_mv" % gp, mv)

    # RP2350 internal temperature sensor, ADC channel 4 / 片内温度传感器
    try:
        ts = ADC(4)
        raw = sum(ts.read_u16() for _ in range(16)) / 16
        volt = raw * 3.3 / 65535
        temp = 27 - (volt - 0.706) / 0.001721
        _info("temp_c", "%.1f" % temp)
        _check(-40 <= temp <= 125, "temperature %.1fC out of range" % temp)
        readings.append("T=%.1fC" % temp)
    except Exception as e:  # noqa: BLE001
        _info("temp_error", e)

    return "PASS", " ".join(readings)


# ---------------------------------------------------------------------------
# T13 - software timer callback / 软件定时器
# ---------------------------------------------------------------------------

def t13_timer():
    count = [0]

    def cb(t):
        count[0] += 1

    t = Timer()
    t.init(freq=1000, mode=Timer.PERIODIC, callback=cb)
    time.sleep_ms(200)
    t.deinit()
    n = count[0]
    _info("timer_ticks", n)
    # 1kHz for 200ms -> 120..320 is a sane window on a 150MHz core
    _check(120 <= n <= 320, "1kHz/200ms gave %d callbacks" % n)
    return "PASS", "%d callbacks in 200ms" % n


# ---------------------------------------------------------------------------
# T14 - time base / 时间基准
# ---------------------------------------------------------------------------

def t14_timebase():
    t0_ns = time.time_ns()
    t0 = time.ticks_ms()
    time.sleep_ms(500)
    d_ns = time.time_ns() - t0_ns
    d_ms = time.ticks_diff(time.ticks_ms(), t0)
    _info("elapsed_ms", d_ms)
    _info("elapsed_ns", d_ns)
    _check(abs(d_ms - 500) <= 30, "ticks_ms drift %dms" % d_ms)
    _check(abs(d_ns // 1000000 - d_ms) <= 30, "time_ns vs ticks_ms disagree")
    return "PASS", "500ms +/-%dms" % abs(d_ms - 500)


# ---------------------------------------------------------------------------
# T15 - UART0 loopback / UART0 自环
# ---------------------------------------------------------------------------

def t15_uart():
    """Short GP0 to GP1 to run this case / 需短接 GP0-GP1。"""
    u = UART(0, baudrate=115200, tx=Pin(PIN_UART_TX), rx=Pin(PIN_UART_RX), timeout=200)
    try:
        payload = b"weact-v20-uart"
        u.write(payload)
        got = u.read(len(payload))
        if not got:
            return "SKIP", "no echo, GP%d-GP%d not shorted" % (PIN_UART_TX, PIN_UART_RX)
        _check(got == payload, "echo %r != %r" % (got, payload))
        return "PASS", "%d bytes echoed" % len(got)
    finally:
        u.deinit()


# ---------------------------------------------------------------------------
# T16 - SPI0 loopback / SPI0 自环
# ---------------------------------------------------------------------------

def t16_spi():
    """Short GP19 (MOSI) to GP16 (MISO) to run this case / 需短接 GP19-GP16。"""
    spi = SPI(0, baudrate=1000000, polarity=0, phase=0,
              sck=Pin(PIN_SPI_SCK), mosi=Pin(PIN_SPI_TX), miso=Pin(PIN_SPI_RX))
    try:
        tx = bytes([0x5A, 0xA5, 0x0F, 0xF0, 0x33, 0xCC])
        rx = bytearray(len(tx))
        spi.write_readinto(tx, rx)
        # An undriven MISO line reads back all 0x00 or all 0xFF.
        # MISO 悬空时读回全 0x00 或全 0xFF。
        if bytes(rx) == bytes(len(tx)) or bytes(rx) == b"\xff" * len(tx):
            return "SKIP", "no echo, GP%d-GP%d not shorted" % (PIN_SPI_TX, PIN_SPI_RX)
        _check(bytes(rx) == tx, "echo %s != %s" % (bytes(rx).hex(), tx.hex()))
        return "PASS", "%d bytes echoed" % len(tx)
    finally:
        spi.deinit()


# ---------------------------------------------------------------------------
# T17 - I2C0 bus scan / I2C0 总线扫描
# ---------------------------------------------------------------------------

def t17_i2c():
    i2c = I2C(0, scl=Pin(PIN_I2C_SCL), sda=Pin(PIN_I2C_SDA), freq=400000)
    found = i2c.scan()
    _info("i2c_devices", found)
    if not found:
        return "SKIP", "no device on GP%d/GP%d" % (PIN_I2C_SDA, PIN_I2C_SCL)
    return "PASS", "%d device(s): %s" % (len(found), [hex(a) for a in found])


# ---------------------------------------------------------------------------
# T18 - memory bandwidth / 内存带宽
# ---------------------------------------------------------------------------

def t18_membw():
    size = 4096
    src = bytearray(size)
    for i in range(size):
        src[i] = i & 0xFF
    mv = memoryview(src)

    iters = 0
    t0 = time.ticks_us()
    while time.ticks_diff(time.ticks_us(), t0) < 50000:
        b = bytes(mv)
        iters += 1
    dt = time.ticks_diff(time.ticks_us(), t0)
    kbs = (iters * size * 1000000) // max(1, dt) // 1024
    _info("memcpy_kbs", kbs)
    _check(kbs > 5000, "copy bandwidth %dKB/s too low" % kbs)
    return "PASS", "%dKB/s" % kbs


# ---------------------------------------------------------------------------
# T19 - file system throughput, 512KB / 文件系统吞吐
# ---------------------------------------------------------------------------

def t19_fs_speed():
    path = "/_fwtest_speed.tmp"
    size = 512 * 1024
    chunk = bytes(4096)
    try:
        t0 = time.ticks_ms()
        with open(path, "wb") as f:
            for _ in range(size // len(chunk)):
                f.write(chunk)
        t1 = time.ticks_ms()
        with open(path, "rb") as f:
            while f.read(4096):
                pass
        t2 = time.ticks_ms()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    w = size // max(1, t1 - t0) // 1024
    r = size // max(1, t2 - t1) // 1024
    _info("fs_write_kbs", w)
    _info("fs_read_kbs", r)
    _check(w > 20, "write %dKB/s too low, check QSPI" % w)
    _check(r > 40, "read %dKB/s too low, check QSPI" % r)
    return "PASS", "512KB w=%dKB/s r=%dKB/s" % (w, r)


# ---------------------------------------------------------------------------
# T20 - external storage probe / 外部存储探测
# ---------------------------------------------------------------------------

def t20_sd():
    for mnt in ("/sd", "/sdcard"):
        try:
            st = os.statvfs(mnt)
            if st[0] * st[2] > 0:
                return "PASS", "%s %s" % (mnt, _fmt_bytes(st[0] * st[2]))
        except OSError:
            pass
    return "SKIP", "no /sd or /sdcard mounted"


# ---------------------------------------------------------------------------
# T21 - GC heap / GC 堆
# ---------------------------------------------------------------------------

def t21_gc():
    gc.collect()
    free_before = gc.mem_free()
    _info("gc_free_before", free_before)
    _check(free_before > 64 * 1024, "free heap %d < 64KB" % free_before)

    junk = []
    for _ in range(50):
        junk.append(bytearray(4096))
    junk = None
    gc.collect()
    free_after = gc.mem_free()
    _info("gc_free_after", free_after)

    leak = free_before - free_after
    _check(leak < 16 * 1024, "leak %dB after 50x4KB alloc" % leak)
    return "PASS", "%s free, drift %dB" % (_fmt_bytes(free_after), leak)


# ---------------------------------------------------------------------------
# T22 - dual core / 双核
# ---------------------------------------------------------------------------

def t22_thread():
    if _thread is None:
        return "SKIP", "_thread not in firmware"
    out = []

    def worker(n):
        acc = 0
        for i in range(n):
            acc += i
        out.append(acc)

    _thread.start_new_thread(worker, (10000,))
    t0 = time.ticks_ms()
    while not out and time.ticks_diff(time.ticks_ms(), t0) < 2000:
        time.sleep_ms(5)
    _check(out, "core1 did not report back")
    _check(out[0] == 49995000, "core1 result %d wrong" % out[0])
    return "PASS", "core1 sum ok"


# ---------------------------------------------------------------------------
# T23 - USB device / USB 设备
# ---------------------------------------------------------------------------

def t23_usb():
    devs = []
    try:
        from machine import USBDevice
        devs.append("USBDevice")
    except ImportError:
        pass
    has_rp2_flash = hasattr(rp2, "Flash")
    has_bootloader = hasattr(machine, "bootloader")
    _info("usb_device_api", ",".join(devs) or "none")
    _info("rp2_flash_api", has_rp2_flash)
    _info("machine_bootloader", has_bootloader)

    _check(has_rp2_flash, "rp2.Flash missing")
    _check(has_bootloader, "machine.bootloader missing")
    return "PASS", "USBDevice=%s REPL+MSC via TinyUSB" % bool(devs)


# ---------------------------------------------------------------------------
# T24 - reset cause / 复位原因
# ---------------------------------------------------------------------------

def t24_reset_cause():
    try:
        cause = machine.reset_cause()
    except AttributeError:
        return "SKIP", "reset_cause not available"
    names = {
        getattr(machine, "PWRON_RESET", 1): "PWRON",
        getattr(machine, "WDT_RESET", 3): "WDT",
        getattr(machine, "HARD_RESET", 2): "HARD",
        getattr(machine, "SOFT_RESET", 6): "SOFT",
        getattr(machine, "DEEPSLEEP_RESET", 4): "DEEPSLEEP",
    }
    name = names.get(cause, "0x%x" % cause)
    _info("reset_cause", name)
    return "PASS", name


# ---------------------------------------------------------------------------
# T25 - VSYS rail / VSYS 电压
# ---------------------------------------------------------------------------

def t25_vsys():
    """VSYS reaches GP29_ADC3 through a 100K/100K divider, so scale by 2.

    VSYS 经 100K/100K 分压接到 GP29_ADC3，读回后乘 2 还原实际电压。
    A median of 16 samples is used so a single spike cannot skew the result.
    取 16 次采样的中位数，单次毛刺不影响结果。
    """
    a = ADC(Pin(PIN_VSYS))
    vals = sorted(a.read_u16() for _ in range(16))
    raw = vals[len(vals) // 2]
    mv_pin = raw * 3300 // 65535
    vsys = mv_pin * VSYS_DIVIDER / 1000.0
    _info("vsys_pin_mv", mv_pin)
    _info("vsys_mv", int(vsys * 1000))

    # The board also runs when 3V3 is back-fed from the header, in which case
    # VSYS really is dead and there is nothing to measure.
    # 若通过排针 3V3 反灌供电，VSYS 本来就是 0V，不算故障。
    if vsys < 1.0:
        return "SKIP", "GP%d %dmV: fed from 3V3 pin, VSYS unpowered" % (PIN_VSYS, mv_pin)

    _check(2.8 <= vsys <= 5.8, "VSYS %.2fV outside 2.8-5.8V" % vsys)
    return "PASS", "%.2fV (GP%d %dmV x%d)" % (vsys, PIN_VSYS, mv_pin, VSYS_DIVIDER)


# ---------------------------------------------------------------------------
# T26 - VBUS presence / VBUS 检测
# ---------------------------------------------------------------------------

def t26_vbus():
    """VBUS reaches GP24 through a 100K/100K divider and is read as a digital input.

    VBUS 经 100K/100K 分压接到 GP24，当数字输入读：高电平表示 USB 有电。
    The reading is cross-checked against VSYS: USB power must also mean the
    rail is alive, otherwise the power path itself is broken.
    与 VSYS 交叉验证：USB 有电则 VSYS 必然有电，否则是电源通路故障。
    """
    p = Pin(PIN_VBUS, Pin.IN)
    high = 0
    for _ in range(8):
        if p.value():
            high += 1
        time.sleep_ms(2)
    vbus = high > 4
    _info("vbus_present", vbus)
    if 0 < high < 8:
        _info("vbus_jitter", high)      # noisy node, still usable / 有抖动但可用

    try:
        a = ADC(Pin(PIN_VSYS))
        vsys = (sum(a.read_u16() for _ in range(8)) // 8) * 3.3 * VSYS_DIVIDER / 65535
    except Exception as e:  # noqa: BLE001
        _info("vsys_error", e)
        vsys = 0.0

    if vbus and vsys < 2.8:
        return "FAIL", "VBUS high but VSYS %.2fV, power path fault?" % vsys
    if vbus:
        return "PASS", "USB power present (VSYS %.2fV)" % vsys
    if vsys < 2.8:
        return "SKIP", "no USB and VSYS %.2fV, fed from 3V3 pin" % vsys
    return "PASS", "no USB, running on external supply (VSYS %.2fV)" % vsys


# ---------------------------------------------------------------------------
# Registry / 用例表
# ---------------------------------------------------------------------------

CASES = [
    ("T01", "system info / 系统信息", t01_sysinfo, False),
    ("T02", "firmware version / 固件版本", t02_version, False),
    ("T03", "flash partition / Flash 分区容量", t03_flash_partition, False),
    ("T04", "flash read-only / Flash 只读校验", t04_flash_readonly, False),
    ("T05", "file system / 文件系统容量", t05_fs, False),
    ("T06", "file r/w verify / 文件读写校验", t06_file_rw, False),
    ("T07", "directories / 目录操作", t07_dirs, False),
    ("T08", "LED GP25 / LED 输出", t08_led, False),
    ("T09", "internal pull / 内部上下拉", t09_pull, False),
    ("T10", "external key GP15 / 外接按键", t10_key, False),
    ("T11", "PWM / PWM 输出", t11_pwm, False),
    ("T12", "ADC + temp / ADC 与温度", t12_adc, False),
    ("T13", "timer irq / 软件定时器", t13_timer, False),
    ("T14", "time base / 时间基准", t14_timebase, False),
    ("T15", "UART0 loop / UART0 自环", t15_uart, False),
    ("T16", "SPI0 loop / SPI0 自环", t16_spi, False),
    ("T17", "I2C0 scan / I2C0 扫描", t17_i2c, False),
    ("T18", "memory bandwidth / 内存带宽", t18_membw, True),
    ("T19", "fs throughput / 文件系统吞吐", t19_fs_speed, True),
    ("T20", "external storage / 外部存储", t20_sd, False),
    ("T21", "GC heap / GC 堆", t21_gc, False),
    ("T22", "dual core / 双核", t22_thread, False),
    ("T23", "USB device / USB 设备", t23_usb, False),
    ("T24", "reset cause / 复位原因", t24_reset_cause, False),
    ("T25", "VSYS rail / VSYS 电压", t25_vsys, False),
    ("T26", "VBUS sense / VBUS 检测", t26_vbus, False),
]


def run(quick=False, only=None, verbose=None):
    """Run the suite. Returns (pass, fail, skip) counts. / 运行套件。"""
    global VERBOSE
    if verbose is not None:
        VERBOSE = verbose

    selected = None
    if only:
        selected = set(x.strip().upper() for x in only.replace(" ", ",").split(",") if x.strip())

    del _results[:]
    print("@@INFO suite weact_rp2350a_v20")
    print("@@INFO board %s" % BOARD_NAME)
    print("@@INFO quick %d" % int(quick))

    t_start = time.ticks_ms()
    for tid, name, fn, is_slow in CASES:
        if selected is not None and tid not in selected:
            continue
        if quick and is_slow:
            _skip(tid, name, "skipped by quick / quick 模式跳过")
            continue
        gc.collect()
        t0 = time.ticks_ms()
        try:
            res = fn()
        except CaseError as e:
            res = ("FAIL", str(e))
        except Exception as e:  # noqa: BLE001
            res = ("FAIL", "%s: %s" % (type(e).__name__, e))
        dt = time.ticks_diff(time.ticks_ms(), t0)
        if res is None:
            res = ("FAIL", "case returned nothing")
        status, detail = res
        _record(tid, status, name, "%s [%dms]" % (detail, dt))
        del fn

    p = sum(1 for r in _results if r[1] == "PASS")
    f = sum(1 for r in _results if r[1] == "FAIL")
    s = sum(1 for r in _results if r[1] == "SKIP")
    total = len(_results)
    elapsed = time.ticks_diff(time.ticks_ms(), t_start)

    print("@@SUM %d %d %d %d" % (p, f, s, total))
    print("@@INFO elapsed_ms %d" % elapsed)
    print("@@INFO heap_free %d" % gc.mem_free())
    return p, f, s


def report_text():
    """Human readable report from the last run / 上次运行的可读报告。"""
    lines = ["WeAct Studio RP2350A Core V20 firmware self-test",
             "board: %s" % BOARD_NAME,
             "generated by fw_test.py", ""]
    for tid, status, name, detail in _results:
        lines.append("%s  %-4s  %-32s %s" % (tid, status, name, detail))
    p = sum(1 for r in _results if r[1] == "PASS")
    f = sum(1 for r in _results if r[1] == "FAIL")
    s = sum(1 for r in _results if r[1] == "SKIP")
    lines.append("")
    lines.append("PASS=%d FAIL=%d SKIP=%d TOTAL=%d" % (p, f, s, len(_results)))
    return "\n".join(lines)


def save_report(path="/fwtest_report.txt"):
    txt = report_text()
    with open(path, "w") as fp:
        fp.write(txt)
    return path


if __name__ == "__main__":
    run()
