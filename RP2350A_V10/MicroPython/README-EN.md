# WeAct RP2350A_V10 MicroPython Firmware Build Guide

[简体中文](./README.md)

---

| Item | Value |
|---|---|
| Target board | WeAct Studio RP2350A_V10 |
| MCU | RP2350A, QFN-60, GPIO0-GPIO29, 520 KB SRAM |
| MicroPython | v1.29.0 |
| Output | `firmware16M/*.uf2` (16 MB Flash), `firmware4M/*.uf2` (4 MB Flash) |

---

## 1. Hardware Facts Affecting the Build

| Item | Location | Conclusion |
|---|---|---|
| MCU | U7 | RP2350_60QFN, i.e. RP2350A, all of GPIO0-GPIO29 broken out |
| QSPI Flash | U8 | `CS`/`CLK`/`DI(IO0)`/`DO(IO1)`/`IO2`/`IO3`, standard QSPI, bootable from Flash |
| Flash size | board spec | 4 MB and 16 MB variants, images must be picked by capacity |
| Crystal | Y1 12 MHz + C22/C23 12 pF | system clock 150 MHz |
| User key | SW3 to GPIO23 | shorts to GND when pressed, active low |
| LED | D1/D2 | LED1 = GPIO24 (blue), LED2 = GPIO25 (green), active high |
| Wireless | none | no CYW43, `RPI_PICO2_W` cannot be reused directly |

---

## 2. What to Change

Only one new board directory is added; no upstream file is modified.

```
ports/rp2/boards/WEACTSTUDIO_RP2350A_CORE/
├── mpconfigboard.cmake          board selection and Flash size
├── mpconfigboard.h              Flash bytes, pins, board name
├── mpconfigvariant.cmake        default variant = 16 MB
├── mpconfigvariant_4M.cmake     4 MB variant
├── mpconfigvariant_RISCV.cmake  optional RISC-V variant
├── pins.csv                     pin aliases
├── manifest.py                  frozen module manifest
├── modules/                     custom frozen module directory
└── board.json                   board metadata
```

Copy `board_files/WEACTSTUDIO_RP2350A_CORE/` into `micropython/ports/rp2/boards/`,
or apply `patch -p1 < patch/0001-*.patch`.

### 2.1 `mpconfigboard.cmake`

```cmake
# reuse the board definition from pico-sdk
set(PICO_BOARD "weact_studio_rp2350a_core_v10_16mb")

# keep the CMake variable in sync with the variant
if(MICROPY_BOARD_VARIANT STREQUAL "4M")
    set(PICO_FLASH_SIZE_BYTES 4194304)      # 4MB
    set(MICROPY_HW_FLASH_16MB 0)
else()
    set(PICO_FLASH_SIZE_BYTES 16777216)     # 16MB
    set(MICROPY_HW_FLASH_16MB 1)
endif()

# pass the value to C code
add_compile_definitions(MICROPY_HW_FLASH_16MB=${MICROPY_HW_FLASH_16MB})

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
```

The third block must use `add_compile_definitions`; `PICO_BOARD_EXTRA_DEFINES` only
affects pico-sdk targets and does not reach the MicroPython `firmware` target.

### 2.2 `mpconfigboard.h`

```c
// USB Mass Storage drive that holds .py files. Defaults to 0; without this only CDC exists.
#define MICROPY_HW_USB_MSC (1)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING  "WeAct"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING "RP2350A V10"
#define MICROPY_HW_USB_MSC_INQUIRY_REVISION_STRING "1.0"

// undef before overriding
#undef PICO_FLASH_SIZE_BYTES
#if MICROPY_HW_FLASH_16MB
#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V10 (16MB)"
#else
#define PICO_FLASH_SIZE_BYTES (4 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V10 (4MB)"
#endif

// UART0 pins, CTS and RTS unconnected
#define MICROPY_HW_UART0_TX (0)
#define MICROPY_HW_UART0_RX (1)
#define MICROPY_HW_UART0_CTS (-1)
#define MICROPY_HW_UART0_RTS (-1)
```

Verify MSC is linked:
`arm-none-eabi-nm build-WEACTSTUDIO_RP2350A_CORE/firmware.elf | grep -c tud_msc`,
expect >= 16.

### 2.3 File System Size

```cmake
# 16MB variant
set(PICO_PLATFORM "rp2350")
set(MICROPY_HW_FLASH_STORAGE_BYTES 15728640)   # 16MB - 1MB = 15MB

# 4MB variant
set(MICROPY_HW_FLASH_STORAGE_BYTES 3145728)    # 4MB - 1MB = 3MB
```

