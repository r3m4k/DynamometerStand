/* Includes H files ----------------------------------------------------------*/
#include "main.h"

/* Includes HPP files --------------------------------------------------------*/
#include <array>
#include <variant>

#include "Consts.hpp"
#include "GPTimers.hpp"
#include "Leds.hpp"
#include "GpioPin.hpp"
#include "HX711.hpp"
#include "HX711Package.hpp"
#include "UsbPort.hpp"
#include "Usart.hpp"
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

/* Defines -------------------------------------------------------------------*/
#define ENABLE_COMMAND_PROCESSING   1   // Дефайн для включения обработки поступивших
                                        // команд (0 - выкл / 1 - вкл)
#define IST_VECTORS_NUM     98          // Количество векторов прерываний
#define MessageLen          8           // Длина отправляемых информационных сообщений

/* Typedefs ------------------------------------------------------------------*/
typedef void (* const pHandler)(void);

/* Global variables ---------------------------------------------------------*/
extern pHandler __isr_vectors[];

/* ****************************************************************************
 * Пользовательские переменные
 *************************************************************************** */

// Собственная таблица прерываний
__attribute__((aligned(128)))    // Cortex-M4 требует выравнивание по 128 байт!
_user_pHandler _user_vector_table[IST_VECTORS_NUM] = {0};

// Необходимые счётчики и флаги
uint32_t tick_counter = 0;
volatile bool hx711_reading_flag = false;

// Светодиоды на плате
STM_CppLib::Leds leds;

#if ENABLE_COMMAND_PROCESSING
// Обработчик поступивших команд
STM_CppLib::Commands::CommandManager command_manager;
#endif  /* ENABLE_COMMAND_PROCESSING */

// Интерфейс связи
STM_CppLib::UsbPort::UsbPort com_port;
// STM_CppLib::USARTx com_port;

// Используемые таймеры -------------------------------------------------------

// Микросекундный таймер на базе Timer2
STM_CppLib::STM_Timer::MicroTimer micro_timer;

// Таймер для чтения АЦП с частотой 10 Гц
STM_CppLib::STM_Timer::Timer3<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED9);

    tick_counter++;
    hx711_reading_flag = true;

}>  timer3;

// Таймер для мерцания светодиодами LED6, LED7
STM_CppLib::STM_Timer::Timer4<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED6);
    leds.ChangeLedStatus(LED7);
}>  timer4;


/* ***********************************************************************
* Конфигурация пинов для использования нескольких АЦП HX711:
*       HX711_1     HX711_2
* DT:   PC2         PA0
* SCK:  PC3         PA3
*********************************************************************** */

// HX711_1 ---------------------------------------------------------------
using PinDT1_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortC, GPIO_PinSource2>;

using PinSCK1_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortC, GPIO_PinSource3>;

using HX711_1_t = HX711::HX711<PinDT1_t, PinSCK1_t>;

// HX711_2 ---------------------------------------------------------------
using PinDT2_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortA, GPIO_PinSource0>;

using PinSCK2_t = STM_CppLib::STM_GPIO::GPIO_Pin
    <STM_CppLib::STM_GPIO::GPIO_Port::PortA, GPIO_PinSource3>;

using HX711_2_t = HX711::HX711<PinDT2_t, PinSCK2_t>;

// HX711_array -----------------------------------------------------------
// Variant, который хранит типы HX711
using HX711Variant = std::variant<HX711_1_t, HX711_2_t>;
constexpr std::size_t HX711num = std::variant_size<HX711Variant>::value;

std::array<HX711Variant, HX711num> hx711_array = {
    HX711_1_t(HX711::HX711Gain::Gain128_A, HX711::enableAutoGainControl),
    HX711_2_t(HX711::HX711Gain::Gain128_A, HX711::enableAutoGainControl),
};

// HX711Packages_array ---------------------------------------------------
std::array<Packages::HX711Package, HX711num> hx711_package_array = {
    Packages::HX711Package(1, &(std::get_if<0>(&hx711_array[0])->adc_value), &(std::get_if<0>(&hx711_array[0])->gain)),
    Packages::HX711Package(2, &(std::get_if<1>(&hx711_array[1])->adc_value), &(std::get_if<1>(&hx711_array[1])->gain)),
};

/* ****************************************************************************
 * Описание стадий программы
 *************************************************************************** */

class ProgramStage{
    CommandHandlerFunc init_func;
    CommandHandlerFunc execute_func;
    
public:
    bool is_init = false;

    ProgramStage(CommandHandlerFunc _init_func, CommandHandlerFunc _execute_func):
        init_func(_init_func), execute_func(_execute_func) {}

    void init(){
        init_func();
        is_init = true;
    }

    void execute(){
        execute_func();
    }
};

// Очередь стадий программ (используется для смены стадий программ)
StaticQueue<ProgramStage*, 2> program_stage_queue;

