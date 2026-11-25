# -*- coding: utf-8 -*-
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor


OUT = Path("output/pdf/spi_imu_user_manual.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont("NotoSC", r"C:\Windows\Fonts\NotoSansSC-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoSCBold", r"C:\Windows\Fonts\Dengb.ttf"))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    "CNTitle", fontName="NotoSCBold", fontSize=22, leading=29,
    alignment=TA_CENTER, textColor=HexColor("#17324d"), spaceAfter=8,
))
styles.add(ParagraphStyle(
    "CNSubTitle", fontName="NotoSC", fontSize=10.5, leading=15,
    alignment=TA_CENTER, textColor=HexColor("#53616f"), spaceAfter=16,
))
styles.add(ParagraphStyle(
    "CNH1", fontName="NotoSCBold", fontSize=15, leading=20,
    textColor=HexColor("#17324d"), spaceBefore=12, spaceAfter=8,
))
styles.add(ParagraphStyle(
    "CNH2", fontName="NotoSCBold", fontSize=12, leading=16,
    textColor=HexColor("#24445f"), spaceBefore=7, spaceAfter=5,
))
styles.add(ParagraphStyle(
    "CNBody", fontName="NotoSC", fontSize=9.2, leading=14,
    textColor=HexColor("#1f2933"), spaceAfter=5,
))
styles.add(ParagraphStyle(
    "CNNote", fontName="NotoSC", fontSize=8.5, leading=13,
    textColor=HexColor("#334155"), backColor=HexColor("#eef5fb"),
    borderColor=HexColor("#b7d5ed"), borderWidth=0.5,
    borderPadding=6, spaceBefore=4, spaceAfter=8,
))
styles.add(ParagraphStyle(
    "CNCode", fontName="NotoSC", fontSize=7.5, leading=9.6,
    textColor=HexColor("#15202b"), backColor=HexColor("#f6f8fa"),
    borderPadding=5, spaceAfter=6,
))


def para(text, style="CNBody"):
    return Paragraph(text, styles[style])


def cell(text):
    if isinstance(text, Paragraph):
        return text
    return Paragraph(str(text), styles["CNBody"])


