module vending(
	input  wire CLK100MHZ,
	input  wire CPU_RESETN,
	input  wire [15:0] SW,
	input  wire BTNC, BTNU, BTNL, BTNR, BTND,
	output reg  [15:0] LED,
	output wire LED16_B, LED16_G, LED16_R,
	output wire LED17_B, LED17_G, LED17_R,
	output reg  CA, CB, CC, CD, CE, CF, CG, DP,
	output reg  [7:0] AN
);


/*
	Module: vending.v
	Description:
	- Simple vending machine controller.
	- Clock: CLK100MHZ (100 MHz)
	- Active-low reset: CPU_RESETN
	- Product selected by SW[2:0] (six valid selections)
	- Coin inputs: BTNL (5.0), BTNR (2.0), BTNU (1.0), BTND (0.5), BTNC (clear)
	- 6 product success LEDs and 6-digit 7-segment display.
	- Change calculation: change_amount = balance - current_price
	- When change_display == 1 the display shows change amount for a blink period.
	- The change display blinks for a number of cycles determined by change_blink_cnt.
	- Blink and debounce timing are parameterized (DEBOUNCE_CYCLES, BLINK_INTERVAL).
	- Note: Units inside the design are in "jiao" (1 yuan = 10 jiao) to avoid floating point.
*/


assign LED16_B = 1'b0;
assign LED16_G = 1'b0;
assign LED16_R = 1'b0;
assign LED17_B = 1'b0;
assign LED17_G = 1'b0;
assign LED17_R = 1'b0;

 
// parameter descriptions 
// DEBOUNCE_CYCLES: debounce stabilization count (in CLK cycles). Default chosen for ~10 ms at 100 MHz.
// BLINK_INTERVAL: number of clock cycles per blink interval (default 50_000_000 -> 0.5 s @100MHz)
parameter integer DEBOUNCE_CYCLES = 1_000_000; // default debounce window (~10 ms @100MHz)
parameter integer BLINK_INTERVAL = 50_000_000; // blink period in clock cycles (default 0.5s)
localparam integer BLINK_HALF = BLINK_INTERVAL / 2;


// price table (units: jiao)
localparam [15:0] PRICE0 = 16'd5;    // 0.5 yuan = 5 jiao
localparam [15:0] PRICE1 = 16'd10;   // 1.0 yuan = 10 jiao
localparam [15:0] PRICE2 = 16'd15;   // 1.5 yuan = 15 jiao
localparam [15:0] PRICE3 = 16'd20;   // 2.0 yuan = 20 jiao
localparam [15:0] PRICE4 = 16'd65;   // 6.5 yuan = 65 jiao
localparam [15:0] PRICE5 = 16'd130;  // 13.0 yuan = 130 jiao

// FSM states 
// S_IDLE      : waiting for a valid product selection
// S_WAIT_COIN : accumulating coins until price is reached
// S_PURCHASE  : perform purchase, set success flags and compute change
// S_CHANGE    : display change amount (blink), then return
localparam [1:0]
	S_IDLE      = 2'd0,
	S_WAIT_COIN = 2'd1,
	S_PURCHASE  = 2'd2,
	S_CHANGE    = 2'd3;

reg [1:0] state, next_state;

// Internal registers for product selection, balance, flags and timers
reg [2:0] product_sel;
reg [15:0] balance;
reg [15:0] current_price;
reg [5:0] success_flags;
reg [15:0] change_amount;
reg change_display;
reg [1:0] blink_cnt;
reg [31:0] blink_timer;
reg [1:0] change_blink_cnt;
reg [31:0] change_blink_timer;

// Debounced button signals and edge-detected pulses
wire btn_5yuan_db, btn_2yuan_db, btn_1yuan_db, btn_5jiao_db, btn_clear_db;
wire btn_5yuan_pulse, btn_2yuan_pulse, btn_1yuan_pulse, btn_5jiao_pulse, btn_clear_pulse;

// Instantiate debounce and edge-detect modules for each button
debounce #(.N(DEBOUNCE_CYCLES)) db_5yuan  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(BTNL), .out(btn_5yuan_db));
debounce #(.N(DEBOUNCE_CYCLES)) db_2yuan  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(BTNR), .out(btn_2yuan_db));
debounce #(.N(DEBOUNCE_CYCLES)) db_1yuan  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(BTNU), .out(btn_1yuan_db));
debounce #(.N(DEBOUNCE_CYCLES)) db_5jiao  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(BTND), .out(btn_5jiao_db));
debounce #(.N(DEBOUNCE_CYCLES)) db_clear  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(BTNC), .out(btn_clear_db));

