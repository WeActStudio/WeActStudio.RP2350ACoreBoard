# WeAct RP2350A_V10 MicroPython 固件编译说明

[English Version](./README-EN.md)

---

| 项目 | 内容 |
|---|---|
| 目标板 | WeAct Studio RP2350A_V10 |
| 芯片 | RP2350A，QFN-60，GPIO0~GPIO29，520KB SRAM |
| MicroPython | v1.29.0 |
| 产物 | `firmware16M/*.uf2`（16MB Flash）、`firmware4M/*.uf2`（4MB Flash） |

---

## 1. 与固件配置相关的硬件信息

| 项目 | 原理图位置 | 结论 |
|---|---|---|
| 主芯片 | U7 | RP2350_60QFN，即 RP2350A，GPIO0~GPIO29 全部引出 |
| QSPI Flash | U8 | `CS`/`CLK`/`DI(IO0)`/`DO(IO1)`/`IO2`/`IO3`，标准 QSPI，可从 Flash 启动 |
| Flash 容量 | 板卡规格 | 4MB / 16MB 两种，需用容量区分固件 |
| 晶振 | Y1 12MHz + C22/C23 12pF | 系统时钟 150MHz |
| 用户按键 | SW3 → GPIO23 | 按下接地，低电平有效 |
| LED | D1/D2 | LED1=GPIO24（蓝），LED2=GPIO25（绿），高电平点亮 |
| 无线 | 无 | 无 CYW43，不能直接套用 `RPI_PICO2_W` |

---

## 2. 需要修改的地方

只需新增一个板级目录，不改任何上游文件。

```
ports/rp2/boards/WEACTSTUDIO_RP2350A_CORE/
├── mpconfigboard.cmake          选板与 Flash 容量
├── mpconfigboard.h              Flash 字节数、引脚、板名
├── mpconfigvariant.cmake        默认变体 = 16MB
├── mpconfigvariant_4M.cmake     4MB 变体
├── mpconfigvariant_RISCV.cmake  可选 RISC-V 变体
├── pins.csv                     引脚别名
├── manifest.py                  冻结模块清单
├── modules/                     自定义冻结模块目录
└── board.json                   板卡元数据
```

复制 `board_files/WEACTSTUDIO_RP2350A_CORE/` 到 `micropython/ports/rp2/boards/`，
或执行 `patch -p1 < patch/0001-*.patch`。

### 2.1 `mpconfigboard.cmake`

```cmake
# 复用 pico-sdk 中的板级定义
set(PICO_BOARD "weact_studio_rp2350a_core_v10_16mb")

# CMake 变量与变体一致
if(MICROPY_BOARD_VARIANT STREQUAL "4M")
    set(PICO_FLASH_SIZE_BYTES 4194304)      # 4MB
    set(MICROPY_HW_FLASH_16MB 0)
else()
    set(PICO_FLASH_SIZE_BYTES 16777216)     # 16MB
    set(MICROPY_HW_FLASH_16MB 1)
endif()

# 传给 C 代码
add_compile_definitions(MICROPY_HW_FLASH_16MB=${MICROPY_HW_FLASH_16MB})

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
```

第三处必须使用 `add_compile_definitions`：`PICO_BOARD_EXTRA_DEFINES` 只作用于
pico-sdk 内部 target，MicroPython 的 `firmware` target 收不到该宏。

### 2.2 `mpconfigboard.h`

```c
// USB 大容量存储，即存放 .py 的盘。默认值为 0，不显式打开时只有 CDC 串口。
#define MICROPY_HW_USB_MSC (1)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING  "WeAct"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING "RP2350A V10"
#define MICROPY_HW_USB_MSC_INQUIRY_REVISION_STRING "1.0"

// 先 undef 再覆盖
#undef PICO_FLASH_SIZE_BYTES
#if MICROPY_HW_FLASH_16MB
#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V10 (16MB)"
#else
#define PICO_FLASH_SIZE_BYTES (4 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V10 (4MB)"
#endif

// UART0 引脚，CTS/RTS 未连接
#define MICROPY_HW_UART0_TX (0)
#define MICROPY_HW_UART0_RX (1)
#define MICROPY_HW_UART0_CTS (-1)
#define MICROPY_HW_UART0_RTS (-1)
```

验证 MSC 已编入固件：
`arm-none-eabi-nm build-WEACTSTUDIO_RP2350A_CORE/firmware.elf | grep -c tud_msc`，
期望 ≥ 16。

### 2.3 文件系统大小

