# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
"""
Auto-run entry point for the WeAct RP2350A Core V20 self-test suite.
上电自动运行入口。

Copy main.py + fw_test.py to the root of the "MicroPython" USB drive.
把 main.py 与 fw_test.py 拷到 MicroPython 盘根目录即可。

The delay before the run gives the host time to enumerate the USB device,
otherwise the first lines are lost on a cold plug.
开跑前先等 2 秒，让主机完成 USB 枚举，否则冷插时前几行输出会丢。
"""

import sys
import time

# Give the host USB stack time to attach / 等主机完成枚举
time.sleep(2)

print()
print("=" * 58)
print(" WeAct Studio RP2350A Core V20 - firmware self-test")
print("=" * 58)

try:
    import fw_test
except ImportError:
    print("fw_test.py not found next to main.py / 同目录缺少 fw_test.py")
    print("Skipping self-test, dropping to REPL.")
    fw_test = None

if fw_test is not None:
    # quick=False: include the two throughput cases / 含两个吞吐量用例
    p, f, s = fw_test.run(quick=False)

    print("-" * 58)
    print("PASS=%d FAIL=%d SKIP=%d TOTAL=%d" % (p, f, s, p + f + s))
    if f:
        print("RESULT: FAIL - see the FAIL lines above / 见上方 FAIL 行")
    else:
        print("RESULT: OK (SKIP lines need extra wiring, not a fault)")
        print("        SKIP 属于未接线，不是故障")

    try:
        path = fw_test.save_report()
        print("report saved to %s" % path)
    except OSError as e:
        print("could not save report: %s" % e)

print("=" * 58)
print("done, REPL available / 自检结束，可直接使用 REPL")
