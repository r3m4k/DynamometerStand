/** ****************************************************************************
 * @file    UsbPort.hpp
 * @brief   Класс для работы с виртуальным COM-портом (VCP) через USB.
 * @details Содержит реализацию UsbPort, которая использует декодер для
 *          обработки входящих сообщений и предоставляет методы для отправки
 *          пакетов и сообщений.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef COM_PORT_HPP
#define COM_PORT_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <string.h>
#include <concepts>

#include "VCP_F3.h"
#include "hw_config.h"
#include "BasePackage.hpp"
#include "Message.hpp"
#include "DecoderTelega.hpp"

/* Defines -------------------------------------------------------------------*/
// TODO: убрать повторный define
#define ENABLE_COMMAND_PROCESSING   1   // Дефайн для включения обработки поступивших
                                        // команд (0 - выкл / 1 - вкл)

/* Usings --------------------------------------------------------------------*/

#if ENABLE_COMMAND_PROCESSING
/**
 * @brief   Тип декодера, используемый для обработки входящих сообщений.
 * @details По умолчанию используется DecoderTelega. Может быть заменён
 *          на другой тип, удовлетворяющий концепту HasVoidMessageProcessing.
 */
using Decoder = DecoderTelega;
#endif  /* ENABLE_COMMAND_PROCESSING */

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace UsbPort
    {
            
    /**
     * @brief   Концепт, проверяющий наличие метода message_processing(Message&).
     * @details Требует, чтобы тип Decoder имел метод
     *          void message_processing(Messages::Message&).
     *          Используется для статической проверки совместимости декодера
     *          с классом UsbPort.
     */
    template<typename T>
    concept HasVoidMessageProcessing = requires(T decoder, Messages::Message& msg) {
        { decoder.message_processing(msg) } -> std::same_as<void>;
    };

    /**
     * @brief   Класс для управления виртуальным COM-портом (VCP).
     * @details Предоставляет инициализацию порта, отправку пакетов и сообщений,
     *          а также обработку входящих данных через декодер.
     */
    class UsbPort{
        
    #if ENABLE_COMMAND_PROCESSING
        static_assert(HasVoidMessageProcessing<Decoder>,
            "\n=== DECODER INTERFACE ERROR ===\n"
            "Decoder type must provide: void message_processing(Messages::Message&)\n"
            "===============================\n");
    #endif  /* ENABLE_COMMAND_PROCESSING */

    private:

    #if ENABLE_COMMAND_PROCESSING
        Decoder decoder;    ///< Декодер для обработки входящих сообщений
    #endif  /* ENABLE_COMMAND_PROCESSING */

    public:
        /**
         * @brief   Конструктор по умолчанию.
         */
        UsbPort() = default;

        /**
         * @brief   Деструктор.
         */
        ~UsbPort() = default;

        /**
         * @brief   Инициализация COM-порта.
         * @details Выполняет сброс порта (VCP_ResetPort) и инициализацию VCP (VCP_Init).
         */
        void Init(){
            VCP_ResetPort();    // Подтягиваем ножку D+ к нулю для правильной идентификации
            VCP_Init();         // Инициализация VCP
        }

        /**
         * @brief   Отправка пакета данных через COM-порт.
         * @param   package   Ссылка на базовый пакет (BasePackage), содержащий данные и длину.
         */
        void SendPackage(Packages::BasePackage& package){
            CDC_Send_DATA(package.data_ptr, package.len);
        }

        /**
         * @brief   Отправка сообщения фиксированной длины через COM-порт.
         * @param   message   Ссылка на объект Message, содержащий массив байт.
         */
        void SendMessage(Message& message){
            CDC_Send_DATA(message.bytes_msg, message.msg_size);
        }
        
    #if ENABLE_COMMAND_PROCESSING
        /**
         * @brief   Обработка входящего сообщения (вызывается из callback USB).
         * @param   message   Ссылка на принятое сообщение.
         * @details Передаёт сообщение декодеру для дальнейшей обработки.
         */
        void EP3_OUT_Callback(Messages::Message& message){
            decoder.message_processing(message);
        }
    #endif  /* ENABLE_COMMAND_PROCESSING */
    };

    } // namespace UsbPort
} // namespace STM_CppLib

#endif /*   COM_PORT_HPP   */