The firmware sits at the bottom of Flash and the FAT file system at the top; the
file system starts at `PICO_FLASH_SIZE_BYTES - MICROPY_HW_FLASH_STORAGE_BYTES`.
The drive is 15 MB on the 16 MB board and 3 MB on the 4 MB board; the firmware
image itself is the same (about 330 KB).

### 2.4 Differences from `RPI_PICO2`

| Item | RPI_PICO2 | WEACTSTUDIO_RP2350A_CORE |
|---|---|---|
| Flash | 4MB | 4MB / 16MB |
| LED | GP25 | GP24 + GP25 |
| Key | none | GP23 |
| UART0 | GP0/GP1 | GP0/GP1 |
| Board name | Raspberry Pi Pico2 | WeAct RP2350A V10 |

---

## 3. Build Steps

### 3.1 Prepare the Environment

```bash
sudo apt install -y build-essential cmake gcc-arm-none-eabi libnewlib-arm-none-eabi \
                    python3 git pkg-config libusb-1.0-0-dev

git clone https://github.com/micropython/micropython.git
cd micropython
git checkout v1.29.0
make -C mpy-cross -j$(nproc)
git submodule update --init lib/pico-sdk lib/tinyusb lib/mbedtls lib/micropython-lib
```

If GitHub is slow, use the codeload tarball:
`curl -L https://codeload.github.com/micropython/micropython/tar.gz/refs/tags/v1.29.0 | tar xz`

`lib/mbedtls` must be 3.6.x (for example `mbedtls-3.6.2`); the 4.x bundled with
pico-sdk does not work with this release.

### 3.2 Add the Board Files

```bash
cp -r rp2350a_weact_v10/board_files/WEACTSTUDIO_RP2350A_CORE micropython/ports/rp2/boards/
```

The `modules/` directory must exist for `freeze("modules")` in `manifest.py`.

### 3.3 Build the 16MB Variant

```bash
cd micropython/ports/rp2
make BOARD=WEACTSTUDIO_RP2350A_CORE submodules
make BOARD=WEACTSTUDIO_RP2350A_CORE -j$(nproc)
```

Output: `build-WEACTSTUDIO_RP2350A_CORE/firmware.uf2`

```
   FLASH:      334748 B         1 MB     31.92%
FLASH_FS:           0 B        15 MB      0.00%
```

### 3.4 Build the 4MB Variant

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE BOARD_VARIANT=4M -j$(nproc)
```

Output: `build-WEACTSTUDIO_RP2350A_CORE-4M/firmware.uf2`, link log shows `FLASH_FS: 0 B 3 MB`.

### 3.5 Optional RISC-V Variant

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE BOARD_VARIANT=RISCV -j$(nproc)
```

### 3.6 Verify the Output

```bash
picotool info -a firmware.uf2
```

```
File firmware.uf2 family ID 'rp2350-arm-s':
 name:            MicroPython
 binary start:    0x10000000
 binary end:      0x10050e08
 embedded drive:  0x10100000-0x11000000 (15360K)
 image type:      ARM Secure
```

The 4 MB variant reports `embedded drive: 0x10d00000-0x11000000 (3072K)`.

---

## 4. Flashing

| Method | Steps |
|---|---|
| UF2 drag and drop | Hold BOOT while plugging in, then copy the `.uf2` to the `RP2350` drive |
| SWD | `picotool load -x firmware.elf` |

Do not flash the 16 MB image on a 4 MB board: the file system base `0x10100000` is
beyond the 4 MB physical Flash, so mounting and writes fail.

After flashing the host shows:

| Device | Description |
|---|---|
| `MicroPython` drive | FAT file system for `main.py` and `boot.py`; about 15 MB on the 16 MB board, 3 MB on the 4 MB board |
| USB serial #1 | MicroPython REPL (USB CDC) |
| USB serial #2 | on-board UART0 (GP0/GP1, 1500000 baud), needs an external USB-TTL adapter |

If only a serial port appears, make sure the flashed file has the `-msc` suffix.

---

## 5. Verification Checklist

