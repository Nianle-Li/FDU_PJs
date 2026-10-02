`timescale 1ns / 1ps

//==============================================================================
// 模块名称: pm (Program Memory)
// 功能描述: 程序存储器，存储CPU执行的机器指令
// 存储容量: 256字节 (64条32位指令)，按字对齐
// 存储格式: Little Endian (小端存储)
// 读取方式: 组合逻辑读取，地址输入立即输出指令
// 初始化方式: 
//   1. 从pm_init.hex文件加载（老师测试用）
//   2. 如果文件不存在，使用硬编码默认程序
//==============================================================================
module pm (
    input  wire [7:0]  addr,        // 字节地址（0-255）
    output wire [31:0] instr        // 读出的32位指令
);

    // 256字节存储器，按字节组织
    reg [7:0] memory [0:255];

    integer i;
    
    // 初始化
    initial begin
        // 先用默认测试程序初始化（硬编码）
        // 这样即使文件加载失败也能运行
        for (i = 0; i < 256; i = i + 1) begin
            memory[i] = 8'h00;
        end
        
        // ===== 默认测试程序：老师test.md的10条指令 =====
        // Little Endian格式：低字节在低地址
        
        // 指令0 (PC=0x00): addi X1, X0, 8  -> X1 = 8
        memory[0]  = 8'h93; memory[1]  = 8'h00; memory[2]  = 8'h80; memory[3]  = 8'h00;
        
        // 指令1 (PC=0x04): lw X2, 4(X1)   -> X2 = DM[12] = 4
        memory[4]  = 8'h03; memory[5]  = 8'ha1; memory[6]  = 8'h40; memory[7]  = 8'h00;
        
        // 指令2 (PC=0x08): add X3, X1, X2 -> X3 = 12
        memory[8]  = 8'hb3; memory[9]  = 8'h81; memory[10] = 8'h20; memory[11] = 8'h00;
        
        // 指令3 (PC=0x0C): sub X4, X3, X1 -> X4 = 4
        memory[12] = 8'h33; memory[13] = 8'h82; memory[14] = 8'h11; memory[15] = 8'h40;
        
        // 指令4 (PC=0x10): or X5, X1, X4  -> X5 = 12
        memory[16] = 8'hb3; memory[17] = 8'he2; memory[18] = 8'h40; memory[19] = 8'h00;
        
        // 指令5 (PC=0x14): ori X6, X5, 1  -> X6 = 13
        memory[20] = 8'h13; memory[21] = 8'he3; memory[22] = 8'h12; memory[23] = 8'h00;
        
        // 指令6 (PC=0x18): sw X6, 0(X2)   -> DM[4] = 13
        memory[24] = 8'h23; memory[25] = 8'h20; memory[26] = 8'h61; memory[27] = 8'h00;
        
        // 指令7 (PC=0x1C): slt X7, X2, X4 -> X7 = 0
        memory[28] = 8'hb3; memory[29] = 8'h23; memory[30] = 8'h41; memory[31] = 8'h00;
        
        // 指令8 (PC=0x20): slti X8, X2, 8 -> X8 = 1
        memory[32] = 8'h13; memory[33] = 8'h24; memory[34] = 8'h81; memory[35] = 8'h00;
        
        // 指令9 (PC=0x24): beq X3, X5, -12 -> 跳转到0x18
        memory[36] = 8'he3; memory[37] = 8'h8a; memory[38] = 8'h51; memory[39] = 8'hfe;
        
        // 尝试从文件加载（会覆盖硬编码）
        // 如果文件存在，使用文件内容；否则使用上面的硬编码
        // 注意：Vivado仿真时，文件路径相对于仿真工作目录
        // 方法1：将pm_init.hex复制到仿真工作目录（推荐）
        // 方法2：使用绝对路径（不推荐，移植性差）
        // 方法3：在Vivado中设置Simulation -> Simulation Settings -> Simulation Top Module Properties -> SIMULATION_WORKING_DIRECTORY
        $readmemh("../sim/pm_init.hex", memory);
        
        $display("[PM] Program Memory initialized");
        $display("[PM] First instruction: 0x%h%h%h%h", 
                 memory[3], memory[2], memory[1], memory[0]);
    end

    // 按Little Endian读取32位指令
    assign instr = {memory[addr+3], memory[addr+2], memory[addr+1], memory[addr]};

endmodule
