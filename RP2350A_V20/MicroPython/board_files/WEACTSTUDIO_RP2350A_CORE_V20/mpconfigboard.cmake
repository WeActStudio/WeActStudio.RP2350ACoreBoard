# CMake file for WeAct Studio RP2350A Core V20
# WeAct Studio RP2350A Core V20 的 CMake 配置
#
# MCU: RP2350A QFN-60, 26 GPIO on the 40-pin header
# 芯片：RP2350A QFN-60，40 pin 排针引出 26 个 GPIO
# Onboard: 16MB/4MB QSPI Flash, 1x LED (GP25), BOOT + RESET keys, USB 1.1
# 板载：16MB/4MB QSPI Flash、1x LED(GP25)、BOOT/RESET 按键、USB1.1
#
# MICROPY_BOARD_VARIANT selects the Flash size: 16M (default) / 4M
# 用 MICROPY_BOARD_VARIANT 区分 Flash 容量：16M（默认）/ 4M

# V20 has no board definition in pico-sdk, so point PICO_BOARD at the header
# shipped in this directory and add that directory to the search path.
# pico-sdk 没有 V20 的板级定义，所以把 PICO_BOARD 指向本目录下的板级头，
# 并把本目录加入头文件搜索路径。
list(APPEND PICO_BOARD_HEADER_DIRS ${MICROPY_BOARD_DIR})
set(PICO_BOARD "weact_studio_rp2350a_core_v20")

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

# File system size = Flash size - 1MB reserved for the firmware.
# This MUST be a plain CMake variable: ports/rp2/CMakeLists.txt turns it into
# both a compile definition (rp2_flash.c) and the linker symbol
# __micropy_flash_storage_bytes__ (linker script asserts / map report).
# Putting it only into MICROPY_DEF_BOARD gives the macro but leaves the linker
# in the dark, which shows up as "FLASH_FS: 0 B 18446744073709551615 B".
# 文件系统容量 = Flash 总量 - 1MB 固件预留。
# 这里必须是普通 CMake 变量：ports/rp2/CMakeLists.txt 会同时把它变成编译宏
# （rp2_flash.c 使用）和链接符号 __micropy_flash_storage_bytes__（链接脚本断言
# 与 map 报告使用）。只写进 MICROPY_DEF_BOARD 时宏有了、链接符号却是空的，
# 表现为 "FLASH_FS: 0 B 18446744073709551615 B"。
if(MICROPY_BOARD_VARIANT STREQUAL "4M")
    if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
        set(MICROPY_HW_FLASH_STORAGE_BYTES 3145728)  # 4MB - 1MB = 3MB
    endif()
else()
    if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
        set(MICROPY_HW_FLASH_STORAGE_BYTES 15728640) # 16MB - 1MB = 15MB
    endif()
endif()

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
