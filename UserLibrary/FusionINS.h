#ifndef _FUSION_INS_TASK_H_
#define _FUSION_INS_TASK_H_

/**
 * @attention   采用UTF-8字符集编码
 */

#include "stdint.h"

typedef struct
{
    struct
    {
        struct
        {
            float FB;
            float LR;
        } Speed;
    } Robot;    //机器人坐标系

    struct
    {
        struct
        {
            float X;
            float Y;
        } Speed;
        struct
        {
            float X;
            float Y;
        } Position;
    } World;    //世界坐标系 取X轴为Yaw=0时朝向的轴
} FusionINS_t;

extern FusionINS_t FusionINS;

#endif
