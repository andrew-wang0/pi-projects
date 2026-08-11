# Picture hardware wiring guide

This guide covers the `picture` app on a Raspberry Pi 3 Model A+ with:

- Raspberry Pi Camera Module 3 Wide
- 7-inch DSI display
- one capture button
- one small pattern LED
- a 12 V non-addressable LED strip
- a 3.3 V-compatible PWM MOSFET controller
- a regulated 5 V-to-12 V boost converter

The GPIO assignments match the defaults in `config.py`.

## Pin summary

Software settings use **BCM GPIO numbers**. Physical pin numbers identify
positions on the Pi's 40-pin header.

| Function              | BCM GPIO | Physical pin | Connection                       |
| --------------------- | -------: | -----------: | -------------------------------- |
| Capture button input  |   GPIO17 |           11 | One side of capture button       |
| Capture button ground |      GND |            9 | Other side of capture button     |
| LED-strip PWM output  |   GPIO18 |           12 | MOSFET controller PWM/input      |
| PWM signal ground     |      GND |           14 | MOSFET controller signal ground  |
| Small pattern LED     |   GPIO12 |           32 | 330 ohm resistor, then LED anode |
| Pattern LED ground    |      GND |           30 | LED cathode                      |

Use these exact physical-header connections:

```text
Capture button:
  physical pin 11 (GPIO17) ---- button ---- physical pin 9 (GND)

MOSFET controller signal:
  physical pin 12 (GPIO18/PWM0) ---------- controller PWM/input
  physical pin 14 (GND) ------------------ controller signal GND

Pattern LED:
  physical pin 32 (GPIO12) ---- 330 ohm --- LED anode (+)
  physical pin 30 (GND) ------------------- LED cathode (-)
```

Physical pin 9 is ground, not a programmable GPIO. “Move the capture button
to pins 9 and 11” therefore means the button connects GPIO17 on physical pin
11 to ground on physical pin 9.

The previous LED-strip toggle button is removed. GPIO17, formerly assigned to
that button, is now the capture-button input. The previous GPIO16 capture
connection and GPIO21 strip-control connection are unused.

## Read this before wiring

Disconnect the Pi, converter, controller, display, and every LED power source
before changing wiring.

Raspberry Pi GPIO is 3.3 V only and is not 5 V tolerant:

- Never connect 5 V or 12 V to GPIO12, GPIO17, or GPIO18.
- Never connect the LED strip or its load current directly to a GPIO pin.
- GPIO18 supplies only the MOSFET controller's PWM control signal.
- The MOSFET controller input must recognize 3.3 V as a valid high level.
- Pi ground and controller signal ground must share a reference unless the
  controller has a specifically documented isolated input.

Check the MOSFET controller documentation before wiring. Terminal names and
power-path arrangements vary. This guide cannot safely infer a controller's
load-terminal order from its product category alone.

The controller must be rated for:

- the strip's 12 V supply;
- the strip's measured continuous current;
- the selected PWM frequency; and
- operation at the actual enclosure temperature.

## Parts required

- Raspberry Pi 3 Model A+ with a stable 5.1 V supply
- 7-inch DSI display and its required power connection
- Camera Module 3 Wide and the correct CSI ribbon cable
- One normally-open momentary tactile button
- One small, two-leg, high-efficiency indicator LED
- One 330 ohm, 1/4 W resistor for the pattern LED
- 12 V non-addressable LED strip with its required current limiting
- 3.3 V-compatible PWM MOSFET controller rated for the strip
- Regulated 5 V-to-12 V boost converter with adequate continuous ratings and
  documented overcurrent, short-circuit, and thermal protection
- Properly rated power wire for the LED current
- Smaller insulated hookup wire for GPIO signals
- Secure terminal blocks or soldered connections
- Heat-shrink tubing, strain relief, and a digital multimeter

Do not carry LED-strip load current through thin Dupont jumpers or solderless
breadboard contacts. Those are suitable only for temporary signal testing.

## Capture button

The app enables an internal pull-up on GPIO17. The open button reads high;
pressing it connects GPIO17 to ground.

```text
Pi physical pin 11 (GPIO17) ---- button ---- Pi physical pin 9 (GND)
```

The button must be normally open. A typical four-leg tactile button has two
permanently connected legs on each side. Use one leg from each opposite side.
With power disconnected, confirm the leg pairs with a multimeter.

Button behavior:

- Press and release in under one second to start a photo.
- Hold for one second to start video while the button remains held.
- Releasing that initial hold does not stop recording.
- Press and release again to stop video.
- Video also stops automatically after 20 seconds.

There is no physical LED-strip on/off button.

## Small pattern LED

```text
Pi physical pin 32 (GPIO12) ---- 330 ohm ---- LED anode (+)
Pi physical pin 30 (GND) -------------------- LED cathode (-)
```

The resistor may be on either side of the LED, but it must be in series.
Never connect the LED directly between GPIO12 and ground.

GPIO12 follows the app's photo and video capture patterns. It turns off after
capture and remains off during saved-media playback. This indicator is
independent of the LED-strip PWM output.

## LED-strip PWM controller

GPIO18 on physical pin 12 provides PWM0 and is the default strip-control pin.
GPIO12 on physical pin 32 remains dedicated to the pattern LED; despite the
similar numbers, physical pin 12 and BCM GPIO12 are different pins.

Connect the control side:

```text
Pi physical pin 12 (GPIO18/PWM0) ---- controller PWM/input
Pi physical pin 14 (GND) ------------ controller signal GND
```

