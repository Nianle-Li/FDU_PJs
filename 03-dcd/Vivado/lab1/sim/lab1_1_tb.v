`timescale 1ns / 1ps

module lab_tb;
    reg [3:0] swt;           // 开关信号
    wire [7:0] led;          // LED信号

    // 实例化被测模块
    lab1_1 uut (
        .swt(swt),
        .led(led)
    );

    initial begin
        // 初始状态，全部为0
        swt = 4'b0000; #10;

        // 低位变化，LED应响应
        swt = 4'b0001; #10;
        swt = 4'b0010; #10;
        swt = 4'b0011; #10;
        swt = 4'b0100; #10;
        swt = 4'b0101; #10;
        swt = 4'b0110; #10;
        swt = 4'b0111; #10;

        // 高位为1，低三位变化，测试高位使能
        swt[3] = 1;
        swt[2:0] = 3'b000; #10;
        swt[2:0] = 3'b001; #10;
        swt[2:0] = 3'b010; #10;
        swt[2:0] = 3'b011; #10;
        swt[2:0] = 3'b100; #10;
        swt[2:0] = 3'b101; #10;
        swt[2:0] = 3'b110; #10;
        swt[2:0] = 3'b111; #10;

        // 关闭使能，验证输出
        swt = 4'b0000; #20;

        $stop; // 停止仿真
    end
endmodule
