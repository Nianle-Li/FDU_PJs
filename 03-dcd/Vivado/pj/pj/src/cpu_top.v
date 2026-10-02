`timescale 1ns / 1ps

//==============================================================================
// 模块名称: cpu_top
// 功能描述: 单周期RISC-V CPU顶层模块
//          集成所有子模块，实现完整的CPU数据通路和控制逻辑
// 支持指令: add, sub, or, slt, addi, ori, slti, lw, sw, beq
// 设计方式: 单周期架构，组合读/同步写
//==============================================================================
module cpu_top (
    input  wire clk,                // 时钟信号
    input  wire rst_n               // 复位信号（低有效）
);

    // ========== 内部信号定义 ==========
    
    // PC相关
    wire [31:0] pc;                 // 当前PC
    wire [31:0] pc_next;            // 下一个PC
    wire [31:0] pc_plus4;           // PC+4（顺序执行）
    wire [31:0] pc_branch;          // 分支目标地址
    wire        pc_write;           // PC写使能
    
    // 指令相关
    wire [31:0] instr;              // 当前指令
    wire [6:0]  opcode;
    wire [4:0]  rs1, rs2, rd;
    wire [2:0]  funct3;
    wire [6:0]  funct7;
    
    // 控制信号
    wire [3:0]  alu_op;
    wire        alu_src;
    wire        mem_read;
    wire        mem_write;
    wire        mem_to_reg;
    wire        reg_write;
    wire        branch;
    wire [2:0]  imm_type;
    
    // 数据通路信号
    wire [31:0] rs1_data, rs2_data; // 寄存器读出数据
    wire [31:0] imm;                // 立即数
    wire [31:0] alu_b;              // ALU第二操作数
    wire [31:0] alu_result;         // ALU结果
    wire        alu_zero;           // ALU零标志
    wire [31:0] mem_read_data;      // 存储器读出数据
    wire [31:0] reg_write_data;     // 寄存器写回数据
    
    // 分支控制
    wire        branch_taken;       // 分支是否跳转

    // ========== 指令字段提取 ==========
    assign opcode = instr[6:0];
    assign rd     = instr[11:7];
    assign funct3 = instr[14:12];
    assign rs1    = instr[19:15];
    assign rs2    = instr[24:20];
    assign funct7 = instr[31:25];

    // ========== PC更新逻辑 ==========
    assign pc_write = 1'b1;         // 始终使能PC更新（单周期CPU）
    assign pc_plus4 = pc + 32'd4;   // 顺序执行：PC+4
    assign pc_branch = pc + imm;    // 分支目标：PC + offset
    
    // 分支判断：beq时当alu_zero=1（rs1==rs2）则跳转
    assign branch_taken = branch & alu_zero;
    
    // PC选择：分支跳转 or 顺序执行
    assign pc_next = branch_taken ? pc_branch : pc_plus4;

    // ========== 数据通路连接 ==========
    
    // ALU第二操作数选择：rs2或立即数
    assign alu_b = alu_src ? imm : rs2_data;
    
    // 寄存器写回数据选择：ALU结果或Memory数据
    assign reg_write_data = mem_to_reg ? mem_read_data : alu_result;

    // ========== 模块实例化 ==========
    
    // 程序计数器
    pc u_pc (
        .clk        (clk),
        .rst_n      (rst_n),
        .pc_write   (pc_write),
        .pc_next    (pc_next),
        .pc         (pc)
    );

    // 程序存储器
    pm u_pm (
        .addr       (pc[7:0]),      // 取低8位作为地址（256 bytes）
        .instr      (instr)
    );

    // 指令译码器
    decoder u_decoder (
        .instr      (instr),
        .alu_op     (alu_op),
        .alu_src    (alu_src),
        .mem_read   (mem_read),
        .mem_write  (mem_write),
        .mem_to_reg (mem_to_reg),
        .reg_write  (reg_write),
        .branch     (branch),
        .imm_type   (imm_type)
    );

    // 立即数生成器
    imm_gen u_imm_gen (
        .instr      (instr),
        .imm_type   (imm_type),
        .imm        (imm)
    );

    // 寄存器堆
    regfile u_regfile (
        .clk        (clk),
        .rst_n      (rst_n),
        .reg_write  (reg_write),
        .rs1        (rs1),
        .rs2        (rs2),
        .rd         (rd),
        .write_data (reg_write_data),
        .rs1_data   (rs1_data),
        .rs2_data   (rs2_data)
    );

    // ALU
    alu u_alu (
        .a          (rs1_data),
        .b          (alu_b),
        .alu_op     (alu_op),
        .result     (alu_result),
        .zero       (alu_zero)
    );

    // 数据存储器
    dm u_dm (
        .clk        (clk),
        .mem_read   (mem_read),
        .mem_write  (mem_write),
        .addr       (alu_result[7:0]), // 取低8位作为地址（256 bytes）
        .write_data (rs2_data),
        .read_data  (mem_read_data)
    );

endmodule
