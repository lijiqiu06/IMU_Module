#include "SPICommTask.h"
#include "FreeRTOS.h"
#include "task.h"
#include <string.h>

#define SPI_SOF_MASTER 0xA5
#define SPI_SOF_SLAVE 0x5A
#define SPI_RESET_UNLOCK 0x5A
#define SPI_DMA_WAIT_TICK 50

extern uint8_t cail_OK;

static uint8_t current_mode = SPI_COMM_MODE_STATUS;
static uint8_t last_crc_error = 0;
static uint8_t last_unknown_mode = 0;
static uint8_t reset_pending = 0;
static TaskHandle_t spi_comm_task_handle = NULL;
static volatile uint8_t spi_dma_done = 0;
static volatile uint8_t spi_dma_error = 0;

volatile uint8_t spi2_debug_rx0;
volatile uint8_t spi2_debug_rx1;
volatile uint8_t spi2_debug_rx2;
volatile uint8_t spi2_debug_rx3;

static void put_bytes(uint8_t *buf, uint8_t *idx, const void *src, uint8_t len)
{
    memcpy(&buf[*idx], src, len);
    *idx += len;
}

static void put_u32(uint8_t *buf, uint8_t *idx, uint32_t v)
{
    put_bytes(buf, idx, &v, 4);
}

static void put_f32(uint8_t *buf, uint8_t *idx, float v)
{
    put_bytes(buf, idx, &v, 4);
}

static uint8_t spi_pack_payload(uint8_t mode, uint8_t *payload)
{
    uint8_t idx = 0;
    uint8_t i;
    uint32_t timestamp;
    Inertial_t snap;
    IMU_Data_t imu = {0};

    timestamp = HAL_GetTick();

    taskENTER_CRITICAL();
    snap = Inertial;
    if (Inertial.IMU != NULL)
    {
        imu = *Inertial.IMU;
    }
    taskEXIT_CRITICAL();

    put_u32(payload, &idx, timestamp);

    switch (mode)
    {
    case SPI_COMM_MODE_STATUS:
        put_f32(payload, &idx, imu.Temperature);
        break;

    case SPI_COMM_MODE_EULER:
        put_f32(payload, &idx, snap.Roll);
        put_f32(payload, &idx, snap.Pitch);
        put_f32(payload, &idx, snap.Yaw);
        put_f32(payload, &idx, snap.YawTotalAngle);
        break;

    case SPI_COMM_MODE_QUAT:
        for (i = 0; i < 4; i++)
        {
            put_f32(payload, &idx, snap.Q[i]);
        }
        break;

    case SPI_COMM_MODE_MOTION:
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, snap.Accel[i]);
        }
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, snap.Gyro[i]);
        }
        break;

    case SPI_COMM_MODE_IMU_RAW:
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, imu.Accel[i]);
        }
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, imu.Gyro[i]);
        }
        put_f32(payload, &idx, imu.Temperature);
        break;

    case SPI_COMM_MODE_ALL:
        put_f32(payload, &idx, snap.Roll);
        put_f32(payload, &idx, snap.Pitch);
        put_f32(payload, &idx, snap.Yaw);
        put_f32(payload, &idx, snap.YawTotalAngle);
        for (i = 0; i < 4; i++)
        {
            put_f32(payload, &idx, snap.Q[i]);
        }
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, snap.Accel[i]);
        }
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, snap.Gyro[i]);
        }
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, imu.Accel[i]);
        }
        for (i = 0; i < 3; i++)
        {
            put_f32(payload, &idx, imu.Gyro[i]);
        }
        put_f32(payload, &idx, imu.Temperature);
        break;

    default:
        break;
    }

    return idx;
}

static void spi_build_frame(uint8_t *tx, uint8_t mode, uint8_t seq)
{
    uint8_t payload_len;

    memset(tx, 0, SPI_COMM_FRAME_LEN);
    tx[0] = SPI_SOF_SLAVE;
    tx[1] = mode;
    tx[2] = seq;
    tx[3] = (cail_OK ? 0x01 : 0x00) |
            (last_crc_error ? 0x02 : 0x00) |
            (last_unknown_mode ? 0x04 : 0x00) |
            (reset_pending ? 0x08 : 0x00);

    payload_len = spi_pack_payload(mode, &tx[5]);
    tx[4] = payload_len;
    CRC16_AppendChecksum(tx, SPI_COMM_FRAME_LEN);
}

static uint8_t spi_mode_valid(uint8_t mode)
{
    return mode <= SPI_COMM_MODE_ALL;
}

void SPICommTask(void const *argument)
{
    uint8_t tx[SPI_COMM_FRAME_LEN];
    uint8_t rx[SPI_COMM_FRAME_LEN];
    uint8_t seq = 0;

    (void)argument;

    spi_comm_task_handle = xTaskGetCurrentTaskHandle();

    while (1)
    {
        spi_build_frame(tx, current_mode, seq);
        spi_dma_done = 0;
        spi_dma_error = 0;

        if (HAL_SPI_TransmitReceive_DMA(&hspi2, tx, rx, SPI_COMM_FRAME_LEN) == HAL_OK)
        {
            spi2_debug_rx0 = rx[0];
            spi2_debug_rx1 = rx[1];
            spi2_debug_rx2 = rx[2];
            spi2_debug_rx3 = rx[3];
            if (ulTaskNotifyTake(pdTRUE, SPI_DMA_WAIT_TICK) > 0 && spi_dma_done && !spi_dma_error)
            {
                seq++;

                last_crc_error = !CRC16_VerifyChecksum(rx, SPI_COMM_FRAME_LEN);
                last_unknown_mode = 0;

                if (!last_crc_error && rx[0] == SPI_SOF_MASTER)
                {
                    if (rx[1] == SPI_COMM_CMD_RESET && rx[3] == SPI_RESET_UNLOCK)
                    {
                        reset_pending = 1;
                        osDelay(20);
                        NVIC_SystemReset();
                    }
                    else if (spi_mode_valid(rx[1]))
                    {
                        current_mode = rx[1];
                    }
                    else
                    {
                        last_unknown_mode = 1;
                    }
                }
            }
            else
            {
                HAL_SPI_DMAStop(&hspi2);
                HAL_SPI_Abort(&hspi2);
                __HAL_SPI_CLEAR_OVRFLAG(&hspi2);
            }
        }
        else
        {
            HAL_SPI_Abort(&hspi2);
            __HAL_SPI_CLEAR_OVRFLAG(&hspi2);
        }

        // osDelay(1);
    }
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi)
{
    BaseType_t higher_priority_task_woken = pdFALSE;

    if (hspi->Instance == SPI2 && spi_comm_task_handle != NULL)
    {
        spi_dma_done = 1;
        vTaskNotifyGiveFromISR(spi_comm_task_handle, &higher_priority_task_woken);
        portYIELD_FROM_ISR(higher_priority_task_woken);
    }
}

void HAL_SPI_ErrorCallback(SPI_HandleTypeDef *hspi)
{
    BaseType_t higher_priority_task_woken = pdFALSE;

    if (hspi->Instance == SPI2 && spi_comm_task_handle != NULL)
    {
        spi_dma_error = 1;
        vTaskNotifyGiveFromISR(spi_comm_task_handle, &higher_priority_task_woken);
        portYIELD_FROM_ISR(higher_priority_task_woken);
    }
}
