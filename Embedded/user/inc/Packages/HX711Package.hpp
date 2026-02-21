/**
 * @file    HX711Package.hpp
 * @author  Романовский Роман
 * @brief   Формирование пакета данных с АЦП HX711.
 * @details Содержит класс HX711Package, наследующий BasePackage, для упаковки
 *          данных с датчиков в бинарный формат, соответствующий протоколу.
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef HX711_PACKAGE_HPP
#define HX711_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "BasePackage.hpp"

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
        uint32_t* adc_value_ptr;     ///< Указатель на внешние данные АЦП

        /**
         * @brief   Внутренняя структура пакета (упакована без выравнивания).
         * @details Соответствует формату протокола путеизмерительной телеги. Поля:
         *          - header[4]:  фиксированный заголовок (первые три байта константы,
         *                        четвёртый байт – длина полезных данных);
         *          - id_num:     порядковый номер АЦП в системе;
         *          - time:       16-битная временная метка;
         *          - adc_value:  данные АЦП;
         *          - control_sum: контрольная сумма (8 бит).
         */
        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {HeaderFirstByte, HeaderSecondByte, Format, 0};
            uint8_t id_num;
            uint32_t time = 0;
            uint32_t adc_value;            
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

    public:
        /**
         * @brief   Конструктор по умолчанию запрещён (требуются указатели на данные).
         */
        HX711Package() = delete;

        /**
         * @brief   Конструктор с указателями на внешние данные.
         * @param   _adc_value_ptr  Указатель на показания АЦП.
         * @param   _id_num         Порядковый номер датчика в системе.
         * @note    Переданные указатели должны оставаться валидными на всём
         *          протяжении использования объекта HX711Package.
         */
        HX711Package(uint32_t* _adc_value_ptr, uint8_t _id_num):
            adc_value_ptr(_adc_value_ptr){

            // Последним байтом заголовка необходимо задать длину полезных данных:
            package_body.header[3] = sizeof(uint8_t) + 2 * sizeof(uint32_t);
            
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