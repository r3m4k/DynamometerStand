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
extern STM_CppLib::Commands::CommandManager command_manager;

// -----------------------------------------------------------------------------
/**
 * @brief   Декодер сообщений от компьютера (протокол «Телега»).
 * @details Содержит конечный автомат для последовательного разбора байтов
 *          входящего сообщения. Поддерживаемый формат:
 *          - Заголовок: 0x7E, 0xE7
 *          - Формат: 0xFF (в данной версии только этот формат)
 *          - Данные: 2 байта
 *          - Контрольная сумма: младший байт суммы всех предыдущих байтов.
 * 
 *          При успешном приёме вызывается com_port.SendConfirmMessage(),
 *          сообщение передаётся в command_manager.match_message_to_command(),
 *          и если команда найдена, она добавляется в очередь команд.
 *          В противном случае отправляется сообщение об ошибке.
 */
class DecoderHX711{
private:
    STM_CppLib::Message current_message;   ///< Текущее обрабатываемое сообщение

public:
    /**
     * @brief   Конструктор по умолчанию.
     * @details Инициализирует автомат начальным состоянием Want7E.
     */
    DecoderHX711() = default;

    /**
     * @brief   Деструктор по умолчанию.
     */
    ~DecoderHX711() = default;

    /**
     * @brief   Обработка входящего сообщения.
     * @param   message   Константная ссылка на объект Message (64 байта).
     * @details Сохраняет сообщение во внутренний буфер и последовательно
     *          передаёт каждый байт методу byte_processing().
     */
    void message_processing(const STM_CppLib::Message& message){
        // Скопируем сообщений для безопасности и 
        // для возможности его использования в других методах
        current_message = message;
        const STM_CppLib::Commands::Command* command = command_manager.match_message_to_command(current_message);
        if (command){
            command_manager.add_command(*command);
        }
        else {
            send_error_msg();
        }
    }
};

#endif /*   DECODER_HX711_HPP   */