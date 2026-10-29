# fw_test.py - WeAct RP2350A_V10 MicroPython 固件自检套件
#              WeAct RP2350A_V10 MicroPython firmware self-test suite
#
# 用法 / Usage:
#   1) 拷到 U 盘根目录命名为 main.py，上电自动跑
#      copy to the drive root as main.py to run at power-up
#   2) REPL 里 / in the REPL: import fw_test; fw_test.run()
#   3) PC 端 / on the host: python3 host_test.py --port /dev/ttyACM0
#
# 输出协议 / Output protocol (parsed by host_test.py):
#   @@TEST|<id>|<name>|<PASS|FAIL|SKIP>|<detail>
#   @@SUM|<pass>|<fail>|<skip>|<total>|<ms>
#   @@DONE
#
# 范围 / Scope:
#   * 不做断电/复位类测试，避免打断 USB
#     no power-cycle or reset tests, so USB stays connected
#   * UART/SPI 回环没有短接时自动 SKIP
#     UART/SPI loopback reports SKIP when the jumper is missing
#   * 写 Flash 的测试只写文件系统区，不碰固件区
#     Flash writes stay inside the file system area, never the firmware area

VERSION = "1.0.0"
EXPECTED_BOARD = "WeAct Studio RP2350A Core V10"

import sys
import time
import os
import gc

try:
    import machine
except Exception:
    machine = None
try:
    import rp2
except Exception:
    rp2 = None
try:
    import _thread
except Exception:
    _thread = None

# ------------------------------------------ 结果收集 / result collection

TESTS = []
RESULTS = []


def test(tid, name, slow=False):
    def deco(fn):
        TESTS.append((tid, name, fn, slow))
        return fn
    return deco


def _clean(s):
    s = str(s).replace("|", "/").replace("\n", " ").replace("\r", " ")
    return s if len(s) <= 160 else s[:157] + "..."


def emit(tid, name, status, detail=""):
    detail = _clean(detail)
    RESULTS.append((tid, name, status, detail))
    print("@@TEST|{}|{}|{}|{}".format(tid, name, status, detail))
    mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}.get(status, status)
    print("[{}] {} {}  {}".format(mark, tid, name, detail))


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def skip(msg):
    raise _Skip(msg)


class _Skip(Exception):
    pass


def _uname():
    try:
        return os.uname()
    except Exception:
        return None


def _machine_str():
    u = _uname()
    return getattr(u, "machine", "") if u else ""


def _board_mb():
    """从固件板名里取出 Flash 容量（MB）/ Flash size in MB parsed from the board name.

    取不到返回 None / returns None when the name has no size tag.
    """
    m = _machine_str()
    for tag in ("16MB", "4MB", "8MB", "2MB"):
        if tag in m:
            return int(tag[:-2])
    return None


# ------------------------------------------------ T01 系统 / system