```cmake
# 16MB 版
set(PICO_PLATFORM "rp2350")
set(MICROPY_HW_FLASH_STORAGE_BYTES 15728640)   # 16MB - 1MB = 15MB

# 4MB 版
set(MICROPY_HW_FLASH_STORAGE_BYTES 3145728)    # 4MB - 1MB = 3MB
```

固件在 Flash 底部，FAT 文件系统在顶部，起始地址 = `PICO_FLASH_SIZE_BYTES - MICROPY_HW_FLASH_STORAGE_BYTES`。
16MB 板的盘为 15MB，4MB 板的盘为 3MB，两者固件本身相同（约 330KB）。

### 2.4 与 `RPI_PICO2` 的差异

| 项目 | RPI_PICO2 | WEACTSTUDIO_RP2350A_CORE |
|---|---|---|
| Flash | 4MB | 4MB / 16MB |
| LED | GP25 | GP24 + GP25 |
| 按键 | 无 | GP23 |
| UART0 | GP0/GP1 | GP0/GP1 |
| 板名 | Raspberry Pi Pico2 | WeAct RP2350A V10 |

---

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

GitHub 访问不稳定时可改用 codeload 压缩包：
`curl -L https://codeload.github.com/micropython/micropython/tar.gz/refs/tags/v1.29.0 | tar xz`

`lib/mbedtls` 需使用 3.6.x（例如 `mbedtls-3.6.2`），pico-sdk 自带的 4.x 与本版本不兼容。

### 3.2 放入板级文件

```bash
cp -r rp2350a_weact_v10/board_files/WEACTSTUDIO_RP2350A_CORE micropython/ports/rp2/boards/
```

`modules/` 目录必须存在，`manifest.py` 中的 `freeze("modules")` 需要它。

### 3.3 编译 16MB 固件

```bash
cd micropython/ports/rp2
make BOARD=WEACTSTUDIO_RP2350A_CORE submodules
make BOARD=WEACTSTUDIO_RP2350A_CORE -j$(nproc)
```

产物：`build-WEACTSTUDIO_RP2350A_CORE/firmware.uf2`

```
   FLASH:      334748 B         1 MB     31.92%
FLASH_FS:           0 B        15 MB      0.00%
```

### 3.4 编译 4MB 固件

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE BOARD_VARIANT=4M -j$(nproc)
```

产物：`build-WEACTSTUDIO_RP2350A_CORE-4M/firmware.uf2`，链接日志为 `FLASH_FS: 0 B 3 MB`。

### 3.5 可选 RISC-V 版本

```bash
make BOARD=WEACTSTUDIO_RP2350A_CORE BOARD_VARIANT=RISCV -j$(nproc)
```

### 3.6 校验产物

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

4MB 版的 `embedded drive` 为 `0x10d00000-0x11000000 (3072K)`。

---

## 4. 烧录

| 方式 | 操作 |
|---|---|
| UF2 拖拽 | 按住 BOOT 插 USB，出现 `RP2350` 盘后把 `.uf2` 拖进去 |
| SWD | `picotool load -x firmware.elf` |

4MB 板不要烧 16MB 固件：文件系统基址 `0x10100000` 超出 4MB 物理 Flash，挂载与写入会失败。

烧录后主机可见：

| 设备 | 说明 |
|---|---|
| `MicroPython` 盘 | FAT 文件系统，放 `main.py`、`boot.py`；16MB 版约 15MB，4MB 版约 3MB |
| USB 串口 #1 | MicroPython REPL（USB CDC） |
| USB 串口 #2 | 板载 UART0（GP0/GP1，1500000 baud），需外接 USB-TTL |

只出现串口而没有盘符时，确认烧的是文件名带 `-msc` 的固件。

---

## 5. 验证用例

| # | 用例 | 命令 | 期望 |
|---|---|---|---|
| 1 | 启动 | 打开 REPL | 打印 `MicroPython v1.29.0 ... WeAct Studio RP2350A Core V10 (16MB)` |
| 2 | 芯片确认 | `os.uname()` | `sysname='rp2'`，machine 含板名 |
| 3 | Flash 分区 | `f=rp2.Flash(); f.ioctl(4,0)*f.ioctl(5,0)` | 16MB 版 15728640；4MB 版 3145728 |
| 4 | 文件系统 | `os.statvfs('/')` | 16MB 版约 15360KB；4MB 版约 3072KB |
| 5 | LED1 | `Pin(24,Pin.OUT).value(1)` | 蓝灯亮 |
| 6 | LED2 | `Pin(25,Pin.OUT).value(1)` | 绿灯亮 |
| 7 | 按键 | `Pin(23,Pin.IN,Pin.PULL_UP).value()` | 未按 1，按下 0 |
| 8 | 盘符 | 写 `main.py` 后复位 | 脚本自动执行 |
| 9 | 主频 | `machine.freq()` | 150000000 |
| 10 | 4MB 固件 | 重复 3、4、8 | 容量与盘符正确 |

第 1~10 条已封装为 [`firmware_test/`](firmware_test/README.md) 自动化套件。

---

## 6. 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 只有串口，没有盘符 | `MICROPY_HW_USB_MSC` 默认为 0 | 加 `#define MICROPY_HW_USB_MSC (1)`，用 `nm \| grep tud_msc` 确认 |
| `No picotool found` | CMake 需要 picotool ≥ 2.x | 单独编译并安装 picotool，加 `-Dpicotool_DIR=...` |
| `"PICO_FLASH_SIZE_BYTES" redefined` | pico-sdk 已定义该宏 | 先 `#undef PICO_FLASH_SIZE_BYTES` |
| `'MICROPY_HW_UART0_CTS' undeclared` | 缺少 CTS/RTS 宏 | `#define ..._CTS (-1)` / `_RTS (-1)` |
| `MICROPY_HW_FLASH_STORAGE_BYTES too big` | C 宏与 CMake 变量不一致 | `PICO_FLASH_SIZE_BYTES` 同时设为 CMake 变量 |
| `manifest error ... /modules` | 缺少 `modules/` 目录 | `mkdir -p .../modules` |
| 4MB 固件板名仍为 `(16MB)` | 宏没有进入 firmware target | 改用 `add_compile_definitions` |
| `lib/mbedtls/library/aes.c` 找不到 | mbedtls 版本过新 | 使用 mbedtls 3.6.x |

