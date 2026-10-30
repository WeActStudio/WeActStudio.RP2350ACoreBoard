// Board and hardware configuration for WeAct Studio RP2350A Core V20
// WeAct Studio RP2350A Core V20 板级与硬件配置
//
// V20 is hardware-identical to Pico 2 except for the Flash size, so this file
// only adds what MicroPython needs on top of pico2.h: the board name, the USB
// mass storage drive, and the per-variant Flash split.
// V20 除 Flash 容量外与 Pico 2 完全一致，因此本文件只在 pico2.h 之上补
// MicroPython 需要的东西：板名、USB 盘符，以及按变体区分的 Flash 划分。
//
// Default build is the 16MB Flash variant;
// 默认构建为 16MB Flash 版本，使用 MICROPY_BOARD_VARIANT=4M 构建 4MB 版本。

// USB Mass Storage: the MicroPython drive that holds .py files.
// USB 大容量存储，即存放 .py 的 MicroPython 盘。mpconfigport.h 中默认值为 0，
// 不显式打开时固件只枚举 CDC 串口，主机不会出现盘符。
#define MICROPY_HW_USB_MSC (1)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING "WeAct"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING "RP2350A V20"
#define MICROPY_HW_USB_MSC_INQUIRY_REVISION_STRING "1.0"

// Onboard LED = GP25, high level lights it up. V20 has no user key:
// only BOOT (QSPI_SS) and RESET (RUN) are populated.
// 板载 LED = GP25，高电平点亮。V20 没有用户按键，板上只有用于下载的 BOOT
// 键（拉低 QSPI_SS）和 RESET 键（拉低 RUN）。
#define MICROPY_HW_LED_PIN (25)
#define MICROPY_HW_LED1_PIN (25)

// UART0 on GP0(TX) / GP1(RX), CTS and RTS not connected
// UART0 引出到 GP0(TX)/GP1(RX)，CTS/RTS 未连接，需显式给 -1。
#define MICROPY_HW_UART0_TX (0)
#define MICROPY_HW_UART0_RX (1)
#define MICROPY_HW_UART0_CTS (-1)
#define MICROPY_HW_UART0_RTS (-1)

// The 3V3 rail is the same RT6150 buck as Pico 2, with MODE on GP23.
// PICO_SMPS_MODE_PIN is therefore defined by the board header, exactly as in
// pico2.h -- see weact_studio_rp2350a_core_v20.h.
// V20 的 3V3 与 Pico 2 同为 RT6150 buck，MODE 接 GP23。因此
// PICO_SMPS_MODE_PIN 与 pico2.h 一样在板级头里定义，这里不再重复。

// Already defined by the pico-sdk board header, undef before overriding
// pico-sdk 板级头已定义该宏，先 undef 再用变体值覆盖。
#undef PICO_FLASH_SIZE_BYTES
#ifndef MICROPY_HW_FLASH_16MB
#define MICROPY_HW_FLASH_16MB 1
#endif

#if MICROPY_HW_FLASH_16MB
// 16MB Flash variant
// 16MB Flash 版本
#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V20 (16MB)"
#else
// 4MB Flash variant
// 4MB Flash 版本
#define PICO_FLASH_SIZE_BYTES (4 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V20 (4MB)"
#endif

// File system size comes from mpconfigboard.cmake as a real CMake variable
// (it becomes both the compile definition and the __micropy_flash_storage_bytes__
// linker symbol). This block is only a defensive fallback for standalone use.
// 文件系统容量由 mpconfigboard.cmake 以普通 CMake 变量传入（同时变成编译宏和
// __micropy_flash_storage_bytes__ 链接符号），这里仅作兜底。
#ifndef MICROPY_HW_FLASH_STORAGE_BYTES
#define MICROPY_HW_FLASH_STORAGE_BYTES (PICO_FLASH_SIZE_BYTES - (1024 * 1024))
#endif
