`timescale 1ns / 1ps

//==============================================================================
// 模块名称: imm_gen (Immediate Generator)
// 功能描述: 立即数生成器，根据指令类型提取并符号扩展立即数
// 支持类型: I型 (12位立即数，符号扩展)
//          S型 (12位立即数，分段存储)
//          B型 (12位偏移量，左移1位)
// 扩展方式: 根据instr[31]进行符号扩展至32位
//==============================================================================
module imm_gen (
    input  wire [31:0] instr,       // 输入指令
    input  wire [2:0]  imm_type,    // 立即数类型
    output reg  [31:0] imm          // 输出立即数（符号扩展到32位）
);

    // 立即数类型定义
    localparam IMM_I = 3'b000;      // I型（addi, ori, slti, lw）
    localparam IMM_S = 3'b001;      // S型（sw）
    localparam IMM_B = 3'b010;      // B型（beq）

    always @(*) begin
        case (imm_type)
            IMM_I: begin
                // I型立即数：instr[31:20]，符号扩展
                imm = {{20{instr[31]}}, instr[31:20]};
            end
            
            IMM_S: begin
                // S型立即数：{instr[31:25], instr[11:7]}，符号扩展
                imm = {{20{instr[31]}}, instr[31:25], instr[11:7]};
            end
            
            IMM_B: begin
                // B型立即数：{instr[31], instr[7], instr[30:25], instr[11:8], 1'b0}
                // 符号扩展，最低位为0（2字节对齐）
                imm = {{20{instr[31]}}, instr[7], instr[30:25], instr[11:8], 1'b0};
            end
            
            default: imm = 32'd0;
        endcase
    end

endmodule
