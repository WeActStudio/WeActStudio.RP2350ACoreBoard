# WeAct RP2350A_V10 Firmware Self-Test Suite

[简体中文](./README.md)

---

Firmware: MicroPython v1.29.0 from `firmware16M/` or `firmware4M/`.

Purpose: verify the board after flashing and produce an archivable report.

## Files

| File | Purpose |
|---|---|
| `fw_test.py` | the suite itself, 24 test cases, outputs the `@@TEST` / `@@SUM` protocol |
| `main.py` | power-up entry, also saves `/fwtest_report.txt` |
| `host_test.py` | host driver and report generator (Markdown + JSON) |
| `tools/mpy_sim.py` | simulated run without a board |

## How to Run

**1. Copy to the drive, run at power-up**

Copy `main.py` and `fw_test.py` to the `MicroPython` drive root, then press RUN or
reset. After a 2-second wait for USB enumeration the suite runs, prints to the
serial port and saves `/fwtest_report.txt`.

**2. One command from the PC**

```bash
pip install mpremote pyserial

python3 host_test.py --port /dev/ttyACM0             # Linux
python3 host_test.py --port COM7                     # Windows
python3 host_test.py --port /dev/ttyACM0 --quick     # skip the slow tests
python3 host_test.py --port /dev/ttyACM0 --fetch     # fetch the saved result
```

Output: `fwtest_report_YYYYmmdd_HHMMSS.md` plus a matching `.json`.

Exit code: 0 all passed (SKIP allowed), 1 a FAIL occurred, 2 environment or
connection error.

**3. Run manually in the REPL**

```python
import fw_test
fw_test.run()            # quick=True skips the slow tests
```

## The 24 Test Cases

| ID | Test | Criterion |
|---|---|---|
| T01 | system info | `sysname=rp2`, board name contains `WeAct RP2350A Core V10`, clock >= 48 MHz |
| T02 | build info | MicroPython >= 1.25, mpy >= 6 |
| T03 | partition size | `ioctl(4)*ioctl(5)` = capacity - 1 MB, cross-checked against the FAT BPB |
| T04 | Flash read | sector 0 holds `EB xx 90`, the OEM name and the `55AA` signature |
| T05 | mount and size | `statvfs` total close to capacity - 1 MB |
| T06 | file read/write | 64 KB written then compared byte by byte |
| T07 | directory, rename | mkdir / rename / rmdir |
| T08 | LED output | GP24 and GP25 read back 1 / 0 |
| T09 | pull-up and pull-down | GP22 pull-up = 1, pull-down = 0 |
| T10 | key level | stuck low for 200 ms is a fault; a press within 3 s passes, otherwise SKIP |
| T11 | PWM output | GP25 at 1 kHz and 25% duty, read back |
| T12 | ADC and core temp | GP26-29 readings, temperature within -40 to 125 C |
| T13 | timer callback | 1 kHz for 200 ms, 120-320 callbacks |
| T14 | time base | `time_ns` agrees with `ticks_ms` over 500 ms |
| T15 | UART0 loopback | needs GP0-GP1 jumpered, otherwise SKIP |
| T16 | SPI0 loopback | needs GP19-GP16 jumpered, otherwise SKIP |
| T17 | I2C0 scan | GP4/GP5, SKIP when no device answers |
| T18 | SRAM copy bandwidth | adaptive iteration, > 5 MB/s |
| T19 | file write speed | 512 KB, write > 20 KB/s and read > 40 KB/s |
| T20 | external storage | report capacity when `/sd` or `/sdcard` is mounted |
| T21 | GC heap | free heap > 64 KB, 50 allocations of 4 KB with no leak |
| T22 | dual core | core1 computes the expected result |
| T23 | USB state | `USBDevice()` exists and the `rp2` interfaces are available |
| T24 | reset reason | prints PWRON / WDT |

SKIP is not a failure: a missing jumper (T15/T16), no I2C device (T17), no SD card
(T20) and no key press (T10) are all expected.

## Reading the Result

| Result | Meaning |
|---|---|
| all PASS with some SKIP | the board is usable |
| T03 FAIL | wrong image for this board, reflash with the matching capacity |
| T10 FAIL | GP23 stuck low, check for a jammed key or a missing pull-up |
| T19 far below baseline | check Flash soldering and QSPI routing |
| T21 FAIL | heap not recovered after repeated allocation |

## Running Without a Board

```bash
python3 tools/mpy_sim.py --mb 16                        # 16 MB board
python3 tools/mpy_sim.py --mb 4                         # 4 MB board
python3 tools/mpy_sim.py --mb 16 --flash 4              # capacity mismatch, T03 fails
python3 tools/mpy_sim.py --mb 16 --uart-loop --spi-loop --i2c --key
python3 host_test.py --log /tmp/sim.log                 # report from a log
```

The simulator stubs `machine` / `rp2` / `_thread` and redirects absolute paths to a
temporary directory. It does not write to the host file system and cannot replace
testing on real hardware.

## Known Limitations

1. T23 reports the device side only. The built-in USB stack (REPL + MSC) is driven by
   the TinyUSB descriptors, so `USBDevice().active()` being `False` is by design;
   confirm MSC from the host side by checking for the drive.
2. The suite does not reset the chip, use the WDT or enter deepsleep, so USB stays
   connected. Reset behaviour is checked through T24 and a manual power cycle.

## Measured Baseline

v1.29.0 on the 16 MB board:

| Metric | Measured |
|---|---|
| SRAM copy bandwidth | 161 MB/s |
| file system write (512 KB) | 228 KB/s |
| file system read (512 KB) | 3403 KB/s |
| 64 KB file write/read | 193 / 1104 KB/s |
| file system size | 15332 KB total, 15292 KB free |
| free heap | 445 KB |
