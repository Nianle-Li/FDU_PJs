`timescale 1ns/1ps

module ALU_tb;
    reg clk;
    reg [3:0] sw_A, sw_B;
    reg [1:0] sw_op;
    wire [6:0] seg;
    wire [7:0] an;

    ALU_Top uut (
        .clk(clk),
        .sw_A(sw_A),
        .sw_B(sw_B),
        .sw_op(sw_op),
        .seg(seg),
        .an(an)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        $display("==== ALU 测试 ====");
        // 加法
        sw_A = 7; sw_B = 8; sw_op = 2'b00; #20;
        $display("加法:   %2d + %2d = %3d (HEX:%02X)", sw_A, sw_B, uut.alu_result, uut.alu_result);
        // 减法
        sw_A = 10; sw_B = 3; sw_op = 2'b01; #20;
        $display("减法:   %2d - %2d = %3d (HEX:%02X)", sw_A, sw_B, $signed({uut.alu_result[7:4], uut.alu_result[3:0]}), uut.alu_result);
        // 取反
        sw_A = 5; sw_B = 0; sw_op = 2'b10; #20;
        $display("取反:   ~%2d      = %3d (HEX:%02X)", sw_A, uut.alu_result[3:0], uut.alu_result);
        // 乘法
        sw_A = 3; sw_B = 4; sw_op = 2'b11; #20;
        $display("乘法:   %2d * %2d = %3d (HEX:%02X)", sw_A, sw_B, uut.alu_result, uut.alu_result);

        $display("==== 测试结束 ====");
        #20 $finish;
    end
endmodule
