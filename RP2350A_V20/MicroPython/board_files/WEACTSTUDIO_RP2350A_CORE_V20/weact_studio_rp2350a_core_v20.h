// Board header for pico-sdk: WeAct Studio RP2350A Core V20
// pico-sdk 板级头文件：WeAct Studio RP2350A Core V20
//
// V20 is hardware-identical to Raspberry Pi Pico 2 apart from the Flash size,
// so every definition below is a copy of boards/pico2.h except the Flash block
// and the board detection macro. When pico2.h changes, diff this file against
// it: anything other than FLASH and the board name is a bug.
// V20 与 Raspberry Pi Pico 2 硬件一致，只有 Flash 容量不同。因此下面除 Flash
// 部分与板名标识宏外，每一条都与 boards/pico2.h 相同。pico2.h 更新时直接对比
// 本文件即可：除 FLASH 与板名以外的差异都算 bug。
//
// This file is picked up by pico-sdk through PICO_BOARD_HEADER_DIRS, so the
// SDK does not need to ship a V20 definition of its own.
// 该文件由 pico-sdk 通过 PICO_BOARD_HEADER_DIRS 找到，无需 SDK 内置 V20 定义。
//
// -----------------------------------------------------
// NOTE: THIS HEADER IS ALSO INCLUDED BY ASSEMBLER SO
//       SHOULD ONLY CONSIST OF PREPROCESSOR DIRECTIVES
// -----------------------------------------------------

#ifndef _BOARDS_WEACT_STUDIO_RP2350A_CORE_V20_H
#define _BOARDS_WEACT_STUDIO_RP2350A_CORE_V20_H

pico_board_cmake_set(PICO_PLATFORM, rp2350)

// For board detection
#define WEACT_STUDIO_RP2350A_CORE_V20

// --- RP2350 VARIANT ---
// RP2350A, QFN-60 = PICO_RP2350A, 30 GPIO total, 26 on the header
// RP2350A，QFN-60 即 PICO_RP2350A，共 30 个 GPIO，其中 26 个到排针
#define PICO_RP2350A 1

// --- UART ---
#ifndef PICO_DEFAULT_UART
#define PICO_DEFAULT_UART 0
#endif
#ifndef PICO_DEFAULT_UART_TX_PIN
#define PICO_DEFAULT_UART_TX_PIN 0
#endif
#ifndef PICO_DEFAULT_UART_RX_PIN
#define PICO_DEFAULT_UART_RX_PIN 1
#endif

// --- LED ---
// Single onboard LED on GP25, active high, same as Pico 2.
// 板载单颗 LED 接 GP25，高电平点亮，与 Pico 2 一致。
#ifndef PICO_DEFAULT_LED_PIN
#define PICO_DEFAULT_LED_PIN 25
#endif
// no PICO_DEFAULT_WS2812_PIN / 没有 WS2812

// --- I2C ---
#ifndef PICO_DEFAULT_I2C
#define PICO_DEFAULT_I2C 0
#endif
#ifndef PICO_DEFAULT_I2C_SDA_PIN
#define PICO_DEFAULT_I2C_SDA_PIN 4
#endif
#ifndef PICO_DEFAULT_I2C_SCL_PIN
#define PICO_DEFAULT_I2C_SCL_PIN 5
#endif

// --- SPI ---
#ifndef PICO_DEFAULT_SPI
#define PICO_DEFAULT_SPI 0
#endif
#ifndef PICO_DEFAULT_SPI_SCK_PIN
#define PICO_DEFAULT_SPI_SCK_PIN 18
#endif
#ifndef PICO_DEFAULT_SPI_TX_PIN
#define PICO_DEFAULT_SPI_TX_PIN 19
#endif
#ifndef PICO_DEFAULT_SPI_RX_PIN
#define PICO_DEFAULT_SPI_RX_PIN 16
#endif
#ifndef PICO_DEFAULT_SPI_CSN_PIN
#define PICO_DEFAULT_SPI_CSN_PIN 17
#endif

// --- FLASH ---
// QSPI flash on the dedicated pins, boot2 compatible with the W25Q/XN25Q family.
// This is the one place where V20 differs from Pico 2: Pico 2 is always 4MB,
// V20 ships in 4MB and 16MB flavours. The real value is set by
// mpconfigboard.cmake per variant; the default here is the 16MB build.
// QSPI Flash 接专用引脚，boot2 与 W25Q/XN25Q 系列兼容。这是 V20 与 Pico 2 唯一
// 的差异：Pico 2 固定 4MB，V20 有 4MB 与 16MB 两种。实际值由
// mpconfigboard.cmake 按变体给出，这里的默认值对应 16MB 版本。
#define PICO_BOOT_STAGE2_CHOOSE_W25Q080 1

#ifndef PICO_FLASH_SPI_CLKDIV
#define PICO_FLASH_SPI_CLKDIV 2
#endif

pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (16 * 1024 * 1024))
#ifndef PICO_FLASH_SIZE_BYTES
#define PICO_FLASH_SIZE_BYTES (16 * 1024 * 1024)
#endif

// --- SMPS ---
// Drive high to force the buck into PWM mode (lower ripple on 3V3 at light
// loads). V20 uses the same RT6150 arrangement as Pico 2, with MODE on GP23,
// so this must be defined exactly as in pico2.h.
// 拉高可强制 buck 进入 PWM 模式（轻载时 3V3 纹波更小）。V20 与 Pico 2 用同一套
// RT6150 电路，MODE 接 GP23，因此必须与 pico2.h 一样定义这一条。
#define PICO_SMPS_MODE_PIN 23

// --- VBUS / VSYS monitor ---
// Both rails use a 100K/100K divider, so the tap carries half the rail:
//   VSYS -> R23 100K ->+-> R24 100K -> GND, tap -> GP29_ADC3
//   VBUS -> 100K     ->+-> 100K     -> GND, tap -> GP24
// VSYS is 5V max, i.e. 2.5V at the pin, inside the 3.3V ADC range. VBUS is read
// as a plain digital input: high = USB power present.
// VSYS 与 VBUS 都是 100K/100K 分压，引脚上只有一半电压：
//   VSYS -> R23 100K ->+-> R24 100K -> GND，中点 -> GP29_ADC3
//   VBUS -> 100K     ->+-> 100K     -> GND，中点 -> GP24
// VSYS 最高 5V，分压后 2.5V，在 3.3V ADC 量程内。VBUS 当数字输入读：
// 高电平即表示 USB 供电存在。
#ifndef PICO_VBUS_PIN
#define PICO_VBUS_PIN 24
#endif
#ifndef PICO_VSYS_PIN
#define PICO_VSYS_PIN 29
#endif

pico_board_cmake_set_default(PICO_RP2350_A2_SUPPORTED, 1)
#ifndef PICO_RP2350_A2_SUPPORTED
#define PICO_RP2350_A2_SUPPORTED 1
#endif

#endif