Do not connect GPIO18 directly to a MOSFET gate unless you intentionally return
to a separately designed direct-gate circuit. The current design expects a
MOSFET controller module with a logic/PWM input.

The software defaults are:

```text
LED_PWM_PIN=18
LED_PWM_ACTIVE_HIGH=true
LED_PWM_FREQUENCY=10000
LED_STRIP_BRIGHTNESS=1.0
```

`LED_STRIP_BRIGHTNESS` is PWM duty cycle: `0.0` is off, `0.5` is 50 percent,
and `1.0` is full output. For visual testing, the app currently uses this value
as the peak while fading bright to off in 2.5 seconds and back to bright in
2.5 seconds. The complete cycle takes five seconds. The strip is switched off
during clean app shutdown.

If the controller input is active-low, set `LED_PWM_ACTIVE_HIGH=false`.
Only change the PWM frequency after checking the controller's supported range.
A frequency that is too low can produce camera banding or visible flicker.
The app's `lgpio` backend supports no more than 10000 Hz; the controller may
have a lower limit. A frequency outside either range can prevent startup,
cause incorrect switching, or cause heating.

## Controller power and load path

Follow the terminal labels and manufacturer diagram for the exact MOSFET
controller. A common non-isolated low-side controller is conceptually wired:

```text
Boost converter OUT+ (+12 V) ---- controller power/load positive
Boost converter OUT- (0 V) ------- controller power ground
LED strip positive (+) ----------- controller load positive
LED strip negative (-) ----------- controller switched load negative
Pi ground ------------------------ controller signal ground
GPIO18 --------------------------- controller PWM/input
```

Some modules use different terminal arrangements, combine positive terminals,
switch the high side, include optical isolation, or require a separate logic
supply. Do not copy the conceptual diagram over contradictory controller
documentation.

The strip's load current must stay in the controller/converter power wiring.
It must not flow through the Pi ground pin or the thin PWM ground jumper.

## Boost converter and power budget

Before connecting the strip, power the boost converter input and adjust its
output to 12.0 V with a multimeter. Disconnect power before attaching the
controller and strip.

The boost converter draws more current at 5 V than the strip uses at 12 V:

```text
5 V input current =
    (12 V × strip current at 12 V) / (5 V × converter efficiency)
```

For example, a strip drawing 0.5 A at 12 V consumes 6 W. At 85 percent
efficiency:

```text
6 W / (5 V × 0.85) = 1.41 A at 5 V
```

Confirm that the Pi supply, USB path, converter, controller, connectors, and
wiring all have adequate continuous ratings with margin. Camera and display
load reduce the current available to the strip. Undervoltage can reset the Pi,
corrupt captures, or damage the filesystem.

If the LED branch has no dedicated fuse, use a converter/controller with
documented current limiting, output short-circuit protection, and thermal
shutdown.

## Camera and DSI display

The camera uses the CSI connector and the display uses the DSI connector.
Never insert or remove either ribbon while powered. Keep LED power wiring and
the controller away from the CSI ribbon and provide strain relief.

## Recommended assembly order

1. Shut down the Pi and disconnect every power source.
2. Verify physical pins 9, 11, 12, 14, 30, and 32 against `pinout`.
3. Wire the capture button between physical pins 11 and 9.
4. Wire the pattern LED and its resistor between physical pins 32 and 30.
5. Confirm no button or LED signal wire reaches 5 V or 12 V.
6. Confirm the MOSFET controller accepts 3.3 V PWM and the strip current.
7. Connect GPIO18 and Pi ground to only the controller's control input.
8. Build the converter/controller/strip power path using rated power wire.
9. Inspect for loose strands, reversed polarity, and exposed conductors.
10. Power the Pi without the strip load and verify the capture button and
    pattern LED.
11. Verify a PWM waveform or average voltage appears on GPIO18 while the app
    runs. At 100 percent brightness it should be a steady logic high.
12. Disconnect power, attach the strip, and perform the checks below.

## First-power checks

1. Keep the system supervised and ready to disconnect power.
2. Confirm the strip is off before the app starts.
3. Start the app and confirm the strip smoothly cycles from bright to off and
   back to bright every five seconds.
4. Confirm capture-button photo, video-start, and video-stop behavior.
5. Confirm the small LED follows its capture pattern independently.
6. Measure strip current at full configured brightness.
7. Run both capture types and check:

   ```bash
   vcgencmd get_throttled
   ```

8. Supervise an extended run and check controller, converter, connectors,
   wires, and cables for abnormal heat.

`throttled=0x0` means there are no current or historical undervoltage or
throttling flags. Correct any nonzero result before unattended use.

Disconnect power if the strip flickers unexpectedly, the controller heats up,
the camera shows PWM banding, connectors warm, or the Pi reports undervoltage.

## Unpowered inspection checklist

- GPIO17 on physical pin 11 reaches only the capture button.
- The other capture-button side reaches ground on physical pin 9.
- There is no second/toggle button.
- GPIO18 on physical pin 12 reaches only the controller PWM/input.
- Controller signal ground reaches Pi ground on physical pin 14.
- GPIO12 on physical pin 32 reaches the pattern LED only through 330 ohms.
- The pattern LED cathode reaches ground on physical pin 30.
- No GPIO pin connects to 5 V or 12 V.
- Strip current does not pass through GPIO or thin signal jumpers.
- Converter and controller polarity matches their manufacturer diagrams.
- Every power conductor is rated for measured continuous current.
- Camera and display ribbons are seated and latched.
- Power cables and ribbons have strain relief.

## References

- [Raspberry Pi GPIO documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio)
- [Raspberry Pi power supply guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)
