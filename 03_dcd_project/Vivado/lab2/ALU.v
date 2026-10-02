`timescale 1ns/1ps

module ALU(
    input  [3:0] A,
    input  [3:0] B,
    input  [1:0] op,
    output reg [7:0] F
);
    // 中间寄存器
    reg [4:0] add_result;
    reg [4:0] sub_result;
    reg [7:0] mul_result;

    always @(*) begin
        case(op)
            2'b00: begin // 加法
                add_result = A + B;
                F[3:0] = add_result[3:0];
                F[7:4] = add_result[4] ? 4'b0001 : 4'b0000; // 高位进位
            end
            2'b01: begin // 减法
                sub_result = A - B;
                F[3:0] = sub_result[3:0];
                F[7:4] = sub_result[4] ? 4'b1111 : 4'b0000; // 高位借位
            end
            2'b10: begin // 取反
                F[3:0] = ~A;
                F[7:4] = 4'b0000;
            end
            2'b11: begin // 乘法
                mul_result = A * B;
                F = mul_result[7:0];
            end
            default: F = 8'b0;
        endcase
    end
endmodule

module SevenSegmentDisplay(
    input clk,
    input [7:0] data,
    output reg [6:0] seg,
    output reg [7:0] an
);
    reg [18:0] counter = 0;
    wire digit_sel;
    wire [3:0] hex_data;
    
    always @(posedge clk) begin
        counter <= counter + 1;
    end
    
    assign digit_sel = counter[18];
    assign hex_data = digit_sel ? data[7:4] : data[3:0];
    
    // 位选
    always @(*) begin
        an = digit_sel ? 8'b11111101 : 8'b11111110;
    end
    
    // 段选（共阴）
    always @(*) begin
        case (hex_data)
            4'h0: seg = 7'b1000000;
            4'h1: seg = 7'b1111001;
            4'h2: seg = 7'b0100100;
            4'h3: seg = 7'b0110000;
            4'h4: seg = 7'b0011001;
            4'h5: seg = 7'b0010010;
            4'h6: seg = 7'b0000010;
            4'h7: seg = 7'b1111000;
            4'h8: seg = 7'b0000000;
            4'h9: seg = 7'b0010000;
            4'hA: seg = 7'b0001000;
            4'hB: seg = 7'b0000011;
            4'hC: seg = 7'b1000110;
            4'hD: seg = 7'b0100001;
            4'hE: seg = 7'b0000110;
            4'hF: seg = 7'b0001110;
        endcase
    end
endmodule

module ALU_Top(
    input clk,
    input [3:0] sw_A,
    input [3:0] sw_B,
    input [1:0] sw_op,
    output wire [6:0] seg,
    output wire [7:0] an
);
    wire [7:0] alu_result;
    
    ALU alu_inst(
        .A(sw_A),
        .B(sw_B),
        .op(sw_op),
        .F(alu_result)
    );
    
    SevenSegmentDisplay display_inst(
        .clk(clk),
        .data(alu_result),
        .seg(seg),
        .an(an)
    );
endmodule