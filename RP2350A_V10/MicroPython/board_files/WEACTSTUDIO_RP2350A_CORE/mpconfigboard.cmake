# CMake file for WeAct Studio RP2350A Core V10
# WeAct Studio RP2350A Core V10 的 CMake 配置
#
# MCU: RP2350A QFN-60, 30 GPIOs (GPIO0-GPIO29)
# 芯片：RP2350A QFN-60，30 个可用 GPIO（GPIO0~GPIO29）
# Onboard: 16MB/4MB QSPI Flash, 2x LED (GP24/GP25), key (GP23), USB 1.1
# 板载：16MB/4MB QSPI Flash、2x LED(GP24/GP25)、按键(GP23)、USB1.1
#
# MICROPY_BOARD_VARIANT selects the Flash size: 16M (default) / 4M
# 用 MICROPY_BOARD_VARIANT 区分 Flash 容量：16M（默认）/ 4M

# Reuse the board definition shipped with pico-sdk
# 复用 pico-sdk 中已有的 RP2350A V10 板级定义，4MB 时由 mpconfigboard.h 覆盖容量。
set(PICO_BOARD "weact_studio_rp2350a_core_v10_16mb")

# Keep the CMake variable in sync with the variant (used for the linker script)
# 让 CMake 变量与变体一致，pico-sdk 用它生成链接脚本中的 Flash 大小。
if(MICROPY_BOARD_VARIANT STREQUAL "4M")
    set(PICO_FLASH_SIZE_BYTES 4194304)
    set(MICROPY_HW_FLASH_16MB 0)
else()
    set(PICO_FLASH_SIZE_BYTES 16777216)
    set(MICROPY_HW_FLASH_16MB 1)
endif()

# CMake variables do not become C macros automatically
# CMake 普通变量不会自动变成 C 宏，必须显式 add_compile_definitions，
# PICO_BOARD_EXTRA_DEFINES 不影响 MicroPython 的 firmware target。
add_compile_definitions(MICROPY_HW_FLASH_16MB=${MICROPY_HW_FLASH_16MB})

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
