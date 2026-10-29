// Board and hardware configuration for WeAct Studio RP2350A Core V10
// WeAct Studio RP2350A Core V10 板级与硬件配置
//
// Default build is the 16MB Flash variant;
// 默认构建为 16MB Flash 版本，使用 MICROPY_BOARD_VARIANT=4M 构建 4MB 版本。

// USB Mass Storage: the MicroPython drive that holds .py files.
// USB 大容量存储，即存放 .py 的 MicroPython 盘。mpconfigport.h 中默认值为 0，
// 不显式打开时固件只枚举 CDC 串口，主机不会出现盘符。
#define MICROPY_HW_USB_MSC (1)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING "WeAct"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING "RP2350A V10"
#define MICROPY_HW_USB_MSC_INQUIRY_REVISION_STRING "1.0"

// Onboard LED1 = GPIO24, LED2 = GPIO25, user key = GPIO23 (active low)
// 板载 LED1=GPIO24、LED2=GPIO25，用户按键=GPIO23，低电平有效。
#define MICROPY_HW_LED1_PIN (24)
#define MICROPY_HW_LED2_PIN (25)
#define MICROPY_HW_KEY_PIN  (23)

// UART0 on GP0(TX) / GP1(RX), CTS and RTS not connected
// UART0 引出到 GP0(TX)/GP1(RX)，CTS/RTS 未连接，需显式给 -1。
#define MICROPY_HW_UART0_TX (0)
#define MICROPY_HW_UART0_RX (1)
#define MICROPY_HW_UART0_CTS (-1)
#define MICROPY_HW_UART0_RTS (-1)

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
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V10 (16MB)"
#else
// 4MB Flash variant
// 4MB Flash 版本
#define PICO_FLASH_SIZE_BYTES (4 * 1024 * 1024)
#define MICROPY_HW_BOARD_NAME "WeAct Studio RP2350A Core V10 (4MB)"
#endif
