/** ****************************************************************************
 * @file CommandProcessing.hpp
 * @brief Модуль обработки команд для встроенной системы.
 * 
 * Данный модуль предоставляет механизмы для регистрации, сравнения и выполнения 
 * команд в системе. Команды представляются в виде байтовых последовательностей 
 * фиксированной длины и связываются с обработчиками - функциями без аргументов.
 * 
 * @version 1.0.0
 * @date Январь 2026
 * @author Романовский Роман
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef COMMAND_PROCESSING_HPP
#define COMMAND_PROCESSING_HPP

/* Includes ------------------------------------------------------------------*/
#include <cstring>

#include "CommandDescription.hpp"
#include "Message.hpp"
#include "StaticQueue.hpp"

/* Defines -------------------------------------------------------------------*/

/* Using  --------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

namespace STM_CppLib{
    namespace Commands{

// -----------------------------------------------------------------------------
/*!
 * @defgroup SupportedCommands Поддерживаемые команды
 * @brief Предопределенные команды системы.
 * 
 * Каждая команда представлена в виде глобального объекта Command 
 * с уникальным байтовым кодом и привязанным обработчиком.
 * @{
 */

//! Количество поддерживаемых команд
inline constexpr uint8_t num_of_supported_commands = 3;

/*!
 * @var Restart
 * @brief Команда перезагрузки микроконтроллера.
 * 
 * Код команды: {0xc8, 0x8c, 0xff, 0xff, 0x00, 0x00}
 * Обработчик: restart()
 */
inline constexpr uint8_t Restart_Code[CommandLength] = 
        {0xc8, 0x8c, 0xff, 0xff, 0x00, 0x00};
inline Command Restart(Restart_Code, restart);

/*!
 * @var Set_FooStage
 * @brief Команда перезагрузки микроконтроллера.
 * 
 * Код команды: {0xc8, 0x8c, 0xff, 0xaa, 0x01, 0x00}
 * Обработчик: restart()
 */
inline constexpr uint8_t Set_FooStage_Code[CommandLength] = 
        {0xc8, 0x8c, 0xff, 0xaa, 0x01, 0x00};
inline Command Set_FooStage(Set_FooStage_Code, set_FooStage);

/*!
 * @var Set_MeasureStage
 * @brief Команда перезагрузки микроконтроллера.
 * 
 * Код команды: {0xc8, 0x8c, 0xff, 0xaa, 0x02, 0x00}
 * Обработчик: restart()
 */
inline constexpr uint8_t Set_MeasureStage_Code[CommandLength] = 
        {0xc8, 0x8c, 0xff, 0xaa, 0x02, 0x00};
inline Command Set_MeasureStage(Set_MeasureStage_Code, set_MeasureStage);

/** @} */ // конец группы SupportedCommands


/** ****************************************************************************
 * @class CommandManager
 * @brief Менеджер команд системы.
 * 
 * Управляет набором поддерживаемых команд, обеспечивает их сопоставление
 * с поступающими сообщениями и помещение в очередь на выполнение.
  **************************************************************************** */
 
class CommandManager{
private:
    // Массив поддерживаемых команд
    inline static Command supported_commands[num_of_supported_commands] = {
        Restart,
        Set_FooStage,
        Set_MeasureStage,
    };

public:
    StaticQueue<CommandHandler, 4> command_queue;      // Статичная очередь поступивших команд

    // Метод для проверки, является ли сообщение одной из поддерживаемых команд
    const Command* match_message_to_command(const Message& message) const {
        for (uint8_t i = 0; i < num_of_supported_commands; i++){
            if (supported_commands[i] == message){
                return &supported_commands[i];
            }
        }
        return nullptr;
    }

    // Добавление команды в очередь команд
    bool add_command(const Command& command){
        if(!command_queue.is_full()){
            command_queue.put(command.command_handler);
            return true;
        }
        return false;
    }

};

    } // namespace Commands
} // namespace STM_CppLib

#endif /*   COMMAND_PROCESSING_HPP   */