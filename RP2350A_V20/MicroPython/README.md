# WeAct Studio RP2350A Core V20 MicroPython 固件

[English Version](README-EN.md)

---

| 项目 | 内容 |
|---|---|
| 目标板 | WeAct Studio RP2350A Core V20 |
| 芯片 | RP2350A，QFN-60，GPIO0~GPIO29，520KB SRAM，150MHz |
| MicroPython | v1.29.0（pico-sdk 2.3.0） |
| 产物 | `firmware16M/*.uf2`（16MB Flash）、`firmware4M/*.uf2`（4MB Flash） |

---

## 1. 硬件：与 Pico 2 的对应关系

**V20 与 Raspberry Pi Pico 2 硬件一致，唯一实质差异是 Flash 容量**（Pico 2 固定 4MB，V20 有 4MB 与 16MB 两版）。因此板级头直接照抄 `pico2.h`，差异只有两项：

| 宏 | `pico2.h` | V20 | 说明 |
|---|---|---|---|
| `PICO_FLASH_SIZE_BYTES` | 4MB | 16MB（`4M` 变体为 4MB） | **唯一的实质差异** |
| 板名标识宏 | `RASPBERRYPI_PICO2` | `WEACT_STUDIO_RP2350A_CORE_V20` | 仅供板卡识别 |

其余全部相同，包括 `PICO_SMPS_MODE_PIN 23`、`PICO_VBUS_PIN 24`、`PICO_VSYS_PIN 29` 这些容易被忽略的内部功能脚。`pins.csv` 也与官方 `RPI_PICO2` **逐字节一致**。

这意味着 Pico 2 的引脚约定、扩展板、例程在这块板子上可以直接用；反过来，看到 V20 上有疑问的引脚，先查 `pico2.h` 通常就有答案。

依据 `HDK/V20_SCH.pdf` 逐块核对的细节：

| 项目 | 原理图位置 | 结论 |
|---|---|---|
| 主芯片 | U7 | RP2350_60QFN，即 RP2350A；GPIO0~GPIO29，其中 26 个引到 40 pin 排针 |
| QSPI Flash | U8 | `CS`/`CLK`/`DI(IO0)`/`DO(IO1)`/`IO2`/`IO3`，标准 QSPI，可 XIP 启动 |
| Flash 容量 | 板卡规格 | 4MB / 16MB 两种，需按容量区分固件 |
| 晶振 | Y1 | 12MHz + C22/C23 12pF + R17 1K，系统时钟 150MHz |
| 板载 LED | D1 | **仅一颗，GPIO25**，高电平点亮（= Pico 2） |
| 用户按键 | — | **没有用户按键**，只有 SW1=USB_BOOT（拉低 QSPI_SS，经 R15 1K）和 SW2=RESET（拉低 RUN），与 Pico 2 一样 |
| 3V3 电源 | U2 + L2 0.47uH | RT6150 同款电路，`MODE` 脚接 **GPIO23 + R20 100K**，故 `PICO_SMPS_MODE_PIN 23` |
| ADC | — | GP26/27/28 引到排针；GP29_ADC3 接 VSYS 分压中点 |
| VSYS 检测 | R23/R24 | **100K/100K 分压**接 GP29_ADC3，实际电压 = ADC 值 × 2 |
| VBUS 检测 | — | **100K/100K 分压**接 GP24，当数字输入读：高 = USB 供电 |
| USB | J1 Type-C 16P | CC1/CC2 各 5.1K 下拉，USB 1.1 全速 |
| 无线 | — | 无 CYW43，不能套用 `RPI_PICO2_W` |

排针上引出 26 个 GPIO：GP0–GP22 与 GP26–GP28。其余四个引脚都在板内：GP23 驱动 buck 的 MODE 脚，GP24 接 VBUS 分压，GP25 接板载 LED，GP29 接 VSYS 分压——GP24/GP29 仍可用数字编号编程访问，但只适合做电源监测。

> **与 V10 的关系**：V10 是另一套硬件（LED1=GP24 + LED2=GP25 双灯、板载按键 GP23）。V20 不是 V10 的引脚兼容升级，而是 Pico 2 的复刻，两者板级文件不能互换。

## 2. 需要修改的地方

只需新增一个板级目录，不改任何上游文件。

