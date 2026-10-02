`timescale 1ns / 1ps

//==============================================================================
// 模块名称: dm (Data Memory)
// 功能描述: 数据存储器，用于lw/sw指令的数据读写
// 存储容量: 256字节，按字 (32位) 读写，地址按字对齐
// 存储格式: Little Endian (小端存储)
// 读取方式: 组合逻辑读取
// 写入方式: 同步写入，时钟上升沿有效
//==============================================================================
module dm (
    input  wire        clk,         // 时钟信号
    input  wire        mem_read,    // 读使能
    input  wire        mem_write,   // 写使能
    input  wire [7:0]  addr,        // 字节地址（0-255）
    input  wire [31:0] write_data,  // 写入数据（32位）
    output wire [31:0] read_data    // 读出数据（32位）
);

    // 256字节存储器，按字节组织
    reg [7:0] memory [0:255];

    integer i;

    // 初始化数据存储器
    // 根据老师test.md的要求，DM[12]需要初始化为4
    initial begin
        for (i = 0; i < 256; i = i + 1) begin
            memory[i] = 8'd0;
        end
        // 特殊初始化：DM[12]=4 (小端格式：低字节在低地址)
        memory[12] = 8'h04;  // DM[12] = 4的低字节
        memory[13] = 8'h00;
        memory[14] = 8'h00;
        memory[15] = 8'h00;
        
        $display("[DM] Data Memory initialized");
        $display("[DM] DM[12-15] = 0x%h (for lw test)", {memory[15], memory[14], memory[13], memory[12]});
    end

    // 同步写操作（时钟上升沿）
    always @(posedge clk) begin
        if (mem_write) begin
            // Little Endian写入：低字节存低地址
            memory[addr]   <= write_data[7:0];
            memory[addr+1] <= write_data[15:8];
            memory[addr+2] <= write_data[23:16];
            memory[addr+3] <= write_data[31:24];
        end
    end

    // 组合读操作（Little Endian）
    assign read_data = mem_read ? 
                       {memory[addr+3], memory[addr+2], memory[addr+1], memory[addr]} : 
                       32'd0;

endmodule
