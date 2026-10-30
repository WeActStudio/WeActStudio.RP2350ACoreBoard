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
Host-side driver for the WeAct RP2350A Core V20 firmware self-test.
PC 端驱动：通过串口运行板端套件、解析结果、生成 Markdown + JSON 报告。

Quick start / 快速开始
    pip install pyserial mpremote
    python3 host_test.py --port /dev/ttyACM0
    python3 host_test.py --port COM7 --quick
    python3 host_test.py --port /dev/ttyACM0 --fetch
    python3 host_test.py --log sim.log          # parse an existing log

Exit codes / 退出码
    0  all PASS (SKIP allowed) / 全通过
    1  at least one FAIL / 有失败项
    2  environment or connection error / 环境或连接错误
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

BAUD = 115200
BOARD = "WeAct Studio RP2350A Core V20"

RE_TEST = re.compile(r"^@@TEST (\S+) (PASS|FAIL|SKIP) (.*?) (.*)$")
RE_SUM = re.compile(r"^@@SUM (\d+) (\d+) (\d+) (\d+)")
RE_INFO = re.compile(r"^@@INFO (\S+) (.*)$")


# ---------------------------------------------------------------------------
# Parsing / 解析
# ---------------------------------------------------------------------------

class Result:
    def __init__(self):
        self.cases = []          # (tid, status, name, detail)
        self.infos = {}          # key -> value
        self.summary = None      # (pass, fail, skip, total)
        self.raw = []

    def feed(self, line):
        line = line.rstrip("\r\n")
        if not line:
            return
        self.raw.append(line)

        m = RE_TEST.match(line)
        if m:
            self.cases.append((m.group(1), m.group(2), m.group(3), m.group(4)))
            return
        m = RE_SUM.match(line)
        if m:
            self.summary = tuple(int(x) for x in m.groups())
            return
        m = RE_INFO.match(line)
        if m:
            self.infos[m.group(1)] = m.group(2)
            return

    def counts(self):
        p = sum(1 for c in self.cases if c[1] == "PASS")
        f = sum(1 for c in self.cases if c[1] == "FAIL")
        s = sum(1 for c in self.cases if c[1] == "SKIP")
        return p, f, s

    def failed(self):
        return [c for c in self.cases if c[1] == "FAIL"]


# ---------------------------------------------------------------------------
# Device run over serial / 串口运行
# ---------------------------------------------------------------------------

