/**
 * @file    MicroTimer.hpp
 * @author  Романовский Роман
 * @brief   Класс микросекундного таймера на базе TIM7.
 * @details Предоставляет функциональность точных микросекундных задержек
 *          с использованием аппаратного таймера TIM7. Реализован как синглтон,
 *          что гарантирует единственный экземпляр для всей программы.
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef MICRO_TIMER_HPP
#define MICRO_TIMER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "BasicTimers.hpp"
#include "GPTimers.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace STM_Timer{

        /**
         * @brief   Класс микросекундного таймера на базе TIM7.
         * @details Обеспечивает задержки с точностью до микросекунды.
         */
        class MicroTimer{
        private:
            
            /**
             * @brief   Счётчик микросекунд, изменяемый в прерывании.
             */
            inline static volatile uint32_t microTimingDelay = 0;
            
            /**
             * @brief   Статический декремент счётчика, вызываемый из прерывания таймера.
             */
            static void microTimingDelay_Decrement(){
                if (microTimingDelay != 0x00){  microTimingDelay--; }
            } 

            Timer2<microTimingDelay_Decrement> micro_timer;   ///< Объект аппаратного таймера TIM7

            
        public:
            /**
             * @brief   Конструктор по умолчанию.
             */
            MicroTimer() = default;

            /**
             * @brief   Деструктор по умолчанию.
             */
            ~MicroTimer() = default;

            /// Запретим копирования
            MicroTimer(const MicroTimer&) = delete;

            /// Запрет присваивания
            MicroTimer& operator=(const MicroTimer&) = delete;

            /**
             * @brief   Инициализация микросекундного таймера.
             */
            void Init(){
                uint32_t micro_timer_period = 2 - 1;
                micro_timer.Init(micro_timer_period, Prescaler_2MHz);
            }
            
            /**
             * @brief   Формирование задержки на заданное число микросекунд.
             * @param   delay_tick   Количество микросекунд (тиков).
             * @details Устанавливает microTimingDelay, запускает таймер и ожидает
             *          обнуления счётчика. После завершения останавливает таймер.
             * @note    Блокирует выполнение программы до окончания задержки.
             */
            void Delay(uint32_t delay_tick){
                microTimingDelay = delay_tick;

                // Запустим микросекундный таймер
                Start();

                // Дождёмся окончания задержки по времени
                while (microTimingDelay != 0){}

                // Выключим таймер для освобождения аппаратных ресурсов
                Stop();
            }

        private:
            /**
             * @brief   Запуск микросекундного таймера.
             * @details Сбрасывает счётчик таймера и включает его работу.
             */
            void Start(){
                micro_timer.ResetCounter();
                micro_timer.Start();
            }

            /**
             * @brief   Остановка микросекундного таймера.
             */
            void Stop(){
                micro_timer.Stop();
            }
        };

        // inline MicroTimer micro_timer;

    } // namespace STM_Timer
} // namespace STM_CppLib

#endif /*   MICRO_TIMER_HPP   */