`timescale 1ns / 1ps

module lab1_2(
    input [3:0] swt,        // 4位输入
    output reg [2:0] led    // 2位编码+1位有效指示
);
    always @* begin
        led = 3'b000;
        led[2] = |swt;      // led[2]为有效指示，只要有输入为1即为1
        // 高位优先编码：若有多个输入为1，优先输出编号高的输入
        if (swt[3])
            led[1:0] = 2'b11;
        else if (swt[2])
            led[1:0] = 2'b10;
        else if (swt[1])
            led[1:0] = 2'b01;
        else if (swt[0])
            led[1:0] = 2'b00;
        // 若全为0，led[2]=0，编码无效
    end
endmodule