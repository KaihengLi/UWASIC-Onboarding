module spi_peripheral(
	input wire SCLK,
	input wire rst_n,
	input wire COPI,
	input wire nCS,
	input wire clk,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);
reg [2:0] sync_COPI, sync_SCLK, sync_nCS;
//reg prev_SCLK, prev_nCS;

reg [4:0] bit_counter;
reg [14:0] shift_reg;
//reg transaction_ready;
reg R_W;
localparam max_address = 8'd4;
reg [6:0] address;

wire filter_SCLK = sync_SCLK[2];
wire sclk_rising = sync_SCLK[2] & ~sync_SCLK[1];
//wire sclk_falling = ~filter_SCLK &  prev_SCLK;
wire cs_rising  = sync_nCS[2] & ~sync_nCS[1];
wire cs_falling = ~sync_nCS[2] & sync_nCS[1];

always @(posedge clk or negedge rst_n) begin
	if (~rst_n) begin
		sync_COPI <= 3'b000;
		sync_SCLK <= 3'b000;
		sync_nCS  <= 3'b111;
		prev_SCLK <= 1'b0;
		address <= 8'd0;
		prev_nCS <= 1'b1;

		bit_counter <= 5'd0;
		shift_reg <= 15'd0;
		R_W <= 1'b0;
		
		//clear registers
		en_reg_out_7_0    <= 8'd0;
		en_reg_out_15_8   <= 8'd0;
		en_reg_pwm_7_0    <= 8'd0;
		en_reg_pwm_15_8   <= 8'd0;
		pwm_duty_cycle <= 8'd0;
	end else begin

		prev_SCLK <= sync_SCLK[2];
		prev_nCS <= sync_nCS[2];
		sync_SCLK <= { sync_SCLK[1:0],SCLK};
		sync_COPI <= { sync_COPI[1:0],COPI};
		sync_nCS  <= { sync_nCS[1:0],nCS};
		if (cs_falling) begin
			bit_counter <= 5'd0;
			shift_reg   <= 15'd0;
			R_W         <= 1'b0;
        end else if (sync_nCS[2]==1'b0 && bit_counter < 5'd16) begin
			if (sclk_rising) begin
				if (bit_counter == 0) begin
					R_W <= sync_COPI[2];
				end else begin
					if (R_W) begin
						shift_reg <= { shift_reg[14:0], sync_COPI[2] };
					end
				end
				bit_counter <= bit_counter + 1;
			end
        end else if(cs_rising && R_W && bit_counter == 5'd16) begin
			address <= shift_reg[14:8];
			if (address <= max_address)begin
				//transaction_ready <= 1;
				case (address)
					4'd0: en_reg_out_7_0 <= shift_reg[7:0];
					4'd1: en_reg_out_15_8 <= shift_reg[7:0];
					4'd2: en_reg_pwm_7_0 <= shift_reg[7:0];
					4'd3: en_reg_pwm_15_8 <= shift_reg[7:0];
					4'd4: pwm_duty_cycle <= shift_reg[7:0];
					default:;
				endcase
			end
			bit_counter <= 5'd0;
            shift_reg   <= 15'd0;
			R_W <= 1'b0;
		end
	end

end

endmodule