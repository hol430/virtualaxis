#!/usr/bin/env python

import evdev
from evdev import InputDevice, UInput, ecodes as e, AbsInfo

# Replace this with the actual eventX of your pedals
pedals_path = "/dev/input/by-id/usb-Thrustmaster_T-Rudder_00000000001A-event-if00"

# Open the input device
pedals = InputDevice(pedals_path)

# Set up the virtual joystick
capabilities = {
    e.EV_ABS: {
        e.ABS_X: AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=1),
        e.ABS_Y: AbsInfo(value=0, min=-512, max=511, fuzz=0, flat=0, resolution=1),
    },
    e.EV_KEY: [
        e.BTN_TRIGGER
    ],
    e.EV_SYN: [],
}

virtual_joystick = UInput(events=capabilities, name="VirtualJoystick", bustype=e.BUS_USB)
print(f"Virtual joystick created: {virtual_joystick.device}")

# Normalize a value to -32768 to 32767 range
def normalize(value, min_val, max_val, ymin = -32768, ymax = 32767):
    yrange = (ymax - ymin)
    return int((value - min_val) / (max_val - min_val) * yrange + ymin)

# Read and combine axes
left_value = 0
right_value = 0
rudder_value = 0
try:
    for event in pedals.read_loop():
        if event.type == e.EV_ABS:
            if event.code == e.ABS_X:  # Left toe brake
                left_value = -normalize(event.value, 0, 1023)
            elif event.code == e.ABS_Y:  # Right toe brake
                right_value = normalize(event.value, 0, 1023)
            elif event.code == e.ABS_Z: # rudders
                rudder_value = normalize(event.value, 0, 1023, -512, 511)
                virtual_joystick.write(e.EV_ABS, e.ABS_Y, rudder_value)
                virtual_joystick.syn()
                continue

            # Combine the two axes (average them)
            combined_value = (left_value + right_value) // 2

            # Send the combined value to the virtual joystick
            virtual_joystick.write(e.EV_ABS, e.ABS_X, combined_value)
            virtual_joystick.syn()

except KeyboardInterrupt:
    print("Exiting...")
    virtual_joystick.close()
