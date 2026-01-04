#!/usr/bin/env python

import select

from evdev import InputDevice, UInput, ecodes as e

joystick_path = "/dev/input/event17"

def open_input_device(path: str) -> InputDevice:
    """Open an evdev input device and reject non-evdev joystick nodes."""

    if path.startswith("/dev/input/js"):
        raise ValueError(
            f"{path} is a legacy joystick node. Use an evdev event device "
            "path like /dev/input/eventX or /dev/input/by-id/*-event-*."
        )

    return InputDevice(path)


def uinput_events_from_device(device: InputDevice) -> dict:
    """Convert an evdev device's capabilities into a UInput events dict."""

    device_caps = device.capabilities(absinfo=True)
    uinput_caps = {}

    abs_caps = device_caps.get(e.EV_ABS)
    if abs_caps is not None:
        abs_map = {}
        for abs_code, abs_info in abs_caps:
            abs_map[abs_code] = abs_info
        uinput_caps[e.EV_ABS] = abs_map

    key_caps = device_caps.get(e.EV_KEY)
    if key_caps is not None:
        uinput_caps[e.EV_KEY] = list(key_caps)

    rel_caps = device_caps.get(e.EV_REL)
    if rel_caps is not None:
        uinput_caps[e.EV_REL] = list(rel_caps)

    uinput_caps[e.EV_SYN] = []
    return uinput_caps


def first_button_code(device: InputDevice) -> int | None:
    """Return the first button keycode exposed by the device, if any."""

    key_caps = device.capabilities().get(e.EV_KEY, [])
    button_codes = [code for code in key_caps if code >= e.BTN_MISC]
    if len(button_codes) == 0:
        return None

    return sorted(button_codes)[0]


def main() -> None:
    """Mirror an input joystick into a virtual joystick and remap button 1."""

    joystick = open_input_device(joystick_path)

    virtual_joystick = UInput(
        events=uinput_events_from_device(joystick),
        name="VirtualJoystickRemapped",
        bustype=e.BUS_USB,
    )
    print(f"Virtual joystick created: {virtual_joystick.device}")

    virtual_keyboard = UInput(
        events={
            e.EV_KEY: [e.KEY_RIGHTCTRL],
            e.EV_SYN: [],
        },
        name="VirtualJoystickKeyboardRemapped",
        bustype=e.BUS_USB,
    )
    print(f"Virtual keyboard created: {virtual_keyboard.device}")

    button_1 = first_button_code(joystick)
    if button_1 is None:
        raise RuntimeError("No joystick buttons detected to use as button 1")

    print(
        "Remapping joystick button 1 "
        f"(keycode={button_1}) to KEY_RIGHTCTRL"
    )

    try:
        while True:
            ready, _, _ = select.select([joystick], [], [])
            for device in ready:
                for event in device.read():
                    if event.type == e.EV_KEY and event.code == button_1:
                        virtual_keyboard.write(
                            e.EV_KEY, e.KEY_RIGHTCTRL, event.value
                        )
                        virtual_keyboard.syn()
                        continue

                    if event.type in (e.EV_ABS, e.EV_KEY, e.EV_REL):
                        virtual_joystick.write(event.type, event.code, event.value)
                        virtual_joystick.syn()

    except KeyboardInterrupt:
        print("Exiting...")
        virtual_keyboard.close()
        virtual_joystick.close()


if __name__ == "__main__":
    main()
