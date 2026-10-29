# Default variant: ARM core + 16MB Flash
# 默认变体：ARM 架构 + 16MB Flash
set(PICO_PLATFORM "rp2350")
set(MICROPY_HW_FLASH_16M 1)

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    # 16MB - 1MB reserved for firmware = 15MB file system
    # 16MB 减去 1MB 固件预留 = 15MB 文件系统
    set(MICROPY_HW_FLASH_STORAGE_BYTES 15728640)
endif()