edge_detect ed_5yuan  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(btn_5yuan_db),  .rise(btn_5yuan_pulse));
edge_detect ed_2yuan  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(btn_2yuan_db),  .rise(btn_2yuan_pulse));
edge_detect ed_1yuan  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(btn_1yuan_db),  .rise(btn_1yuan_pulse));
edge_detect ed_5jiao  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(btn_5jiao_db),  .rise(btn_5jiao_pulse));
edge_detect ed_clear  (.clk(CLK100MHZ), .rstn(CPU_RESETN), .in(btn_clear_db),  .rise(btn_clear_pulse));

// ========== Product selection mapping ==========
always @(*) begin
	// Map SW[2:0] to product index and price.
	// SW pattern -> product index (0..5) and current_price in jiao.
	// Default: product_sel = 7 indicates "no selection".
	case (SW[2:0])
		3'b001: begin product_sel = 3'd0; current_price = PRICE0; end // SW=001 -> Product 1
		3'b010: begin product_sel = 3'd1; current_price = PRICE1; end // SW=010 -> Product 2
		3'b011: begin product_sel = 3'd2; current_price = PRICE2; end // SW=011 -> Product 3
		3'b100: begin product_sel = 3'd3; current_price = PRICE3; end // SW=100 -> Product 4
		3'b101: begin product_sel = 3'd4; current_price = PRICE4; end // SW=101 -> Product 5
		3'b110: begin product_sel = 3'd5; current_price = PRICE5; end // SW=110 -> Product 6
		default: begin product_sel = 3'd7; current_price = 16'd0; end // No selection
	endcase
end

// ========== FSM state register ==========
always @(posedge CLK100MHZ or negedge CPU_RESETN) begin
	if (!CPU_RESETN) begin
		state <= S_IDLE;
	end else begin
		state <= next_state;
	end
end

