# WeAct Studio RP2350A Core V20 MicroPython Firmware

[中文版](README.md)

---

| Item | Value |
|---|---|
| Board | WeAct Studio RP2350A Core V20 |
| MCU | RP2350A, QFN-60, GPIO0-GPIO29, 520KB SRAM, 150MHz |
| MicroPython | v1.29.0 (pico-sdk 2.3.0) |
| Output | `firmware16M/*.uf2` (16MB Flash), `firmware4M/*.uf2` (4MB Flash) |

---

## 1. Hardware: how it maps to Pico 2

**V20 is hardware-identical to Raspberry Pi Pico 2; the only real difference is
the Flash size** (Pico 2 is always 4MB, V20 ships in 4MB and 16MB flavours). The
board header is therefore a copy of `pico2.h` with exactly two deviations:

| Macro | `pico2.h` | V20 | Note |
|---|---|---|---|
| `PICO_FLASH_SIZE_BYTES` | 4MB | 16MB (`4M` variant: 4MB) | **the only real difference** |
| board detection macro | `RASPBERRYPI_PICO2` | `WEACT_STUDIO_RP2350A_CORE_V20` | identification only |

Everything else matches, including the easily-missed internal pins
`PICO_SMPS_MODE_PIN 23`, `PICO_VBUS_PIN 24` and `PICO_VSYS_PIN 29`. The
`pins.csv` is **byte-identical** to the official `RPI_PICO2` one.

That means Pico 2 pinouts, add-on boards and example code work here as-is; and
when a pin on V20 looks surprising, `pico2.h` usually already answers it.

Facts verified against `HDK/V20_SCH.pdf`:

| Item | Ref | Conclusion |
|---|---|---|
| MCU | U7 | RP2350_60QFN = RP2350A; GPIO0-29, 26 of them on the 40-pin header |
| QSPI Flash | U8 | `CS`/`CLK`/`DI(IO0)`/`DO(IO1)`/`IO2`/`IO3`, standard QSPI, XIP boot |
| Flash size | board spec | 4MB or 16MB, needs separate images |
| Crystal | Y1 | 12MHz + C22/C23 12pF + R17 1K, core at 150MHz |
| Onboard LED | D1 | **one LED only, GPIO25**, active high (= Pico 2) |
| User key | - | **no user key**, only SW1 = USB_BOOT (pulls QSPI_SS low via R15 1K) and SW2 = RESET (pulls RUN low), same as Pico 2 |
| 3V3 rail | U2 + L2 0.47uH | same RT6150 circuit, `MODE` on **GPIO23 + R20 100K**, hence `PICO_SMPS_MODE_PIN 23` |
| ADC | - | GP26/27/28 on the header; GP29_ADC3 taps the VSYS divider |
| VSYS sense | R23/R24 | **100K/100K divider** into GP29_ADC3, rail = ADC x 2 |
| VBUS sense | - | **100K/100K divider** into GP24, read as a digital input: high = USB power |
| USB | J1 Type-C 16P | CC1/CC2 each 5.1K to GND, USB 1.1 full speed |
| Wireless | - | no CYW43, cannot reuse `RPI_PICO2_W` |

The 26 GPIOs on the header are GP0-GP22 and GP26-GP28. The other four stay
on-board: GP23 drives the buck MODE pin, GP24 taps the VBUS divider, GP25 is the
onboard LED and GP29 taps the VSYS divider. GP24/GP29 remain addressable by
number but are only good for power monitoring.

> **Relation to V10**: V10 is different hardware (LED1=GP24 + LED2=GP25, onboard
> key on GP23). V20 is not a pin-compatible upgrade of V10 but a Pico 2 clone,
> so the two board file sets are not interchangeable.
> **V20 has a single LED on GP25 and no user key.** V10 board files and examples
> do not carry over unchanged.

## 2. What has to be added

One new board directory, no upstream file is touched.

```
ports/rp2/boards/WEACTSTUDIO_RP2350A_CORE_V20/
├── mpconfigboard.cmake          board selection, Flash size, filesystem size
├── mpconfigboard.h              board name, LED, UART0, USB MSC
├── mpconfigvariant.cmake        default variant = 16MB
├── mpconfigvariant_4M.cmake     4MB variant
├── mpconfigvariant_RISCV.cmake  optional RISC-V variant
├── pins.csv                     GP0..GP22 and GP25..GP28, plus LED
├── manifest.py                  frozen module list
├── modules/                     frozen modules (with .gitkeep)
├── board.json                   board metadata
└── weact_studio_rp2350a_core_v20.h   SDK board header (copy of pico2.h, Flash only)
```

