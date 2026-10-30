# WeAct RP2350A Core V20 Firmware Self-Test Suite

[中文版](README.md)

---

Works with the MicroPython v1.29.0 images in `firmware16M/` or `firmware4M/`.

Purpose: confirm the board and the board-level configuration after flashing, and
produce an archivable report.

## Files

| File | Purpose |
|---|---|
| `fw_test.py` | the suite itself, 26 cases, emits `@@TEST` / `@@SUM` |
| `main.py` | auto-run entry, also saves `/fwtest_report.txt` |
| `host_test.py` | PC-side driver and report generator (Markdown + JSON) |
| `tools/mpy_sim.py` | run the suite without a board |

## Running it

**1. Copy to the drive and let it auto-run**

Put `main.py` and `fw_test.py` in the root of the `MicroPython` drive, then press
RESET. The board waits 2s for USB enumeration, runs the suite, prints to the
serial port and writes `/fwtest_report.txt`.

**2. One command from the PC**

```bash
pip install pyserial

python3 host_test.py --port /dev/ttyACM0
python3 host_test.py --port COM7
python3 host_test.py --port /dev/ttyACM0 --quick     # skip speed cases
python3 host_test.py --port /dev/ttyACM0 --fetch     # pull the saved report
```

Output: `fwtest_report_YYYYmmdd_HHMMSS.md` plus a matching `.json`.

Exit codes: 0 all passed (SKIP allowed), 1 at least one FAIL, 2 environment error.

**3. From the REPL**

```python
import fw_test
fw_test.run()
fw_test.run(quick=True)
fw_test.run(only="T01,T03")
```

## The 26 cases

| ID | Case | Pass condition |
|---|---|---|
| T01 | System info | `sysname=rp2`, board name contains `WeAct Studio RP2350A Core V20`, freq >= 48MHz |
| T02 | Firmware version | MicroPython >= 1.25, prints mpy version |
| T03 | Flash partition | `ioctl(4)*ioctl(5)` = capacity - 1MB, cross-checked against the FAT BPB |
| T04 | Flash read-only | sector 0 has `EB xx 90`, the OEM name and the `55AA` signature |
| T05 | File system | `statvfs("/")` total ~ capacity - 1MB |
| T06 | File read/write | 64KB written then byte-compared, also reports throughput |
| T07 | Directories | mkdir / rename / rmdir |
| T08 | LED GP25 | output read-back 1/0 |
| T09 | Internal pulls | GP22 pull-up=1, pull-down=0 |
| T10 | External key GP15 | FAIL only if held low 1.5s; PASS if pressed within 3s, else SKIP |
| T11 | PWM | GP25 1kHz, 25% duty read-back |
| T12 | ADC + die temp | GP26/27/28 readings, temperature within -40..125C |
| T13 | Software timer | 1kHz for 200ms, 120..320 callbacks |
| T14 | Time base | `time_ns` agrees with `ticks_ms` over 500ms |
| T15 | UART0 loopback | needs GP0-GP1 shorted, otherwise SKIP |
| T16 | SPI0 loopback | needs GP19-GP16 shorted, otherwise SKIP |
| T17 | I2C0 scan | GP4/GP5, SKIP when nothing answers |
| T18 | Memory bandwidth | > 5MB/s |
| T19 | FS throughput | 512KB, write > 20KB/s, read > 40KB/s |
| T20 | External storage | reports capacity of `/sd` or `/sdcard` when mounted |
| T21 | GC heap | > 64KB free, no leak after 50 x 4KB allocations |
| T22 | Dual core | core1 result via `_thread` is correct |
| T23 | USB device API | `rp2.Flash` and `machine.bootloader` present |
| T24 | Reset cause | prints PWRON / WDT / SOFT etc. |
| T25 | VSYS rail | GP29 reading x2, must sit in 2.8-5.8V; SKIP when fed from the 3V3 pin |
| T26 | VBUS sense | GP24 digital read, cross-checked against VSYS for power-path faults |

**SKIP is not a failure**: no key fitted for T10, no wires for T15/T16, no I2C
device for T17, no SD card for T20 are all normal.

## V20 vs V10 differences

V20 is hardware-identical to Pico 2, so the V20 column below must equal the
Pico 2 column everywhere -- any difference is a bug.

| Case | V10 | Pico 2 | V20 |
|---|---|---|---|
| T08 LED | GP24 blue + GP25 green | single LED on GP25 | **same as Pico 2** |
| T10 key | onboard GP23 | no key | **same as Pico 2** (wire GP15-GND) |
| T12 ADC | GP26-GP29 | GP26/27/28, GP29 for VSYS | **same as Pico 2** |
| T25 VSYS | none | GP29 + 100K/100K | **same as Pico 2** |
| T26 VBUS | none | GP24 + 100K/100K | **same as Pico 2** |
| T01 board name | `WeAct RP2350A Core V10` | `Raspberry Pi Pico2` | `WeAct Studio RP2350A Core V20` |

## Reading the result

| Result | Meaning |
|---|---|
| All PASS, a few SKIP | board is good |
| T03 FAIL | firmware does not match the Flash size, flash the matching image |
| T05/T06 FAIL | file system did not mount, check you flashed the `-msc` image |
| T10 FAIL | GP15 stuck low, check for a short to GND |
| T19 low | check Flash soldering and QSPI routing |
| T21 FAIL | heap does not recover after repeated allocation |

## Running without a board

```bash
python3 tools/mpy_sim.py --mb 16
python3 tools/mpy_sim.py --mb 4
python3 tools/mpy_sim.py --mb 16 --uart-loop --spi-loop --i2c --key --sd
python3 tools/mpy_sim.py --mb 16 --quick
python3 tools/mpy_sim.py --mb 16 --out sim.log
python3 host_test.py --log sim.log
```

The simulator swaps `machine` / `rp2` / `_thread` / `time.ticks_*` for stubs and
redirects every path starting with `/` into a temp directory; it never touches
your real file system. It validates the test logic and the output protocol only,
and is **not** a substitute for on-board verification.

Expected result with defaults (16MB, USB powered): `@@SUM 21 0 5 26` (the 5 SKIPs
are key, UART, SPI, I2C and SD). With every peripheral switch on: `@@SUM 26 0 0 26`.
Back-fed from the 3V3 pin (`--vsys 0 --no-vbus`), T25/T26 both SKIP: `@@SUM 19 0 7 26`.

## Known limits

1. T23 only checks that the device-side APIs exist. The built-in USB (REPL + MSC)
   is driven by TinyUSB's own descriptors; whether MSC works is visible on the
   host as a drive letter.
2. The suite deliberately skips reset, WDT and deepsleep so it never drops the
   USB connection. Reset behaviour is covered by T24 plus a manual power cycle.
3. T10 needs a human to press the external key inside the 3s window. Unattended
   runs will report SKIP, which is expected.
