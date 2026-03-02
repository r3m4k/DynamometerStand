/** ****************************************************************************
 * @file    HX711Package.hpp
 * @author  Романовский Роман
 * @brief   Формирование пакета данных с АЦП HX711.
 * @details Содержит класс HX711Package, наследующий BasePackage, для упаковки
 *          данных с датчиков в бинарный формат, соответствующий протоколу.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef HX711_PACKAGE_HPP
#define HX711_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "BasePackage.hpp"
#include "HX711.hpp"

/* Defines -------------------------------------------------------------------*/
/**
 * @def     HeaderFirstByte
 * @brief   Первый байт заголовка пакета
 */
#define HeaderFirstByte     0xC8

/**
 * @def     HeaderSecondByte
 * @brief   Второй байт заголовка пакета
 */
#define HeaderSecondByte    0x8C

/**
 * @def     Format
 * @brief   Байт формата пакета
 */
#define Format              0x01

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace Packages{

    /**
     * @brief   Класс пакета данных с АЦП HX711.
     * @details Наследует BasePackage и формирует бинарный пакет фиксированной
     *          структуры. Использует внешние данные через указатели, переданные в конструктор.
     */
    class HX711Package: public BasePackage{
    private:
        int32_t* adc_value_ptr;        ///< Указатель на внешние данные АЦП
        HX711::HX711Gain* gain_ptr;     ///< Указатель на текущий канал и коэффициент усиления

        /**
         * @brief   Внутренняя структура пакета.
         * @details Соответствует формату протокола путеизмерительной телеги. Поля:
         *          - header[4]:  фиксированный заголовок (первые три байта константы,
         *                        четвёртый байт – длина полезных данных);
         *          - id_num:     порядковый номер АЦП в системе;
         *          - time:       32-битная временная метка;
         *          - adc_value:  данные АЦП;
         *          - gain:       коэффициент усиления;
         *          - control_sum: контрольная сумма (8 бит).
         */
        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {HeaderFirstByte, HeaderSecondByte, Format, 0};
            uint32_t time = 0;
            uint8_t id_num;
            int32_t adc_value;
            uint8_t gain;       
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

        static_assert(sizeof(package_body_t) <= 64,
              "HX711Package: structure package_body_t exceeds 64 bytes.\n"
              "Either increase the buffer size in hw_config.c or reduce the structure size.");

    public:
        /**
         * @brief   Конструктор по умолчанию запрещён (требуются указатели на данные).
         */
        HX711Package() = delete;

        /**
         * @brief   Конструктор с указателями на внешние данные.
         * @param   _id_num         Порядковый номер датчика в системе.
         * @param   _adc_value_ptr  Указатель на показания АЦП.
         * @param   _gain_ptr       Указатель на канал и коэффициент усиления АЦП.
         * @note    Переданные указатели должны оставаться валидными на всём
         *          протяжении использования объекта HX711Package.
         */
        HX711Package(uint8_t _id_num, int32_t* _adc_value_ptr, HX711::HX711Gain* _gain_ptr):
            adc_value_ptr(_adc_value_ptr), gain_ptr(_gain_ptr){

            // Последним байтом заголовка необходимо задать длину полезных данных:
            package_body.header[3] = sizeof(package_body) - sizeof(package_body.header) - sizeof(package_body.control_sum);
            
            // Укажем номер датчика для возможности идентификации нескольких датчиков 
            package_body.id_num = _id_num;
            
            len = sizeof(package_body);                             ///< Общая длина пакета
            data_ptr = reinterpret_cast<uint8_t*>(&package_body);   ///< Указатель на начало пакета
        }

        /**
         * @brief   Обновить содержимое пакета актуальными данными.
         * @details Копирует текущие значения из внешних объектов во внутреннюю структуру.
         */
        void UpdateData() {
            package_body.adc_value = *adc_value_ptr;
            package_body.gain = static_cast<uint8_t>(*gain_ptr);
        }

        /**
         * @brief   Обновить временную метку пакета.
         * @param   new_time   Новое значение времени.
         */
        void UpdateTime(uint32_t new_time){
            package_body.time = new_time;
        }

        /**
         * @brief   Пересчитать и обновить контрольную сумму пакета.
         * @details Вызывает CountControlSum() и сохраняет результат в поле control_sum.
         */
        void UpdateControlSum(){
            package_body.control_sum = CountControlSum();
        }
        
    private:
        /**
         * @brief   Вычисление контрольной суммы пакета.
         * @return  uint8_t   Сумма всех байтов пакета, кроме байта самой контрольной суммы.
         * @details Проходит по всем байтам data_ptr,
         *          накапливает сумму в 16-битной переменной и возвращает младший байт.
         */
        uint8_t CountControlSum(){
            uint16_t crc = 0;
            // Исключаем последний байт (собственно контрольную сумму)
            for (uint8_t i = 0; i < len - 1; i++){
                crc += data_ptr[i];
            }
            return static_cast<uint8_t>(crc);
        }        
    };

} // namespace Packages

#endif /*   HX711_PACKAGE_HPP   */