Copy `board_files/WEACTSTUDIO_RP2350A_CORE_V20/` into
`micropython/ports/rp2/boards/`, or run `patch -p1 < patch/0001-*.patch`.

### 2.1 Why a private SDK board header

pico-sdk 2.x ships `weact_studio_rp2350a_core_v10_16mb.h` but **not V20**. So
`mpconfigboard.cmake` has to do two things:

```cmake
list(APPEND PICO_BOARD_HEADER_DIRS ${MICROPY_BOARD_DIR})
set(PICO_BOARD "weact_studio_rp2350a_core_v20")
```

The header passes CMake defaults with the **function-call form**:

```c
pico_board_cmake_set(PICO_PLATFORM, rp2350)
pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (16 * 1024 * 1024))
```

> **Do not** use the older `// pico_cmake_set PICO_PLATFORM=rp2350` comment
> form. `cmake/generic_board.cmake` in pico-sdk 2.3.0 only matches the
> `pico_board_cmake_set(var, value)` call; the comment form is silently
> ignored -- no error, the value just never takes effect. On the C side both
> forms are harmless: `pico.h` defines these as empty macros.

### 2.2 `mpconfigboard.cmake` key points

```cmake
if(MICROPY_BOARD_VARIANT STREQUAL "4M")
    set(PICO_FLASH_SIZE_BYTES 4194304)
    set(MICROPY_HW_FLASH_16MB 0)
else()
    set(PICO_FLASH_SIZE_BYTES 16777216)
    set(MICROPY_HW_FLASH_16MB 1)
endif()

add_compile_definitions(MICROPY_HW_FLASH_16MB=${MICROPY_HW_FLASH_16MB})

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    if(MICROPY_BOARD_VARIANT STREQUAL "4M")
        set(MICROPY_HW_FLASH_STORAGE_BYTES 3145728)   # 4MB - 1MB
    else()
        set(MICROPY_HW_FLASH_STORAGE_BYTES 15728640)  # 16MB - 1MB
    endif()
endif()
```

Two traps:

1. **`add_compile_definitions` is mandatory.** `PICO_BOARD_EXTRA_DEFINES` only
   reaches pico-sdk internal targets; the MicroPython `firmware` target never
   sees that macro.
2. **`MICROPY_HW_FLASH_STORAGE_BYTES` must be a plain CMake variable**, not just
   an entry in `MICROPY_DEF_BOARD`. `ports/rp2/CMakeLists.txt` turns it into the
   compile definition **and** the linker symbol `__micropy_flash_storage_bytes__`.
   With only the macro the linker script has no size and the map prints
   `FLASH_FS: 0 B 18446744073709551615 B` (-1).

### 2.3 `mpconfigboard.h` key points

```c
#define MICROPY_HW_USB_MSC (1)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING  "WeAct"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING "RP2350A V20"
#define MICROPY_HW_USB_MSC_INQUIRY_REVISION_STRING "1.0"

#define MICROPY_HW_LED_PIN (25)
#define MICROPY_HW_LED1_PIN (25)

#define MICROPY_HW_UART0_TX (0)
#define MICROPY_HW_UART0_RX (1)
#define MICROPY_HW_UART0_CTS (-1)
#define MICROPY_HW_UART0_RTS (-1)

#undef PICO_FLASH_SIZE_BYTES
#if MICROPY_HW_FLASH_16MB
#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V20 (16MB)"
#else
#define PICO_FLASH_SIZE_BYTES (4 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V20 (4MB)"
#endif
```

Notes:

- `MICROPY_HW_USB_MSC` defaults to **0**; without it the board enumerates CDC
  serial only and no drive letter appears.
- `#undef PICO_FLASH_SIZE_BYTES` first, otherwise the SDK header redefinition warns.
- **Do** define `PICO_SMPS_MODE_PIN 23`, exactly as `pico2.h` does. The 3V3 rail
  is the same RT6150 circuit with `MODE` on GP23; with it defined you can call
  the SDK's `board_smps_mode()` to force PWM mode and cut light-load ripple.