```
ports/rp2/boards/WEACTSTUDIO_RP2350A_CORE_V20/
├── mpconfigboard.cmake          选板、Flash 容量、文件系统大小
├── mpconfigboard.h              板名、LED、UART0、USB MSC
├── mpconfigvariant.cmake        默认变体 = 16MB
├── mpconfigvariant_4M.cmake     4MB 变体
├── mpconfigvariant_RISCV.cmake  可选 RISC-V 变体
├── pins.csv                     引脚别名 GP0..GP22、GP25..GP28 + LED
├── manifest.py                  冻结模块清单
├── modules/                     自定义冻结模块目录（含 .gitkeep）
├── board.json                   板卡元数据
└── weact_studio_rp2350a_core_v20.h   pico-sdk 板级头（pico2.h 的副本，只改 FLASH）
```

复制 `board_files/WEACTSTUDIO_RP2350A_CORE_V20/` 到 `micropython/ports/rp2/boards/`，或执行 `patch -p1 < patch/0001-*.patch`。

### 2.1 为什么必须自带 pico-sdk 板级头

pico-sdk 2.x 自带 `weact_studio_rp2350a_core_v10_16mb.h`，但**没有 V20**。所以 `mpconfigboard.cmake` 里要做两件事：

```cmake
list(APPEND PICO_BOARD_HEADER_DIRS ${MICROPY_BOARD_DIR})
set(PICO_BOARD "weact_studio_rp2350a_core_v20")
```

板级头里用**函数式**声明给 CMake 传默认值：

```c
pico_board_cmake_set(PICO_PLATFORM, rp2350)
pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (16 * 1024 * 1024))
```

> **别写成旧式的 `// pico_cmake_set PICO_PLATFORM=rp2350` 注释。** pico-sdk 2.3.0 的 `cmake/generic_board.cmake` 只匹配 `pico_board_cmake_set(var, value)` 这种函数调用形式，注释形式会被静默忽略——不报错，但值不生效，属于很难查的那类问题。这两行在 C 侧也不会有副作用：`pico.h` 把它们定义成空宏。

### 2.2 `mpconfigboard.cmake` 要点

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

两点容易踩：

1. **`add_compile_definitions` 不可省**。`PICO_BOARD_EXTRA_DEFINES` 只作用于 pico-sdk 内部 target，MicroPython 的 `firmware` target 收不到该宏。
2. **`MICROPY_HW_FLASH_STORAGE_BYTES` 必须是普通 CMake 变量**，不能只写进 `MICROPY_DEF_BOARD`。`ports/rp2/CMakeLists.txt` 会拿它生成编译宏**和**链接符号 `__micropy_flash_storage_bytes__`；只给宏的话链接脚本拿不到容量，map 里会出现 `FLASH_FS: 0 B 18446744073709551615 B`（即 −1）。

### 2.3 `mpconfigboard.h` 要点

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

注意事项：

- `MICROPY_HW_USB_MSC` 默认为 **0**，不打开时板子只枚举 CDC 串口，主机看不到盘符。
- `PICO_FLASH_SIZE_BYTES` 先 `#undef` 再重定义，否则 pico-sdk 板级头已经定义过会告警。
- `PICO_SMPS_MODE_PIN 23` **要定义**，且要与 `pico2.h` 完全一致。V20 的 3V3 是 RT6150 同款电路，`MODE` 脚接 GP23；定义后可用 SDK 的 `board_smps_mode()` 强制 PWM 模式降低轻载纹波。
- `PICO_VSYS_PIN 29` 与 `PICO_VBUS_PIN 24` **要定义**：两路都是 100K/100K 分压，与 Pico 2 一致。定义了 `PICO_VSYS_PIN` 之后 GP29 就不能再当普通 IO 用。

### 2.4 文件系统大小

固件在 Flash 底部，FAT 文件系统在顶部，起始地址 = `PICO_FLASH_SIZE_BYTES − MICROPY_HW_FLASH_STORAGE_BYTES`。

| 变体 | Flash | 文件系统 | 运行期 `flash_base` / `flash_size` |
|---|---|---|---|
| 16MB | 16MB | 15MB（15360K） | `0x00100000` / `0x00F00000` |
| 4MB | 4MB | 3MB（3072K） | `0x00100000` / `0x00300000` |

两者固件体积相同（约 334KB，占 1MB 预留的 32%）。

### 2.5 与官方 `RPI_PICO2` 的差异

