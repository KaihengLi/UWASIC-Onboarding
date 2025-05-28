/*
 * Copyright (c) 2024 Henry Li
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
module tt_um_onboarding_HenryLi (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: input path
    output wire [7:0] uio_out,  // IOs: output path
    output wire [7:0] uio_oe,   // IOs: enable (1=output)
    input  wire       ena,      // ignore
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
  assign uio_oe = 8'hFF;

  wire [7:0] en_reg_out_7_0;
  wire [7:0] en_reg_out_15_8;
  wire [7:0] en_reg_pwm_7_0;
  wire [7:0] en_reg_pwm_15_8;
  wire [7:0] pwm_duty_cycle;

  

  spi_peripheral spi_peripheral_inst (
	.clk(clk),
    .rst_n(rst_n),
	.SCLK(ui_in[0]),
    .COPI(ui_in[1]),
    .nCS(ui_in[2]),
    .en_reg_out_7_0(en_reg_out_7_0),
    .en_reg_out_15_8(en_reg_out_15_8),
    .en_reg_pwm_7_0(en_reg_pwm_7_0),
    .en_reg_pwm_15_8(en_reg_pwm_15_8),
    .pwm_duty_cycle(pwm_duty_cycle)

  );

  pwm_peripheral pwm_peripheral_inst (
	.clk(clk),
	.rst_n(rst_n),
	.en_reg_out_7_0(en_reg_out_7_0),
	.en_reg_out_15_8(en_reg_out_15_8),
	.en_reg_pwm_7_0(en_reg_pwm_7_0),
	.en_reg_pwm_15_8(en_reg_pwm_15_8),
	.pwm_duty_cycle(pwm_duty_cycle),
	.out({uio_out, uo_out})
  );
  wire _unused = &{ena, ui_in[7:3], uio_in, 1'b0};

endmodule