def _open_serial(port, baud, timeout=1):
    try:
        import serial
    except ImportError:
        sys.stderr.write(
            "pyserial is missing / 缺少 pyserial:\n"
            "    pip install pyserial\n")
        raise SystemExit(2)
    try:
        return serial.Serial(port, baud, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("cannot open %s: %s\n" % (port, e))
        sys.stderr.write(
            "close any other REPL (mpremote, Thonny, screen) first\n"
            "先关掉其它占用串口的程序\n")
        raise SystemExit(2)


def _interrupt(ser):
    """Ctrl-C twice + a newline to break out of a running script."""
    ser.write(b"\r\x03\x03")
    time.sleep(0.2)
    ser.reset_input_buffer()


def run_over_serial(port, baud, quick, only, timeout):
    ser = _open_serial(port, baud)
    res = Result()
    try:
        _interrupt(ser)

        # Soft reboot into a clean state, then import the suite.
        # 软重启得到干净状态，再导入套件。
        ser.write(b"\x02")              # Ctrl-B soft reboot
        time.sleep(1.2)
        ser.reset_input_buffer()

        kwargs = []
        if quick:
            kwargs.append("quick=True")
        if only:
            kwargs.append("only=%r" % only)
        cmd = "import fw_test; fw_test.run(%s)\r" % ", ".join(kwargs)
        ser.write(cmd.encode())

        t0 = time.time()
        seen_sum = False
        while time.time() - t0 < timeout:
            line = ser.readline().decode("utf-8", "replace")
            if not line:
                if seen_sum:
                    break
                continue
            res.feed(line)
            if line.startswith("@@TEST") or line.startswith("@@SUM") or line.startswith("@@INFO"):
                sys.stdout.write(line)
                sys.stdout.flush()
            if res.summary and not seen_sum:
                seen_sum = True
                # drain a little more for the trailing @@INFO lines
                t0 = time.time() - timeout + 1.5
    finally:
        ser.close()
    return res


def fetch_report(port, baud):
    """Read /fwtest_report.txt saved by the board / 取回板端已存报告"""
    ser = _open_serial(port, baud)
    res = Result()
    try:
        _interrupt(ser)
        ser.write(b"\x02")
        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.write(
            b"import sys\rprint('@@BEGIN')\r"
            b"f=open('/fwtest_report.txt')\r"
            b"sys.stdout.write(f.read())\rf.close()\r"
            b"print('@@END')\r")
        t0 = time.time()
        inside = False
        while time.time() - t0 < 15:
            line = ser.readline().decode("utf-8", "replace")
            if "@@BEGIN" in line:
                inside = True
                continue
            if "@@END" in line:
                break
            if inside and line.strip():
                # Convert the plain text report back into @@ lines
                parts = line.rstrip("\r\n").split(None, 3)
                if len(parts) >= 2 and re.match(r"^T\d\d$", parts[0]):
                    res.feed("@@TEST %s %s %s" % (parts[0], parts[1],
                                                  (parts[2] if len(parts) > 2 else "")))
    finally:
        ser.close()
    return res


def parse_log(path):
    res = Result()
    with open(path, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            res.feed(line)
    return res


# ---------------------------------------------------------------------------
# Reports / 报告生成
# ---------------------------------------------------------------------------

def write_reports(res, outdir="."):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(outdir, "fwtest_report_%s" % stamp)
    p, f, s = res.counts()

    md = []
    md.append("# %s firmware self-test report" % BOARD)
    md.append("")
    md.append("| item | value |")
    md.append("|---|---|")
    md.append("| generated | %s |" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    md.append("| board | %s |" % BOARD)
    for k in ("sysname", "machine", "release", "freq", "flash_total",
              "fs_declared", "fs_mounted", "temp_c", "reset_cause"):
        if k in res.infos:
            md.append("| %s | %s |" % (k, res.infos[k]))
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append("PASS **%d** / FAIL **%d** / SKIP **%d** / TOTAL **%d**" %
              (p, f, s, len(res.cases)))
    md.append("")

    fails = res.failed()
    if fails:
        md.append("> FAIL: the board needs attention. See the table below.")
    elif s:
        md.append("> OK. SKIP items are missing external wiring, not a fault.")
    else:
        md.append("> OK. All cases passed.")
    md.append("")

    md.append("## Cases")
    md.append("")
    md.append("| id | case | result | detail |")
    md.append("|---|---|---|---|")
    for tid, status, name, detail in res.cases:
        md.append("| %s | %s | %s | %s |" % (tid, name, status, detail))
    md.append("")

    if res.raw:
        md.append("## Raw log")
        md.append("")
        md.append("```")
        md.extend(res.raw[-200:])
        md.append("```")
        md.append("")

    md_path = base + ".md"
    with open(md_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(md))

    js_path = base + ".json"
    with open(js_path, "w", encoding="utf-8") as fp:
        json.dump({
            "board": BOARD,
            "timestamp": stamp,
            "counts": {"pass": p, "fail": f, "skip": s, "total": len(res.cases)},
            "cases": [{"id": t, "status": st, "name": n, "detail": d}
                      for t, st, n, d in res.cases],
            "info": res.infos,
        }, fp, ensure_ascii=False, indent=2)

    return md_path, js_path


def print_summary(res):
    p, f, s = res.counts()
    print()
    print("-" * 58)
    print("PASS=%d FAIL=%d SKIP=%d TOTAL=%d" % (p, f, s, len(res.cases)))
    if f:
        print("FAILED CASES:")
        for tid, status, name, detail in res.failed():
            print("  %s  %s  %s" % (tid, name, detail))
    print("-" * 58)


# ---------------------------------------------------------------------------
# CLI / 命令行
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="WeAct RP2350A Core V20 MicroPython self-test (host side)")
    ap.add_argument("--port", help="serial port, e.g. /dev/ttyACM0 or COM7")
    ap.add_argument("--baud", type=int, default=BAUD)
    ap.add_argument("--quick", action="store_true", help="skip speed cases T18/T19")
    ap.add_argument("--only", help="comma separated case ids, e.g. T01,T03,T08")
    ap.add_argument("--fetch", action="store_true",
                    help="read /fwtest_report.txt already saved on the board")
    ap.add_argument("--log", help="parse a saved log file instead of a port")
    ap.add_argument("--timeout", type=int, default=180, help="seconds per run")
    ap.add_argument("--outdir", default=".", help="where to write reports")
    args = ap.parse_args(argv)

    if args.log:
        res = parse_log(args.log)
    elif args.fetch:
        if not args.port:
            ap.error("--fetch needs --port")
        res = fetch_report(args.port, args.baud)
    elif args.port:
        res = run_over_serial(args.port, args.baud, args.quick, args.only, args.timeout)
    else:
        ap.error("give --port, --log or --fetch --port")

    if not res.cases:
        sys.stderr.write("no @@TEST lines found / 没有解析到用例结果\n")
        return 2

    print_summary(res)
    md, js = write_reports(res, args.outdir)
    print("report: %s" % md)
    print("json  : %s" % js)

    _, f, _ = res.counts()
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