- **Do** define `PICO_VSYS_PIN 29` and `PICO_VBUS_PIN 24`: both rails use a
  100K/100K divider, exactly like Pico 2. Once `PICO_VSYS_PIN` is defined, GP29
  is no longer a general purpose IO.

### 2.4 Filesystem size

Firmware sits at the bottom of Flash, the FAT filesystem at the top; the base is
`PICO_FLASH_SIZE_BYTES - MICROPY_HW_FLASH_STORAGE_BYTES`.

| Variant | Flash | Filesystem | Runtime `flash_base` / `flash_size` |
|---|---|---|---|
| 16MB | 16MB | 15MB (15360K) | `0x00100000` / `0x00F00000` |
| 4MB | 4MB | 3MB (3072K) | `0x00100000` / `0x00300000` |

Both images are the same size, about 334KB (32% of the 1MB reserve).

### 2.5 Differences from `RPI_PICO2`

| Item | RPI_PICO2 | WEACTSTUDIO_RP2350A_CORE_V20 |
|---|---|---|
| `PICO_FLASH_SIZE_BYTES` | 4MB | 16MB (`4M` variant: 4MB) |
| Board name | Raspberry Pi Pico2 | WeAct Studio RP2350A Core V20 |
| Filesystem | 3MB | 15MB / 3MB |
| LED / UART0 / I2C0 / SPI0 / SMPS MODE / VBUS / VSYS | GP25 / 0-1 / 4-5 / 18-19-16-17 / 23 / 24 / 29 | **identical** |
| `pins.csv` | 28 lines | **byte-identical** |

Everything except the three Flash-related rows matches, so MicroPython code
written for Pico 2 ports over directly; only code that depends on the Flash
capacity ceiling needs per-variant handling.

## 3. Building

### 3.1 Toolchain

```bash
sudo apt install -y build-essential cmake gcc-arm-none-eabi libnewlib-arm-none-eabi \
                    python3 git pkg-config libusb-1.0-0-dev

git clone https://github.com/micropython/micropython.git
cd micropython
git checkout v1.29.0
make -C mpy-cross -j$(nproc)
git submodule update --init lib/pico-sdk lib/tinyusb lib/mbedtls lib/micropython-lib
```

Mirrors help when GitHub is slow:

```bash
git clone https://gitee.com/mirrors/micropython.git
# mbedtls must be 3.6.x; the 4.x bundled with pico-sdk does not work here
git clone --branch mbedtls-3.6.6 https://gitee.com/mirrors/mbedtls.git lib/mbedtls
```

`picotool` must be >= 2.3.0 (pico-sdk 2.3.0 enforces it), otherwise CMake stops
with `Incompatible picotool installation found`. Build it and either put it on
PATH or pass `-Dpicotool_DIR=<build dir>`.

### 3.2 Drop in the board files

```bash
cp -r RP2350A_V20/MicroPython/board_files/WEACTSTUDIO_RP2350A_CORE_V20 micropython/ports/rp2/boards/
# or
patch -p1 < RP2350A_V20/MicroPython/patch/0001-add-board-WEACTSTUDIO_RP2350A_CORE_V20.patch
```

`modules/` must exist because `manifest.py` calls `freeze("modules")`.

### 3.3 16MB image

```bash
cd micropython/ports/rp2
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 submodules
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 -j$(nproc)
```

Result: `build-WEACTSTUDIO_RP2350A_CORE_V20/firmware.uf2`

```
           FLASH:      334088 B         1 MB     31.86%
        FLASH_FS:           0 B        15 MB      0.00%
             RAM:       27240 B       512 KB      5.20%
```

### 3.4 4MB image

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 BOARD_VARIANT=4M -j$(nproc)
```

Result: `build-WEACTSTUDIO_RP2350A_CORE_V20-4M/firmware.uf2`, with
`FLASH_FS: 0 B 3 MB` in the link summary.

### 3.5 Optional RISC-V variant

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 BOARD_VARIANT=RISCV -j$(nproc)
```

### 3.6 Verify the image

```bash
picotool info -a firmware.uf2
```

```
File ... family ID 'rp2350-arm-s':
 name:            MicroPython
 version:         v1.29.0
 embedded drive:  0x10100000-0x11000000 (15360K): MicroPython flags 0x0003
 target chip:     RP2350
 image type:      ARM Secure
 boot2_name:      boot2_w25q080
```

Confirm MSC is linked in: `arm-none-eabi-nm firmware.elf | grep -ci tud_msc` -> **16**.

