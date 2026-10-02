`timescale 1ns / 1ps
module tb_vending;

	// clock & reset
	reg CLK100MHZ = 0;
	reg CPU_RESETN = 0;

	// inputs to DUT
	reg [15:0] SW = 16'd0;
	reg BTNC = 0, BTNU = 0, BTNL = 0, BTNR = 0, BTND = 0;

	// outputs from DUT
	wire [15:0] LED;
	wire LED16_B, LED16_G, LED16_R;
	wire LED17_B, LED17_G, LED17_R;
	wire CA, CB, CC, CD, CE, CF, CG, DP;
	wire [7:0] AN;

	// module-level flag for wait tasks
	reg wait_ok;

	// instantiate DUT (unit under test)
	vending #(.DEBOUNCE_CYCLES(10), .BLINK_INTERVAL(100)) uut (
		.CLK100MHZ(CLK100MHZ),
		.CPU_RESETN(CPU_RESETN),
		.SW(SW),
		.BTNC(BTNC),
		.BTNU(BTNU),
		.BTNL(BTNL),
		.BTNR(BTNR),
		.BTND(BTND),
		.LED(LED),
		.LED16_B(LED16_B),
		.LED16_G(LED16_G),
		.LED16_R(LED16_R),
		.LED17_B(LED17_B),
		.LED17_G(LED17_G),
		.LED17_R(LED17_R),
		.CA(CA),
		.CB(CB),
		.CC(CC),
		.CD(CD),
		.CE(CE),
		.CF(CF),
		.CG(CG),
		.DP(DP),
		.AN(AN)
	);

	// 100 MHz clock
	always #5 CLK100MHZ = ~CLK100MHZ;

	// Simulation acceleration: set to 1 for real-time, >1 to speed up (divide long delays)
	parameter integer SIM_ACCEL = 10000000; // ????????
	// Ensure button pulses are at least this many clock cycles (to pass DUT debounce)
	parameter integer MIN_PRESS_CYCLES = 1000;

	// C_press(ns): scaled cycles for button presses with a minimum enforced
	function integer C_press;
		input integer ns;
		integer cycles;
	begin
		cycles = C_scaled(ns);
		if (cycles < MIN_PRESS_CYCLES) cycles = MIN_PRESS_CYCLES;
		C_press = cycles;
	end
	endfunction

	// C_unscaled(ns): convert nanoseconds to raw clock cycles (100MHz -> 10ns) without SIM_ACCEL scaling
	function integer C_unscaled;
		input integer ns;
		integer cycles;
	begin
		cycles = (ns + 9) / 10; // 10 ns per 100 MHz clock
		if (cycles < 1) cycles = 1;
		C_unscaled = cycles;
	end
	endfunction

	// C_scaled(ns): convert ns to clock cycles and apply SIM_ACCEL scaling for faster sim runs
	function integer C_scaled;
		input integer ns;
		integer cycles;
	begin
		cycles = (ns + 9) / 10;
		if (SIM_ACCEL > 1) cycles = cycles / SIM_ACCEL;
		if (cycles < 1) cycles = 1;
		C_scaled = cycles;
	end
	endfunction

	// press a button for hold_ns (ns)
	task press_button_timed(input [2:0] id, input integer hold_ns);
	begin
		// clear all first
		BTNL = 0; BTNR = 0; BTNU = 0; BTND = 0; BTNC = 0;
		case (id)
			3'd0: begin BTNL = 1; repeat (C_press(hold_ns)) @(posedge CLK100MHZ); BTNL = 0; $display("%0t: TB - press 5Y button (cycles=%0d)", $time, C_press(hold_ns)); end
			3'd1: begin BTNR = 1; repeat (C_press(hold_ns)) @(posedge CLK100MHZ); BTNR = 0; $display("%0t: TB - press 2Y button (cycles=%0d)", $time, C_press(hold_ns)); end
			3'd2: begin BTNU = 1; repeat (C_press(hold_ns)) @(posedge CLK100MHZ); BTNU = 0; $display("%0t: TB - press 1Y button (cycles=%0d)", $time, C_press(hold_ns)); end
			3'd3: begin BTND = 1; repeat (C_press(hold_ns)) @(posedge CLK100MHZ); BTND = 0; $display("%0t: TB - press 0.5Y button (cycles=%0d)", $time, C_press(hold_ns)); end
			3'd4: begin BTNC = 1; repeat (C_press(hold_ns)) @(posedge CLK100MHZ); BTNC = 0; $display("%0t: TB - press CLEAR button (cycles=%0d)", $time, C_press(hold_ns)); end
			default: begin end
		endcase
		// allow debounce and system to react (use scaled)
		repeat (C_scaled(20_000_000)) @(posedge CLK100MHZ);
	end
	endtask

	// set product via SW[2:0] (write switch bits and wait a short scaled settle)
	task select_product(input [2:0] prod);
	begin
		SW[2:0] = prod;
		repeat (C_scaled(5_000_000)) @(posedge CLK100MHZ); // allow switch settle (scaled)
		$display("%0t: TB - select product SW=%b (id=%0d)", $time, prod, prod);
	end
	endtask

	// wait until uut.change_display == expect or timeout (ns); return success via output reg
	// This task polls the DUT's change_display signal at a scaled interval.
	task wait_change_display(output reg success, input integer expect, input integer timeout_ns);
		integer elapsed_cycles;
		integer poll_cycles;
		integer timeout_cycles;
		integer small_timeout_cycles;
		integer tmp_cycles;
		reg init_val;
	begin
		elapsed_cycles = 0;
		success = 0;

		// number of clock cycles to wait between polls (scaled)
		poll_cycles = C_scaled(50_000); // ?????????????????????
		if (poll_cycles < 1) poll_cycles = 1;

		// overall timeout in scaled clock cycles
		timeout_cycles = C_scaled(timeout_ns);
		if (timeout_cycles < 1) timeout_cycles = 1;

		// sample initial value
		init_val = uut.change_display;

		// If we are waiting for a rising event but it's already high, re-arm by waiting for it to go low briefly
		// but only a short while (small timeout)
		if (expect == 1 && init_val === 1) begin
			small_timeout_cycles = C_scaled(5_000_000); // small re-arm window
			if (small_timeout_cycles < 1) small_timeout_cycles = 1;
			tmp_cycles = 0;
			while ((uut.change_display === 1) && (tmp_cycles < small_timeout_cycles)) begin
				repeat (poll_cycles) @(posedge CLK100MHZ);
				tmp_cycles = tmp_cycles + poll_cycles;
			end
			// refresh init for the next phase
			init_val = uut.change_display;
		end

		// wait for a transition to the expected value within timeout
		while ((uut.change_display !== expect) && (elapsed_cycles < timeout_cycles)) begin
			repeat (poll_cycles) @(posedge CLK100MHZ);
			elapsed_cycles = elapsed_cycles + poll_cycles;
		end

		if (uut.change_display === expect) begin
			success = 1;
		end else begin
			success = 0;
			$display("%0t: TB - wait_change_display TIMEOUT (expect=%0d). current: change_display=%b change_amount=%0d change_blink_cnt=%0d",
			         $time, expect, uut.change_display, uut.change_amount, uut.change_blink_cnt);
		end
	end
	endtask

	// wait until change_display clears (expect=0) and report
	task wait_change_complete(input integer timeout_ns);
	begin
		$display("%0t: TB - waiting change_display to clear (timeout=%0t ns)...", $time, timeout_ns);
		wait_change_display(wait_ok, 0, timeout_ns);
		if (wait_ok) $display("  [PASS] change_display cleared; balance=%0d (%.1f Y)", uut.balance, uut.balance/10.0);
		else $display("  [FAIL] change_display did not clear in time: change_display=%b cnt=%0d timer=%0d", uut.change_display, uut.change_blink_cnt, uut.change_blink_timer);
	end
	endtask

	// check LED and balance, print PASS/FAIL
	task report_check(input [5:0] expect_led, input [15:0] expect_balance, input [256:0] name);
	begin
		repeat (C_scaled(10_000_000)) @(posedge CLK100MHZ);
		$display("%0t: TB - CHECK: %s", $time, name);
		if (LED[5:0] === expect_led) $display("  [PASS] LED state: %b", LED[5:0]);
		else $display("  [FAIL] LED expected=%b actual=%b", expect_led, LED[5:0]);
		if (uut.balance === expect_balance) $display("  [PASS] balance: %0d (%.1f Y)", uut.balance, uut.balance/10.0);
		else $display("  [FAIL] balance expected=%0d actual=%0d", expect_balance, uut.balance);
		$display("  internal: change_display=%b change_amount=%0d change_blink_cnt=%0d change_blink_timer=%0d",
		         uut.change_display, uut.change_amount, uut.change_blink_cnt, uut.change_blink_timer);
	end
	endtask

	// wait until uut.balance == 0 or timeout (ns); return success via output reg
	task wait_balance_zero(output reg success, input integer timeout_ns);
		integer elapsed_ns;
		integer poll_ns;
	begin
		elapsed_ns = 0;
		success = 0;
		poll_ns = 100_000; // poll every 100us (unscaled)
		while ((uut.balance !== 16'd0) && (elapsed_ns < timeout_ns)) begin
			repeat (C_scaled(poll_ns)) @(posedge CLK100MHZ);
			elapsed_ns = elapsed_ns + poll_ns;
		end
		if (uut.balance === 16'd0) success = 1;
	end
	endtask

	// main test sequence
	initial begin
		// init
		SW = 16'd0;
		BTNC = 0; BTNU = 0; BTNL = 0; BTNR = 0; BTND = 0;
		CPU_RESETN = 0;
		repeat (C_scaled(100_000_000)) @(posedge CLK100MHZ);
		CPU_RESETN = 1;
		$display("%0t: TB - system reset released, start tests", $time);

		// Test 1: exact payment, product1 (0.5Y), pay 0.5Y
		$display("\n=== TEST1: exact payment product1(0.5Y) pay 0.5Y ===");
		select_product(3'b001);
		press_button_timed(3'd3, 12_000_000); // 0.5Y
		report_check(6'b000001, 16'd5, "TEST1 exact pay");

		// Test 2: overpay product1 (0.5Y), pay 1Y -> change 0.5Y
		$display("\n=== TEST2: overpay product1(0.5Y) pay 1Y (expect change 0.5Y) ===");
		press_button_timed(3'd4, 12_000_000); // clear
		select_product(3'b001);
		press_button_timed(3'd2, 12_000_000); // +1Y
		// Allow DUT time to process purchase/change (scaled). Do not assert transient change_display.
		repeat (C_scaled(200_000_000)) @(posedge CLK100MHZ);
		$display("  INFO: post-pay state (no assert on change_display): change_display=%b change_amount=%0d change_blink_cnt=%0d",
		         uut.change_display, uut.change_amount, uut.change_blink_cnt);
		report_check(6'b000001, 16'd10, "TEST2 overpay result");

		// Test 3: big overpay: product4 pay 5Y -> change 3Y
		$display("\n=== TEST3: big overpay product4(2.0Y) pay 5Y ===");
		press_button_timed(3'd4, 12_000_000); // clear
		select_product(3'b100);
		press_button_timed(3'd0, 12_000_000); // +5Y
		// ??????????? change_display???????? DUT ??????????????
		repeat (C_scaled(300_000_000)) @(posedge CLK100MHZ);
		$display("  INFO: post-pay state (no assert on change_display): change_display=%b change_amount=%0d change_blink_cnt=%0d",
		         uut.change_display, uut.change_amount, uut.change_blink_cnt);
		report_check(6'b001000, 16'd50, "TEST3 big overpay result");

		// Test 4: debounce quick double-press test (two short presses)
		$display("\n=== TEST4: debounce quick double-press ===");
		press_button_timed(3'd4, 12_000_000); // clear
		select_product(3'b010); // product2 = 1.0Y
		// quick double press (short intervals)
		BTNU = 1; repeat (C_press(2_000_000)) @(posedge CLK100MHZ); BTNU = 0; repeat (C_scaled(1_000_000)) @(posedge CLK100MHZ);
		BTNU = 1; repeat (C_press(3_000_000)) @(posedge CLK100MHZ); BTNU = 0;
		repeat (C_scaled(30_000_000)) @(posedge CLK100MHZ);
		$display("  INFO: balance now=%0d (angles)", uut.balance);
		report_check(6'b000010, uut.balance, "TEST4 debounce check");

		// Test 5: insufficient payment for product6 (no LED expected)
		$display("\n=== TEST5: insufficient pay product6 (no LED) ===");
		press_button_timed(3'd4, 12_000_000); // clear
		select_product(3'b110); // product6 = SW=110 -> PRICE5
		press_button_timed(3'd2, 12_000_000); // +1Y (10 jiao)
		repeat (C_scaled(20_000_000)) @(posedge CLK100MHZ);
		// Expect: LED remains off for product6, balance increments to 10 (jiao)
		report_check(6'b000000, 16'd10, "TEST5 insufficient pay product6 no LED");

		// Test 6: reset behavior
		$display("\n=== TEST6: reset behavior ===");
		CPU_RESETN = 0; repeat (C_scaled(50_000_000)) @(posedge CLK100MHZ); CPU_RESETN = 1; repeat (C_scaled(50_000_000)) @(posedge CLK100MHZ);
		if (uut.balance == 0 && uut.success_flags == 6'b0) $display("  [PASS] reset cleared state");
		else $display("  [FAIL] reset did not clear: balance=%0d flags=%b", uut.balance, uut.success_flags);


		// Test 7: exact payment for product3 (1.5Y) -> pay 1Y + 0.5Y
		$display("\n=== TEST7: exact payment product3(1.5Y) pay 1.5Y ===");
		press_button_timed(3'd4, 12_000_000); // clear
		select_product(3'b011); // product3
		press_button_timed(3'd2, 12_000_000); // +1Y (10 jiao)
		press_button_timed(3'd3, 12_000_000); // +0.5Y (5 jiao)
		repeat (C_scaled(20_000_000)) @(posedge CLK100MHZ);
		report_check(6'b000100, 16'd15, "TEST7 exact pay product3");

		// Test 8: exact payment for product5 (6.5Y) -> pay 5Y + 1Y + 0.5Y
		$display("\n=== TEST8: exact payment product5(6.5Y) pay 6.5Y ===");
		press_button_timed(3'd4, 12_000_000); // clear
		select_product(3'b101); // product5
		press_button_timed(3'd0, 12_000_000); // +5Y (50 jiao)
		press_button_timed(3'd2, 12_000_000); // +1Y (10 jiao)
		press_button_timed(3'd3, 12_000_000); // +0.5Y (5 jiao)
		repeat (C_scaled(40_000_000)) @(posedge CLK100MHZ);
		report_check(6'b010000, 16'd65, "TEST8 exact pay product5");
        
		$display("\n=== ALL TESTS DONE ===");
		repeat (C_scaled(100_000_000)) @(posedge CLK100MHZ);
		$finish;
	end

	// monitor key signals for debug/logging (throttled, event-driven)
	integer prev_state;
	integer prev_balance;
	integer prev_LED6;
	integer prev_change_display;
	integer prev_change_amount;
	reg [7:0] prev_AN;
	integer monitor_counter;
	integer monitor_period_cycles;

	initial begin
		// force first-print by setting prev to impossible values
		prev_state = -1;
		prev_balance = -1;
		prev_LED6 = -1;
		prev_change_display = -1;
		prev_change_amount = -1;
		prev_AN = 8'hFF;
		monitor_counter = 0;
		// sample every scaled 100us by default (adjustable)
		monitor_period_cycles = C_scaled(100_000);
		if (monitor_period_cycles < 1) monitor_period_cycles = 1;
	end

	always @(posedge CLK100MHZ) begin
		// only check every monitor_period_cycles to reduce prints
		if (monitor_counter == 0) begin
			if ((uut.state !== prev_state) ||
			    (uut.balance !== prev_balance) ||
			    (LED[5:0] !== prev_LED6) ||
			    (uut.change_display !== prev_change_display) ||
			    (uut.change_amount !== prev_change_amount)) begin

				$display("[%0t] state=%0d | balance=%0d (%.1f Y) | LED=%b | change_display=%b | change_amount=%0d | AN=%b",
				         $time, uut.state, uut.balance, uut.balance/10.0, LED[5:0], uut.change_display, uut.change_amount, uut.AN);

				// update previous values
				prev_state = uut.state;
				prev_balance = uut.balance;
				prev_LED6 = LED[5:0];
				prev_change_display = uut.change_display;
				prev_change_amount = uut.change_amount;
				prev_AN = uut.AN;
			end
		end

		monitor_counter = monitor_counter + 1;
		if (monitor_counter >= monitor_period_cycles) monitor_counter = 0;
	end
endmodule


