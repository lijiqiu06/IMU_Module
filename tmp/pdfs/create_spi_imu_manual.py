from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Preformatted, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor


OUT = Path("output/pdf/spi_imu_user_manual.pdf")
pdfmetrics.registerFont(TTFont("NotoSC", r"C:\Windows\Fonts\NotoSansSC-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoSCBold", r"C:\Windows\Fonts\Dengb.ttf"))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("CNTitle", fontName="NotoSCBold", fontSize=22, leading=28, alignment=TA_CENTER, textColor=HexColor("#17324d"), spaceAfter=8))
styles.add(ParagraphStyle("CNSubTitle", fontName="NotoSC", fontSize=10.5, leading=15, alignment=TA_CENTER, textColor=HexColor("#5a6872"), spaceAfter=16))
styles.add(ParagraphStyle("CNH1", fontName="NotoSCBold", fontSize=15, leading=20, textColor=HexColor("#17324d"), spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle("CNH2", fontName="NotoSCBold", fontSize=12, leading=16, textColor=HexColor("#24445f"), spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle("CNBody", fontName="NotoSC", fontSize=9.2, leading=14, textColor=HexColor("#1f2933"), spaceAfter=5))
styles.add(ParagraphStyle("CNNote", fontName="NotoSC", fontSize=8.5, leading=13, textColor=HexColor("#4a5568"), backColor=HexColor("#eef5fb"), borderColor=HexColor("#b7d5ed"), borderWidth=0.5, borderPadding=6, spaceBefore=4, spaceAfter=8))
styles.add(ParagraphStyle("CNCode", fontName="Courier", fontSize=7.3, leading=9.2, textColor=HexColor("#15202b"), backColor=HexColor("#f6f8fa"), borderPadding=5, spaceAfter=6))


def p(text, style="CNBody"):
    return Paragraph(text, styles[style])


def t(data, widths=None, font_size=8.0):
    tbl = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
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
    p("SPI IMU 模块通信用户手册", "CNTitle"),
    p("STM32F401 从机模块与 TC264 主机通信 - 当前工程版本总结", "CNSubTitle"),
    p("本文档基于当前两个工程代码生成：从机工程 E:/STM32_Proj/HAL/F401RBT6/Proj，主机工程 E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl。内容覆盖硬件连接、SPI 配置、帧协议、主从代码结构、使用方法、调试方法和当前已发现的时序问题。"),
    p("当前结论", "CNH1"),
    t([
        ["项目", "当前状态"],
        ["从机角色", "STM32F401，SPI2 硬件从机，DMA_NORMAL 单帧收发，96 字节固定帧"],
        ["主机角色", "TC264，SPI0 硬件主机，当前测试使用 SPI_MODE2，5 MHz，读取周期 5 ms"],
        ["协议状态", "两帧读取机制：主机第一帧下发 mode，第二帧读取上一帧切换后的 payload"],
        ["当前调试现象", "主机偶尔收到 0x5A 帧头，从机可看到 0xA5 出现在 rx1，说明链路通但存在首字节错位或从机 DMA 重挂时序窗口"],
        ["建议验证配置", "主机先用 SPI_MODE2、降低到 1 MHz、帧间延时 2-5 ms；从机去掉 osDelay(1)，尽快重挂 DMA"],
    ], [35 * mm, 135 * mm]),
]

story += [
    p("1. 硬件连接与 SPI 参数", "CNH1"),
    p("从机使用 STM32 SPI2，管脚由 CubeMX 生成。主机当前代码使用 TC264 SPI0。四根信号线必须一一对应，另外必须共地。"),
    t([
        ["信号", "STM32 从机", "TC264 主机当前代码", "说明"],
        ["NSS/CS", "PB12 - SPI2_NSS", "SPI0_CS2_P20_13", "主机片选，低有效，每 96 字节形成一帧"],
        ["SCK", "PB13 - SPI2_SCK", "SPI0_SCLK_P20_11", "主机输出时钟"],
        ["MISO", "PB14 - SPI2_MISO", "SPI0_MISO_P20_12", "从机输出，主机输入"],
        ["MOSI", "PB15 - SPI2_MOSI", "SPI0_MOSI_P20_14", "主机输出，从机输入"],
        ["GND", "GND", "GND", "必须共地"],
    ], [23 * mm, 42 * mm, 45 * mm, 60 * mm]),
    p("注意：MOSI 接 MOSI，MISO 接 MISO。这里按每个设备自身方向命名，不是像 UART TX/RX 那样交叉命名。", "CNNote"),
    t([
        ["参数", "从机 STM32 当前配置", "主机 TC264 当前配置或建议"],
        ["数据宽度", "8 bit", "8 bit"],
        ["位序", "MSB first", "MSB first"],
        ["CPOL", "High", "High"],
        ["CPHA", "2 edge", "当前测试 SPI_MODE2 更接近；若稳定后仍 CRC 错，再比较 Mode 3"],
        ["NSS/CS", "Hardware input", "硬件 CS 输出，低有效"],
        ["帧长", "96 字节", "每次 spi_transfer_8bit 长度 96"],
        ["DMA", "RX:S3 NORMAL；TX:S4 NORMAL", "阻塞式 FIFO 传输"],
    ], [45 * mm, 60 * mm, 65 * mm], 7.2),
]

story += [
    p("2. 协议帧格式", "CNH1"),
    p("主从均使用 96 字节固定长度全双工帧。SPI 从机无法在本帧收到 mode 后立即改变本帧输出，因此协议采用上一帧命令决定下一帧数据的方式。"),
    p("主机发送帧", "CNH2"),
    t([
        ["字节", "字段", "含义"],
        ["0", "SOF", "0xA5，主机帧头"],
        ["1", "mode", "请求模式：00 状态；01 姿态角；02 四元数；03 运动量；04 原始量；05 全量；F0 复位"],
        ["2", "seq", "主机发送序号，每帧自增"],
        ["3", "unlock", "普通命令为 0；软件复位命令必须为 0x5A"],
        ["4..93", "reserved", "保留，当前填 0"],
        ["94..95", "CRC16", "小端 CRC16，调用 CRC16_AppendChecksum 追加"],
    ], [22 * mm, 30 * mm, 118 * mm]),
    p("从机返回帧", "CNH2"),
    t([
        ["字节", "字段", "含义"],
        ["0", "SOF", "0x5A，从机帧头"],
        ["1", "mode", "当前返回数据所属模式"],
        ["2", "seq", "从机发送序号，每成功完成一帧后自增"],
        ["3", "status", "bit0 校准完成；bit1 上一帧 CRC 错；bit2 未知 mode；bit3 即将复位"],
        ["4", "payload_len", "payload 实际长度"],
        ["5..93", "payload", "数据区，最大 89 字节"],
        ["94..95", "CRC16", "小端 CRC16"],
    ], [22 * mm, 30 * mm, 118 * mm]),
    p("所有 payload 的第一个字段均为 uint32_t timestamp，来自从机 HAL_GetTick()。float 和 uint32 均按小端内存顺序发送。"),
    p("3. Payload 数据布局", "CNH1"),
    t([
        ["mode", "payload_len", "payload 字段顺序"],
        ["0x00 STATUS", "8", "uint32 tick；float temperature"],
        ["0x01 EULER", "20", "uint32 tick；float roll；float pitch；float yaw；float yaw_total_angle"],
        ["0x02 QUAT", "20", "uint32 tick；float q[4]"],
        ["0x03 MOTION", "28", "uint32 tick；float accel[3]；float gyro[3]"],
        ["0x04 IMU_RAW", "32", "uint32 tick；float imu_accel[3]；float imu_gyro[3]；float temperature"],
        ["0x05 ALL", "88", "uint32 tick；Euler4；Q4；Accel3；Gyro3；RawAccel3；RawGyro3；temperature"],
    ], [34 * mm, 26 * mm, 110 * mm], 7.7),
]

story += [
    PageBreak(),
    p("4. 从机代码概括和解释", "CNH1"),
    p("从机工程的核心文件是 Task/SPICommTask.c、Task/SPICommTask.h、Core/Src/spi.c、Core/Src/dma.c。当前从机通信采用 DMA_NORMAL，即每完成一帧后 DMA 停止，任务解析后重新启动下一帧 DMA。"),
    p("从机 SPI2 初始化", "CNH2"),
    code("""hspi2.Instance = SPI2;
hspi2.Init.Mode = SPI_MODE_SLAVE;
hspi2.Init.Direction = SPI_DIRECTION_2LINES;
hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
hspi2.Init.CLKPolarity = SPI_POLARITY_HIGH;
hspi2.Init.CLKPhase = SPI_PHASE_2EDGE;
hspi2.Init.NSS = SPI_NSS_HARD_INPUT;
hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;"""),
    p("从机 DMA 配置", "CNH2"),
    t([
        ["方向", "DMA", "模式", "说明"],
        ["RX", "DMA1_Stream3 Channel0", "DMA_NORMAL", "SPI2 DR 到 rx[96]"],
        ["TX", "DMA1_Stream4 Channel0", "DMA_NORMAL", "tx[96] 到 SPI2 DR"],
        ["NVIC", "DMA1_Stream3/4 IRQ priority 5", "-", "适配 FreeRTOS FromISR 通知"],
    ], [30 * mm, 55 * mm, 35 * mm, 50 * mm]),
    p("SPICommTask 主循环", "CNH2"),
    code("""while (1) {
    spi_build_frame(tx, current_mode, seq);
    spi_dma_done = 0;
    spi_dma_error = 0;

    if (HAL_SPI_TransmitReceive_DMA(&hspi2, tx, rx, 96) == HAL_OK) {
        if (ulTaskNotifyTake(pdTRUE, 50) > 0 && spi_dma_done && !spi_dma_error) {
            seq++;
            last_crc_error = !CRC16_VerifyChecksum(rx, 96);
            if (!last_crc_error && rx[0] == 0xA5) {
                // 处理 mode 切换或软件复位
            }
        }
    }
}"""),
    p("回调函数负责从 DMA 中断上下文唤醒 SPICommTask。HAL_SPI_TxRxCpltCallback 表示 96 字节 DMA 收发完成；HAL_SPI_ErrorCallback 表示 SPI/DMA 错误。"),
    p("数据来源", "CNH2"),
    p("spi_pack_payload() 会进入临界区复制全局 Inertial 快照和 Inertial.IMU 指向的 BMI088 数据，随后按 mode 打包。每种模式的 payload 都先写入 HAL_GetTick() 时间戳。"),
    p("当前调试变量", "CNH2"),
    p("从机当前加入了 spi2_debug_rx0..rx3，用于观察收到的主机前 4 字节。注意当前代码中这些变量在 DMA 启动后、等待完成前赋值，实际调试时更建议移动到 DMA 完成并校验前赋值，这样读到的是本帧完成后的 rx 数据。", "CNNote"),
]

story += [
    p("5. 主机代码概括和解释", "CNH1"),
    p("主机工程的核心文件是 code/fall_imu_A.c、code/fall_imu_A.h、task/InertialTask.c。驱动使用逐飞库 spi_init() 和 spi_transfer_8bit()。"),
    p("主机初始化", "CNH2"),
    code("""imu_module_spi_init(SPI_0,
                    5 * 1000 * 1000,
                    SPI0_SCLK_P20_11,
                    SPI0_MOSI_P20_14,
                    SPI0_MISO_P20_12,
                    SPI0_CS2_P20_13);"""),
    p("fall_imu_A.c 当前初始化内部使用 SPI_MODE2。逐飞库中 Mode 2 映射为 CPOL idleHigh，shiftClock trailing edge。这个选择来自调试结果：Mode 3 下 0x5A 被采成 0x2D/0xAD，存在 1 bit 相位错；Mode 2 下偶尔能采到 0x5A。"),
    p("读取流程", "CNH2"),
    code("""imu_module_read_euler(&euler)
  -> imu_module_read_frame(0x01, &frame)
       -> imu_module_transfer(0x01, 0, NULL)   // 第一帧切换从机 mode
       -> vTaskDelay(1)
       -> imu_module_transfer(0x01, 0, &frame) // 第二帧读取目标 payload
  -> 解析 tick, roll, pitch, yaw, yaw_total_angle"""),
    p("主机在每次 imu_module_transfer() 前调用 vTaskDelay(1)，并在两帧之间再次 vTaskDelay(1)。这是为当前 DMA_NORMAL 从机留出重挂 DMA 的时间。"),
    p("主机返回值", "CNH2"),
    t([
        ["返回值", "枚举", "含义"],
        ["0", "IMU_MODULE_OK", "帧头、CRC、mode 和长度均通过"],
        ["1", "IMU_MODULE_ERR_SOF", "rx[0] 不是 0x5A，链路、相位或帧同步问题"],
        ["2", "IMU_MODULE_ERR_CRC", "帧头正确但 CRC 错，通常是位错、字节错位或协议不一致"],
        ["3", "IMU_MODULE_ERR_MODE", "返回帧 mode 不是请求 mode，可能两帧机制未对齐"],
        ["4", "IMU_MODULE_ERR_LEN", "payload_len 小于当前模式所需长度"],
    ], [20 * mm, 45 * mm, 105 * mm]),
]

story += [
    PageBreak(),
    p("6. 当前问题分析与调试方法", "CNH1"),
    p("已观察到的现象包括：主机 ret 多为 1；Mode 3 时主机收到 0x2D，而 0x5A 右移 1 bit 正是 0x2D；Mode 2 时偶尔收到 0x5A 但后续仍乱码；从机调试窗口显示 rx1 可能为 0xA5，rx0 变化。这些共同说明链路不是完全断开，而是存在采样相位和从机 DMA 重挂时序问题。"),
    p("判断表", "CNH2"),
    t([
        ["观察值", "解释", "优先处理"],
        ["主机 rx0 = 0x2D 或 0xAD", "0x5A 发生 1 bit 错位", "切换 SPI_MODE2/3，降低速率"],
        ["主机 rx0 偶尔 = 0x5A，但 CRC 错", "帧头通了，后续字节错位或从机未准备好", "加帧间延时，降低速率，看从机 rx[0..3]"],
        ["从机 rx1 = 0xA5，rx0 随机", "从机 DMA 晚启动，丢了第一个字节", "主机每帧前延时；从机尽快重挂 DMA；考虑 circular 双缓冲"],
        ["主机 rx 全为 0xFF", "MISO 悬空、CS 未选中或从机未驱动", "查接线和 NSS"],
        ["主机 rx 全为 0x00", "线被拉低、从机未输出或模式严重错误", "查供电、接线、波形"],
    ], [42 * mm, 68 * mm, 60 * mm], 7.6),
    p("推荐调试步骤", "CNH2"),
    p("1. 保持主机 SPI_MODE2，将主机波特率先降到 1 MHz。2. 主机读取周期先设为 20 ms。3. imu_module_transfer() 前保留 1-2 tick 延时，两帧之间保留 2-5 ms 延时。4. 从机去掉 osDelay(1)，保证完成一帧后尽快重新 HAL_SPI_TransmitReceive_DMA。5. 同时观察主机 imu_debug_rx0..rx3 与从机 spi2_debug_rx0..rx3。目标是主机 rx0 稳定为 0x5A，从机 rx0 稳定为 0xA5。"),
    p("更长期方案：Circular DMA 双缓冲", "CNH2"),
    p("如果需要高频稳定通信，建议将从机 DMA 改为 circular 双缓冲。RX/TX 缓冲长度设为 2*96=192 字节，在半传输和全传输事件中分别处理前半帧和后半帧。这样 DMA 始终挂载，能消除 DMA_NORMAL 重新启动造成的空窗。但需要额外处理帧边界、缓冲区更新时机和错位重新同步。"),
    p("7. 主机使用示例", "CNH1"),
    code("""// 初始化一次
imu_module_spi_init(SPI_0,
                    1 * 1000 * 1000,
                    SPI0_SCLK_P20_11,
                    SPI0_MOSI_P20_14,
                    SPI0_MISO_P20_12,
                    SPI0_CS2_P20_13);

// 周期读取姿态角
imu_module_euler_t euler;
imu_module_result_enum ret;
ret = imu_module_read_euler(&euler);
if (ret == IMU_MODULE_OK) {
    // euler.tick, euler.roll, euler.pitch, euler.yaw 可用
} else {
    // 查看 ret 和 imu_debug_rx0..rx3
}"""),
    p("软件复位命令", "CNH2"),
    p("主机调用 imu_module_soft_reset() 会发送 mode=0xF0 且 unlock=0x5A。从机 CRC 校验通过后延时 20 ms 调用 NVIC_SystemReset()。"),
]

story += [
    p("8. 验收标准", "CNH1"),
    t([
        ["层级", "成功标准"],
        ["物理层", "主机发送时从机 DMA 完成计数增加；SCK、CS、MOSI、MISO 均有波形"],
        ["帧头层", "主机 rx0 稳定为 0x5A；从机 rx0 稳定为 0xA5"],
        ["CRC 层", "主机 ret 不再是 2；从机 status bit1 不再频繁置位"],
        ["协议层", "ret = 0，frame.mode 等于请求 mode，payload_len 等于模式表长度"],
        ["数据层", "tick 持续递增，Euler/Quat/Accel/Gyro 随模块运动变化"],
    ], [35 * mm, 135 * mm]),
    p("附录：当前关键文件路径", "CNH1"),
    t([
        ["角色", "文件"],
        ["从机协议任务", "E:/STM32_Proj/HAL/F401RBT6/Proj/Task/SPICommTask.c/.h"],
        ["从机 SPI/DMA 配置", "E:/STM32_Proj/HAL/F401RBT6/Proj/Core/Src/spi.c, dma.c"],
        ["主机驱动", "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl/code/fall_imu_A.c/.h"],
        ["主机调用任务", "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl/task/InertialTask.c/.h"],
        ["主机 SPI 库", "E:/SmartCar/ADS_Proj/DOG/Wheel_DOG_PosControl/libraries/zf_driver/zf_driver_spi.c"],
    ], [35 * mm, 135 * mm]),
]


doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A4,
    rightMargin=16 * mm,
    leftMargin=16 * mm,
    topMargin=16 * mm,
    bottomMargin=16 * mm,
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT.resolve())
