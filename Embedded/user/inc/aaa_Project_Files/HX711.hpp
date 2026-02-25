/** ****************************************************************************
 * @file    HX711.hpp
 * @author  Романовский Роман
 * @brief   Драйвер для 24-битного АЦП HX711
 * @details Содержит шаблонный класс HX711 для управления датчиками на основе
 *          HX711 через два GPIO-пина (данные и тактовый сигнал). Поддерживает
 *          выбор канала и коэффициента усиления с помощью перечисления HX711Gain.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef HX711_HPP
#define HX711_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <cmath>

#include "main.h"
#include "GpioPin.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace HX711
{

    /**
     * @brief   Выбор канала и коэффициента усиления для HX711.
     * @details Значения соответствуют количеству импульсов после чтения 24 бит:
     *          - Gain128_A: 1 импульс  → канал A, усиление 128
     *          - Gain32_B:  2 импульса → канал B, усиление 32
     *          - Gain64_A:  3 импульса → канал A, усиление 64
     */
    enum class HX711Gain : uint8_t {
        Gain128_A = 1,  ///< 1 pulse: Channel A, gain 128
        Gain32_B  = 2,  ///< 2 pulses: Channel B, gain 32
        Gain64_A  = 3   ///< 3 pulses: Channel A, gain 64
    };

    /**
     * @brief   Получить меньшее значение усиления (переключение вниз).
     * @param   gain   Текущее значение усиления.
     * @return  Предыдущее (меньшее) значение усиления в порядке возрастания:
     *          - Gain32_B  → Gain32_B (без изменений, т.к. это минимум);
     *          - Gain64_A  → Gain32_B;
     *          - Gain128_A → Gain64_A.
     */
    HX711Gain get_lower_gain(HX711Gain gain){
        switch (gain) {
            case HX711Gain::Gain32_B:  return HX711Gain::Gain32_B;
            case HX711Gain::Gain64_A:  return HX711Gain::Gain32_B;
            case HX711Gain::Gain128_A: return HX711Gain::Gain64_A;
            default: return gain;
        }
    }

    /**
     * @brief   Получить большее значение усиления (переключение вверх).
     * @param   gain   Текущее значение усиления.
     * @return  Следующее (большее) значение усиления в порядке возрастания:
     *          - Gain32_B  → Gain64_A;
     *          - Gain64_A  → Gain128_A;
     *          - Gain128_A → Gain128_A (без изменений, т.к. это максимум).
     */
    HX711Gain get_higher_gain(HX711Gain gain){
        switch (gain) {
            case HX711Gain::Gain32_B:  return HX711Gain::Gain64_A;
            case HX711Gain::Gain64_A:  return HX711Gain::Gain128_A;
            case HX711Gain::Gain128_A: return HX711Gain::Gain128_A;
            default: return gain;
        }
    }

    /// Разрядность АЦП (24 бита)
    constexpr uint8_t HX711BitRate = 24;

    /**
     * @brief   Количество итераций пустого цикла для задержки около 0.1 мкс.
     * @note    Значение подобрано эмпирически и зависит от частоты ядра.
     */
    constexpr uint8_t HX711FrontRisingTicks = 10;

    /// Максимальное число итераций при ожидании готовности данных (защита от зависания)
    constexpr uint32_t HX711MaxTimeout = 1000000;
    
    /// Флаг включения автоматического переключения канала и усиления (значение true)
    constexpr bool enableAutoGainControl = true;

    /// Флаг отключения автоматического переключения канала и усиления (значение false)
    constexpr bool disableAutoGainControl = false;

    /**
     * @brief   Верхнее пороговое значение АЦП для автоматического переключения канала или усиления.
     * @details Если измеренное значение превышает данный порог, то инициируется автоматическое
     *          переключение канала или коэффициента усиления для предотвращения насыщения
     *          и оптимизации измеряемого диапазона.
     */
    constexpr int32_t HighBoundaryADCValue = 0x7FFFFC;     // 0000 0000 0111 1111 1111 1111 1111 1100

    /**
     * @brief   Нижнее пороговое значение АЦП для автоматического переключения канала или усиления.
     * @details Если измеренное значение меньше данного порога, то инициируется автоматическое
     *          переключение канала или коэффициента усиления.
     */
    constexpr int32_t LowBoundaryADCValue = 0x0F;          // 0000 0000 0000 0000 0000 0000 0000 1111

    // -------------------------------------------------------------------------

    /**
     * @brief   Шаблонный класс для работы с 24-разрядным АЦП HX711.
     * @tparam  PinDT   Тип пина данных
     * @tparam  PinSCK  Тип тактового пина
     * @details Реализует протокол обмена с HX711: ожидание готовности, чтение 24 бит,
     *          выбор канала/усиления для следующего измерения. Тайминги обеспечиваются
     *          функциями microDelay() и пустым циклом для сверхкоротких задержек.
     * @warning Перед использованием необходимо вызвать init() для настройки пинов.
     * @note    Для работы требуются функции micro_timer_start/stop() и microDelay(),
     *          определённые в main.h.
     */
    template <STM_CppLib::STM_GPIO::GpioPinConcept PinDT, 
              STM_CppLib::STM_GPIO::GpioPinConcept PinSCK>
    class HX711{
    private:
        PinDT pin_dt;           ///< Пин данных (DOUT) HX711
        PinSCK pin_sck;         ///< Тактовый пин (SCK) HX711
        
    public:
        int32_t adc_value;      ///< Последнее считанное значение АЦП        
        HX711Gain gain;         ///< Выбранный канал и усиление
        bool auto_gain_control; ///< Флаг автоматического переключения канала и усиления

        /**
         * @brief   Конструктор по умолчанию запрещён – необходимо указать усиление.
         */
        HX711() = delete;

        /**
         * @brief   Конструктор с заданием усиления.
         * @param   initial_gain   Начальный канал и коэффициент усиления.
         */
        HX711(HX711Gain initial_gain, bool init_auto_gain_control): 
            gain(initial_gain), auto_gain_control(init_auto_gain_control) {}

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~HX711() = default;

        /**
         * @brief   Инициализация пинов для работы с HX711.
         * @details Настраивает пины: DT – вход без подтяжки, SCK – выход Push-Pull,
         *          скорость 2 МГц. Должен быть вызван до первого чтения.
         */
        void init(){
            pin_dt.InitPin(GPIO_Mode_IN, GPIO_PuPd_NOPULL, GPIO_Speed_2MHz);
            pin_sck.InitPin(GPIO_Mode_OUT, GPIO_PuPd_NOPULL, GPIO_Speed_2MHz);
        }

        /**
         * @brief   Выполняет чтение данных из АЦП.
         * @details Реализует временную диаграмму HX711: ожидание готовности (DT=0),
         *          затем 24 такта на SCK с формированием задержек. После чтения
         *          подаются импульсы для выбора следующего канала/усиления.
         *          Результат сохраняется в поле adc_value.
         * @note    Включает микросекундный таймер на время измерений.
         * @note    При таймауте ожидания готовности таймер останавливается и вызывается error_handler().
         */
        void read_adc_val(){
            uint32_t data = 0;
            uint32_t timeout = HX711MaxTimeout;

            // Ждем готовности данных (DT переходит в низкий уровень)
            while(pin_dt.ReadPin() == Bit_SET){
                if (--timeout == 0) {
                    micro_timer_stop();
                    error_handler();
                    return;
                }
            }

            // Подождём 1 мкс
            micro_timer_start();
            microDelay(1);      // T1: Небольшая задержка перед первым тактом
            
            // Считаем показания АЦП
	        for (uint8_t i = 0; i < HX711BitRate; i++){
                pin_sck.SetPin();

                // Задержка для нарастания/спада фронта
                // T2: установка SCK -> данные готовы
                for(uint8_t d = 0; d < HX711FrontRisingTicks; d++){
                    __NOP();    
                }

                // Считаем бит
                data <<= 1;
                if (pin_dt.ReadPin() == Bit_SET) {
                    data |= 1;
                }
                // T3: длительность высокого уровня
                microDelay(1);      

                pin_sck.ResetPin();
                
                // T4: длительность низкого уровня
                microDelay(1);
            }

            // Преобразование в знаковое 32-битное число
            // TODO: Проверить корректность перевода числа из дополнительного кода
	        if (data & 0x800000) data |= 0xFF000000;

            // Сохраним data в adc_value
            adc_value = static_cast<int32_t>(data);

            // Импульсы для указания усиления следующего измерения
            set_channel_multiplier();

            // Завершим чтение данных (лишний сброс оставлен для гарантии)
            pin_sck.ResetPin();
            micro_timer_stop();
        }

    private:

        /**
         * @brief   Подача импульсов для выбора канала и усиления следующего измерения.
         * @details Количество импульсов определяется значением gain.
         */
        void set_channel_multiplier(){
            if (auto_gain_control){
                // Автоматически изменим выбранный канал и усиление
                if(abs(adc_value) < LowBoundaryADCValue){
                    gain = get_higher_gain(gain);
                }
                else if (abs(adc_value) > HighBoundaryADCValue){
                    gain = get_lower_gain(gain);
                }                
            }

	        for (uint8_t i = 0; i < static_cast<uint8_t>(gain); i++){
                pin_sck.SetPin();
                microDelay(1);          // T3: длительность высокого уровня   
                pin_sck.ResetPin();
                microDelay(1);          // T4: длительность низкого уровня
            }
        }

        /**
         * @brief   Обработчик ошибки (таймаут ожидания готовности).
         * @todo    Реализовать более разумное поведение, например, удаление
         *          экземпляра из списка или установку флага ошибки.
         */
        void error_handler(){
            while (true)
            {
                /* code */
            }
        }
    };

} // namespace HX711

#endif /*   HX711_HPP   */