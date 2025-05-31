# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers  import FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.triggers import Timer
from cocotb.triggers import with_timeout
from cocotb.types import Logic
from cocotb.types import LogicArray
from cocotb.utils import get_sim_time
from cocotb.result import SimTimeoutError, TestFailure


async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)
@cocotb.test()
async def test_pwm_freq(dut):
    #setup
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut.ena.value = 1

    dut.ui_in.value = ui_in_logicarray(1, 0, 0)

    await send_spi_transaction(dut, 1, 0x02, 1)

    #set 50% duty
    await send_spi_transaction(dut, 1, 0x04, 128)

    await ClockCycles(dut.clk, 7000)

    pwm_sig = dut.uo_out[0]
    
    #timeout error
    period_expected = 1e9/3000
    timeout = int(period_expected*2)

    try:
        await with_timeout(RisingEdge(pwm_sig), timeout, "ns")
    except SimTimeoutError:
        level = int(pwm_sig.value)
        raise TestFailure(f"No rising edge within {timeout} ns; line stuck at {level}")

    t1 = get_sim_time("ns")
    await RisingEdge(pwm_sig)
    t2 = get_sim_time("ns")

    period_ns = t2 - t1
    freq_hz   = 1e9 / period_ns
    assert 2970 <= freq_hz <= 3030, f"Measured {freq_hz:.1f} Hz; expected 3000 Hz ±1%"

    dut._log.info(f"PWM freq OK: {freq_hz:.1f} Hz")



@cocotb.test()
async def test_pwm_duty(dut):
    #setup
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut.ena.value = 1
    
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    await send_spi_transaction(dut, 1, 0x02, 1)

    pwm_sig = dut.uo_out[0]

    #50%
    await send_spi_transaction(dut, 1, 0x04, 128)
    
    #wait
    await ClockCycles(dut.clk, 7000)
   
   #timeout error
    period_expected = 1e9/3000
    timeout = int(period_expected*2)
    try:
        await with_timeout(RisingEdge(pwm_sig), timeout, "ns")
    except SimTimeoutError:
        level = int(pwm_sig.value)
        raise TestFailure(f"No rising edge within {timeout} ns; line stuck at {level}")
    
    t_r = get_sim_time("ns")
    await FallingEdge(pwm_sig)
    t_f = get_sim_time("ns")
    await RisingEdge(pwm_sig)
    t_n = get_sim_time("ns")
    high_ns = t_f - t_r
    period_ns = t_n - t_r
    duty = 100 * high_ns / period_ns
    assert 49 <= duty <= 51, f"50%: measured {duty:.1f}%, 50 +- 1%"

    # 0%
    await send_spi_transaction(dut, 1, 0x04, 0)
    await ClockCycles(dut.clk, 7000)
    for _ in range(10):
        await ClockCycles(dut.clk, 100)
        assert int(pwm_sig.value) == 0, f"0%: saw {int(pwm_sig.value)}, expected always 0"

    # 100%
    await send_spi_transaction(dut, 1, 0x04, 255)
    await ClockCycles(dut.clk, 7000)
    for _ in range(10):
        await ClockCycles(dut.clk, 100)
        assert int(pwm_sig.value) == 1, f"100%: saw {int(pwm_sig.value)}, expected always 1"

    dut._log.info("PWM duty-cycle tests passed")