import serial
import serial.tools.list_ports
import time

def send_measure_stage_code(port='COM7', baudrate=115200, timeout=1):
    """
    Opens the specified serial port, sends the Measure Stage code,
    and closes the port.
    """
    # The byte sequence to send
    data = bytes([0xc8, 0x8c, 0xff, 0xaa, 0x02, 0x00])

    try:
        # Open the serial port
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            print(f"Opened {port} at {baudrate} baud.")
            # Optionally, wait a moment for the device to be ready
            time.sleep(0.1)

            # Send the data
            bytes_written = ser.write(data)
            print(f"Sent {bytes_written} bytes: {data.hex().upper()}")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    send_measure_stage_code(port='COM7', baudrate=921600)
