`timescale 1ns / 1ps

//==============================================================================
// 模块名称: decoder (Instruction Decoder)
// 功能描述: 指令译码器，根据指令操作码和功能码生成控制信号
// 支持指令: R型 (add, sub, or, slt)
//          I型 (addi, ori, slti, lw)
//          S型 (sw), B型 (beq)
// 输出信号: alu_op, alu_src, mem_read/write, reg_write, mem_to_reg, 
//          branch, imm_type
//==============================================================================
module decoder (
    input  wire [31:0] instr,       // 输入指令
    
    // 控制信号输出
    output reg  [3:0]  alu_op,      // ALU操作码
    output reg         alu_src,     // ALU第二操作数来源：0=rs2, 1=imm
    output reg         mem_read,    // 数据存储器读使能
    output reg         mem_write,   // 数据存储器写使能
    output reg         mem_to_reg,  // 写回寄存器数据来源：0=ALU, 1=Memory
    output reg         reg_write,   // 寄存器写使能
    output reg         branch,      // 分支指令标志
    output reg  [2:0]  imm_type     // 立即数类型
);

    // 提取指令字段
    wire [6:0] opcode = instr[6:0];
    wire [2:0] funct3 = instr[14:12];
    wire [6:0] funct7 = instr[31:25];

    // ALU操作码定义
    localparam ALU_ADD = 4'b0000;
    localparam ALU_SUB = 4'b0001;
    localparam ALU_OR  = 4'b0010;
    localparam ALU_SLT = 4'b0011;

    // 立即数类型定义
    localparam IMM_I = 3'b000;
    localparam IMM_S = 3'b001;
    localparam IMM_B = 3'b010;

    // opcode定义
    localparam OP_R_TYPE = 7'b0110011;  // R型（add, sub, or, slt）
    localparam OP_I_ALU  = 7'b0010011;  // I型ALU（addi, ori, slti）
    localparam OP_LOAD   = 7'b0000011;  // Load（lw）
    localparam OP_STORE  = 7'b0100011;  // Store（sw）
    localparam OP_BRANCH = 7'b1100011;  // Branch（beq）

    // 译码主逻辑
    always @(*) begin
        // 默认值（避免latch）
        alu_op = ALU_ADD;
        alu_src = 1'b0;
        mem_read = 1'b0;
        mem_write = 1'b0;
        mem_to_reg = 1'b0;
        reg_write = 1'b0;
        branch = 1'b0;
        imm_type = IMM_I;

        case (opcode)
            // R型指令：add, sub, or, slt
            OP_R_TYPE: begin
                alu_src = 1'b0;         // 使用rs2
                reg_write = 1'b1;       // 写回寄存器
                mem_to_reg = 1'b0;      // 写回ALU结果
                
                case (funct3)
                    3'b000: begin       // add or sub
                        alu_op = (funct7 == 7'b0100000) ? ALU_SUB : ALU_ADD;
                    end
                    3'b110: alu_op = ALU_OR;   // or
                    3'b010: alu_op = ALU_SLT;  // slt
                    default: alu_op = ALU_ADD;
                endcase
            end

            // I型ALU指令：addi, ori, slti
            OP_I_ALU: begin
                alu_src = 1'b1;         // 使用立即数
                reg_write = 1'b1;       // 写回寄存器
                mem_to_reg = 1'b0;      // 写回ALU结果
                imm_type = IMM_I;       // I型立即数（符号扩展）
                
                case (funct3)
                    3'b000: alu_op = ALU_ADD;  // addi
                    3'b110: alu_op = ALU_OR;   // ori（按要求使用符号扩展）
                    3'b010: alu_op = ALU_SLT;  // slti
                    default: alu_op = ALU_ADD;
                endcase
            end

            // Load指令：lw
            OP_LOAD: begin
                alu_src = 1'b1;         // 使用立即数
                imm_type = IMM_I;       // I型立即数
                
                case (funct3)
                    3'b010: begin       // lw (load word)
                        alu_op = ALU_ADD;       // 地址计算：rs1 + imm
                        mem_read = 1'b1;        // 读数据存储器
                        reg_write = 1'b1;       // 写回寄存器
                        mem_to_reg = 1'b1;      // 写回Memory数据
                    end
                    default: begin
                        alu_op = ALU_ADD;
                        mem_read = 1'b0;
                        reg_write = 1'b0;
                        mem_to_reg = 1'b0;
                    end
                endcase
            end

            // Store指令：sw
            OP_STORE: begin
                alu_src = 1'b1;         // 使用立即数
                imm_type = IMM_S;       // S型立即数
                
                case (funct3)
                    3'b010: begin       // sw (store word)
                        alu_op = ALU_ADD;       // 地址计算：rs1 + imm
                        mem_write = 1'b1;       // 写数据存储器
                        reg_write = 1'b0;       // 不写回寄存器
                    end
                    default: begin
                        alu_op = ALU_ADD;
                        mem_write = 1'b0;
                        reg_write = 1'b0;
                    end
                endcase
            end

            // Branch指令：beq
            OP_BRANCH: begin
                alu_src = 1'b0;         // 使用rs2
                imm_type = IMM_B;       // B型立即数
                
                case (funct3)
                    3'b000: begin       // beq
                        alu_op = ALU_SUB;       // 比较：rs1 - rs2
                        branch = 1'b1;          // 分支指令标志
                    end
                    default: begin
                        alu_op = ALU_ADD;
                        branch = 1'b0;
                    end
                endcase
            end

            default: begin
                // 非法指令，保持默认值
            end
        endcase
    end

endmodule
