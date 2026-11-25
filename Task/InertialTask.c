/**
 * @attention   閲囩敤UTF-8瀛楃闆嗙紪鐮?
 * @brief       鎯€у鑸换鍔?
 * @authors     鍖楀伐澶IP鎴橀槦 妯婇儭鎹?
 * @version     v1.0
 * @date        2024-10-14
 * @details     瀹炵幇浜嗛檧铻轰华娓╁害闂幆鎺у埗
 *              瀹炵幇浜嗛檧铻轰华鏍″噯
 *              瀹炵幇浜嗛檧铻轰华鏍″噯鏁版嵁鍦‵lash涓殑淇濆瓨鍜岃鍙?閫氳繃淇敼header.h涓殑鏍″噯鏃堕棿鎴虫潵瑙﹀彂鏍″噯)
 *              鐩墠鍙疄鐜颁簡EKF鎵╁睍鍗″皵鏇煎Э鎬佽В绠?鐜轰浆鐨勫紑婧?
 */

#include "header.h"

#define INERTIAL_TASK_UPDATE_TICK 2

void BodyFrameToEarthFrame(const float *vecBF, float *vecEF, float *q);
void EarthFrameToBodyFrame(const float *vecEF, float *vecBF, float *q);

typedef struct
{
    uint32_t TimeStamp;    // 校准时的时间戳
    uint32_t TempWhenCali; // 校准时的温度 4字节对齐
    union
    {
        uint32_t Raw;
        float Value;
    } GyroOffset[3];
    union
    {
        uint32_t Raw;
        float Value;
    } AccelScale; // 和9.81标准重力加速度相差的系数
} IMU_CaliData_t;

Inertial_t Inertial = {0};
uint8_t cail_OK=0;

const IMU_CaliData_t *const IMU_FlashCaliData = (void *)IMU_CALI_DATA_FLASH_ADDR;

void InertialCalibrateTask(void const *argument)
{
    float TempErrorFadingFilter = 10;
    const float FadingFactor = 0.9f;

    Inertial.IMU->TempWhenCali = IMU_HEATER_TEMP_SET; // 作为温度PID的设置值
    osDelay(4000);                                    // 先等待温度基本稳定

    while (1)
    {
        osDelay(100);

        // 计算一段时间内误差非线性累计值
        TempErrorFadingFilter *= FadingFactor;
        TempErrorFadingFilter += fabsf(Inertial.ImuHeaterPID.Error[0]) * (1 - FadingFactor);

        if (TempErrorFadingFilter < 0.1f)
            break;
    }

    while (BMI088_init(&hspi3, 1) != BMI088_NO_ERROR)
        ; // 重新初始化 并执行校准

    Inertial.IMU->TempWhenCali = IMU_HEATER_TEMP_SET; // 作为温度PID的设置值

    IMU_CaliData_t IMU_CaliData;
    IMU_CaliData.TimeStamp = IMU_CALI_TIMESTAMP;

    IMU_CaliData.TempWhenCali = IMU_HEATER_TEMP_SET;
    for (int i = 0; i < 3; i++)
        IMU_CaliData.GyroOffset[i].Value = Inertial.IMU->GyroOffset[i];
    IMU_CaliData.AccelScale.Value = Inertial.IMU->AccelScale;

    HAL_FLASH_Unlock();
    FLASH_WaitForLastOperation(1000);

    // 2. 配置擦除参数
    FLASH_EraseInitTypeDef FlashEraseInit = {0};
    uint32_t SectorError = 0;

    FlashEraseInit.TypeErase = FLASH_TYPEERASE_SECTORS;
    FlashEraseInit.Banks = FLASH_BANK_1;    // 根据手册选择 Bank
    FlashEraseInit.Sector = FLASH_SECTOR_4; // F401 128K Flash的最后一个扇区
    FlashEraseInit.NbSectors = 1;
    FlashEraseInit.VoltageRange = FLASH_VOLTAGE_RANGE_3; // 2.7~3.6V

    if (HAL_FLASHEx_Erase(&FlashEraseInit, &SectorError) != HAL_OK)
        SectorError = 1;

    FLASH_WaitForLastOperation(1000);

    uint32_t flash_buffer[8]; // 8 * 4 = 32 bytes

    flash_buffer[0] = IMU_CaliData.TimeStamp;
    flash_buffer[1] = IMU_CaliData.TempWhenCali;
    flash_buffer[2] = IMU_CaliData.GyroOffset[0].Raw;
    flash_buffer[3] = IMU_CaliData.GyroOffset[1].Raw;
    flash_buffer[4] = IMU_CaliData.GyroOffset[2].Raw;
    flash_buffer[5] = IMU_CaliData.AccelScale.Raw;
    flash_buffer[6] = 0; // 补齐
    flash_buffer[7] = 0; // 补齐

    // 写入 32 字节
    for (uint8_t i = 0; i < 8; i++)
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, IMU_CALI_DATA_FLASH_ADDR + i * 4, flash_buffer[i]);
   
    FLASH_WaitForLastOperation(1000);
    HAL_FLASH_Lock();
    FLASH_WaitForLastOperation(1000);
		cail_OK=1;
    osThreadTerminate(osThreadGetId());
}