// Поддерживаемые стадии программы
ProgramStage FooStage(FooStage_init, FooStage_execute);
ProgramStage MeasureStage(MeasureStage_init, MeasureStage_execute);

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

    program_stage_queue.put(&FooStage);
    ProgramStage* current_stage_ptr = nullptr;

    // ---------------------------------------------------------------------------
    // Основной цикл программы
    while (true)
    {
       
    #if ENABLE_COMMAND_PROCESSING
        // Выполним поступившую команду при её наличии
        if (!command_manager.command_queue.is_empty()){
            auto command = command_manager.command_queue.get();
            command.execute();
        }
    #endif

        // Сменим current_stage_ptr, если есть элементы в очереди program_stage_queue
        if(!program_stage_queue.is_empty()){
            current_stage_ptr = program_stage_queue.get();
        }

        // Если current_stage_ptr == nullptr, то остановим итерацию цикла 
        if (!current_stage_ptr){
            continue;
        }

        /* ***********************************************************************
        ШАБЛОН ОТРАБОТКИ СТАДИИ ПРОГРАММЫ:
        Каждая стадия (ProgramStage) отрабатывается по единому принципу:
        1. ИНИЦИАЛИЗАЦИЯ СТАДИИ (однократное выполнение при входе в стадию)
        2. ЦИКЛИЧЕСКОЕ ВЫПОЛНЕНИЕ ОСНОВНОЙ ЛОГИКИ СТАДИИ
        *********************************************************************** */

        if (!current_stage_ptr->is_init){
            current_stage_ptr->init();
        }
        current_stage_ptr->execute();        
    }
}

// -------------------------------------------------------------------------------
// Инициализация оборудования
// -------------------------------------------------------------------------------
void InitAll(){
    // Настройка периферии -------------------------------------------------------
    leds.Init();
    leds.LedsOn();
    
    com_port.Init();
    init_all_hx711();

    // Настройка таймеров --------------------------------------------------------
    micro_timer.Init();
    
    // Настройка основного таймера с периодом счёта в 100 мс (10 Гц)
    uint32_t tim3_period = 1000 - 1;
    timer3.Init(tim3_period, Prescaler_10kHz, nullptr, 2, 0);

    // Настройка таймера для мерцания светодиодами с периодом счёта в 2 с
    uint32_t tim4_period = 20000 - 1;
    timer4.Init(tim4_period);
}

// -------------------------------------------------------------------------------
// Функции для отработки стадий программы
// -------------------------------------------------------------------------------

// Функция для инициализации FooStage
void FooStage_init(){
    // Остановим все таймеры
    timer3.Stop();
    timer3.ResetCounter();
    timer4.Stop();
    timer4.ResetCounter();
    
    // Включим все светодиоды
    leds.LedsOn();
}

// Функция для исполнения FooStage 
void FooStage_execute(){
    __NOP();
}

// Функция для инициализации MeasureStage
void MeasureStage_init(){
    tick_counter = 0;
    leds.LedsOff();

    // Запустим таймер сбора данных
    timer3.ResetCounter();
    timer3.Start();

    // Запустим таймер индикации работы
    timer4.ResetCounter();
    timer4.Start();
}

// Функция для исполнения MeasureStage 
void MeasureStage_execute(){
    if (hx711_reading_flag){
        // Переключим светодиод для индикации работы
        leds.ChangeLedStatus(LED8);

        // Считаем значения АЦП и отправим пакеты данных
        read_all_hx711();
        send_all_hx711_packages();

        // Сбросим флаг
        hx711_reading_flag = false;
    }
}


// -------------------------------------------------------------------------------
// Функции для работы со всеми подключёнными АЦП HX711
// -------------------------------------------------------------------------------

// Инициализация всех подключённых АЦП HX711
void init_all_hx711(){
    for(auto& hx711_variant : hx711_array){
        std::visit([](auto& hx711){
                hx711.init();
            }, hx711_variant);
    }
}

// Чтение всех подключённых АЦП HX711
void read_all_hx711(){
    for(auto& hx711_variant : hx711_array){
        std::visit([](auto& hx711){
                hx711.read_adc_val();
            }, hx711_variant);
    }
}

// Отправка пакетов данных о всех подключённых АЦП HX711
void send_all_hx711_packages(){
    for (auto& package : hx711_package_array){
        // Обновим данные в пакете
        package.UpdateTime(tick_counter);
        package.UpdateData();
        package.UpdateControlSum();

        // Отправим пакет по com порту
        com_port.SendPackage(package);
    }
}


// -------------------------------------------------------------------------------
// Функции для отработки поступивших команд
// -------------------------------------------------------------------------------

void UserEP3_OUT_Callback(uint8_t *buffer){
#if ENABLE_COMMAND_PROCESSING
    STM_CppLib::Message message(buffer);
    com_port.EP3_OUT_Callback(message);
#endif  /* ENABLE_COMMAND_PROCESSING */
}

void USART1_IRQHandler(void)
{
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET) // было прерывание от приемника
        __NOP();

    if (USART_GetITStatus(USART1, USART_IT_TXE) != RESET){ // было прерывание от передатчика
        while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET){} // дожидаюсь завершения выдачи текущего байта и отключаю прерывания от выдачи
        USART_ITConfig(USART1, USART_IT_TXE, DISABLE);
    }
    USART_ClearITPendingBit(USART1, USART_IT_ORE);
}

// Функции для перезагрузки МК
void restart(){
    NVIC_SystemReset();
}

// Функция для добавления FooStage в очередь program_stage_queue
void set_FooStage(){
    program_stage_queue.put(&FooStage);
}

// Функция для добавления MeasureStage в очередь program_stage_queue
void set_MeasureStage(){
    program_stage_queue.put(&MeasureStage);
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
