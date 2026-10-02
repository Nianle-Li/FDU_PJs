`timescale 1ns / 1ps

// 3-8译码器模块
module lab1_1(
    input [3:0] swt,         // swt[3]: 使能信号, swt[2:0]: 3位输入
    output reg [7:0] led     // 8位输出，对应译码结果
);
    always @* begin
        led = 8'b0;          // 默认所有输出为0
        if (swt[3]) begin    // 使能信号为1时，进行译码
            case (swt[2:0])  // 根据3位输入选择输出
                3'b000: led[0] = 1; // 译码输出000，对应led[0]
                3'b001: led[1] = 1; // 译码输出001，对应led[1]
                3'b010: led[2] = 1; // 译码输出010，对应led[2]
                3'b011: led[3] = 1; // 译码输出011，对应led[3]
                3'b100: led[4] = 1; // 译码输出100，对应led[4]
                3'b101: led[5] = 1; // 译码输出101，对应led[5]
                3'b110: led[6] = 1; // 译码输出110，对应led[6]
                3'b111: led[7] = 1; // 译码输出111，对应led[7]
            endcase
        end
    end
endmodule