/// @brief 初始化惯导的IMU部分 尝试从Flash中读取校准参数 若出错则重新校准并保存到Flash
/// @param
void Inertial_ImuInit(void)
{
    PID_InitStruct_t PID_InitParam = {0};
    PID_InitParam.kP = 150;
    PID_InitParam.kI = 5;
    PID_InitParam.kD = 0;
    PID_InitParam.DeltaTime = INERTIAL_TASK_UPDATE_TICK / 1000.f;
    PID_InitParam.MaxError = 50;
    PID_InitParam.MaxOutput = 2000;
    PID_InitParam.I_Max = 1600;
    PID_InitParam.DeadBand = 0;
    PID_InitParam.IntegralBand = 20;
    PID_Init(&Inertial.ImuHeaterPID, &PID_InitParam);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);

    Inertial.IMU = &BMI088;
    while (BMI088_init(&hspi3, 0) != BMI088_NO_ERROR)
        ; // 鍗充娇闇€瑕佹牎鍑?涔熼渶瑕佸厛鍒濆鍖栬姱鐗囨墠鑳借鍙栬姱鐗囨俯搴?

    if (IMU_FlashCaliData->TimeStamp == IMU_CALI_TIMESTAMP)
    {
        Inertial.IMU->TempWhenCali = Constrain(IMU_FlashCaliData->TempWhenCali, 70, 40);
        for (int i = 0; i < 3; i++)
            Inertial.IMU->GyroOffset[i] = IMU_FlashCaliData->GyroOffset[i].Value;
        Inertial.IMU->AccelScale = IMU_FlashCaliData->AccelScale.Value;

        cail_OK=1;
    }
    else
    {
        osThreadDef(InertialCalibrate, InertialCalibrateTask, osPriorityAboveNormal, 0, 128);
        osThreadCreate(osThread(InertialCalibrate), NULL);

        cail_OK=0;
    }
}

void InertialTask(void const *argument)
{
    uint32_t PreviousWakeTime = osKernelSysTick();

    const float Gravity[3] = {0, 0, 9.81f};
    const float xb[3] = {1, 0, 0};
    const float yb[3] = {0, 1, 0};
    const float zb[3] = {0, 0, 1};

    Inertial_ImuInit();

    IMU_QuaternionEKF_Init(20, 0.005f, 3500000, 0.9999, 0);
    for (int i = 0; i < 3; i++)
    {
        LPF_1stOrderIIR_Init(&Inertial.AccelLPF[i], INERTIAL_TASK_UPDATE_TICK / 1000.f, 20);
        LPF_1stOrderIIR_Init(&Inertial.GyroLPF[i], INERTIAL_TASK_UPDATE_TICK / 1000.f, 10);
        LPF_1stOrderIIR_Init(&Inertial.dGyroLPF[i], INERTIAL_TASK_UPDATE_TICK / 1000.f, 50);
    }

    while (1)
    {
        osDelayUntil(&PreviousWakeTime, INERTIAL_TASK_UPDATE_TICK);

        BMI088_Read(Inertial.IMU);

        PID_Calc(&Inertial.ImuHeaterPID, Inertial.IMU->Temperature, Inertial.IMU->TempWhenCali);
        __HAL_TIM_SetCompare(&htim2, TIM_CHANNEL_1, Constrain(Inertial.ImuHeaterPID.Output, 2000, 0));

        if (cail_OK==0) // 陀螺仪校准好之前只计算温度闭环PID
            continue;

        float DeltaTime = INERTIAL_TASK_UPDATE_TICK / 1000.f;

        Inertial.Accel[AX] = Inertial.IMU->Accel[AY];
        Inertial.Accel[AY] = -Inertial.IMU->Accel[AX];
        Inertial.Accel[AZ] = Inertial.IMU->Accel[AZ];
        Inertial.Gyro[AX] = Inertial.IMU->Gyro[AY];
        Inertial.Gyro[AY] = -Inertial.IMU->Gyro[AX];
        Inertial.Gyro[AZ] = Inertial.IMU->Gyro[AZ];

        // demo function,鐢ㄤ簬淇瀹夎璇樊,鍙互涓嶇,鏈琩emo鏆傛椂娌＄敤
        // IMU_Param_Correction(&Inertial_Param, Inertial.Gyro, Inertial.Accel);

        // 璁＄畻閲嶅姏鍔犻€熷害鐭㈤噺鍜宐绯荤殑XY涓よ酱鐨勫す瑙?鍙敤浣滃姛鑳芥墿灞?鏈琩emo鏆傛椂娌＄敤
        // Inertial.atanxz = -atan2f(Inertial.Accel[AX], Inertial.Accel[AZ]) * 180 / PI;
        // Inertial.atanyz = atan2f(Inertial.Accel[AY], Inertial.Accel[AZ]) * 180 / PI;

        // 鏍稿績鍑芥暟,EKF鏇存柊鍥涘厓鏁?
        IMU_QuaternionEKF_Update(Inertial.Gyro[AX], Inertial.Gyro[AY], Inertial.Gyro[AZ], Inertial.Accel[AX], Inertial.Accel[AY], Inertial.Accel[AZ], DeltaTime);

        memcpy(Inertial.Q, QEKF_INERTIAL.q, sizeof(QEKF_INERTIAL.q));

        // 鏈轰綋绯诲熀鍚戦噺杞崲鍒板鑸潗鏍囩郴锛屾湰渚嬮€夊彇鎯€х郴涓哄鑸郴
        BodyFrameToEarthFrame(xb, Inertial.xn, Inertial.Q);
        BodyFrameToEarthFrame(yb, Inertial.yn, Inertial.Q);
        BodyFrameToEarthFrame(zb, Inertial.zn, Inertial.Q);

        // 灏嗛噸鍔涗粠瀵艰埅鍧愭爣绯籲杞崲鍒版満浣撶郴b,闅忓悗鏍规嵁鍔犻€熷害璁℃暟鎹绠楄繍鍔ㄥ姞閫熷害
        float gravity_b[3];
        EarthFrameToBodyFrame(Gravity, gravity_b, Inertial.Q);
        for (uint8_t i = 0; i < 3; i++) // 鍚屾牱杩囦竴涓綆閫氭护娉?
        {
            LPF_1stOrderIIR_Update(&Inertial.AccelLPF[i], Inertial.Accel[i] - gravity_b[i]);
            Inertial.MotionAccel_b[i] = Inertial.AccelLPF[i].Output;
        }
        BodyFrameToEarthFrame(Inertial.MotionAccel_b, Inertial.MotionAccel_n, Inertial.Q); // 杞崲鍥炲鑸郴n

        for (int i = 0; i < 3; i++)
        {
            float GypoLpfPrev = Inertial.GyroLPF[i].Output;
            LPF_1stOrderIIR_Update(&Inertial.GyroLPF[i], Inertial.Gyro[i]);
            Inertial.dGyro[i] = (Inertial.GyroLPF[i].Output - GypoLpfPrev) / DeltaTime;
            LPF_1stOrderIIR_Update(&Inertial.dGyroLPF[i], Inertial.dGyro[i]);
        }

        // 鑾峰彇鏈€缁堟暟鎹?
        Inertial.Yaw = QEKF_INERTIAL.Yaw;
        Inertial.Pitch = QEKF_INERTIAL.Pitch;
        Inertial.Roll = QEKF_INERTIAL.Roll;
        Inertial.YawTotalAngle = QEKF_INERTIAL.YawTotalAngle;
    }
}

