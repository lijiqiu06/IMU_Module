/**
 * @attention   采用UTF-8字符集编码
 * @brief       通用函数库
 * @authors     北工大PIP战队 樊郡捷
 * @version     v1.1
 * @date        2025-02-27
 * @details
 */

#include "header.h"

int Constrain(int val, int max, int min)
{
    return val > max ? max : val < min ? min : val;
}

float ConstrainF(float val, float max, float min)
{
    return val > max ? max : val < min ? min : val;
}

/// @brief 相位卷绕
/// @param val 角度值
/// @param max 一圈对应的值
/// @return 卷绕后的角度值 例:AngleWrap(361, 360)=>1
int AngleWrap(int val, int max)
{
    return val > max ? val % max : (val < 0 ? val % max + max : val);
}

/// @brief 相位卷绕
/// @param val 角度值
/// @param max 一圈对应的值
/// @return 卷绕后的角度值 例:AngleWrap(361, 360)=>1
float AngleWrapF(float val, float max)
{
    return val > max ? fmodf(val, max) : (val < 0 ? fmodf(val, max) + max : val);
}

/// @brief 计算两角之间的角度差a-b 返回劣弧
/// @param a    被减数
/// @param b    减数
/// @param max  一圈对应的值
/// @return a-b 劣弧
int AngleDiff(int a, int b, int max)
{
    int err = AngleWrap(a, max) - AngleWrap(b, max);
    int halfMax = max / 2;
    if (err > halfMax)
        err -= max;
    else if (err < -halfMax)
        err += max;
    return err;
}

/// @brief 计算两角之间的角度差a-b 返回劣弧
/// @param a    被减数
/// @param b    减数
/// @param max  一圈对应的值
/// @return a-b 劣弧
float AngleDiffF(float a, float b, float max)
{
    float err = AngleWrapF(a, max) - AngleWrapF(b, max);
    float halfMax = max / 2;
    if (err > halfMax)
        err -= max;
    else if (err < -halfMax)
        err += max;
    return err;
}

/// @brief 生成汉宁窗
/// @param out  输出
/// @param n    长度
void HanningWindow_Init(float* out, int n)
{
    for (int i = 0; i < n; i++)
        out[i] = 0.5f - 0.5f * arm_cos_f32(2 * PI * i / (n - 1));
}

void AngleUnwrap_Init(AngleUnwrap_t* angleUnwrap, float value, float circle)
{
    angleUnwrap->Value = value;
    angleUnwrap->Unwraped = value;
    angleUnwrap->PrevVal = value;
    angleUnwrap->Circle = circle;
}

float AngleUnwrap_Update(AngleUnwrap_t* angleUnwrap, float value)
{
    angleUnwrap->Value = value;
    float DeltaAngle = angleUnwrap->Value - angleUnwrap->PrevVal;
    angleUnwrap->PrevVal = value;

    //过零点时计算劣弧
    float HalfCircle = angleUnwrap->Circle / 2;
    if (DeltaAngle > HalfCircle)
        DeltaAngle -= angleUnwrap->Circle;
    else if (DeltaAngle < -HalfCircle)
        DeltaAngle += angleUnwrap->Circle;

    angleUnwrap->Unwraped += DeltaAngle;

    return angleUnwrap->Unwraped;
}

/// @brief 浮点数转换成整数
/// @param val 浮点数
/// @param val 浮点数范围
/// @param val 正数范围
int32_t Float2Int32(float val, float float_range, int32_t int_range)
{
    if (val > float_range)
        val = float_range;
    else if (val < -float_range)
        val = -float_range;
    return (int32_t)(val / float_range * int_range);
} 

/// @brief 整数转换成浮点数
/// @param val 整数数
/// @param val 整数范围
/// @param val 浮点数范围
float Int32ToFloat(int32_t val, int32_t int_range, float float_range)
{
    if (val > int_range)
        val = int_range;
    else if (val < -int_range)
        val = -int_range;
    return ((float)val / (float)int_range) * float_range;
}


void Ramp(int16_t input, int16_t* rev, int16_t step)
{
    if (input - *rev > 0)
    {
        if (input - *rev > step)
            *rev += step;
        else
            *rev = input;
    }
    else if (input - *rev < 0)
    {
        if (*rev - input > step)
            *rev -= step;
        else
            *rev = input;
    }
}

void RampF(float input, float* rev, float step)
{
    if (input - *rev > 0)
    {
        if (input - *rev > step)
            *rev += step;
        else
            *rev = input;
    }
    else if (input - *rev < 0)
    {
        if (*rev - input > step)
            *rev -= step;
        else
            *rev = input;
    }
}

float get_distance(float x1, float y1, float x2, float y2)
{
    return sqrtf((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}

float get_max(float a, float b)
{
    return a > b ? a : b;
}

float get_min(float a, float b)
{
    return a < b ? a : b;
}
