`timescale 1ns / 1ps

//==============================================================================
// 模块名称: alu (Arithmetic Logic Unit)
// 功能描述: 算术逻辑单元，执行CPU核心运算操作
// 支持操作: ADD (加法), SUB (减法), OR (按位或), SLT (有符号小于比较)
// 零标志位: 用于beq指令的分支判断 (result == 0)
// 运算方式: 纯组合逻辑，无时序
//==============================================================================
module alu (
    input  wire [31:0] a,           // 操作数A（通常来自rs1）
    input  wire [31:0] b,           // 操作数B（来自rs2或立即数）
    input  wire [3:0]  alu_op,      // ALU操作码
    output reg  [31:0] result,      // ALU运算结果
    output wire        zero         // 零标志（用于beq分支判断）
);

    // ALU操作码定义
    localparam ALU_ADD = 4'b0000;   // 加法（用于add, addi, lw, sw地址计算）
    localparam ALU_SUB = 4'b0001;   // 减法（用于sub, beq比较）
    localparam ALU_OR  = 4'b0010;   // 按位或（用于or, ori）
    localparam ALU_SLT = 4'b0011;   // 有符号比较小于（用于slt, slti）

    // 中间信号
    wire [31:0] b_inv;              // B的反码
    wire [31:0] sum;                // 加法/减法结果
    wire        carry_in;           // 进位输入

    // 减法通过加反码+1实现：a - b = a + (~b) + 1
    assign b_inv = (alu_op == ALU_SUB) ? ~b : b;
    assign carry_in = (alu_op == ALU_SUB) ? 1'b1 : 1'b0;
    assign sum = a + b_inv + carry_in;

    // 零标志：结果为0时置1（用于beq）
    assign zero = (sum == 32'd0);

    // ALU主逻辑
    always @(*) begin
        case (alu_op)
            ALU_ADD: result = sum;                                      // 加法
            ALU_SUB: result = sum;                                      // 减法
            ALU_OR:  result = a | b;                                    // 按位或
            ALU_SLT: result = ($signed(a) < $signed(b)) ? 32'd1 : 32'd0; // 有符号比较
            default: result = 32'd0;
        endcase
    end

endmodule
