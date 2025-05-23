module pwm_peripheral(
input wire SCLK,
input wire rst_n,
input wire COPI,
input wire nCS,
input wire clk,

output reg [7:0] reg_out_7_0,
output reg [7:0] reg_out_15_8,
output reg [7:0] reg_pwm_7_0,
output reg [7:0] reg_pwm_15_8,
output reg [7:0] pwm_duty_cycle
);
reg [2:0] sync_COPI, sync_SCLK, sync_nCS;
reg [4:0] bit_counter;
reg [14:0] shift_reg;
reg prev_SCLK;
reg prev_nCS;


//reg transaction_ready;
reg R_W;
reg [7:0] max_address = 4;
reg [7:0] address;
wire clean_SCLK = sync_SCLK[2];
wire sclk_rising  =  clean_SCLK & ~prev_SCLK;
//wire sclk_falling = ~clean_SCLK &  prev_SCLK;
wire cs_rising =  sync_nCS[2] && ~prev_nCS;

always @(posedge clk or negedge rst_n) begin
	if (~rst_n) begin
		sync_COPI <= 3'b000;
		sync_SCLK <= 3'b000;
		sync_nCS  <= 3'b111;
		prev_SCLK <= 1'b0;
		bit_counter <= 5'd0;
		shift_reg   <= 15'd0;
		address     <= 8'd0;
		reg_out_7_0    <= 8'd0;
		reg_out_15_8   <= 8'd0;
		reg_pwm_7_0    <= 8'd0;
		reg_pwm_15_8   <= 8'd0;
		pwm_duty_cycle <= 8'd0;
		R_W <= 1'b0;
	end else begin
		prev_SCLK <= sync_SCLK[2];
		prev_nCS <= sync_nCS[2];
		sync_SCLK <= { sync_SCLK[1:0],SCLK};
		sync_COPI <= { sync_COPI[1:0],COPI};
		sync_nCS  <= { sync_nCS[1:0],nCS};
		if (sync_nCS[2] == 1'b0 && bit_counter < 5'd16) begin 
			if (sclk_rising) begin
				if (bit_counter == 0) begin
   					R_W <= sync_COPI[2];
				end else begin 
					if (R_W) begin 
						shift_reg <= {shift_reg[13:0], sync_COPI[2]};
					end
				end
				bit_counter <= bit_counter + 1;
			end 
		end else if(cs_rising && R_W) begin
			address <= shift_reg[14:8];
			if (address <= max_address)begin
			//transaction_ready <= 1;
				case (address)
					3'd0: reg_out_7_0    <= shift_reg[7:0];
					3'd1: reg_out_15_8   <= shift_reg[7:0];
					3'd2: reg_pwm_7_0    <= shift_reg[7:0];
					3'd3: reg_pwm_15_8   <= shift_reg[7:0];
					3'd4: pwm_duty_cycle <= shift_reg[7:0];
				endcase
			end
			bit_counter <= 5'd0;
  			shift_reg <= 15'd0;
		end
	end

end

endmodule
