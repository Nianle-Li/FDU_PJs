`timescale 1ns / 1ps

//==============================================================================
// 模块名称: regfile (Register File)
// 功能描述: 寄存器堆，包含32个32位通用寄存器 (x0-x31)
// 特殊规则: x0寄存器硬连线为0，任何写入操作被忽略
// 读取方式: 组合逻辑，支持2读1写
// 写入方式: 同步写入，时钟上升沿有效
//==============================================================================
module regfile (
    input  wire        clk,         // 时钟信号
    input  wire        rst_n,       // 复位信号（低有效）
    input  wire        reg_write,   // 写使能信号
    input  wire [4:0]  rs1,         // 源寄存器1地址
    input  wire [4:0]  rs2,         // 源寄存器2地址
    input  wire [4:0]  rd,          // 目标寄存器地址
    input  wire [31:0] write_data,  // 写入数据
    output wire [31:0] rs1_data,    // 源寄存器1读出数据
    output wire [31:0] rs2_data     // 源寄存器2读出数据
);

    // 32个寄存器
    reg [31:0] registers [0:31];
    
    integer i;

    // 同步写操作（时钟上升沿）
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // 复位时清零所有寄存器
            for (i = 0; i < 32; i = i + 1) begin
                registers[i] <= 32'd0;
            end
        end else begin
            // 写使能时写入数据，x0除外（x0恒为0）
            if (reg_write && rd != 5'd0) begin
                registers[rd] <= write_data;
            end
        end
    end

    // 组合读操作（异步读取）
    assign rs1_data = (rs1 == 5'd0) ? 32'd0 : registers[rs1];
    assign rs2_data = (rs2 == 5'd0) ? 32'd0 : registers[rs2];

endmodule
