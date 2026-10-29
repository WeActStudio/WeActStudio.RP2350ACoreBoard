# main.py - 上电自动自检入口 / power-up self-test entry
#
# 放到 U 盘（MicroPython 盘）根目录即可，每次上电/复位自动跑一遍。
# 跑完结果同时存到 /fwtest_report.txt，PC 端可用 host_test.py 取回。
# Copy this file to the MicroPython drive root; it runs on every power-up or
# reset. The result is also saved to /fwtest_report.txt and can be fetched from
# a PC with host_test.py.
#
# 不想每次上电都跑：改名成 selftest.py，需要时 REPL 里 `import selftest`。
# To disable it, rename the file to selftest.py and run `import selftest`.

import time

# 等 USB 枚举 + 主机挂盘完成，否则前面的输出会丢
# wait for USB enumeration and mounting, otherwise the first lines are lost
time.sleep(2)

try:
    import fw_test
    fw_test.run(quick=False, save=True)
except Exception as e:
    print("自检启动失败 / self-test failed to start:", e)
    print("请确认 fw_test.py 与 main.py 在同一目录（U 盘根目录）")
    print("make sure fw_test.py is in the same directory (the drive root)")
