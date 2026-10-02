`timescale 1ns / 1ps

module lab1_2_tb;
    reg [3:0] swt;
    wire [2:0] led;

    // 实例化待测模块
    lab1_2 uut (
        .swt(swt),
        .led(led)
    );

    initial begin
        // 依次测试所有输入组合
        swt = 4'b0000; #10;
        swt = 4'b0001; #10;
        swt = 4'b0010; #10;
        swt = 4'b0011; #10;
        swt = 4'b0100; #10;
        swt = 4'b0101; #10;
        swt = 4'b0110; #10;
        swt = 4'b0111; #10;
        swt = 4'b1000; #10;
        swt = 4'b1001; #10;
        swt = 4'b1010; #10;
        swt = 4'b1011; #10;
        swt = 4'b1100; #10;
        swt = 4'b1101; #10;
        swt = 4'b1110; #10;
        swt = 4'b1111; #10;
        #10;
        $stop;
    end
endmodule