| 项目 | RPI_PICO2 | WEACTSTUDIO_RP2350A_CORE_V20 |
|---|---|---|
| `PICO_FLASH_SIZE_BYTES` | 4MB | 16MB（`4M` 变体 4MB） |
| 板名 | Raspberry Pi Pico2 | WeAct Studio RP2350A Core V20 |
| 文件系统 | 3MB | 15MB / 3MB |
| LED / UART0 / I2C0 / SPI0 / SMPS MODE / VBUS / VSYS | GP25 / 0-1 / 4-5 / 18-19-16-17 / 23 / 24 / 29 | **完全相同** |
| `pins.csv` | 28 行 | **逐字节相同** |

除 FLASH 相关三行外全部一致，所以针对 Pico 2 写的 MicroPython 代码可以直接搬过来，只有依赖 Flash 容量上限的部分需要按变体处理。

## 3. 编译步骤

### 3.1 准备环境

```bash
sudo apt install -y build-essential cmake gcc-arm-none-eabi libnewlib-arm-none-eabi \
                    python3 git pkg-config libusb-1.0-0-dev

git clone https://github.com/micropython/micropython.git
cd micropython
git checkout v1.29.0
make -C mpy-cross -j$(nproc)
git submodule update --init lib/pico-sdk lib/tinyusb lib/mbedtls lib/micropython-lib
```

GitHub 直连不稳定时可改用镜像：

```bash
git clone https://gitee.com/mirrors/micropython.git
# mbedtls 需 3.6.x，pico-sdk 自带的 4.x 与本版本不兼容
git clone --branch mbedtls-3.6.6 https://gitee.com/mirrors/mbedtls.git lib/mbedtls
```

`picotool` 必须 ≥ 2.3.0（pico-sdk 2.3.0 强制校验），否则报 `Incompatible picotool installation found`。自行编译安装后加 `-Dpicotool_DIR=<build dir>` 或确保 `picotool` 在 PATH 中。

### 3.2 放入板级文件

```bash
cp -r RP2350A_V20/MicroPython/board_files/WEACTSTUDIO_RP2350A_CORE_V20 micropython/ports/rp2/boards/
# 或
patch -p1 < RP2350A_V20/MicroPython/patch/0001-add-board-WEACTSTUDIO_RP2350A_CORE_V20.patch
```

`modules/` 目录必须存在，`manifest.py` 中的 `freeze("modules")` 需要它。

### 3.3 编译 16MB 固件

```bash
cd micropython/ports/rp2
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 submodules
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 -j$(nproc)
```

产物：`build-WEACTSTUDIO_RP2350A_CORE_V20/firmware.uf2`

链接汇总（本次实测）：

```
           FLASH:      334088 B         1 MB     31.86%
        FLASH_FS:           0 B        15 MB      0.00%
             RAM:       27240 B       512 KB      5.20%
```

### 3.4 编译 4MB 固件

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 BOARD_VARIANT=4M -j$(nproc)
```

产物：`build-WEACTSTUDIO_RP2350A_CORE_V20-4M/firmware.uf2`，链接日志为 `FLASH_FS: 0 B 3 MB`。

### 3.5 可选 RISC-V 版本

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 BOARD_VARIANT=RISCV -j$(nproc)
```

### 3.6 校验产物

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

验证 MSC 已编入：`arm-none-eabi-nm firmware.elf | grep -ci tud_msc` → **16**。

> `picotool` 显示的 `embedded drive` 起始地址固定从 `0x10100000` 开始拼，它不代表运行期的真实基址。真实基址由链接符号 `__micropy_flash_size__` 与 `rp2_flash_obj.flash_base` 决定，上面 2.4 节的表格是从 ELF 里读出来的实测值。4MB 版显示 `0x10100000-0x10400000 (3072K)`，容量正确即说明配置无误。

## 4. 烧录

| 方式 | 操作 |
|---|---|
| UF2 拖拽 | 按住 **BOOT** 再插 USB（或按住 BOOT 按 RESET），出现 `RP2350` 盘后把 `.uf2` 拖进去 |
| SWD | `picotool load -x firmware.elf` |

**4MB 板不要烧 16MB 固件**：文件系统基址 `0x10100000` 在 4MB 物理 Flash 之外，挂载和写入都会失败。

烧录后主机可见：

| 设备 | 说明 |
|---|---|
| `MicroPython` 盘 | FAT 文件系统，放 `main.py`、`boot.py`；16MB 版约 15MB，4MB 版约 3MB |
| USB 串口 #1 | MicroPython REPL（USB CDC） |
| USB 串口 #2 | 板载 UART0（GP0/GP1，115200 8N1），需外接 USB-TTL |

只出现串口而没有盘符时，确认烧的是文件名带 `-msc` 的固件。

## 5. 验证用例

