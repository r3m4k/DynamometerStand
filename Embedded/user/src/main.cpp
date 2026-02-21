/* Includes H files ----------------------------------------------------------*/
#include "main.h"

/* Includes HPP files --------------------------------------------------------*/
#include "Consts.hpp"
#include "GPTimers.hpp"
#include "Leds.hpp"
#include "GpioPin.hpp"
#include "HX711.hpp"
#include "HX711Package.hpp"
#include "ComPort.hpp"
#include "Message.hpp"
#include "CommandProcessing.hpp"

// ----------------------------------------------------------------------------
//
// Standalone STM32F3 empty sample (trace via NONE).
//
// Trace support is enabled by adding the TRACE macro definition.
// By default the trace messages are forwarded to the NONE output,
// but can be rerouted to any device or completely suppressed, by
// changing the definitions required in system/src/diag/trace_impl.c
// (currently OS_USE_TRACE_ITM, OS_USE_TRACE_SEMIHOSTING_DEBUG/_STDOUT).
//

/* #global variables -----------------------------------------*/
RCC_ClocksTypeDef RCC_Clocks; // structure used for setting up the SysTick Interrupt

// Unused global variables that have to be included to ensure correct compiling
// ###### DO NOT CHANGE ######
// ===============================================================================
__IO uint32_t TimingDelay = 0;                     // used with the Delay function
__IO uint8_t DataReady = 0;
__IO uint32_t USBConnectTimeOut = 100;
__IO uint32_t UserButtonPressed = 0;
__IO uint8_t PrevXferComplete = 1;
__IO uint8_t buttonState;
// ===============================================================================


/* Global variables ---------------------------------------------------------*/
typedef void
(* const pHandler)(void);

extern pHandler __isr_vectors[];

// ----------------------------------------------------------------------------
#define IST_VECTORS_NUM     98      // Количество векторов прерываний

// Собственная таблица прерываний
__attribute__((aligned(128)))    // Cortex-M4 требует выравнивание по 128 байт!
_user_pHandler _user_vector_table[IST_VECTORS_NUM] = {0};

// ----------------------------------------------------------------------------

volatile uint32_t microTimingDelay = 0;


// Стадии программы
enum class ProgramStages{InfiniteSending};

STM_CppLib::STM_GPIO::GPIO_Pin_EXTI
    <STM_CppLib::STM_GPIO::GPIO_Port::PortC, GPIO_PinSource1, update_package_data> Pin_PC1;

// ----------------------------------------------------------------------------

// Периферия
STM_CppLib::Leds leds;                   // Светодиоды на плате

// Обработчик поступивших команд
STM_CppLib::Commands::CommandManager command_manager;

// Интерфейсы связи
STM_CppLib::ComPort::ComPort com_port;

// Используемые таймеры
STM_CppLib::STM_Timer::Timer2<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    microTimingDelay_Decrement();
}>  timer2;     // Таймер для реализации микросекундных задержек

STM_CppLib::STM_Timer::Timer3<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED9);
    read_all_hx711();    
}>  timer3;     // Таймер для чтения АЦП с частотой 10 Гц

STM_CppLib::STM_Timer::Timer4<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED6);
    leds.ChangeLedStatus(LED7);
}>  timer4;     // Таймер для мерцания светодиодами LED6, LED7


/* ***********************************************************************
* Укажем конфигурацию пинов для использования АЦП HX711:
*       HX711_1     HX711_2     HX711_3
* DT:   PC2         PA0         PA4
* SCK:  PC3         PA3         PA5
*********************************************************************** */

// HX711_1 ---------------------------------------------------------------
using PinDT1_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortC, GPIO_PinSource2>;

using PinSCK1_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortC, GPIO_PinSource3>;

// HX711_2 ---------------------------------------------------------------
using PinDT2_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortA, GPIO_PinSource0>;

using PinSCK2_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortA, GPIO_PinSource3>;

// HX711_3 ---------------------------------------------------------------
using PinDT3_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortA, GPIO_PinSource4>;

using PinSCK3_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortA, GPIO_PinSource5>;

// -------------------------------------------------------------------------------


