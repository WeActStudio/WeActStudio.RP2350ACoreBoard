#!/usr/bin/env python3
# =============================================================================
#  WeAct Studio Official Link
#    taobao     : weactstudio.taobao.com
#    aliexpress : weactstudio.aliexpress.com
#    github     : github.com/WeActStudio
#    gitee      : gitee.com/WeAct-TC
#    blog      : www.weact-tc.cn
# =============================================================================
"""check_pico2_parity.py -- 校验 V20 板级头是否仍与 pico2.h 一致
                           Verify the V20 board header still matches pico2.h

V20 与 Pico 2 硬件一致，只有 Flash 容量不同。板级头是 pico2.h 的手抄副本，
因此一旦 pico-sdk 升级改了 pico2.h，本文件就有可能与上游漂移。
这个脚本把"两边只差 FLASH 和板名"这句话变成可执行的检查。

V20 is hardware-identical to Pico 2 apart from the Flash size, so the board
header is a hand-maintained copy of pico2.h. After a pico-sdk bump the copy can
silently drift. This script turns "they only differ in FLASH and the board name"
into a check you can actually run.

用法 / Usage:
    python3 tools/check_pico2_parity.py
    python3 tools/check_pico2_parity.py --pico2 /path/to/pico-sdk/src/boards/include/boards/pico2.h

退出码 / Exit code: 0 = 一致, 1 = 有意外差异, 2 = 找不到头文件
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_HEADER = os.path.join(
    HERE, os.pardir, "board_files", "WEACTSTUDIO_RP2350A_CORE_V20",
    "weact_studio_rp2350a_core_v20.h")

# 允许存在的差异 / differences that are expected
ALLOWED_ONLY_PICO2 = {"RASPBERRYPI_PICO2", "_BOARDS_PICO2_H"}
ALLOWED_ONLY_V20 = {"WEACT_STUDIO_RP2350A_CORE_V20",
                    "_BOARDS_WEACT_STUDIO_RP2350A_CORE_V20_H"}
ALLOWED_VALUE_DIFF = {"PICO_FLASH_SIZE_BYTES"}


def parse(path):
    """返回 (宏字典, pico_board_cmake_set 行列表) / returns (defines, cmake lines)."""
    defines = {}
    cmake = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            st = line.strip()
            if st.startswith("//") or not st:
                continue
            m = re.match(r"#define\s+(\w+)\s*(.*)$", st)
            if m:
                defines[m.group(1)] = m.group(2).strip()
            elif st.startswith("pico_board_cmake_set"):
                cmake.append(st)
    return defines, cmake


def find_pico2(explicit):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    # 在常见的 pico-sdk 位置上找 / look in the usual pico-sdk places
    guesses = [
        os.path.join(HERE, os.pardir, os.pardir, "lib", "pico-sdk",
                     "src", "boards", "include", "boards", "pico2.h"),
        os.path.join(HERE, os.pardir, "lib", "pico-sdk",
                     "src", "boards", "include", "boards", "pico2.h"),
        os.path.expanduser("~/pico-sdk/src/boards/include/boards/pico2.h"),
    ]
    for g in guesses:
        if os.path.exists(g):
            return os.path.normpath(g)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="check V20 board header against pico2.h")
    ap.add_argument("--pico2", default=None, help="path to pico2.h")
    args = ap.parse_args(argv)

    pico2_path = find_pico2(args.pico2)
    if not pico2_path:
        print("找不到 pico2.h，用 --pico2 指定路径")
        print("pico2.h not found, pass --pico2 <path>")
        return 2

    print("pico2.h : %s" % pico2_path)
    print("V20     : %s" % os.path.normpath(BOARD_HEADER))
    print()

    p2, c2 = parse(pico2_path)
    v20, c20 = parse(BOARD_HEADER)

    problems = []

    only_p2 = sorted(set(p2) - set(v20) - ALLOWED_ONLY_PICO2)
    only_v20 = sorted(set(v20) - set(p2) - ALLOWED_ONLY_V20)
    value_diff = [(k, p2[k], v20[k]) for k in sorted(set(p2) & set(v20))
                  if p2[k] != v20[k] and k not in ALLOWED_VALUE_DIFF]

    if only_p2:
        problems.append("pico2.h 有但 V20 缺 / missing in V20: %s" % ", ".join(only_p2))
    if only_v20:
        problems.append("V20 多出来 / extra in V20: %s" % ", ".join(only_v20))
    for k, a, b in value_diff:
        problems.append("%s: pico2=%s, v20=%s" % (k, a, b))

    # cmake 声明除 FLASH 默认值外应完全一致
    # the cmake declarations must match apart from the FLASH default
    def norm(lines):
        out = []
        for ln in lines:
            out.append(re.sub(r"\(4 \* 1024 \* 1024\)|\(16 \* 1024 \* 1024\)",
                              "(FLASH)", ln))
        return out
    if norm(c2) != norm(c20):
        problems.append("pico_board_cmake_set 声明不一致 / cmake declarations differ:\n"
                        "  pico2: %s\n  v20  : %s" % (c2, c20))

    # FLASH 差异本身必须存在，否则说明默认值写错了
    # the FLASH difference must exist, otherwise the default is wrong
    if p2.get("PICO_FLASH_SIZE_BYTES") == v20.get("PICO_FLASH_SIZE_BYTES"):
        problems.append("PICO_FLASH_SIZE_BYTES 与 pico2.h 相同，V20 默认应为 16MB")

    if problems:
        print("FAIL - 发现意外差异 / unexpected differences:")
        for p in problems:
            print("  - " + p)
        return 1

    print("PASS - 除 FLASH 容量与板名外，与 pico2.h 完全一致")
    print("       identical to pico2.h except for the Flash size and board name")
    print()
    shared = len(set(p2) & set(v20))
    print("  共享宏 %d 个 / %d shared macros" % (shared, shared))
    print("  PICO_FLASH_SIZE_BYTES: pico2=%s  v20=%s"
          % (p2.get("PICO_FLASH_SIZE_BYTES"), v20.get("PICO_FLASH_SIZE_BYTES")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