| # | 用例 | 命令 | 期望 |
|---|---|---|---|
| 1 | 启动 | 打开 REPL | 打印 `MicroPython v1.29.0 ... WeAct Studio RP2350A Core V20 (16MB) with RP2350` |
| 2 | 芯片确认 | `os.uname()` | `sysname='rp2'`，machine 含板名 |
| 3 | Flash 分区 | `f=rp2.Flash(); f.ioctl(4,0)*f.ioctl(5,0)` | 16MB 版 15728640；4MB 版 3145728 |
| 4 | 文件系统 | `os.statvfs('/')` | 16MB 版约 15360KB；4MB 版约 3072KB |
| 5 | LED | `Pin(25,Pin.OUT).value(1)` | 板载 LED 点亮 |
| 6 | 按键 | `Pin(15,Pin.IN,Pin.PULL_UP).value()` | 外接键未按 1，按下 0 |
| 7 | 盘符 | 写 `main.py` 后复位 | 脚本自动执行 |
| 8 | 主频 | `machine.freq()` | 150000000 |
| 9 | ADC | `ADC(Pin(26)).read_u16()` | 0~65535，电压对应排针电平 |
| 10 | 4MB 固件 | 重复 3、4、7 | 容量与盘符正确 |
| 11 | VSYS 电压 | `ADC(Pin(29)).read_u16()` | 换算 `raw*3.3*2/65535`，USB 供电时约 4.6–5.1V |
| 12 | VBUS 检测 | `Pin(24,Pin.IN).value()` | 插 USB 为 1，仅外部供电为 0 |
| 13 | 电源监测例程 | `mpremote run examples/13_vsys_vbus_monitor.py` | 每 500ms 打印电压，插拔 USB 有事件提示 |

第 1~13 条已封装为 [`firmware_test/`](firmware_test/README.md) 自动化套件（26 个用例，含报告生成与无板模拟器）。

## 6. 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 只有串口，没有盘符 | `MICROPY_HW_USB_MSC` 默认为 0 | 加 `#define MICROPY_HW_USB_MSC (1)`，用 `nm \| grep -c tud_msc` 确认 |
| map 里 `FLASH_FS: 0 B 18446744073709551615 B` | 容量只进了 `MICROPY_DEF_BOARD`，链接符号缺失 | 改成普通 CMake 变量 `set(MICROPY_HW_FLASH_STORAGE_BYTES ...)` |
| `No picotool found` | CMake 需要 picotool ≥ 2.3.0 | 单独编译安装 picotool，加 `-Dpicotool_DIR=...` |
| `Incompatible picotool installation found` | 版本低于 SDK 要求 | 升级到 ≥ 2.3.0 |
| `"PICO_FLASH_SIZE_BYTES" redefined` | pico-sdk 已定义该宏 | 先 `#undef PICO_FLASH_SIZE_BYTES` |
| `'MICROPY_HW_UART0_CTS' undeclared` | 缺 CTS/RTS 宏 | 定义 `_CTS (-1)` / `_RTS (-1)` |
| `'MP_QSTR_\U0000feffGP0' undeclared` | `pins.csv` 带 UTF-8 BOM | 去掉 BOM（`python3 -c "..."` 或 `sed -i '1s/^\xEF\xBB\xBF//'`） |
| `MICROPY_HW_FLASH_STORAGE_BYTES too big` | 宏与 CMake 变量不一致 | 两边都按变体设置 |
| `manifest error ... /modules` | 缺 `modules/` 目录 | `mkdir -p .../modules` |
| 4MB 固件板名仍是 `(16MB)` | 宏没进 firmware target | 改用 `add_compile_definitions` |
| `lib/mbedtls/library/aes.c` 找不到 | mbedtls 版本过新 | 使用 mbedtls 3.6.x |

### 6.1 Flash 型号与 boot2

本仓库两个变体都用 pico-sdk 的 `boot2_w25q080`，与常见 4MB/16MB QSPI NOR（如 XM25QH128、W25Q128）兼容：

| boot2 动作 | 对 Flash 的要求 | 常见芯片 |
|---|---|---|
| `0xEB` Quad I/O 读，模式位 `0xA0` | 支持 `EBh`，M7-M4=1010 进入连续读 | 支持 |
| 读 SR2 后置 QE=1 | QSPI 需 QE=1 | 支持 |
| CLKDIV=2，即 75MHz | 支持 104MHz | 支持 |
| SPI Mode 0 / Mode 3 | 两种都支持 | 支持 |

