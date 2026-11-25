#ifndef SPICOMM_TASK_H
#define SPICOMM_TASK_H

#include "header.h"

#define SPI_COMM_TASK_UPDATE_TICK 10
#define SPI_COMM_FRAME_LEN 96

#define SPI_COMM_MODE_STATUS  0x00
#define SPI_COMM_MODE_EULER   0x01
#define SPI_COMM_MODE_QUAT    0x02
#define SPI_COMM_MODE_MOTION  0x03
#define SPI_COMM_MODE_IMU_RAW 0x04
#define SPI_COMM_MODE_ALL     0x05
#define SPI_COMM_CMD_RESET    0xF0

void SPICommTask(void const *argument);

#endif
