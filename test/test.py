# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.types import LogicArray
from cocotb.utils import get_sim_time
from cocotb.result import TestFailure


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
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior - SPI")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

async def wait_for_level(dut, desired_level, max_cycles=5000):
    for _ in range(max_cycles):
        await ClockCycles(dut.clk, 1)
        bit0 = int(dut.uo_out.value) & 1
        if bit0 == desired_level:
            return get_sim_time("ns")
    stuck = (int(dut.uo_out.value) & 1)
    raise TestFailure(f"Timeout: PWM never reached {desired_level}; stuck at {stuck} after {max_cycles} cycles")

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

    #pwm_sig = dut.uo_out[0]

    t1 = await wait_for_level(dut,1,max_cycles=5000)
    tf = await wait_for_level(dut,0,max_cycles=5000)
    t2 = await wait_for_level(dut,1,max_cycles=5000)

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
    
    t1 = await wait_for_level(dut,1,max_cycles=5000)
    tf = await wait_for_level(dut,0,max_cycles=5000)
    t2 = await wait_for_level(dut,1,max_cycles=5000)

    high_ns = tf - t1
    period_ns = t2 - t1
    duty = 100 * high_ns / period_ns
    assert 49 <= duty <= 51, f"50%: measured {duty:.1f}%, outside of 50 +- 1%"

    # 0%
    await send_spi_transaction(dut, 1, 0x04, 0)
    await ClockCycles(dut.clk, 7000)
    assert int(pwm_sig.value) == 0, f"0%: saw {int(pwm_sig.value)}, expected always 0"

    # 100%
    await send_spi_transaction(dut, 1, 0x04, 255)
    await ClockCycles(dut.clk, 7000)
    assert int(pwm_sig.value) == 1, f"100%: saw {int(pwm_sig.value)}, expected always 1"

    dut._log.info("PWM duty-cycle tests passed")