无需更换 boot2。若某批次出现 XIP 异常，可在 `mpconfigboard.cmake` 中改用：

```cmake
set(PICO_FLASH_BOOT_STAGE2_NAME "boot2_generic_03h")
```

## 7. 交付清单

```
RP2350A_V20/MicroPython/
├── README.md                                            本文档（中文）
├── README-EN.md                                         英文版
├── firmware16M/
│   ├── WEACTSTUDIO_RP2350A_CORE_V20_16M-v1.29.0-msc.uf2 16MB 板
│   └── firmware_16M.elf                                 SWD 调试
├── firmware4M/
│   ├── WEACTSTUDIO_RP2350A_CORE_V20_4M-v1.29.0-msc.uf2  4MB 板
│   └── firmware_4M.elf
├── board_files/WEACTSTUDIO_RP2350A_CORE_V20/            板级文件
├── patch/0001-add-board-WEACTSTUDIO_RP2350A_CORE_V20.patch  补丁
├── firmware_test/                                       自检套件（26 用例 + 模拟器）
├── tools/check_pico2_parity.py                          校验板级头与 pico2.h 是否仍一致
└── examples/                                            13 个例程 + 板级封装
```

### 7.1 固件属性

| 项目 | 16MB 版 | 4MB 版 |
|---|---|---|
| UF2 family | `rp2350-arm-s` | `rp2350-arm-s` |
| MicroPython | v1.29.0 | v1.29.0 |
| pico-sdk | 2.3.0 | 2.3.0 |
| MSC 符号数 | 16 | 16 |
| 文件系统区 | `0x10100000-0x11000000`（15360K） | `0x10100000-0x10400000`（3072K） |
| 运行期 `flash_base`/`flash_size` | `0x00100000` / `0x00F00000` | `0x00300000` / `0x00300000` |
| MSC INQUIRY | WeAct / RP2350A V20 / 1.0 | 同左 |
| boot2 | `boot2_w25q080` | `boot2_w25q080` |
| 板名 | `WeAct Studio RP2350A Core V20 (16MB)` | `… (4MB)` |

### 7.2 例程

| 文件 | 内容 |
|---|---|
| `weact_board.py` | 引脚定义与 `Led` / `Key` 封装 |
| `01`~`12` | LED、按键、UART、PWM、ADC、I2C、SPI、定时器、状态机 |

运行方式与接线说明见 [`examples/README.md`](examples/README.md)。

### 7.3 与 Pico 2 的一致性检查

板级头的设计约束是「与 `pico2.h` 只差 Flash 容量」。这条约束靠脚本守着，不靠人记：

```bash
# 在 MicroPython 源码树里跑
python3 /path/to/tools/check_pico2_parity.py --pico2 ports/rp2/boards/RPI_PICO2/pico2.h
```

脚本解析双方的 `#define` 与 `pico_board_cmake_set*` 行，逐项比对并按 `pico_board_cmake_set_default` 语义判断“值不同是否允许”。它同时断言 **Flash 差异必须存在**——如果哪天有人把 V20 的 `PICO_FLASH_SIZE_BYTES` 抄成了 Pico 2 的 4MB，脚本会失败而不是默默通过。

| 退出码 | 含义 |
|---|---|
| `0` | 一致，仅 `PICO_FLASH_SIZE_BYTES` 不同 |
| `1` | 出现多余差异（有人改了板级头） |
| `2` | 找不到 `pico2.h` 或解析失败 |

实测输出：

```
pico2.h : /tmp/mp129/lib/pico-sdk/src/boards/include/boards/pico2.h
V20     : .../board_files/WEACTSTUDIO_RP2350A_CORE_V20/weact_studio_rp2350a_core_v20.h

PASS - 除 FLASH 容量与板名外，与 pico2.h 完全一致
       identical to pico2.h except for the Flash size and board name

  共享宏 20 个 / 20 shared macros
  PICO_FLASH_SIZE_BYTES: pico2=(4 * 1024 * 1024)  v20=(16 * 1024 * 1024)
```

反向验证：把 `pico2.h` 里的 `PICO_VSYS_PIN` 从 `29` 改成 `28`，脚本立刻报

```
FAIL - 发现意外差异 / unexpected differences:
  - PICO_VSYS_PIN: pico2=28, v20=29
```

退出码 `1`。这说明脚本不是空转的。

## 8. 许可

板级文件与例程随本仓库发布；MicroPython 本体遵循 MIT，pico-sdk 遵循 BSD-3-Clause。