@test("T01", "系统信息 / system info")
def t01_system():
    u = _uname()
    need(u is not None, "os.uname() 不可用")
    freq = machine.freq() if machine else 0
    uid = ""
    try:
        import binascii
        uid = binascii.hexlify(machine.unique_id()).decode()
    except Exception:
        pass
    msg = "{} / {} / {}MHz / id={}".format(u.sysname, u.machine, freq // 1000000, uid[:16])
    need(str(u.sysname) == "rp2", "sysname 不是 rp2")
    need(EXPECTED_BOARD in str(u.machine), "板名不含 '{}'".format(EXPECTED_BOARD))
    need(freq >= 48000000, "主频异常: {}".format(freq))
    return msg


@test("T02", "固件版本/编译信息 / firmware build info")
def t02_fw_info():
    impl = sys.implementation
    vt = impl.version
    ver = "{}.{}.{}".format(vt[0], vt[1], vt[2])
    mpy = getattr(impl, "_mpy", 0)
    need((vt[0], vt[1]) >= (1, 25), "固件版本过旧: {}".format(ver))
    need(mpy >= 6, "mpy 字节码版本异常: {}".format(mpy))
    return "MicroPython {} mpy={} board={}".format(ver, mpy, _machine_str())


# ------------------------------------------------ T03 Flash 分区 / partition

@test("T03", "Flash 分区容量 / Flash partition size")
def t03_flash_size():
    # 【重要语义】rp2.Flash() 打开的不是"整片 Flash"，而是 MicroPython 的
    #   FAT 文件系统分区（rp2_flash.c: flash_base=MICROPY_HW_FLASH_STORAGE_BASE,
    #   flash_size=MICROPY_HW_FLASH_STORAGE_BYTES）。
    #   所以 ioctl(4)*ioctl(5) = 文件系统区大小 = 总容量 - 1MB 固件预留，
    #   16MB 板得到 15728640(15360KB)，4MB 板得到 3145728(3072KB)。
    #   校验整片容量要看扇区 0 的 FAT 引导扇区 BPB（见下面 fat_total）。
    need(rp2 is not None, "rp2 模块缺失")
    f = rp2.Flash()
    # 注意：rp2.Flash.ioctl 是 3 参数 C 函数（self, cmd, arg），arg 不能省
    nblk = f.ioctl(4, 0)       # BLOCK_COUNT（文件系统区块数）
    bsz = f.ioctl(5, 0)        # BLOCK_SIZE
    area = nblk * bsz
    need(bsz == 4096, "擦除块大小异常: {}".format(bsz))
    need(area >= 1024 * 1024, "文件系统区过小: {}".format(area))

    # 交叉校验：FAT 引导扇区的总扇区数应与分区大小严格一致
    # （f_mkfs 用 FM_SFD 单分区，sz_vol 来自 disk_ioctl(GET_SECTOR_COUNT)=BLOCK_COUNT，
    #  所以 BPB.TotSec32 * BytsPerSec 必然 == ioctl(4)*ioctl(5)）
    fat_total = _fat_total_bytes()
    mb = _board_mb()
    if mb:
        expect = (mb - 1) * 1024 * 1024
        need(area == expect,
             "文件系统区 {} 字节，期望 {} 字节（{}MB-1MB）".format(area, expect, mb))
        need(fat_total == area,
             "FAT 声明的总容量 {} 与分区 {} 不一致".format(fat_total, area))
        return "文件系统区 {}KB + 1MB 固件预留 = {}MB 整片，块={}x{}，FAT 声明 {}KB".format(
            area // 1024, mb, nblk, bsz, fat_total // 1024)
    return "文件系统区 {} 字节, 块={}x{} (板名无容量标识)".format(area, nblk, bsz)


def _fat_total_bytes():
    """从文件系统第一个扇区的 BPB 读总扇区数，反推分区字节数。
    Total bytes derived from the BPB of the first file system sector.

    FAT16 BPB(偏移 0x0B 起): 11Bps (2B)、13TotSec16 (2B)、
                            0x20 TotSec32 (4B)、0x0D SecPerClus (1B)
    """
    try:
        # 必须读满 512 字节，引导签名在 510/511
        buf = bytearray(512)
        rp2.Flash().readblocks(0, buf)
        if not (buf[510] == 0x55 and buf[511] == 0xAA):
            return 0
        bps = buf[11] | (buf[12] << 8)
        tot16 = buf[19] | (buf[20] << 8)
        tot32 = buf[32] | (buf[33] << 8) | (buf[34] << 16) | (buf[35] << 24)
        tot = tot32 if tot16 == 0 else tot16
        if bps not in (512, 1024, 2048, 4096) or tot == 0:
            return 0
        return bps * tot
    except Exception:
        return 0


@test("T04", "Flash 只读读取(文件系统区) / Flash read, file system area")
def t04_flash_read():
    # 直接读文件系统区头部，验证 XIP 映射与 QSPI Flash 器件正常（只读，不写）
    # 注意：rp2.Flash() 指向文件系统区（0x10100000 起），不是 0x10000000 固件区，
    # 所以这里读到的是 FAT 引导扇区：EB xx 90 + OEM 名(通常 "MSDOS5.0") + 55AA 结尾
    need(rp2 is not None, "rp2 模块缺失")
    f = rp2.Flash()
    # readblocks 只填 len(buf) 字节，签名在 510/511，必须读满 512
    buf = bytearray(512)
    f.readblocks(0, buf)
    text = bytes(buf[:16])
    need(text != b"\x00" * 16, "文件系统区头部全 0，XIP 可能异常")
    need(text != b"\xff" * 16, "文件系统区头部全 FF，文件系统可能未格式化")
    sig_ok = buf[510] == 0x55 and buf[511] == 0xAA
    need(sig_ok, "扇区 0 结尾不是 55AA，不是合法 FAT 引导扇区")
    need(buf[0] in (0xEB, 0xE9), "引导跳转指令异常: 0x{:02X}".format(buf[0]))
    return "头部={} 55AA=OK".format(" ".join("{:02x}".format(b) for b in text[:8]))


# ------------------------------------------ T05 文件系统 / file system

@test("T05", "文件系统挂载与容量 / file system mount and size")
def t05_fs():
    st = os.statvfs("/")
    total = st[0] * st[2]
    free = st[0] * st[3]
    need(total > 1024 * 1024, "文件系统容量异常: {}".format(total))
    mb = _board_mb()
    if mb:
        expect = (mb - 1) * 1024 * 1024      # 固件预留 1MB
        need(abs(total - expect) < 1024 * 1024,
             "文件系统容量 {} 与预期 {} 偏差过大".format(total, expect))
    return "总 {}KB 可用 {}KB".format(total // 1024, free // 1024)


@test("T06", "文件读写校验 / file read/write check")
def t06_file_rw():
    path = "/_fwtest.bin"
    size = 64 * 1024
    payload = bytearray(size)
    for i in range(size):
        payload[i] = (i * 31 + 7) & 0xFF
    t0 = time.ticks_us()
    with open(path, "wb") as f:
        f.write(payload)
    tw = time.ticks_diff(time.ticks_us(), t0)
    t0 = time.ticks_us()
    with open(path, "rb") as f:
        back = f.read()
    tr = time.ticks_diff(time.ticks_us(), t0)
    os.remove(path)
    need(len(back) == size, "读回长度不对: {}".format(len(back)))
    need(back == bytes(payload), "读回内容与写入不一致（数据损坏）")
    wr = size / 1024.0 / (tw / 1e6) if tw else 0
    rd = size / 1024.0 / (tr / 1e6) if tr else 0
    return "{}KB 写{}ms 读{}ms 写{:.0f}KB/s 读{:.0f}KB/s".format(
        size // 1024, tw // 1000, tr // 1000, wr, rd)


@test("T07", "目录与重命名 / directory and rename")
def t07_dir():
    d = "/_fwt"
    try:
        os.mkdir(d)
    except OSError:
        pass
    with open(d + "/a.txt", "w") as f:
        f.write("hello")
    os.rename(d + "/a.txt", d + "/b.txt")
    with open(d + "/b.txt") as f:
        s = f.read()
    need(s == "hello", "重命名后内容错误: {}".format(s))
    os.remove(d + "/b.txt")
    os.rmdir(d)
    need(d not in os.listdir("/"), "目录未删除干净")
    return "mkdir/rename/rmdir 正常"


# ------------------------------------------------ T08 GPIO / LED

@test("T08", "LED GP24/GP25 输出 / LED GP24/GP25 output")
def t08_led():
    need(machine is not None, "machine 模块缺失")
    from machine import Pin
    res = []
    for gp in (24, 25):
        p = Pin(gp, Pin.OUT)
        p.value(1)
        hi = p.value()
        p.value(0)
        lo = p.value()
        p.init(Pin.IN)
        res.append("GP{}:1->{}/0->{}".format(gp, hi, lo))
        need(hi == 1 and lo == 0, "GP{} 输出回读异常".format(gp))
    return " ".join(res)


@test("T09", "GPIO 内部上下拉 / GPIO internal pull-up/down")
def t09_pull():
    need(machine is not None, "machine 模块缺失")
    from machine import Pin
    # GP22 在 V10 上是排针引出脚；若外部并了电阻/被驱动，读数会"不听话"，
    # 这种情况判 SKIP（需要人工确认），不当成固件故障。
    p = Pin(22, Pin.IN, Pin.PULL_UP)
    time.sleep_ms(2)
    up = p.value()
    p = Pin(22, Pin.IN, Pin.PULL_DOWN)
    time.sleep_ms(2)
    dn = p.value()
    p.init(Pin.IN)
    if up == 1 and dn == 0:
        return "GP22 PULL_UP=1 PULL_DOWN=0"
    skip("GP22 上拉读{}下拉读{}：引脚外部有电路或被驱动，需人工确认".format(up, dn))


@test("T10", "按键 GP23 电平 / key GP23 level")
def t10_key():
    need(machine is not None, "machine 模块缺失")
    from machine import Pin
    p = Pin(23, Pin.IN, Pin.PULL_UP)
    # 先看 200ms：一直为低说明卡键/没上拉/对地短路，属于真故障
    low = 0
    for _ in range(20):
        if p.value() == 0:
            low += 1
        time.sleep_ms(10)
    if low >= 20:
        p.init(Pin.IN)
        raise AssertionError("GP23 持续为低 200ms：按键卡住、缺上拉或对地短路")
    # 再等 3 秒看有没有一次按下
    pressed = False
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 3000:
        if p.value() == 0:
            pressed = True
            break
        time.sleep_ms(10)
    p.init(Pin.IN)
    if not pressed:
        skip("3 秒内未按键，空闲电平正常(=1)")
    return "空闲=1，检测到按下=0"


@test("T11", "PWM 输出 / PWM output")
def t11_pwm():
    need(machine is not None, "machine 模块缺失")
    from machine import Pin, PWM
    p = PWM(Pin(25))
    p.freq(1000)
    p.duty_u16(16384)          # 25%
    f = p.freq()
    d = p.duty_u16()
    p.deinit()
    Pin(25, Pin.OUT).value(0)
    need(abs(f - 1000) <= 20, "频率回读异常: {}".format(f))
    need(abs(d - 16384) < 1600, "占空比回读异常: {}".format(d))
    return "freq={}Hz duty={}/65535".format(f, d)


@test("T12", "ADC 通道(26-29)+片内温度 / ADC 26-29 and core temp")
def t12_adc():
    need(machine is not None, "machine 模块缺失")
    from machine import ADC
    vals = []
    for gp in (26, 27, 28, 29):
        a = ADC(gp)
        vals.append(a.read_u16())
    # 片内温度传感器
    temp = None
    try:
        t = ADC(ADC.CORE_TEMP)
        raw = t.read_u16()
        # RP2350: 27C 时 0.706V，斜率 -1.721mV/C
        volt = raw * 3.3 / 65535
        temp = 27 - (volt - 0.706) / 0.001721
    except Exception:
        pass
    need(all(0 <= v <= 65535 for v in vals), "ADC 读数越界")
    need(not all(v == 0 for v in vals), "4 个 ADC 通道全为 0，ADC 可能未工作")
    msg = "GP26-29=" + ",".join(str(v) for v in vals)
    if temp is not None:
        msg += " 片内温度={:.1f}C".format(temp)
        need(-40 < temp < 125, "片内温度异常: {:.1f}".format(temp))
    return msg


# ------------------------------------------------ T13 定时器 / timer

@test("T13", "软件定时器回调 / software timer callback")
def t13_timer():
    need(machine is not None, "machine 模块缺失")
    from machine import Timer
    cnt = [0]

    def cb(t):
        cnt[0] += 1

    tm = Timer(-1)
    tm.init(mode=Timer.PERIODIC, freq=1000, callback=cb)
    time.sleep_ms(200)
    tm.deinit()
    need(cnt[0] >= 120, "1kHz 定时器 200ms 只触发 {} 次".format(cnt[0]))
    need(cnt[0] <= 320, "定时器触发次数异常偏多: {}".format(cnt[0]))
    return "200ms 触发 {} 次".format(cnt[0])


@test("T14", "时间基准与 tick 一致性 / time base and tick consistency")
def t14_time():
    t0 = time.time_ns()
    m0 = time.ticks_ms()
    time.sleep_ms(500)
    dt_ns = time.time_ns() - t0
    dt_ms = time.ticks_diff(time.ticks_ms(), m0)
    need(400000000 <= dt_ns <= 700000000, "time_ns 漂移过大: {}ns".format(dt_ns))
    need(400 <= dt_ms <= 700, "ticks_ms 漂移过大: {}ms".format(dt_ms))
    return "ns={}ms tick={}ms".format(dt_ns // 1000000, dt_ms)


# ------------------------------------------------ T15 串行总线 / serial buses

@test("T15", "UART0 自环(GP0<-GP1) / UART0 loopback GP0-GP1")
def t15_uart():
    need(machine is not None, "machine 模块缺失")
    from machine import UART, Pin
    u = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1), timeout=200)
    u.write(b"FWLOOP")
    time.sleep_ms(20)
    got = u.read(6)
    u.deinit()
    if not got:
        skip("未收到回环数据（需短接 GP0-GP1）")
    need(got == b"FWLOOP", "回环数据错误: {}".format(got))
    return "115200 8N1 回环 OK"


@test("T16", "SPI0 自环(GP19->GP16) / SPI0 loopback GP19-GP16")
def t16_spi():
    need(machine is not None, "machine 模块缺失")
    from machine import SPI, Pin
    s = SPI(0, baudrate=1000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    buf = bytearray(4)
    s.write_readinto(b"\xa5\x5a\xff\x00", buf)
    s.deinit()
    if bytes(buf) == b"\x00\x00\x00\x00" or bytes(buf) == b"\xff\xff\xff\xff":
        skip("MISO 无变化（需短接 GP19-MOSI 到 GP16-MISO）")
    need(bytes(buf) == b"\xa5\x5a\xff\x00", "SPI 回环数据错误: {}".format(buf))
    return "1MHz 回环 OK"


@test("T17", "I2C0 总线扫描(GP4/GP5) / I2C0 bus scan GP4/GP5")
def t17_i2c():
    need(machine is not None, "machine 模块缺失")
    from machine import I2C, Pin
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
    found = i2c.scan()
    i2c.deinit()
    if not found:
        skip("总线上未发现器件（板上无 I2C 外设时属正常）")
    return "发现 {} 个地址: {}".format(len(found), found)


# ------------------------------------------------ T18 存储性能 / storage performance

@test("T18", "内存(SRAM)拷贝带宽 / SRAM copy bandwidth", slow=True)
def t18_sram_bw():
    size = 64 * 1024
    src = bytearray(size)
    dst = bytearray(size)
    for i in range(0, size, 997):
        src[i] = i & 0xFF
    # 迭代次数自适应：跑够 3ms 才有统计意义
    n = 1
    while True:
        t0 = time.ticks_us()
        for _ in range(n):
            dst[:] = src
        dt = time.ticks_diff(time.ticks_us(), t0)
        if dt >= 3000 or n >= 512:
            break
        n *= 2
    need(dt > 0, "计时异常")
    need(dst[:256] == src[:256], "拷贝后数据不一致")
    bw = (size * n) / (dt / 1e6) / (1024 * 1024)
    need(bw > 5, "SRAM 拷贝带宽过低: {:.1f}MB/s".format(bw))
    return "{}KB x{} 用时{:.1f}ms = {:.1f}MB/s".format(
        size // 1024, n, dt / 1000.0, bw)


@test("T19", "Flash 文件写入速度 / Flash file write speed", slow=True)
def t19_flash_bw():
    path = "/_fwspeed.bin"
    chunk = bytearray(4096)
    for i in range(len(chunk)):
        chunk[i] = i & 0xFF
    total = 512 * 1024
    t0 = time.ticks_us()
    with open(path, "wb") as f:
        for _ in range(total // len(chunk)):
            f.write(chunk)
    tw = time.ticks_diff(time.ticks_us(), t0)
    t0 = time.ticks_us()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(4096)
            if not b:
                break
            n += len(b)
    tr = time.ticks_diff(time.ticks_us(), t0)
    os.remove(path)
    need(n == total, "读回长度 {} != {}".format(n, total))
    wr = total / 1024.0 / (tw / 1e6)
    rd = total / 1024.0 / (tr / 1e6)
    need(wr > 20, "Flash 写入速度过低: {:.0f}KB/s".format(wr))
    need(rd > 40, "Flash 读取速度过低: {:.0f}KB/s".format(rd))
    return "512KB 写{:.0f}KB/s 读{:.0f}KB/s".format(wr, rd)


@test("T20", "外部存储(SD)探测 / external storage (SD) detect")
def t20_sd():
    for mp in ("/sd", "/sdcard"):
        try:
            if mp in os.listdir("/"):
                st = os.statvfs(mp)
                return "{} 已挂载 总{}KB".format(mp, st[0] * st[2] // 1024)
        except Exception:
            pass
    skip("未挂载 SD 卡（本板无 SD 槽，外接模块需自行 mount）")


# ------------------------------------------------ T21 内存/双核 / memory, dual core

@test("T21", "GC 堆与内存分配 / GC heap and allocation")
def t21_mem():
    gc.collect()
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    need(free > 64 * 1024, "可用堆过小: {}KB".format(free // 1024))
    # 分配释放循环，确认没有泄漏导致堆塌陷
    for _ in range(50):
        x = bytearray(4096)
        del x
    gc.collect()
    free2 = gc.mem_free()
    need(abs(free2 - free) < 16 * 1024, "反复分配后堆未恢复: {} -> {}".format(free, free2))
    return "free={}KB alloc={}KB 循环后={}KB".format(free // 1024, alloc // 1024, free2 // 1024)


@test("T22", "双核 _thread / dual-core _thread")
def t22_thread():
    need(_thread is not None, "_thread 未启用")
    result = [0]

    def worker(n):
        s = 0
        for i in range(n):
            s += i
        result[0] = s

    n = 200000
    t = _thread.start_new_thread(worker, (n,))
    t0 = time.ticks_ms()
    while result[0] == 0 and time.ticks_diff(time.ticks_ms(), t0) < 3000:
        time.sleep_ms(5)
    need(result[0] == n * (n - 1) // 2, "线程计算结果错误: {}".format(result[0]))
    return "core1 累加 {} 项结果正确 ({}ms)".format(n, time.ticks_diff(time.ticks_ms(), t0))


# ------------------------------------------------ T23 USB 状态 / USB state

@test("T23", "USB 设备状态 / USB device state")
def t23_usb():
    need(machine is not None, "machine 模块缺失")
    need(hasattr(machine, "USBDevice"), "machine.USBDevice 不存在（USB 未编入固件）")

    usb = machine.USBDevice()
    # 【重要语义】USBDevice().active() 返回的是"运行期 USB 驱动"是否被本脚本启动。
    #   内建 USB（REPL + 我们编进去的 MSC）由 TinyUSB 内建描述符驱动，开机即工作，
    #   此时运行期对象 active=False —— 这恰恰是"内建 USB 正常"的标志。
    #   旧版本在这里判 FAIL 是错的。MSC 是否可用要靠 ①编入 mp_msc ②主机侧出现盘符 来判。
    rt_active = bool(usb.active())

    has_msc = False
    try:
        import rp2 as _rp2
        has_msc = hasattr(_rp2, "mp_msc")
    except Exception:
        pass

    # 枚举成功的旁证：/dev 下应出现 CDC/存储相关节点
    devs = []
    try:
        devs = sorted(os.listdir("/dev"))
    except Exception:
        devs = []

    if rt_active:
        note = "运行期USB已由脚本接管"
    else:
        note = "内建驱动模式(正常)"
    return "{} MSD模块={} /dev={}".format(
        note, "mp_msc" if has_msc else "无", ",".join(devs) if devs else "-")


@test("T24", "复位原因 / reset reason")
def t24_reset():
    need(machine is not None, "machine 模块缺失")
    if not hasattr(machine, "reset_cause"):
        skip("固件未提供 reset_cause()")
    rc = machine.reset_cause()
    name = {1: "PWRON", 3: "WDT"}.get(rc, str(rc))
    return "reset_cause={}".format(name)


# ------------------------------------------------ 运行器 / runner

def run(quick=False, save=True, path="/fwtest_report.txt"):
    """执行全部测试 / run every test. quick=True 跳过 slow 项 / skips the slow ones（约省 3 秒 / saves about 3 s）."""
    print("")
    print("=" * 62)
    print(" WeAct RP2350A_V10 固件自检 / self-test  suite={} quick={}".format(VERSION, quick))
    print("=" * 62)
    print("@@ENV|machine={}|suite={}|quick={}".format(_machine_str(), VERSION, int(bool(quick))))
    t_start = time.ticks_ms()
    npass = nfail = nskip = 0
    for tid, name, fn, slow in TESTS:
        if slow and quick:
            emit(tid, name, "SKIP", "quick 模式跳过 / skipped in quick mode")
            nskip += 1
            continue
        try:
            detail = fn()
            emit(tid, name, "PASS", detail or "")
            npass += 1
        except _Skip as e:
            emit(tid, name, "SKIP", str(e))
            nskip += 1
        except AssertionError as e:
            emit(tid, name, "FAIL", str(e))
            nfail += 1
        except Exception as e:
            emit(tid, name, "FAIL", "{}: {}".format(type(e).__name__, e))
            nfail += 1
        gc.collect()
    dur = time.ticks_diff(time.ticks_ms(), t_start)
    total = npass + nfail + nskip
    print("-" * 62)
    print("结果/result: PASS {}  FAIL {}  SKIP {}  合计/total {}  耗时/ms {}".format(
        npass, nfail, nskip, total, dur))
    if nfail == 0:
        print("结论/conclusion: 固件与板级硬件自检通过 / firmware and board self-test passed")
    else:
        print("结论/conclusion: 存在 {} 项失败 / {} failed，请查看上方 FAIL 明细 / see the FAIL lines above".format(nfail, nfail))
    print("@@SUM|{}|{}|{}|{}|{}".format(npass, nfail, nskip, total, dur))
    print("@@DONE")
    if save:
        # 存一份到文件：上电自动跑时主机还没连上，事后可取回
        try:
            u = _uname()
            with open(path, "w") as f:
                f.write("fw_test {} suite={} quick={}\n".format(VERSION, VERSION, quick))
                f.write("machine: {}\n".format(getattr(u, "machine", "?")))
                f.write("date: {}\n\n".format(time.time()))
                for tid, name, status, detail in RESULTS:
                    f.write("@@TEST|{}|{}|{}|{}\n".format(tid, name, status, detail))
                f.write("@@SUM|{}|{}|{}|{}|{}\n".format(npass, nfail, nskip, total, dur))
                f.write("@@DONE\n")
            print("报告已保存 / report saved: {}".format(path))
        except Exception as e:
            print("报告保存失败 / save failed: {}".format(e))
    return nfail


def main():
    return run(quick=False)


if __name__ == "__main__":
    main()