> `picotool` always prints the embedded drive starting at `0x10100000`; that is a
> metadata display convention, not the runtime base. The real base comes from the
> linker symbol `__micropy_flash_size__` and `rp2_flash_obj.flash_base`, and the
> values in section 2.4 were read out of the ELF. For the 4MB image picotool
> prints `0x10100000-0x10400000 (3072K)`; a correct capacity means the config is right.

## 4. Flashing

| Method | Steps |
|---|---|
| UF2 drag-and-drop | hold **BOOT** while plugging USB (or hold BOOT and press RESET), a `RP2350` drive appears, drag the `.uf2` in |
| SWD | `picotool load -x firmware.elf` |

**Never flash the 16MB image on a 4MB board**: the filesystem base `0x10100000`
is outside the physical Flash, mount and writes will fail.

After flashing the host sees:

| Device | Meaning |
|---|---|
| `MicroPython` drive | FAT filesystem for `main.py` / `boot.py`; about 15MB on 16MB boards, 3MB on 4MB boards |
| USB serial #1 | MicroPython REPL over USB CDC |
| USB serial #2 | onboard UART0 (GP0/GP1, 115200 8N1), needs an external USB-TTL |

If only serial ports appear and no drive, check you flashed the `-msc` image.

## 5. Verification checklist

| # | Check | Command | Expected |
|---|---|---|---|
| 1 | Boot | open the REPL | `MicroPython v1.29.0 ... WeAct Studio RP2350A Core V20 (16MB) with RP2350` |
| 2 | Chip | `os.uname()` | `sysname='rp2'`, machine contains the board name |
| 3 | Flash partition | `f=rp2.Flash(); f.ioctl(4,0)*f.ioctl(5,0)` | 15728640 (16MB) / 3145728 (4MB) |
| 4 | Filesystem | `os.statvfs('/')` | about 15360KB / 3072KB |
| 5 | LED | `Pin(25,Pin.OUT).value(1)` | onboard LED lights up |
| 6 | Key | `Pin(15,Pin.IN,Pin.PULL_UP).value()` | 1 idle, 0 pressed |
| 7 | Drive | write `main.py`, reset | the script runs at boot |
| 8 | Clock | `machine.freq()` | 150000000 |
| 9 | ADC | `ADC(Pin(26)).read_u16()` | 0..65535 |
| 10 | 4MB image | repeat 3, 4, 7 | capacity and drive are correct |

Checks 1-10 are automated in [`firmware_test/`](firmware_test/README-EN.md)
(26 cases, report generation, off-board simulator).

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Serial only, no drive | `MICROPY_HW_USB_MSC` defaults to 0 | add `#define MICROPY_HW_USB_MSC (1)`, confirm with `nm \| grep -c tud_msc` |
| `FLASH_FS: 0 B 18446744073709551615 B` in the map | size only reached `MICROPY_DEF_BOARD`, linker symbol missing | use a plain `set(MICROPY_HW_FLASH_STORAGE_BYTES ...)` |
| `No picotool found` | CMake needs picotool >= 2.3.0 | build and install it, pass `-Dpicotool_DIR=...` |
| `Incompatible picotool installation found` | version older than the SDK requires | upgrade to >= 2.3.0 |
| `"PICO_FLASH_SIZE_BYTES" redefined` | already defined by the SDK header | `#undef PICO_FLASH_SIZE_BYTES` first |
| `'MICROPY_HW_UART0_CTS' undeclared` | missing CTS/RTS macros | define `_CTS (-1)` / `_RTS (-1)` |
| `'MP_QSTR_\U0000feffGP0' undeclared` | `pins.csv` has a UTF-8 BOM | strip the BOM |
| `MICROPY_HW_FLASH_STORAGE_BYTES too big` | macro and CMake variable disagree | set both per variant |
| `manifest error ... /modules` | `modules/` missing | `mkdir -p .../modules` |
| 4MB image still says `(16MB)` | macro never reached the target | use `add_compile_definitions` |
| `lib/mbedtls/library/aes.c` not found | mbedtls too new | use mbedtls 3.6.x |

### 6.1 Flash part and boot2

Both variants use the SDK's `boot2_w25q080`, compatible with common 4MB/16MB QSPI
NOR parts (XM25QH128, W25Q128):

