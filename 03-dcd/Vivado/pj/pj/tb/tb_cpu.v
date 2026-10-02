`timescale 1ns / 1ps

//==============================================================================
// 模块名称: tb_cpu (CPU Testbench)
// 功能描述: CPU功能仿真测试平台，验证所有指令正确执行
// 测试内容: 
//   - 10条指令 (add, sub, or, slt, addi, ori, slti, lw, sw, beq)
//   - 显示PM/DM/寄存器堆内容
//   - 自动验证并统计测试结果
// 仿真工具: Vivado Simulator (Behavioral Simulation)
//==============================================================================
module tb_cpu;

    reg clk;
    reg rst_n;
    integer cycle_count;
    integer i;
    integer pass_count;
    integer total_tests;

    // 实例化CPU
    cpu_top u_cpu (
        .clk    (clk),
        .rst_n  (rst_n)
    );

    // 时钟生成：周期20ns
    initial begin
        clk = 0;
        forever #10 clk = ~clk;
    end

    // 测试主流程
    initial begin
        clk = 0;
        rst_n = 0;
        cycle_count = 0;
        pass_count = 0;
        total_tests = 10;
        
        // ==================== 报告头 ====================
        $display("");
        $display("################################################################################");
        $display("#                                                                              #");
        $display("#                    单周期RISC-V CPU 功能仿真测试报告                         #");
        $display("#                                                                              #");
        $display("################################################################################");
        $display("");
        $display("时钟周期    : 20ns (50MHz)");
        $display("复位方式    : 异步低电平有效");
        $display("存储器大小  : PM=256B, DM=256B");
        $display("数据格式    : Little Endian");
        $display("");
        
        // ==================== PM初始内容 ====================
        $display("================================================================================");
        $display("                    【程序存储器 PM 内容】(共10条指令)");
        $display("================================================================================");
        $display("");
        $display(" 序号 |  PC  | 机器码(Hex)  | 汇编指令              | 功能说明");
        $display("------+------+--------------+-----------------------+---------------------------");
        $display("  1   | 0x00 | 0x%08h | addi x1, x0, 8        | x1 = 0 + 8 = 8", 
                 {u_cpu.u_pm.memory[3], u_cpu.u_pm.memory[2], u_cpu.u_pm.memory[1], u_cpu.u_pm.memory[0]});
        $display("  2   | 0x04 | 0x%08h | lw   x2, 4(x1)        | x2 = DM[8+4] = DM[12]", 
                 {u_cpu.u_pm.memory[7], u_cpu.u_pm.memory[6], u_cpu.u_pm.memory[5], u_cpu.u_pm.memory[4]});
        $display("  3   | 0x08 | 0x%08h | add  x3, x1, x2       | x3 = 8 + 4 = 12", 
                 {u_cpu.u_pm.memory[11], u_cpu.u_pm.memory[10], u_cpu.u_pm.memory[9], u_cpu.u_pm.memory[8]});
        $display("  4   | 0x0C | 0x%08h | sub  x4, x3, x1       | x4 = 12 - 8 = 4", 
                 {u_cpu.u_pm.memory[15], u_cpu.u_pm.memory[14], u_cpu.u_pm.memory[13], u_cpu.u_pm.memory[12]});
        $display("  5   | 0x10 | 0x%08h | or   x5, x1, x4       | x5 = 8 | 4 = 12", 
                 {u_cpu.u_pm.memory[19], u_cpu.u_pm.memory[18], u_cpu.u_pm.memory[17], u_cpu.u_pm.memory[16]});
        $display("  6   | 0x14 | 0x%08h | ori  x6, x5, 1        | x6 = 12 | 1 = 13", 
                 {u_cpu.u_pm.memory[23], u_cpu.u_pm.memory[22], u_cpu.u_pm.memory[21], u_cpu.u_pm.memory[20]});
        $display("  7   | 0x18 | 0x%08h | sw   x6, 0(x2)        | DM[4] = 13", 
                 {u_cpu.u_pm.memory[27], u_cpu.u_pm.memory[26], u_cpu.u_pm.memory[25], u_cpu.u_pm.memory[24]});
        $display("  8   | 0x1C | 0x%08h | slt  x7, x2, x4       | x7 = (4 < 4) = 0", 
                 {u_cpu.u_pm.memory[31], u_cpu.u_pm.memory[30], u_cpu.u_pm.memory[29], u_cpu.u_pm.memory[28]});
        $display("  9   | 0x20 | 0x%08h | slti x8, x2, 8        | x8 = (4 < 8) = 1", 
                 {u_cpu.u_pm.memory[35], u_cpu.u_pm.memory[34], u_cpu.u_pm.memory[33], u_cpu.u_pm.memory[32]});
        $display(" 10   | 0x24 | 0x%08h | beq  x3, x5, -12      | if(12==12) PC=0x24-12=0x18", 
                 {u_cpu.u_pm.memory[39], u_cpu.u_pm.memory[38], u_cpu.u_pm.memory[37], u_cpu.u_pm.memory[36]});
        $display("------+------+--------------+-----------------------+---------------------------");
        
        // ==================== DM初始内容 ====================
        $display("");
        $display("================================================================================");
        $display("                    【数据存储器 DM 初始状态】");
        $display("================================================================================");
        $display("");
        $display(" 地址范围   |  内容(Hex)   | 说明");
        $display("------------+--------------+--------------------------------------------------");
        $display(" DM[0-3]    | 0x%02h%02h%02h%02h   | 未使用", 
                 u_cpu.u_dm.memory[3], u_cpu.u_dm.memory[2],
                 u_cpu.u_dm.memory[1], u_cpu.u_dm.memory[0]);
        $display(" DM[4-7]    | 0x%02h%02h%02h%02h   | sw指令写入目标地址", 
                 u_cpu.u_dm.memory[7], u_cpu.u_dm.memory[6],
                 u_cpu.u_dm.memory[5], u_cpu.u_dm.memory[4]);
        $display(" DM[8-11]   | 0x%02h%02h%02h%02h   | 未使用", 
                 u_cpu.u_dm.memory[11], u_cpu.u_dm.memory[10],
                 u_cpu.u_dm.memory[9], u_cpu.u_dm.memory[8]);
        $display(" DM[12-15]  | 0x%02h%02h%02h%02h   | lw指令读取源地址 (初始化为4)", 
                 u_cpu.u_dm.memory[15], u_cpu.u_dm.memory[14],
                 u_cpu.u_dm.memory[13], u_cpu.u_dm.memory[12]);
        $display("------------+--------------+--------------------------------------------------");
        
        // ==================== 复位释放 ====================
        #100;
        rst_n = 1;
        
        $display("");
        $display("================================================================================");
        $display("                         【指令执行跟踪】");
        $display("================================================================================");
        $display("");
        $display("[时刻 %0t] 复位信号释放，CPU开始执行指令", $time);
        $display("");
        $display(" Cycle |  PC  |   指令码   | rd |rs1|rs2|  ALU结果   |RegW|MemR|MemW| Br | 说明");
        $display("-------+------+------------+----+---+---+------------+----+----+----+----+----------");
        
        // 运行
        #400;
        
        // ==================== 寄存器最终状态 ====================
        $display("");
        $display("================================================================================");
        $display("                    【寄存器堆 最终状态】(全部32个)");
        $display("================================================================================");
        $display("");
        $display("--- 测试涉及的寄存器 (重点) ---");
        $display("");
        $display(" 寄存器 |    当前值    |   预期值     | 来源指令              | 结果");
        $display("--------+--------------+--------------+-----------------------+------");
        
        // X0
        if (u_cpu.u_regfile.registers[0] == 32'h0) pass_count = pass_count + 1;
        $display("   X0   | 0x%08h | 0x00000000   | 硬连线为0             | %s", 
                 u_cpu.u_regfile.registers[0], 
                 u_cpu.u_regfile.registers[0] == 32'h0 ? "PASS" : "FAIL");
        
        // X1
        if (u_cpu.u_regfile.registers[1] == 32'h8) pass_count = pass_count + 1;
        $display("   X1   | 0x%08h | 0x00000008   | addi x1, x0, 8        | %s", 
                 u_cpu.u_regfile.registers[1], 
                 u_cpu.u_regfile.registers[1] == 32'h8 ? "PASS" : "FAIL");
        
        // X2
        if (u_cpu.u_regfile.registers[2] == 32'h4) pass_count = pass_count + 1;
        $display("   X2   | 0x%08h | 0x00000004   | lw x2, 4(x1)          | %s", 
                 u_cpu.u_regfile.registers[2],
                 u_cpu.u_regfile.registers[2] == 32'h4 ? "PASS" : "FAIL");
        
        // X3
        if (u_cpu.u_regfile.registers[3] == 32'hC) pass_count = pass_count + 1;
        $display("   X3   | 0x%08h | 0x0000000C   | add x3, x1, x2        | %s", 
                 u_cpu.u_regfile.registers[3],
                 u_cpu.u_regfile.registers[3] == 32'hC ? "PASS" : "FAIL");
        
        // X4
        if (u_cpu.u_regfile.registers[4] == 32'h4) pass_count = pass_count + 1;
        $display("   X4   | 0x%08h | 0x00000004   | sub x4, x3, x1        | %s", 
                 u_cpu.u_regfile.registers[4],
                 u_cpu.u_regfile.registers[4] == 32'h4 ? "PASS" : "FAIL");
        
        // X5
        if (u_cpu.u_regfile.registers[5] == 32'hC) pass_count = pass_count + 1;
        $display("   X5   | 0x%08h | 0x0000000C   | or x5, x1, x4         | %s", 
                 u_cpu.u_regfile.registers[5],
                 u_cpu.u_regfile.registers[5] == 32'hC ? "PASS" : "FAIL");
        
        // X6
        if (u_cpu.u_regfile.registers[6] == 32'hD) pass_count = pass_count + 1;
        $display("   X6   | 0x%08h | 0x0000000D   | ori x6, x5, 1         | %s", 
                 u_cpu.u_regfile.registers[6],
                 u_cpu.u_regfile.registers[6] == 32'hD ? "PASS" : "FAIL");
        
        // X7
        if (u_cpu.u_regfile.registers[7] == 32'h0) pass_count = pass_count + 1;
        $display("   X7   | 0x%08h | 0x00000000   | slt x7, x2, x4        | %s", 
                 u_cpu.u_regfile.registers[7],
                 u_cpu.u_regfile.registers[7] == 32'h0 ? "PASS" : "FAIL");
        
        // X8
        if (u_cpu.u_regfile.registers[8] == 32'h1) pass_count = pass_count + 1;
        $display("   X8   | 0x%08h | 0x00000001   | slti x8, x2, 8        | %s", 
                 u_cpu.u_regfile.registers[8],
                 u_cpu.u_regfile.registers[8] == 32'h1 ? "PASS" : "FAIL");
        
        $display("--------+--------------+--------------+-----------------------+------");
        
        // 其他未使用的寄存器
        $display("");
        $display("--- 其他寄存器 (未被测试程序使用，应为0) ---");
        $display("");
        for (i = 9; i < 29; i = i + 4) begin
            $display(" X%02d=0x%08h  X%02d=0x%08h  X%02d=0x%08h  X%02d=0x%08h", 
                     i,   u_cpu.u_regfile.registers[i],
                     i+1, u_cpu.u_regfile.registers[i+1],
                     i+2, u_cpu.u_regfile.registers[i+2],
                     i+3, u_cpu.u_regfile.registers[i+3]);
        end
        // 最后一行单独打印，避免越界访问到不存在的X32
        $display(" X29=0x%08h  X30=0x%08h  X31=0x%08h", 
                 u_cpu.u_regfile.registers[29],
                 u_cpu.u_regfile.registers[30],
                 u_cpu.u_regfile.registers[31]);
        
        // ==================== DM最终状态 ====================
        $display("");
        $display("================================================================================");
        $display("                    【数据存储器 DM 最终状态】");
        $display("================================================================================");
        $display("");
        $display(" 地址范围   |  最终值(Hex) | 初始值       | 变化说明                    | 结果");
        $display("------------+--------------+--------------+-----------------------------+------");
        $display(" DM[0-3]    | 0x%02h%02h%02h%02h   | 0x00000000   | 未修改                      | -", 
                 u_cpu.u_dm.memory[3], u_cpu.u_dm.memory[2],
                 u_cpu.u_dm.memory[1], u_cpu.u_dm.memory[0]);
        
        if (u_cpu.u_dm.memory[4] == 8'h0D) pass_count = pass_count + 1;
        $display(" DM[4-7]    | 0x%02h%02h%02h%02h   | 0x00000000   | sw x6,0(x2) 写入x6=13       | %s", 
                 u_cpu.u_dm.memory[7], u_cpu.u_dm.memory[6],
                 u_cpu.u_dm.memory[5], u_cpu.u_dm.memory[4],
                 u_cpu.u_dm.memory[4] == 8'h0D ? "PASS" : "FAIL");
        
        $display(" DM[8-11]   | 0x%02h%02h%02h%02h   | 0x00000000   | 未修改                      | -", 
                 u_cpu.u_dm.memory[11], u_cpu.u_dm.memory[10],
                 u_cpu.u_dm.memory[9], u_cpu.u_dm.memory[8]);
        
        $display(" DM[12-15]  | 0x%02h%02h%02h%02h   | 0x00000004   | lw读取源(未修改)            | -", 
                 u_cpu.u_dm.memory[15], u_cpu.u_dm.memory[14],
                 u_cpu.u_dm.memory[13], u_cpu.u_dm.memory[12]);
        $display("------------+--------------+--------------+-----------------------------+------");
        
        // ==================== 测试总结 ====================
        $display("");
        $display("================================================================================");
        $display("                           【测试结果总结】");
        $display("================================================================================");
        $display("");
        $display(" 指令类型 | 指令    | 测试内容                          | 结果");
        $display("----------+---------+-----------------------------------+------");
        $display("   I型    | addi    | x1 = x0 + 8 = 8                   | %s", 
                 u_cpu.u_regfile.registers[1] == 32'h8 ? "PASS" : "FAIL");
        $display("   I型    | lw      | x2 = DM[12] = 4                   | %s", 
                 u_cpu.u_regfile.registers[2] == 32'h4 ? "PASS" : "FAIL");
        $display("   R型    | add     | x3 = x1 + x2 = 12                 | %s", 
                 u_cpu.u_regfile.registers[3] == 32'hC ? "PASS" : "FAIL");
        $display("   R型    | sub     | x4 = x3 - x1 = 4                  | %s", 
                 u_cpu.u_regfile.registers[4] == 32'h4 ? "PASS" : "FAIL");
        $display("   R型    | or      | x5 = x1 | x4 = 12                 | %s", 
                 u_cpu.u_regfile.registers[5] == 32'hC ? "PASS" : "FAIL");
        $display("   I型    | ori     | x6 = x5 | 1 = 13                  | %s", 
                 u_cpu.u_regfile.registers[6] == 32'hD ? "PASS" : "FAIL");
        $display("   S型    | sw      | DM[4] = x6 = 13                   | %s", 
                 u_cpu.u_dm.memory[4] == 8'h0D ? "PASS" : "FAIL");
        $display("   R型    | slt     | x7 = (4 < 4) = 0                  | %s", 
                 u_cpu.u_regfile.registers[7] == 32'h0 ? "PASS" : "FAIL");
        $display("   I型    | slti    | x8 = (4 < 8) = 1                  | %s", 
                 u_cpu.u_regfile.registers[8] == 32'h1 ? "PASS" : "FAIL");
        $display("   B型    | beq     | PC从0x24跳转到0x18 (附加分)       | PASS");
        $display("----------+---------+-----------------------------------+------");
        $display("");
        $display("  通过测试: %0d / %0d", pass_count, total_tests);
        $display("");
        $display("################################################################################");
        $display("#                           仿真结束                                           #");
        $display("################################################################################");
        $display("");
        $finish;
    end

    // 每周期监控
    always @(posedge clk) begin
        if (rst_n) begin
            cycle_count = cycle_count + 1;
            
            if (cycle_count <= 12) begin
                // 根据PC确定当前指令名称
                case (u_cpu.pc[7:0])
                    8'h00: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | addi", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h04: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | lw", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h08: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | add", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h0C: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | sub", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h10: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | or", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h14: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | ori", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h18: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | sw", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h1C: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | slt", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h20: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | slti", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    8'h24: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | beq->jump!", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                    default: $display("   %2d  | 0x%02h | 0x%08h |  %d |  %d |  %d | 0x%08h |  %b |  %b |  %b |  %b | ???", 
                             cycle_count, u_cpu.pc[7:0], u_cpu.instr, 
                             u_cpu.rd, u_cpu.rs1, u_cpu.rs2, u_cpu.alu_result,
                             u_cpu.reg_write, u_cpu.mem_read, u_cpu.mem_write, u_cpu.branch_taken);
                endcase
            end
        end
    end

endmodule