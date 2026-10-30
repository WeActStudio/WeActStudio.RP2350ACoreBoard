# Default variant: ARM cores + 16MB Flash
# 默认变体：ARM 双核 + 16MB Flash
set(PICO_PLATFORM "rp2350")

# File system size lives in mpconfigboard.cmake (single source of truth),
# because ports/rp2/CMakeLists.txt needs it as a CMake variable, not only as a
# compiler definition.
# 文件系统容量统一在 mpconfigboard.cmake 里设定（唯一来源），因为
# ports/rp2/CMakeLists.txt 需要它作为 CMake 变量，而不只是编译宏。
