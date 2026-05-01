/**
 * @file    DecoderHX711.hpp
 * @author  Романовский Роман
 * @brief   Декодер сообщений протокола «HX711» для приёма команд по COM-порту.
 * 
 * @note    Для работы необходимы глобальный объект command_manager
 *          определённый в пользовательском коде.
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef DECODER_HX711_HPP
#define DECODER_HX711_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "Message.hpp"
#include "CommandManager.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/
/**
 * @brief   Внешний менеджер команд, определённый в пользовательском коде.
 */
extern Commands::CommandManager command_manager;

// -----------------------------------------------------------------------------

namespace Decoder{

    /**
     * @brief   Декодер командных пакетов IMU-протокола.
     * @details Конкретизирует BaseDecoder под протокол IMU: задаёт байты
     *          заголовка, реализует выбор функции разбора по байту формата.
     *          Для контрольной суммы используется реализация по умолчанию
     *          (модульная сумма) из BaseDecoder.
     */
    class DecoderHX711 : public BaseDecoder<DecoderHX711>{
    public:
        /**
         * @brief   Первый байт заголовка командного пакета.
         */
        static constexpr uint8_t HeaderFirstByte  = 0xC8;

        /**
         * @brief   Второй байт заголовка командного пакета.
         */
        static constexpr uint8_t HeaderSecondByte = 0x8C;

        /**
         * @def     HX711CommandType
         * @brief   Байт формата для командного пакета.
         */
        static constexpr uint8_t HX711CommandType = 0xAB;

        /**
         * @brief   Возвращает функцию разбора пакета по байту формата.
         * @param   fmt   Байт формата из пакета.
         * @return  DecodeFunc   Функция-обработчик пакета или nullptr,
         *                       если формат неизвестен.
         * @details Поддерживаемые форматы:
         *          - HX711CommandType (0xAB) – командный пакет, обрабатывается
         *            функцией process_command_packet.
         *          Возвращает nullptr для любых других значений.
         */
        DecodeFunc get_decode_func(uint8_t fmt){
            switch (fmt){
                case HX711CommandType: return &process_command_packet;
                default: return nullptr;
            }
        }

    private:
        /**
         * @brief   Обработчик командного пакета.
         * @param   msg   Собранный пакет (header + format + length + data + crc).
         * @details Строит view-объект на data-секцию пакета и ищет команду
         *          сначала в списке срочных, затем в списке отложенных:
         *          - срочная команда: если команда требует подтверждения
         *            (confirm_policy == Required), выполняется
         *            Send_Confirm_Cmd.handler.execute() (блокирующая отправка
         *            в IRQ), затем сразу исполняется обработчик полученной
         *            команды в контексте декодера;
         *          - отложенная команда: если команда требует подтверждения,
         *            в очередь помещается Send_Confirm_Cmd, затем сам обработчик.
         *            Иначе — только обработчик. Записи исполняются в main
         *            в порядке добавления.
         *          - если команда не найдена — в очередь помещается
         *            Send_Error_Cmd, которая в main отправит ПК сообщение
         *            об ошибке.
         *
         * @note    Срочные команды исполняются в контексте USART IRQ,
         *          поэтому должны быть короткими и IRQ-safe.
         *          Блокирующая отправка confirm в urgent-ветке (при Required) —
         *          временный компромисс; перенос в main запланирован вместе
         *          с миграцией USART.
         */
        static void process_command_packet(const Messages::Message& msg){
            // View на data-секцию принятого пакета:
            //   смещение 4 (header 2 + format 1 + length 1),
            //   длина из байта length (bytes_msg[3]).
            const uint8_t data_len = msg.bytes_msg[3];
            Messages::Message code(&msg.bytes_msg[4], data_len);

            // 1. Срочная команда — подтвердить (если требуется) и исполнить немедленно.
            const Commands::BaseCommand* urgent = command_manager.find_urgent(code);
            if (urgent){
                if (urgent->confirm_policy == Commands::ConfirmPolicy::Required){
                    Commands::Send_Confirm_Cmd.handler.execute();
                }
                urgent->handler.execute();
                return;
            }

            // 2. Отложенная команда — в очередь сначала подтверждение
            //    (если команда его требует), затем сам обработчик.
            //    Обе записи исполнятся в main.
            const Commands::BaseCommand* deferred = command_manager.find_deferred(code);
            if (deferred){
                if (deferred->confirm_policy == Commands::ConfirmPolicy::Required){
                    command_manager.add_to_queue(Commands::Send_Confirm_Cmd);
                }
                command_manager.add_to_queue(*deferred);
                return;
            }

            // 3. Команда не найдена — положить в очередь сообщение об ошибке.
            command_manager.add_to_queue(Commands::Send_Error_Cmd);
        }
    };

} // namespace Decoder

#endif /*   DECODER_HX711_HPP   */