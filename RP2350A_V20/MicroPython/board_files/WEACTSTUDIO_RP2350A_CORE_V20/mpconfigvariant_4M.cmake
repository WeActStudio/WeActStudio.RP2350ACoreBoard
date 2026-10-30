# 4MB Flash variant: make BOARD=WEACTSTUDIO_RP2350A_CORE_V20 BOARD_VARIANT=4M
# 4MB Flash 变体
set(PICO_PLATFORM "rp2350")

# 3MB file system = 4MB Flash - 1MB firmware reserve, set in mpconfigboard.cmake
# 3MB 文件系统 = 4MB Flash - 1MB 固件预留，具体值在 mpconfigboard.cmake 中设定