int main()
{
    /* ***************************************************************************
    * Загрузим собственную таблицу прерываний для возможности её модификации
    *************************************************************************** */

    __disable_irq();    // Отключим прерывания

    // Скопируем исходную таблицу прерываний
    memcpy(_user_vector_table, __isr_vectors, IST_VECTORS_NUM * sizeof(pHandler));

    SCB->VTOR = (uint32_t)_user_vector_table;

    __DSB();    // Ожидаем завершения записи в регистр VTOR
    __ISB();    // Сбрасываем конвейер команд, чтобы следующие инструкции и прерывания
                // использовали новую таблицу векторов

    __enable_irq();     // Включим прерывания

    // ---------------------------------------------------------------------------

    // Получаем текущие значения тактовых частот системы и настроим
    // SysTick для генерации прерываний с периодом 1 мс
    // Если конфигурация SysTick завершилась ошибкой – входим в бесконечный цикл
	RCC_GetClocksFreq(&RCC_Clocks);
	if (SysTick_Config(RCC_Clocks.HCLK_Frequency / 1000))
		while(true) {}
    
    // ---------------------------------------------------------------------------

    // Инициализируем всё оборудования
    InitAll();             
    
    // Поморгаем светодиодами после успешной инициализации
    leds.ToggleLeds();

    // ---------------------------------------------------------------------------

   

    // ---------------------------------------------------------------------------
    // Основной цикл программы
    while (true)
    {
        /* ***********************************************************************
        * Место для дальнейшего размещения кода проверки 
        * очереди поступивших команд и её отработки.
        *********************************************************************** */
       
        // if (!command_manager.command_queue.is_empty()){
        //     auto command = command_manager.command_queue.get();
        //     command.execute();
        // }

        switch (stage)
        {
        case ProgramStages::InfiniteSending:
            // Вызов "пустой" функции для ограничения оптимизации компилятора
            __NOP();    

            break;
        }
    }
}

// -------------------------------------------------------------------------------
// Инициализация оборудования
// -------------------------------------------------------------------------------
void InitAll(){
    micro_timer_init();

    leds.Init();
    leds.LedsOn();
    
    com_port.Init();

    // Настройка основного таймера с периодом счёта в 100 мс (10 Гц)
    uint32_t tim3_period = 1000 - 1;
    timer3.Init(tim3_period);

    // Настройка таймера для мерцания светодиодами с периодом счёта в 2 с
    uint32_t tim4_period = 20000 - 1;
    timer4.Init(tim4_period);
}

// -------------------------------------------------------------------------------
// Функции для чтения всех подключённых АЦП
// -------------------------------------------------------------------------------
void read_all_hx711(){

}

// -------------------------------------------------------------------------------
// Функции для отработки поступивших команд
// -------------------------------------------------------------------------------

void UserEP3_OUT_Callback(uint8_t *buffer){
    STM_CppLib::Message message(buffer);
    com_port.EP3_OUT_Callback(message);
}

// Функции для обработки поступивших команд
void restart(){
    NVIC_SystemReset();
}


// -------------------------------------------------------------------------------
// Отправка предопределённых сообщений
// -------------------------------------------------------------------------------

void send_confirm_msg(){
    constexpr uint8_t ConfirmMessage[MessageLen] = {0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0};
    STM_CppLib::Message message(ConfirmMessage, MessageLen);
    com_port.SendMessage(message);   // В таком случае передаём lvalue ссылку
}

void send_hello_msg(){
    const char* text = "Dynamometer by Romanovskiy Roma\n";
    STM_CppLib::Message message(reinterpret_cast<const uint8_t*>(text), strlen(text));
    com_port.SendMessage(message);
}

void send_error_msg(){
    constexpr uint8_t ErrorMessage[MessageLen] = {0x7e, 0xe7, 0xff, 0xff, 0xff, 0x62, 0};
    STM_CppLib::Message message(ErrorMessage, MessageLen);
    com_port.SendMessage(message);
}

// -------------------------------------------------------------------------------
// Функции для работы с микросекундным таймером 
// -------------------------------------------------------------------------------

// Инициализация микросекундного таймера
void micro_timer_init(void){
    // Настройка таймера для реализации микросекундных задержек
    uint32_t tim2_period = 1;
    timer2.Init(tim2_period, Prescaler_1MHz);
}

// Запуск микросекундного таймера
void micro_timer_start(void){
    timer2.ResetCounter();
    timer2.Start();
}

// Остановка микросекундного таймера
void micro_timer_stop(void){
    timer2.Stop();
}

void microDelay(uint32_t nTime){
    microTimingDelay = nTime;
    while (microTimingDelay != 0){}
}

void microTimingDelay_Decrement(void){
    if (microTimingDelay != 0x00){  microTimingDelay--; }
}

// -------------------------------------------------------------------------------
// Системные функции
// -------------------------------------------------------------------------------

void Error_Handler(void)
{
    /* Turn LED10/3 (RED) on */
    STM_EVAL_LEDOn(LED10);
    STM_EVAL_LEDOn(LED3);
    while (1)
    {
    }
}


// Function to insert a timing delay of nTime
// ###### DO NOT CHANGE ######
void Delay(__IO uint32_t nTime)
{
    TimingDelay = nTime;

    while (TimingDelay != 0){}
    // for (int i = 0; i < 1000000; i++){}
}

// Function to Decrement the TimingDelay variable.
// ###### DO NOT CHANGE ######
void TimingDelay_Decrement(void)
{
    if (TimingDelay != 0x00)
    {
        TimingDelay--;
    }
}

// Unused functions that have to be included to ensure correct compiling
// ###### DO NOT CHANGE ######
// =======================================================================
uint32_t L3GD20_TIMEOUT_UserCallback(void)
{
    return 0;
}

uint32_t LSM303DLHC_TIMEOUT_UserCallback(void)
{
    return 0;
}
// =======================================================================
