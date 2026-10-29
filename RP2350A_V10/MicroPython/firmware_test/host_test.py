#!/usr/bin/env python3
"""host_test.py -- PC 端驱动 WeAct RP2350A_V10 固件自检并生成报告
                  Drive the WeAct RP2350A_V10 self-test from a PC and build a report.

用法 / Usage:
    # 1. 直接跑（需要 pip install mpremote pyserial）
    #    run directly (needs: pip install mpremote pyserial)
    python3 host_test.py --port /dev/ttyACM0

    # 2. Windows
    python3 host_test.py --port COM7

    # 3. 取回上电自动自检的结果（main.py 已保存到 /fwtest_report.txt）
    #    fetch the result saved by main.py at power-up
    python3 host_test.py --port /dev/ttyACM0 --fetch

    # 4. 没有板子时解析已有日志
    #    parse an existing log without a board
    python3 host_test.py --log capture.txt

产物 / Output: fwtest_report_YYYYmmdd_HHMMSS.md 与同名 .json / plus a .json file
退出码 / Exit code: 0 全通过（允许 SKIP）/ all passed (SKIP allowed)；
                    1 有 FAIL / some test failed；2 环境或连接错误 / env or connect error
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FW_TEST = os.path.join(HERE, "fw_test.py")
DEVICE_REPORT = "/fwtest_report.txt"

RE_TEST = re.compile(r"^@@TEST\|([^|]*)\|([^|]*)\|([^|]*)\|(.*)$")
RE_SUM = re.compile(r"^@@SUM\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_ENV = re.compile(r"^@@ENV\|machine=([^|]*)\|suite=([^|]*)\|quick=(\d)$")


def parse(text):
    """从串口/日志文本里抓 @@TEST 与 @@SUM / parse @@TEST and @@SUM lines.\n\n    返回 (rows, summary) / returns (rows, summary).\n    """
    rows, summary = [], None
    for line in text.splitlines():
        line = line.strip()
        m = RE_TEST.match(line)
        if m:
            rows.append({
                "id": m.group(1), "name": m.group(2),
                "status": m.group(3), "detail": m.group(4).strip(),
            })
            continue
        m = RE_SUM.match(line)
        if m:
            summary = {
                "pass": int(m.group(1)), "fail": int(m.group(2)),
                "skip": int(m.group(3)), "total": int(m.group(4)),
                "ms": int(m.group(5)),
            }
    return rows, summary


def run_mpremote(port, quick, timeout):
    """通过 mpremote 把套件送进板子执行 / run the suite on the board via mpremote.\n\n    返回 stdout 文本 / returns the stdout text.\n    """
    exe = shutil.which("mpremote")
    if not exe:
        raise RuntimeError(
            "未找到 mpremote / mpremote not found。安装/install： pip install mpremote\n"
            "或改用 / or use --log to parse a captured log.")

    with open(FW_TEST, "r", encoding="utf-8") as f:
        src = f.read()
    src += "\n\nrun(quick={}, save=True)\n".format(bool(quick))

    tmp = tempfile.NamedTemporaryFile("w", suffix="_fwtest_run.py",
                                      delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        cmd = [exe, "connect", port, "run", tmp.name]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
        out = (proc.stdout or "") + (proc.stderr or "")
        if "@@DONE" not in out and proc.returncode != 0:
            raise RuntimeError("mpremote 执行失败 / run failed（rc={}）：\n{}".format(
                proc.returncode, out[-1500:]))
        return out
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def fetch_report(port, timeout):
    exe = shutil.which("mpremote")
    if not exe:
        raise RuntimeError("未找到 mpremote / mpremote not found。安装/install： pip install mpremote")
    proc = subprocess.run([exe, "connect", port, "cat", DEVICE_REPORT],
                          capture_output=True, text=True, timeout=timeout)
    out = proc.stdout or ""
    if "@@TEST" not in out:
        raise RuntimeError("设备上没有可用的报告 / no report on the device（先跑一次自检 / run the self-test first）：\n"
                           + (proc.stderr or "")[-800:])
    return out


def write_report(rows, summary, meta):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(HERE, "fwtest_report_{}".format(ts))
    n = 1
    while os.path.exists(base + ".md"):          # 同一秒内多次运行不互相覆盖 / avoid overwriting reports created in the same second
        n += 1
        base = os.path.join(HERE, "fwtest_report_{}_{}".format(ts, n))
    md = base + ".md"
    js = base + ".json"

    npass = sum(1 for r in rows if r["status"] == "PASS")
    nfail = sum(1 for r in rows if r["status"] == "FAIL")
    nskip = sum(1 for r in rows if r["status"] == "SKIP")
    verdict = "通过 / PASS" if nfail == 0 else "不通过 / FAIL"

    lines = []
    lines.append("# WeAct RP2350A_V10 固件自检报告 / Self-test Report\n")
    lines.append("| 项目 / Item | 值 / Value |")
    lines.append("|---|---|")
    lines.append("| 结论 / Verdict | **{}** |".format(verdict))
    lines.append("| 时间 / Time | {} |".format(meta.get("time", "")))
    lines.append("| 端口/来源 / Source | {} |".format(meta.get("source", "")))
    lines.append("| 固件板名 / Board | {} |".format(meta.get("machine", "—")))
    lines.append("| 套件版本 / Suite | {} |".format(meta.get("suite", "—")))
    lines.append("| 统计 / Counts | PASS {} / FAIL {} / SKIP {} / 共 {} total |".format(
        npass, nfail, nskip, len(rows)))
    if summary:
        lines.append("| 板端耗时 / Board time | {:.1f} s |".format(summary["ms"] / 1000.0))
    lines.append("")

    if nfail:
        lines.append("## 失败项 / Failed（需处理 / action needed）\n")
        lines.append("| 编号 / ID | 测试项 / Test | 现象 / Detail |")
        lines.append("|---|---|---|")
        for r in rows:
            if r["status"] == "FAIL":
                lines.append("| {} | {} | {} |".format(
                    r["id"], r["name"], r["detail"].replace("|", "/")))
        lines.append("")

    if nskip:
        lines.append("## 跳过项 / Skipped（需人工确认 / manual check）\n")
        lines.append("| 编号 / ID | 测试项 / Test | 原因 / Reason |")
        lines.append("|---|---|---|")
        for r in rows:
            if r["status"] == "SKIP":
                lines.append("| {} | {} | {} |".format(
                    r["id"], r["name"], r["detail"].replace("|", "/")))
        lines.append("")

    lines.append("## 全部结果 / All Results\n")
    lines.append("| 编号 / ID | 测试项 / Test | 结果 / Result | 详情 / Detail |")
    lines.append("|---|---|---|---|")
    icon = {"PASS": "PASS", "FAIL": "**FAIL**", "SKIP": "SKIP"}
    for r in rows:
        lines.append("| {} | {} | {} | {} |".format(
            r["id"], r["name"], icon.get(r["status"], r["status"]),
            r["detail"].replace("|", "/")))
    lines.append("")
    lines.append("> 报告由 host_test.py 自动生成 / generated by host_test.py；"
                 "SKIP 不等于失败 / SKIP is not a failure，"
                 "但涉及外设的 SKIP 需人工确认是否属于预期 / verify peripheral SKIPs manually.\n")

    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "summary": summary, "results": rows},
                  f, ensure_ascii=False, indent=2)
    return md, js, verdict


def main():
    ap = argparse.ArgumentParser(description="RP2350A_V10 固件自检驱动")
    ap.add_argument("--port", help="串口，如 /dev/ttyACM0 或 COM7")
    ap.add_argument("--log", help="解析已有日志文件（无板子时用）")
    ap.add_argument("--fetch", action="store_true",
                    help="取回设备上 /fwtest_report.txt（上电自动跑的结果）")
    ap.add_argument("--quick", action="store_true", help="跳过耗时的性能测试")
    ap.add_argument("--timeout", type=int, default=120, help="超时秒数")
    args = ap.parse_args()

    try:
        if args.log:
            with open(args.log, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            source = "log:" + os.path.basename(args.log)
        elif args.fetch:
            text = fetch_report(args.port, args.timeout)
            source = "fetch " + args.port
        elif args.port:
            text = run_mpremote(args.port, args.quick, args.timeout)
            source = "mpremote " + args.port
        else:
            ap.error("需要 --port 或 --log 之一")
    except subprocess.TimeoutExpired:
        print("错误：执行超时（{}s）。检查端口是否正确、板子是否在 REPL。".format(
            args.timeout), file=sys.stderr)
        return 2
    except Exception as e:
        print("错误：{}".format(e), file=sys.stderr)
        return 2

    rows, summary = parse(text)
    if not rows:
        print("没有解析到任何测试结果。原始输出末尾：\n" + text[-1200:],
              file=sys.stderr)
        return 2

    machine = ""
    suite = ""
    for line in text.splitlines():
        m = RE_ENV.match(line.strip())
        if m:
            machine, suite = m.group(1).strip(), m.group(2).strip()
            break
    if not machine:                       # 兼容设备端保存的报告文件
        for line in text.splitlines():
            if line.startswith("machine:"):
                machine = line.split(":", 1)[1].strip()
            if line.startswith("fw_test") and "suite=" in line:
                suite = line.split("suite=", 1)[1].split()[0]

    meta = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source, "machine": machine, "suite": suite,
    }
    md, js, verdict = write_report(rows, summary, meta)

    # 控制台摘要
    print("")
    print("{:<5} {:<24} {:<6} {}".format("编号", "测试项", "结果", "详情"))
    print("-" * 88)
    for r in rows:
        print("{:<5} {:<24} {:<6} {}".format(
            r["id"], r["name"][:22], r["status"], r["detail"][:44]))
    print("-" * 88)
    nfail = sum(1 for r in rows if r["status"] == "FAIL")
    print("结论: {}  (FAIL {}/{}，报告: {})".format(
        verdict, nfail, len(rows), os.path.basename(md)))
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
