// =============================================================================
//  WeAct Studio Official Link
//    taobao     : weactstudio.taobao.com
//    aliexpress : weactstudio.aliexpress.com
//    github     : github.com/WeActStudio
//    gitee      : gitee.com/WeAct-TC
//    blog      : www.weact-tc.cn
// =============================================================================
//  weact_link.h -- WeAct Studio 版权头与板级引脚宏 / copyright header and pin macros
//
//  功能 / Function:
//      提供可直接复制到 .c / .h 文件开头的 /** */ 版权注释，
//      以及本板引脚、LED、按键的宏定义与 GPIO 编号。
//      Provide the /** */ copyright block to copy into .c / .h files, plus the
//      onboard LED, key and bus pin macros with their GPIO numbers.
// =============================================================================

/** WeAct Studio Official Link
  * taobao     : weactstudio.taobao.com
  * aliexpress : weactstudio.aliexpress.com
  * github     : github.com/WeActStudio
  * gitee      : gitee.com/WeAct-TC
  * blog      : www.weact-tc.cn
  */

#ifndef WEACT_BOARD_H
#define WEACT_BOARD_H

/* LED, active high / LED，高电平点亮 */
#define WEACT_LED1_PIN          24u
#define WEACT_LED2_PIN          25u

/* User key, active low, needs pull-up / 用户按键，低电平有效，需上拉 */
#define WEACT_KEY_PIN           23u

/* UART0 */
#define WEACT_UART0_TX_PIN      0u
#define WEACT_UART0_RX_PIN      1u

/* I2C0 */
#define WEACT_I2C0_SDA_PIN      4u
#define WEACT_I2C0_SCL_PIN      5u

/* SPI0 */
#define WEACT_SPI0_SCK_PIN      18u
#define WEACT_SPI0_MOSI_PIN     19u
#define WEACT_SPI0_MISO_PIN     16u
#define WEACT_SPI0_CSN_PIN      17u

/* ADC channels / ADC 通道 */
#define WEACT_ADC0_PIN          26u
#define WEACT_ADC1_PIN          27u
#define WEACT_ADC2_PIN          28u
#define WEACT_ADC3_PIN          29u

#endif /* WEACT_BOARD_H */
