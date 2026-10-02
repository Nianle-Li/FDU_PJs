`timescale 1ns / 1ps

//==============================================================================
// 模块名称: pc (Program Counter)
// 功能描述: 程序计数器，存储当前指令地址
//          在每个时钟上升沿根据pc_next更新PC值
// 复位行为: 异步低电平复位，复位后PC=0x00000000
//==============================================================================
module pc (
    input  wire        clk,         // 时钟信号
    input  wire        rst_n,       // 复位信号（低有效）
    input  wire        pc_write,    // PC写使能（可用于暂停）
    input  wire [31:0] pc_next,     // 下一个PC值
    output reg  [31:0] pc           // 当前PC值
);

    // 同步更新PC
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 32'd0;            // 复位时PC=0
        end else if (pc_write) begin
            pc <= pc_next;          // 更新PC
        end
    end

endmodule
