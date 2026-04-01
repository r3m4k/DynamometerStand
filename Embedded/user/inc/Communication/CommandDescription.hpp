/** ****************************************************************************
 * @file CommandDescription.hpp
 * @brief Модуль описания команд для встроенной системы.
 * 
 * @version 1.0.0
 * @date Январь 2026
 * @author Романовский Роман
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef COMMAND_DESCRIPTION_HPP
#define COMMAND_DESCRIPTION_HPP

/* Includes ------------------------------------------------------------------*/
#include <cstring>

#include "main.h"
#include "Message.hpp"
#include "StaticQueue.hpp"

/* Defines -------------------------------------------------------------------*/
#define CommandLength   6   // Длина массива для кодировки команды

/* Using  --------------------------------------------------------------------*/
using CommandHandlerFunc = void(*)(void);

/* Global variables ----------------------------------------------------------*/

namespace STM_CppLib{
    namespace Commands{

/** ****************************************************************************
 * @class CommandHandler
 * @brief Класс-обёртка для функции-обработчика команды.
 * 
 * Инкапсулирует указатель на функцию, предоставляет безопасный интерфейс 
 * для выполнения обработчика. Поддерживает только копирование, перемещение 
 * запрещено.
 **************************************************************************** */

class CommandHandler{
    CommandHandlerFunc handler;

public:
    // 
    CommandHandler(): handler(nullptr) {}

    // Конструктор с функцией без аргументов
    CommandHandler(CommandHandlerFunc _handler): handler(_handler){}

    // Конструктор копирования
    CommandHandler(const CommandHandler& other){
        handler = other.handler;
    }
    
    // Оператор присваивания копированием
    CommandHandler& operator=(const CommandHandler& other){
        if (this != &other){
            handler = other.handler;
        }        
        return *this;
    }

    // Конструктор перемещения 
    CommandHandler(CommandHandler&& other) noexcept = delete;
    
    // Оператор присваивания перемещением
    CommandHandler& operator=(CommandHandler&& other) noexcept = delete;

    // Запуск обработчика
    void execute(){
        if (handler) {
            handler();
        }
    }
};

/** ****************************************************************************
 * @class Command
 * @brief Класс, описывающий команду системы.
 * 
 * Содержит байтовый код команды и связанный с ней обработчик.
 * Предоставляет операторы сравнения с сообщениями и другими командами.
 **************************************************************************** */

class Command{
public:
    uint8_t command_code[CommandLength];    // Массив для кодировки команды
    CommandHandler command_handler;         // Обработчик команды
    
    // Конструктор с массивом и обработчиком
    Command(const uint8_t* _command_code, CommandHandlerFunc _handler_func): 
            command_handler(_handler_func){
        std::memcpy(command_code, _command_code, CommandLength);
    }

    // Конструктор копирования
    Command(const Command& other) : command_handler(other.command_handler) {
        std::memcpy(command_code, other.command_code, CommandLength);
    }
    
    // Оператор присваивания копированием
    Command& operator=(const Command& other){
        if (this != &other){
            std::memcpy(command_code, other.command_code, CommandLength);
            command_handler = other.command_handler;
        }        
        return *this;
    }

    // Конструктор перемещения 
    Command(Command&& other) noexcept = delete;
    
    // Оператор присваивания перемещением
    Command& operator=(Command&& other) noexcept = delete;

    // Оператор сравнения
    bool operator==(const Message& msg){
        return std::memcmp(command_code, msg.bytes_msg, CommandLength) == 0;
    }

    // Оператор сравнения с массивом байтов
    bool operator==(const uint8_t* code) const {
        return std::memcmp(command_code, code, CommandLength) == 0;
    }
};

    } // namespace Commands
} // namespace STM_CppLib

#endif /*   COMMAND_DESCRIPTION_HPP   */