| # | Test | Command | Expected |
|---|---|---|---|
| 1 | boot | open the REPL | prints `MicroPython v1.29.0 ... WeAct Studio RP2350A Core V10 (16MB)` |
| 2 | board | `os.uname()` | `sysname='rp2'`, machine contains the board name |
| 3 | Flash partition | `f=rp2.Flash(); f.ioctl(4,0)*f.ioctl(5,0)` | 15728640 on 16 MB, 3145728 on 4 MB |
| 4 | file system | `os.statvfs('/')` | about 15360 KB on 16 MB, 3072 KB on 4 MB |
| 5 | LED1 | `Pin(24,Pin.OUT).value(1)` | blue on |
| 6 | LED2 | `Pin(25,Pin.OUT).value(1)` | green on |
| 7 | key | `Pin(23,Pin.IN,Pin.PULL_UP).value()` | 1 idle, 0 pressed |
| 8 | drive | write `main.py`, then reset | the script runs automatically |
| 9 | clock | `machine.freq()` | 150000000 |
| 10 | 4 MB image | repeat 3, 4, 8 | capacity and drive correct |

Items 1-10 are automated in the [`firmware_test/`](firmware_test/README-EN.md) suite.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| serial only, no drive | `MICROPY_HW_USB_MSC` defaults to 0 | add `#define MICROPY_HW_USB_MSC (1)`, confirm with `nm \| grep tud_msc` |
| `No picotool found` | CMake needs picotool >= 2.x | build and install picotool, pass `-Dpicotool_DIR=...` |
| `"PICO_FLASH_SIZE_BYTES" redefined` | pico-sdk already defines it | `#undef PICO_FLASH_SIZE_BYTES` first |
| `'MICROPY_HW_UART0_CTS' undeclared` | missing CTS/RTS macros | `#define ..._CTS (-1)` and `_RTS (-1)` |
| `MICROPY_HW_FLASH_STORAGE_BYTES too big` | C macro out of sync with the CMake variable | also set `PICO_FLASH_SIZE_BYTES` as a CMake variable |
| `manifest error ... /modules` | `modules/` directory missing | `mkdir -p .../modules` |
| 4 MB image still reports `(16MB)` | macro never reaches the firmware target | use `add_compile_definitions` |
| `lib/mbedtls/library/aes.c` not found | mbedtls too new | use mbedtls 3.6.x |

### 6.1 Flash Part and boot2

This board carries an XM25QH128 (16 MB); the WeAct board definition in pico-sdk uses
`boot2_w25q080`. Compatibility with this part:

| boot2 action | XM25QH128 requirement | Match |
|---|---|---|
| `0xEB` Quad I/O read, mode bits `0xA0` | supports `EBh`, M7-M4 = 1010 selects continuous read | yes |
| read SR2 then set QE = 1 | QSPI needs QE = 1, factory default is 0 | yes |
| CLKDIV = 2, i.e. 75 MHz | supports 104 MHz | yes |
| SPI Mode 0 / Mode 3 | both supported | yes |

No change is required. If a batch shows XIP problems, switch to
`set(PICO_FLASH_BOOT_STAGE2_NAME "boot2_generic_03h")` in `mpconfigboard.cmake`.

---

## 7. Deliverables

```
rp2350a_weact_v10/
├── README.md                                            Chinese version
├── README-EN.md                                         this document
├── firmware16M/
│   ├── WEACTSTUDIO_RP2350A_CORE_16M-v1.29.0-msc.uf2     16 MB board
│   └── firmware_16M.elf                                 for SWD debugging
├── firmware4M/
│   ├── WEACTSTUDIO_RP2350A_CORE_4M-v1.29.0-msc.uf2      4 MB board
│   └── firmware_4M.elf
├── board_files/WEACTSTUDIO_RP2350A_CORE/                board files
├── patch/0001-add-board-WEACTSTUDIO_RP2350A_CORE.patch  patch
├── firmware_test/                                       self-test suite
└── examples/                                            example code
```

### 7.1 Firmware Properties

| Item | 16 MB variant | 4 MB variant |
|---|---|---|
| UF2 family | `rp2350-arm-s` | `rp2350-arm-s` |
| MSC symbols | 16 | 16 |
| File system area | `0x10100000-0x11000000` (15360K) | `0x10d00000-0x11000000` (3072K) |
| MSC INQUIRY | WeAct / RP2350A V10 / 1.0 | same |
| Board name | `WeAct Studio RP2350A Core V10 (16MB)` | `... (4MB)` |

### 7.2 Example Code

| File | Content |
|---|---|
| `weact_board.py` | pin map, `Led` and `Key` wrappers |
| `01`-`12` | LED, key, UART, PWM, ADC, I2C, SPI, timer, state machine |
| `weact_link.h` | C copyright header and pin macros |

How to run: `exec(open("03_key_poll.py").read())`, see [examples/README-EN.md](examples/README-EN.md).