### 6.1 Flash 型号与 boot2

本板 Flash 为 XM25QH128（16MB），pico-sdk 的 WeAct 板级定义使用 `boot2_w25q080`，
与本板兼容性如下：

| boot2 动作 | XM25QH128 要求 | 匹配 |
|---|---|---|
| `0xEB` Quad I/O 读，模式位 `0xA0` | 支持 `EBh`，M7-M4=1010 进入连续读 | 是 |
| 读 SR2 后置 QE=1 | QSPI 需 QE=1，出厂为 0 | 是 |
| CLKDIV=2，即 75MHz | 支持 104MHz | 是 |
| SPI Mode 0 / Mode 3 | 两种都支持 | 是 |

无需更换 boot2。若某批次出现 XIP 异常，可在 `mpconfigboard.cmake` 中改用
`set(PICO_FLASH_BOOT_STAGE2_NAME "boot2_generic_03h")`。

---

## 7. 交付清单

```
rp2350a_weact_v10/
├── README.md                                            本文档（中文）
├── README-EN.md                                         英文版
├── firmware16M/
│   ├── WEACTSTUDIO_RP2350A_CORE_16M-v1.29.0-msc.uf2     16MB 板
│   └── firmware_16M.elf                                 SWD 调试
├── firmware4M/
│   ├── WEACTSTUDIO_RP2350A_CORE_4M-v1.29.0-msc.uf2      4MB 板
│   └── firmware_4M.elf
├── board_files/WEACTSTUDIO_RP2350A_CORE/                板级文件
├── patch/0001-add-board-WEACTSTUDIO_RP2350A_CORE.patch  补丁
├── firmware_test/                                       自检套件
└── examples/                                            示例代码
```

### 7.1 固件属性

| 项目 | 16MB 版 | 4MB 版 |
|---|---|---|
| UF2 family | `rp2350-arm-s` | `rp2350-arm-s` |
| MSC 符号数 | 16 | 16 |
| 文件系统区 | `0x10100000-0x11000000`（15360K） | `0x10d00000-0x11000000`（3072K） |
| MSC INQUIRY | WeAct / RP2350A V10 / 1.0 | 同左 |
| 板名 | `WeAct Studio RP2350A Core V10 (16MB)` | `… (4MB)` |

### 7.2 示例代码

| 文件 | 内容 |
|---|---|
| `weact_board.py` | 引脚定义与 `Led` / `Key` 封装 |
| `01`~`12` | LED、按键、UART、PWM、ADC、I2C、SPI、定时器、状态机 |
| `weact_link.h` | C 语言版权头与引脚宏 |

运行方式：`exec(open("03_key_poll.py").read())`，详见 [examples/README.md](examples/README.md)。