def table(data, widths=None, font_size=8.0):
    rows = [[cell(x) for x in row] for row in data]
    tbl = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "NotoSCBold"),
        ("FONTNAME", (0, 1), (-1, -1), "NotoSC"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 3.2),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#dcebf7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#17324d")),
        ("GRID", (0, 0), (-1, -1), 0.35, HexColor("#b9c6d3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f8fbfd")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def code(text):
    return Preformatted(text.rstrip(), styles["CNCode"])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("NotoSC", 8)
    canvas.setFillColor(HexColor("#66788a"))
    canvas.drawString(18 * mm, 10 * mm, "SPI IMU 模块通信用户手册")
    canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


story = []

story += [
    para("SPI IMU 模块通信用户手册", "CNTitle"),
    para("STM32F401 从机模块 与 TC264 主机通信：当前可正常通信版本", "CNSubTitle"),
    para(
        "本文档根据当前两份工程代码整理：从机工程 "
        "E:/STM32_Proj/HAL/F401RBT6/Proj，主机工程 "
        "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl。内容覆盖硬件连接、SPI 配置、96 字节帧协议、"
        "payload 数据格式、从机 SPICommTask 代码结构、主机 fall_imu_A 驱动接口和推荐调用方式。",
    ),
    para("当前配置总览", "CNH1"),
    table([
        ["项目", "当前使用方式"],
        ["从机", "STM32F401，SPI2 硬件从机，DMA_NORMAL 双向收发，固定 96 字节帧。"],
        ["主机", "TC264，SPI0 硬件主机，当前使用 SPI_MODE2，5 MHz，固定 96 字节传输。"],
        ["读数机制", "主机连续传输两帧：第一帧下发 mode，第二帧读取该 mode 对应的数据。"],
        ["数据内容", "所有读取模式的 payload 第一项都是从机时间戳 tick，后续为姿态角、四元数、加速度、角速度、温度等数据。"],
        ["CRC", "两端均调用项目 CRC 库的 CRC16_AppendChecksum() 和 CRC16_VerifyChecksum()。"],
        ["当前状态", "两份代码的配置已经可以正常通信，本文档按当前可用配置编写。"],
    ], [36 * mm, 134 * mm]),
]

story += [
    para("1. 硬件连接与 SPI 参数", "CNH1"),
    para(
        "SPI 为全双工总线。主机负责产生 SCK 和 CS，从机在 CS 有效且收到时钟时同步收发数据。"
        "本模块每次通信必须保持 CS 覆盖完整 96 字节帧。"
    ),
    table([
        ["信号", "STM32 从机", "TC264 主机", "说明"],
        ["NSS / CS", "PB12 / SPI2_NSS", "SPI0_CS2_P20_13", "片选，低有效。"],
        ["SCK", "PB13 / SPI2_SCK", "SPI0_SCLK_P20_11", "主机输出时钟。"],
        ["MISO", "PB14 / SPI2_MISO", "SPI0_MISO_P20_12", "从机输出，主机输入。"],
        ["MOSI", "PB15 / SPI2_MOSI", "SPI0_MOSI_P20_14", "主机输出，从机输入。"],
        ["GND", "GND", "GND", "必须共地。"],
    ], [25 * mm, 43 * mm, 45 * mm, 57 * mm]),
    para("当前 SPI 参数", "CNH2"),
    table([
        ["参数", "STM32 从机 SPI2", "TC264 主机 SPI0"],
        ["工作角色", "SPI_MODE_SLAVE", "SPI 主机。"],
        ["数据线", "SPI_DIRECTION_2LINES", "全双工。"],
        ["数据宽度", "8 bit", "8 bit。"],
        ["位序", "MSB first", "MSB first。"],
        ["时钟极性", "CPOL High", "SPI_MODE2 对应 idleHigh。"],
        ["时钟相位", "CPHA 2Edge", "SPI_MODE2 对应 shiftClock trailing edge。"],
        ["片选", "硬件 NSS 输入", "硬件 CS 输出，低有效。"],
        ["速率", "由主机决定", "当前 InertialTask 中为 5 MHz。"],
    ], [40 * mm, 65 * mm, 65 * mm]),
    para(
        "注意：这里按每个芯片自身的信号方向命名，MOSI 接 MOSI，MISO 接 MISO。它不是 UART TX/RX 那种交叉命名方式。",
        "CNNote",
    ),
]

story += [
    para("2. 固定帧协议", "CNH1"),
    para(
        "协议采用固定长度 96 字节帧。SPI 从机需要在主机时钟到来前准备好 TX 缓冲，因此从机本帧返回的是上一帧已经选定的 mode 数据。"
        "主机驱动已经把这个特性封装为两帧读取。"
    ),
    para("主机发送帧", "CNH2"),
    table([
        ["字节", "字段", "含义"],
        ["0", "SOF", "0xA5，主机帧头。"],
        ["1", "mode", "请求模式：00 状态，01 姿态角，02 四元数，03 处理后运动量，04 BMI088 物理量，05 全量，F0 软件复位。"],
        ["2", "seq", "主机序号，每次构造命令帧自增。"],
        ["3", "unlock", "普通读取为 0x00；软件复位必须为 0x5A。"],
        ["4..93", "reserved", "保留，当前填 0。"],
        ["94..95", "CRC16", "小端 CRC16，由 CRC16_AppendChecksum() 写入。"],
    ], [22 * mm, 30 * mm, 118 * mm]),
    para("从机返回帧", "CNH2"),
    table([
        ["字节", "字段", "含义"],
        ["0", "SOF", "0x5A，从机帧头。"],
        ["1", "mode", "当前返回数据所属的 mode。"],
        ["2", "seq", "从机序号，每完成一次有效 DMA 帧后自增。"],
        ["3", "status", "bit0 校准完成；bit1 上一帧 CRC 标志；bit2 未知 mode 标志；bit3 即将复位标志。"],
        ["4", "payload_len", "payload 实际长度。"],
        ["5..93", "payload", "数据区，最大 89 字节。"],
        ["94..95", "CRC16", "小端 CRC16。"],
    ], [22 * mm, 30 * mm, 118 * mm]),
    para(
        "所有多字节数据都按 MCU 内存的小端顺序发送。uint32_t 占 4 字节，float 占 4 字节。"
        "主机解析时直接按 little-endian 读取即可。"
    ),
]

story += [
    para("3. Mode 与 Payload 布局", "CNH1"),
    table([
        ["mode", "payload_len", "payload 字段顺序"],
        ["0x00 STATUS", "8", "uint32 tick；float temperature。"],
        ["0x01 EULER", "20", "uint32 tick；float roll；float pitch；float yaw；float yaw_total_angle。"],
        ["0x02 QUAT", "20", "uint32 tick；float q[4]。"],
        ["0x03 MOTION", "28", "uint32 tick；float accel[3]；float gyro[3]。"],
        ["0x04 IMU_RAW", "32", "uint32 tick；float imu_accel[3]；float imu_gyro[3]；float temperature。"],
        ["0x05 ALL", "88", "uint32 tick；Euler4；Q4；Accel3；Gyro3；RawAccel3；RawGyro3；Temperature。"],
        ["0xF0 RESET", "0", "主机发送命令帧，unlock=0x5A 且 CRC 正确后，从机延时 20 ms 执行 NVIC_SystemReset()。"],
    ], [34 * mm, 26 * mm, 110 * mm]),
    para(
        "tick 来自从机 HAL_GetTick()，代表从机打包该帧时的毫秒计数。主机可用它判断数据是否在持续更新，也可把它作为主从数据对齐的时间基准。"
    ),
]

story += [
    PageBreak(),
    para("4. 从机代码概括", "CNH1"),
    para(
        "从机核心文件为 Task/SPICommTask.c、Task/SPICommTask.h、Core/Src/spi.c、Core/Src/dma.c。"
        "SPICommTask 每轮先根据 current_mode 打包 96 字节 TX 帧，再启动 HAL_SPI_TransmitReceive_DMA()，"
        "等待 DMA 完成回调通知，随后校验主机 RX 帧并切换下一轮 current_mode。"
    ),
    para("SPI2 初始化", "CNH2"),
    code("""hspi2.Instance = SPI2;
hspi2.Init.Mode = SPI_MODE_SLAVE;
hspi2.Init.Direction = SPI_DIRECTION_2LINES;
hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
hspi2.Init.CLKPolarity = SPI_POLARITY_HIGH;
hspi2.Init.CLKPhase = SPI_PHASE_2EDGE;
hspi2.Init.NSS = SPI_NSS_HARD_INPUT;
hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;"""),
    para("DMA 配置", "CNH2"),
    table([
        ["方向", "DMA", "模式", "说明"],
        ["RX", "DMA1_Stream3 Channel0", "DMA_NORMAL", "SPI2_DR 到 rx[96]。"],
        ["TX", "DMA1_Stream4 Channel0", "DMA_NORMAL", "tx[96] 到 SPI2_DR。"],
        ["NVIC", "DMA1_Stream3/4 IRQ priority 5", "中断使能", "回调中唤醒 SPICommTask。"],
    ], [30 * mm, 55 * mm, 35 * mm, 50 * mm]),
    para("SPICommTask 主流程", "CNH2"),
    code("""while (1) {
    spi_build_frame(tx, current_mode, seq);
    spi_dma_done = 0;
    spi_dma_error = 0;

    if (HAL_SPI_TransmitReceive_DMA(&hspi2, tx, rx, 96) == HAL_OK) {
        if (ulTaskNotifyTake(pdTRUE, 50) > 0 && spi_dma_done && !spi_dma_error) {
            seq++;
            last_crc_error = !CRC16_VerifyChecksum(rx, 96);
            last_unknown_mode = 0;

            if (!last_crc_error && rx[0] == 0xA5) {
                if (rx[1] == 0xF0 && rx[3] == 0x5A) {
                    osDelay(20);
                    NVIC_SystemReset();
                } else if (rx[1] <= 0x05) {
                    current_mode = rx[1];
                }
            }
        }
    }
}"""),
    para("数据打包", "CNH2"),
    para(
        "spi_pack_payload() 在临界区内复制 Inertial 快照和 Inertial.IMU 指向的 BMI088 数据，"
        "随后按 mode 顺序写入 payload。每种 mode 都先写入 HAL_GetTick()，因此主机所有读取结构体第一项都是 tick。"
    ),
    para("回调与任务同步", "CNH2"),
    para(
        "HAL_SPI_TxRxCpltCallback() 在 SPI2 DMA 收发完成时设置 spi_dma_done 并通过 vTaskNotifyGiveFromISR() 唤醒任务。"
        "HAL_SPI_ErrorCallback() 设置 spi_dma_error 并同样唤醒任务。SPICommTask 使用 ulTaskNotifyTake() 等待本帧结束。"
    ),
]

story += [
    para("5. 主机驱动概括", "CNH1"),
    para(
        "主机核心文件为 code/fall_imu_A.c、code/fall_imu_A.h、task/InertialTask.c。"
        "驱动对外提供按数据类型划分的读取接口，应用层通常只需要调用 imu_module_read_euler()、imu_module_read_all() 等函数。"
    ),
    para("初始化", "CNH2"),
    code("""imu_module_spi_init(SPI_0,
                    5 * 1000 * 1000,
                    SPI0_SCLK_P20_11,
                    SPI0_MOSI_P20_14,
                    SPI0_MISO_P20_12,
                    SPI0_CS2_P20_13);"""),
    para(
        "imu_module_spi_init() 内部保存 SPI 编号，并调用逐飞库 spi_init()。当前驱动固定使用 SPI_MODE2，"
        "baud 参数由应用层传入，当前 InertialTask 使用 5 MHz。"
    ),
    para("两帧读取流程", "CNH2"),
    code("""imu_module_read_euler(&euler)
  -> imu_module_read_frame(0x01, &frame)
       -> imu_module_transfer(0x01, 0x00, NULL)
       -> vTaskDelay(1)
       -> imu_module_transfer(0x01, 0x00, &frame)
  -> parse tick, roll, pitch, yaw, yaw_total_angle"""),
    para(
        "第一帧用于通知从机下一轮切换到目标 mode；第二帧读取目标 mode 的 payload。"
        "imu_module_transfer() 每次构造 96 字节 TX 帧，追加 CRC16，然后调用 spi_transfer_8bit() 同步收发 96 字节。"
    ),
    para("主机 API", "CNH2"),
    table([
        ["函数", "读取内容"],
        ["imu_module_read_status()", "tick + temperature。"],
        ["imu_module_read_euler()", "tick + roll/pitch/yaw/yaw_total_angle。"],
        ["imu_module_read_quat()", "tick + q[4]。"],
        ["imu_module_read_motion()", "tick + 处理后的 accel[3]/gyro[3]。"],
        ["imu_module_read_raw()", "tick + BMI088 Accel[3]/Gyro[3]/Temperature。"],
        ["imu_module_read_all()", "tick + 姿态角、四元数、处理后运动量、BMI088 物理量、温度。"],
        ["imu_module_soft_reset()", "发送 mode=0xF0、unlock=0x5A 的软件复位命令。"],
    ], [62 * mm, 108 * mm]),
    para(
        "读取函数返回 IMU_MODULE_OK 表示本次数据有效。应用层使用结构体中的 tick 和数据字段，不需要自己处理帧头、CRC 或两帧读取细节。"
    ),
]

story += [
    PageBreak(),
    para("6. 应用层使用示例", "CNH1"),
    para("当前主机 task/InertialTask.c 的使用方式如下：", "CNBody"),
    code("""imu_module_euler_t euler;
imu_module_result_enum ret;

void InertialTask(void *pvParameters)
{
    imu_module_spi_init(SPI_0,
                        5 * 1000 * 1000,
                        SPI0_SCLK_P20_11,
                        SPI0_MOSI_P20_14,
                        SPI0_MISO_P20_12,
                        SPI0_CS2_P20_13);

    TickType_t last_inertial_tick = xTaskGetTickCount();
    while (1) {
        vTaskDelayUntil(&last_inertial_tick,
                        pdMS_TO_TICKS(INERTIAL_UPDATE_TICK));

        ret = imu_module_read_euler(&euler);
        gpio_toggle_level(LED4);
    }
}"""),
    para(
        "读取成功后，euler.tick 是从机打包时刻，euler.roll、euler.pitch、euler.yaw、euler.yaw_total_angle 是姿态角数据。"
        "如果需要一次读取全部数据，可把周期调用替换为 imu_module_read_all(&all_data)。"
    ),
    para("读取其他模式示例", "CNH2"),
    code("""imu_module_all_t all_data;

if (imu_module_read_all(&all_data) == IMU_MODULE_OK) {
    float roll = all_data.roll;
    float gyro_z = all_data.gyro[2];
    float temperature = all_data.temperature;
    uint32_t module_tick = all_data.tick;
}"""),
    para("软件复位示例", "CNH2"),
    code("""imu_module_soft_reset();"""),
    para(
        "该函数会发送带 CRC 的复位命令帧。从机校验通过后设置复位状态，并在 20 ms 后调用 NVIC_SystemReset()。"
    ),
]

story += [
    para("7. 正常通信验证", "CNH1"),
    table([
        ["层级", "验证点"],
        ["物理层", "主机传输时，CS 每 96 字节形成一次完整低电平窗口，SCK/MOSI/MISO 都有波形。"],
        ["帧头", "主机收到的返回帧 rx[0] 为 0x5A；从机收到的命令帧 rx[0] 为 0xA5。"],
        ["协议层", "读取函数返回 IMU_MODULE_OK，frame.mode 与请求 mode 一致，payload_len 与 mode 表一致。"],
        ["数据层", "tick 持续递增，姿态角、四元数、加速度、角速度随模块运动变化。"],
        ["任务层", "InertialTask 周期运行，ret 为 IMU_MODULE_OK 时使用本次 euler 或 all_data。"],
    ], [32 * mm, 138 * mm]),
    para(
        "在正常通信状态下，建议应用层优先用 ret == IMU_MODULE_OK 作为数据有效条件，再用 tick 判断数据新鲜度。"
        "调试变量 imu_debug_rx0..rx3 和 spi2_debug_rx0..rx3 可用于观察帧头和前几个控制字节。"
    ),
]

story += [
    para("8. 文件位置", "CNH1"),
    table([
        ["工程", "文件", "作用"],
        ["STM32 从机", "E:/STM32_Proj/HAL/F401RBT6/Proj/Task/SPICommTask.c", "SPI2 DMA 通信任务、打包 payload、解析主机命令。"],
        ["STM32 从机", "E:/STM32_Proj/HAL/F401RBT6/Proj/Task/SPICommTask.h", "帧长度、mode 宏、任务声明。"],
        ["STM32 从机", "E:/STM32_Proj/HAL/F401RBT6/Proj/Core/Src/spi.c", "SPI2 从机与 DMA 句柄配置。"],
        ["STM32 从机", "E:/STM32_Proj/HAL/F401RBT6/Proj/Core/Src/dma.c", "DMA1 时钟与中断配置。"],
        ["TC264 主机", "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl/code/fall_imu_A.c", "主机 SPI 驱动实现、两帧读取、CRC 校验、payload 解析。"],
        ["TC264 主机", "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl/code/fall_imu_A.h", "主机驱动宏、结构体和 API 声明。"],
        ["TC264 主机", "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl/task/InertialTask.c", "主机应用层周期读取示例。"],
    ], [28 * mm, 92 * mm, 50 * mm], 7.2),
]

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A4,
    rightMargin=18 * mm,
    leftMargin=18 * mm,
    topMargin=16 * mm,
    bottomMargin=16 * mm,
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT.resolve())