// ========== FSM next-state logic ==========
always @(*) begin
	next_state = state;
	
	case (state)
		S_IDLE: begin
			// when a valid product is selected enter WAIT_COIN
			if (product_sel != 3'd7) begin
				next_state = S_WAIT_COIN;
			end
		end
		
		S_WAIT_COIN: begin
			// if selection cleared go back to idle
			if (product_sel == 3'd7) begin
				next_state = S_IDLE;
			// if enough balance and product not yet purchased, go to purchase
			end else if (balance >= current_price && !success_flags[product_sel]) begin
				next_state = S_PURCHASE;
			end
		end
		
		S_PURCHASE: begin
			// if change display active go to CHANGE state, otherwise back to WAIT_COIN
			if (change_display) begin
				next_state = S_CHANGE;
			end else begin
				next_state = S_WAIT_COIN;
			end
		end
		
		S_CHANGE: begin
			// wait until change_display completes, then return to WAIT_COIN or IDLE
			if (!change_display) begin
				if (product_sel != 3'd7) 
					next_state = S_WAIT_COIN;
				else 
					next_state = S_IDLE;
			end
		end
		
		default: next_state = S_IDLE;
	endcase
end

// ========== FSM outputs and internal updates ==========
always @(posedge CLK100MHZ or negedge CPU_RESETN) begin
	if (!CPU_RESETN) begin
		// reset internal state
		balance <= 16'd0;
		success_flags <= 6'b000000;
		blink_cnt <= 2'd0;
		blink_timer <= 26'd0;
		change_amount <= 16'd0;
		change_display <= 1'b0;
		change_blink_cnt <= 2'd0;
		change_blink_timer <= 26'd0;
	end else begin
		if (btn_clear_pulse) begin
			// Clear action: reset balance and flags immediately
			balance <= 16'd0;
			success_flags <= 6'b000000;
			blink_cnt <= 2'd0;
			blink_timer <= 26'd0;
			change_display <= 1'b0;
			change_amount <= 16'd0;
			change_blink_cnt <= 2'd0;
			change_blink_timer <= 26'd0;
		end else begin
			// Balance accumulation in WAIT_COIN
			if (state == S_WAIT_COIN) begin
				if (btn_5yuan_pulse)  balance <= balance + 16'd50;
				if (btn_2yuan_pulse)  balance <= balance + 16'd20;
				if (btn_1yuan_pulse)  balance <= balance + 16'd10;
				if (btn_5jiao_pulse)  balance <= balance + 16'd5;
			end

			// Purchase handling and change logic
			case (state)
				S_PURCHASE: begin
					if (!success_flags[product_sel]) begin
						success_flags[product_sel] <= 1'b1;
						blink_cnt <= 2'd3;
						blink_timer <= 26'd0;

						// Calculate change amount: change_amount = balance - current_price
						change_amount <= (balance >= current_price) ? (balance - current_price) : 16'd0;

						// Activate change display if balance > current_price
						if (balance > current_price) begin
							change_display <= 1'b1;
							change_blink_cnt <= 2'd3;   // 3 blinks for change display
							change_blink_timer <= 26'd0;
						end else begin
							change_display <= 1'b0;
							change_blink_cnt <= 2'd0;
							change_blink_timer <= 26'd0;
						end
					end
				end

				// S_CHANGE state: manage change display blinking
				default: ;
			endcase

			// Blink timer management for success LED indication
			if (blink_cnt > 0) begin
				if (blink_timer >= BLINK_INTERVAL) begin
					blink_timer <= 32'd0;
					blink_cnt <= blink_cnt - 1'd1;
				end else begin
					blink_timer <= blink_timer + 1'd1;
				end
			end

			// ======= Change display blinking logic =======
			if (change_display) begin
				if (change_blink_timer >= BLINK_INTERVAL - 1) begin
					// Toggle change display every BLINK_INTERVAL cycles
					change_blink_timer <= 32'd0;
					if (change_blink_cnt > 1) begin
						change_blink_cnt <= change_blink_cnt - 1'd1;
					end else begin
						change_blink_cnt <= 2'd0;
						change_display <= 1'b0;
						change_amount <= 16'd0;
					end
				end else begin
					change_blink_timer <= change_blink_timer + 1'd1;
				end
			end
		end
	end
end

// LED update logic: show blink phase or latched success flags
always @(posedge CLK100MHZ or negedge CPU_RESETN) begin
	if (!CPU_RESETN) begin
		LED <= 16'd0;
	end else begin
		// During blink period, show blanking pattern, else show success flags
		if (blink_cnt > 0 && blink_timer < BLINK_HALF) begin
			LED[5:0] <= 6'b000000; // Blanking
		end else begin
			LED[5:0] <= success_flags; // Show success flags
		end
		LED[15:6] <= 10'b0000000000;
	end
end

// 7-segment multiplexing control
reg [2:0] mux_idx;
reg [19:0] mux_cnt;
// digits array for 6 display positions (each 4-bit BCD)
reg [3:0] digits [0:5];

always @(posedge CLK100MHZ or negedge CPU_RESETN) begin
	if (!CPU_RESETN) begin
		mux_cnt <= 20'd0;
		mux_idx <= 3'd0;
	end else begin
		// multiplex counter: drive AN cycling at configured rate
		if (mux_cnt == 20'd0) begin
			mux_cnt <= 20'd6249; // 100MHz / 6250 = 16kHz
			mux_idx <= mux_idx + 1'd1;
		end else begin
			mux_cnt <= mux_cnt - 1'd1;
		end
	end
end

// digit extraction helper
function [3:0] get_digit;
	input [15:0] value;
	input [2:0] position; // 0=units, 1=tens, 2=hundreds, 3=thousands
	reg [15:0] temp;
	begin
		temp = value;
		case (position)
			3'd0: get_digit = temp % 10;
			3'd1: get_digit = (temp / 10) % 10;
			3'd2: get_digit = (temp / 100) % 10;
			3'd3: get_digit = (temp / 1000) % 10;
			default: get_digit = 4'd0;
		endcase
	end
endfunction

always @(*) begin
	// Choose digits to display: change_amount when change_display active, otherwise balance
	if (change_display) begin
		digits[0] = get_digit(change_amount, 3'd0);
		digits[1] = get_digit(change_amount, 3'd1);
		digits[2] = get_digit(change_amount, 3'd2);
		digits[3] = get_digit(change_amount, 3'd3);
	end else begin
		// Display balance digits
		digits[0] = get_digit(balance, 3'd0);
		digits[1] = get_digit(balance, 3'd1);
		digits[2] = get_digit(balance, 3'd2);
		digits[3] = get_digit(balance, 3'd3);
	end
	
	// Product selection display logic
	if (product_sel == 3'd7) begin
		digits[4] = 4'd0;
		digits[5] = 4'd0;
	end else begin
		digits[4] = (product_sel + 3'd1) % 10;
		digits[5] = (product_sel + 3'd1) / 10;
	end
end

// 7-seg segment assignment and AN control with change-display blink behavior
always @(*) begin
	// Decode digit values to 7-segment control signals
	case (mux_idx[2:0])
		3'd0: {CG,CF,CE,CD,CC,CB,CA} = encode_digit_func(digits[0]);
		3'd1: {CG,CF,CE,CD,CC,CB,CA} = encode_digit_func(digits[1]);
		3'd2: {CG,CF,CE,CD,CC,CB,CA} = encode_digit_func(digits[2]);
		3'd3: {CG,CF,CE,CD,CC,CB,CA} = encode_digit_func(digits[3]);
		3'd4: {CG,CF,CE,CD,CC,CB,CA} = (product_sel != 3'd7) ? encode_digit_func(digits[4]) : 7'b1111111;
		3'd5: {CG,CF,CE,CD,CC,CB,CA} = (product_sel != 3'd7) ? encode_digit_func(digits[5]) : 7'b1111111;
		default: {CG,CF,CE,CD,CC,CB,CA} = 7'b1111111;
	endcase

	DP = (mux_idx == 3'd1) ? 1'b0 : 1'b1;

	// AN control with change-display blink behavior
	case (mux_idx[2:0])
		3'd0: AN = (change_display && (change_blink_timer >= BLINK_HALF)) ? 8'hFF : 8'b11111110;
		3'd1: AN = (change_display && (change_blink_timer >= BLINK_HALF)) ? 8'hFF : 8'b11111101;
		3'd2: AN = (change_display && (change_blink_timer >= BLINK_HALF)) ? 8'hFF : 8'b11111011;
		3'd3: AN = (change_display && (change_blink_timer >= BLINK_HALF)) ? 8'hFF : 8'b11110111;
		3'd4: AN = (product_sel != 3'd7) ? 8'b11101111 : 8'hFF;
		3'd5: AN = (product_sel != 3'd7) ? 8'b11011111 : 8'hFF;
		default: AN = 8'hFF;
	endcase
end

// digit encoding function (unchanged)
function [6:0] encode_digit_func;
	input [3:0] val;
	begin
		case (val)
			4'h0: encode_digit_func = 7'b1000000;
			4'h1: encode_digit_func = 7'b1111001;
			4'h2: encode_digit_func = 7'b0100100;
			4'h3: encode_digit_func = 7'b0110000;
			4'h4: encode_digit_func = 7'b0011001;
			4'h5: encode_digit_func = 7'b0010010;
			4'h6: encode_digit_func = 7'b0000010;
			4'h7: encode_digit_func = 7'b1111000;
			4'h8: encode_digit_func = 7'b0000000;
			4'h9: encode_digit_func = 7'b0010000;
			default: encode_digit_func = 7'b1111111;
		endcase
	end
endfunction

task encode_digit(input [3:0] val);
	begin
		{CG,CF,CE,CD,CC,CB,CA} = encode_digit_func(val);
	end
endtask

endmodule

// Debounce module (synchronizer + stable counter)
module debounce #(parameter integer N = 2_000_000) (
	input  wire clk,
	input  wire rstn,
	input  wire in,
	output reg  out
);
	reg [31:0] cnt;
	reg sync0, sync1;
	
	always @(posedge clk or negedge rstn) begin
		if (!rstn) begin
			sync0 <= 1'b0;
			sync1 <= 1'b0;
			out <= 1'b0;
			cnt <= 32'd0;
		end else begin
			sync0 <= in;
			sync1 <= sync0;
			
			if (sync1 == out) begin
				cnt <= 32'd0;
			end else begin
				if (cnt >= N - 1) begin
					out <= sync1;
					cnt <= 32'd0;
				end else begin
					cnt <= cnt + 1'd1;
				end
			end
		end
	end
endmodule

// Edge-detect module (single-cycle rise pulse)
module edge_detect (
	input  wire clk,
	input  wire rstn,
	input  wire in,
	output reg  rise
);
	reg prev;
	
	always @(posedge clk or negedge rstn) begin
		if (!rstn) begin
			rise <= 1'b0;
			prev <= 1'b0;
		end else begin
			rise <= in & ~prev;
			prev <= in;
		end
	end
endmodule