| boot2 behaviour | Requires | Typical parts |
|---|---|---|
| `0xEB` Quad I/O read, mode bits `0xA0` | supports `EBh`, M7-M4=1010 enters continuous read | yes |
| read SR2 then set QE=1 | QSPI needs QE=1 | yes |
| CLKDIV=2, i.e. 75MHz | rated 104MHz | yes |
| SPI mode 0 and mode 3 | both supported | yes |

No boot2 change needed. If a batch shows XIP problems, switch in
`mpconfigboard.cmake`:

```cmake
set(PICO_FLASH_BOOT_STAGE2_NAME "boot2_generic_03h")
```

## 7. Deliverables

```
RP2350A_V20/MicroPython/
├── README.md                                            this file (Chinese)
├── README-EN.md                                         English version
├── firmware16M/
│   ├── WEACTSTUDIO_RP2350A_CORE_V20_16M-v1.29.0-msc.uf2 16MB board
│   └── firmware_16M.elf                                 SWD debugging
├── firmware4M/
│   ├── WEACTSTUDIO_RP2350A_CORE_V20_4M-v1.29.0-msc.uf2  4MB board
│   └── firmware_4M.elf
├── board_files/WEACTSTUDIO_RP2350A_CORE_V20/
├── patch/0001-add-board-WEACTSTUDIO_RP2350A_CORE_V20.patch
├── firmware_test/                                       26-case suite + simulator
├── tools/check_pico2_parity.py                          asserts board header still matches pico2.h
└── examples/                                            13 examples + board helpers
```

### 7.1 Image properties

| Item | 16MB | 4MB |
|---|---|---|
| UF2 family | `rp2350-arm-s` | `rp2350-arm-s` |
| MicroPython | v1.29.0 | v1.29.0 |
| pico-sdk | 2.3.0 | 2.3.0 |
| MSC symbols | 16 | 16 |
| Filesystem region | `0x10100000-0x11000000` (15360K) | `0x10100000-0x10400000` (3072K) |
| Runtime `flash_base`/`flash_size` | `0x00100000` / `0x00F00000` | `0x00300000` / `0x00300000` |
| MSC INQUIRY | WeAct / RP2350A V20 / 1.0 | same |
| boot2 | `boot2_w25q080` | `boot2_w25q080` |
| Board name | `WeAct Studio RP2350A Core V20 (16MB)` | `... (4MB)` |

### 7.2 Examples

| File | Content |
|---|---|
| `weact_board.py` | pin map plus `Led` / `Key` helpers |
| `01`-`12` | LED, key, UART, PWM, ADC, I2C, SPI, timer, state machine |

See [`examples/README-EN.md`](examples/README-EN.md) for wiring and how to run.

### 7.3 Pico 2 parity check

The board header is designed to differ from `pico2.h` in the Flash size only. A
script enforces that, so nobody has to remember it:

```bash
# run from the MicroPython source tree
python3 /path/to/tools/check_pico2_parity.py --pico2 ports/rp2/boards/RPI_PICO2/pico2.h
```

It parses both sides' `#define` and `pico_board_cmake_set*` lines, compares them
item by item, and applies `pico_board_cmake_set_default` semantics to decide
whether a differing value is legitimate. It also asserts that the Flash
difference **is present** — if someone copies Pico 2's 4 MB value into the V20
header, the script fails instead of silently passing.

| Exit code | Meaning |
|---|---|
| `0` | identical except `PICO_FLASH_SIZE_BYTES` |
| `1` | extra differences found (the header drifted) |
| `2` | `pico2.h` missing or unparsable |

Actual output:

```
pico2.h : /tmp/mp129/lib/pico-sdk/src/boards/include/boards/pico2.h
V20     : .../board_files/WEACTSTUDIO_RP2350A_CORE_V20/weact_studio_rp2350a_core_v20.h

PASS - identical to pico2.h except for the Flash size and board name

  20 shared macros
  PICO_FLASH_SIZE_BYTES: pico2=(4 * 1024 * 1024)  v20=(16 * 1024 * 1024)
```

Negative test: change `PICO_VSYS_PIN` in `pico2.h` from `29` to `28` and it reports

```
FAIL - unexpected differences:
  - PICO_VSYS_PIN: pico2=28, v20=29
```

with exit code `1` — so the check is not a no-op.

## 8. License

Board files and examples ship with this repository. MicroPython itself is MIT,
pico-sdk is BSD-3-Clause.
