//系统
#include "stm32f4xx_hal.h"
#include "stdint.h"
#include "math.h"
#include "cmsis_os.h"
#include "arm_math.h"

//宏
#include "RobotConfig.h"
#ifndef PI
#define PI 3.14159265358979f
#endif
#ifndef SQRT2
#define SQRT2 1.414213562373095f
#endif
#ifndef SQRT3
#define SQRT3 1.732050807568877f
#endif
#ifndef FLOAT_MAX_VAL
#define FLOAT_MAX_VAL 3.4028234663852886e+38
#endif

#define IMU_CALI_DATA_FLASH_ADDR (0x08010000)    //F401 128K Flash空间中的最后一页
#define IMU_CALI_TIMESTAMP 2607312017u  //将此数改为另一个值即可触发一次陀螺仪校准 此处可以将其设置为时间戳 注意该值要满足32位宽度
#define IMU_HEATER_TEMP_SET 50  //摄氏度 会优先使用从Flash中读取到的数值 仅修改此处无效 该值在校准后被写入Flash

//外部硬件

#include "BMI088driver.h"


//外设
#include "usart.h"
#include "tim.h"
#include "spi.h"

//软件
#include "stdint.h"
#include "Universal.h"
#include "UniversalPID.h"
#include "UniversalFilter.h"
#include "UniversalCRC.h"
#include "QuaternionEKF.h"
#include "FusionINS.h"
#include "KalmanFilterInertial.h"

//任务
#include "InertialTask.h"
#include "SPICommTask.h"