/**
 * @brief          Transform 3dvector from BodyFrame to EarthFrame
 * @param[1]       vector in BodyFrame
 * @param[2]       vector in EarthFrame
 * @param[3]       quaternion
 */
void BodyFrameToEarthFrame(const float *vecBF, float *vecEF, float *q)
{
    vecEF[0] = 2.0f * ((0.5f - q[2] * q[2] - q[3] * q[3]) * vecBF[0] +
                       (q[1] * q[2] - q[0] * q[3]) * vecBF[1] +
                       (q[1] * q[3] + q[0] * q[2]) * vecBF[2]);

    vecEF[1] = 2.0f * ((q[1] * q[2] + q[0] * q[3]) * vecBF[0] +
                       (0.5f - q[1] * q[1] - q[3] * q[3]) * vecBF[1] +
                       (q[2] * q[3] - q[0] * q[1]) * vecBF[2]);

    vecEF[2] = 2.0f * ((q[1] * q[3] - q[0] * q[2]) * vecBF[0] +
                       (q[2] * q[3] + q[0] * q[1]) * vecBF[1] +
                       (0.5f - q[1] * q[1] - q[2] * q[2]) * vecBF[2]);
}

/**
 * @brief          Transform 3dvector from EarthFrame to BodyFrame
 * @param[1]       vector in EarthFrame
 * @param[2]       vector in BodyFrame
 * @param[3]       quaternion
 */
void EarthFrameToBodyFrame(const float *vecEF, float *vecBF, float *q)
{
    vecBF[0] = 2.0f * ((0.5f - q[2] * q[2] - q[3] * q[3]) * vecEF[0] +
                       (q[1] * q[2] + q[0] * q[3]) * vecEF[1] +
                       (q[1] * q[3] - q[0] * q[2]) * vecEF[2]);

    vecBF[1] = 2.0f * ((q[1] * q[2] - q[0] * q[3]) * vecEF[0] +
                       (0.5f - q[1] * q[1] - q[3] * q[3]) * vecEF[1] +
                       (q[2] * q[3] + q[0] * q[1]) * vecEF[2]);

    vecBF[2] = 2.0f * ((q[1] * q[3] + q[0] * q[2]) * vecEF[0] +
                       (q[2] * q[3] - q[0] * q[1]) * vecEF[1] +
                       (0.5f - q[1] * q[1] - q[2] * q[2]) * vecEF[2]);
}
