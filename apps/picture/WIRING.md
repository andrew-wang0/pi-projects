# Picture hardware wiring guide

This document covers the complete wiring for the `picture` app on a Raspberry
Pi 3 Model A+ with:

- Raspberry Pi Camera Module 3 Wide
- 7-inch DSI display
- 12 V, non-addressable LED strip
- 5 V-to-12 V DC boost converter
- IRLB8721 N-channel MOSFET
- Two four-leg momentary tactile buttons
- One three-leg SPDT slide switch

The GPIO assignments match the defaults in `config.py`.

## Read this before wiring

Disconnect the Pi's power and every LED power source before changing any wire.
The project uses low voltage, but a shorted 5 V input, 12 V converter output,
or USB cable can still overheat wiring, damage the Pi, corrupt the SD card, or
start a fire.

The design assumes the LED product is a complete **12 V strip intended to run
directly from regulated 12 V**, with its own current-limiting resistors or
controller. It is not suitable for bare LEDs without current limiting or an
addressable strip that requires a data signal.

Raspberry Pi GPIO is 3.3 V only and is not 5 V tolerant:

- Never connect USB 5 V or the converter's 12 V output to GPIO16, GPIO17,
  GPIO20, GPIO21, or GPIO26.
- Never connect the LED strip directly to GPIO21.
- GPIO21 drives only the MOSFET gate.
- The buttons and switch connect GPIO inputs to ground, not to 5 V.

### Important IRLB8721 limitation

The IRLB8721 datasheet guarantees its on-resistance at gate voltages of 4.5 V
and 10 V. It does **not** guarantee an on-resistance at the Pi's 3.3 V GPIO
level. Its gate-threshold specification is measured at only 25 microamps and
does not mean that the MOSFET is fully on at that voltage.

Direct 3.3 V drive may be adequate for a small 12 V LED-strip load, but it must
be validated under the strip's actual current. For the most robust final
build, use either:

- an N-channel MOSFET whose datasheet specifies a maximum `RDS(on)` at a gate
  voltage of 2.5 V or 3.0 V; or
- a 3.3 V-compatible, non-inverting MOSFET gate driver that drives the
  IRLB8721 gate at 4.5-5 V.

Never connect 5 V directly to the gate while it is still connected to GPIO21.

## Parts required

- Raspberry Pi 3 Model A+ and a stable 5.1 V power supply
- 7-inch DSI display and its required power connection
- Camera Module 3 Wide and correct CSI ribbon cable
- 12 V LED strip
- Regulated 5 V-to-12 V boost converter with adequate continuous input/output
  current ratings and documented overcurrent, short-circuit, and thermal
  protection
- IRLB8721 in a TO-220AB package
- One small, two-leg, high-efficiency indicator LED
- Two 330 ohm, 1/4 W resistors: one for the MOSFET gate and one for the small
  LED
- One 10 kilohm, 1/4 W resistor for the gate pulldown
- Two normally-open, four-leg tactile buttons
- One SPDT, three-leg slide switch
- Properly rated power wire for the LED current
- Smaller insulated hookup wire for GPIO signals
- Soldered perfboard, terminal blocks, or another secure final connection
  method
- Heat-shrink tubing and strain relief
- Digital multimeter
- Optional heatsink for the MOSFET, only if measurements show it is needed

Do not carry the LED strip's load current through thin Dupont jumpers or
solderless breadboard contacts. Those are acceptable for temporary GPIO signal
testing, not for an unattended power circuit.

## GPIO connection summary

All software pin names use **BCM numbering**. Physical pin numbers identify
positions on the Pi's 40-pin header.

| Function                      | BCM GPIO | Physical pin | Connects to                        |
| ----------------------------- | -------: | -----------: | ---------------------------------- |
| Video/photo mode switch       |   GPIO26 |           37 | Switch center/common leg           |
| Capture button, BTN1          |   GPIO16 |           36 | One side of capture button         |
| Small pattern LED             |   GPIO20 |           38 | 330 ohm resistor, then LED anode   |
| LED MOSFET control            |   GPIO21 |           40 | 330 ohm resistor, then MOSFET gate |
| BTN1 ground                   |      GND |           34 | Other side of capture button       |
| Lower control ground          |      GND |           39 | Mode switch and small LED cathode  |
| LED-strip on/off button, BTN2 |   GPIO17 |           11 | One side of strip toggle button    |
| Upper control ground          |      GND |            9 | Other side of BTN2                 |

The relevant bottom end of the header is:

```text
Physical pin 33: unused     Physical pin 34: GND
Physical pin 35: unused     Physical pin 36: GPIO16
Physical pin 37: GPIO26     Physical pin 38: GPIO20
Physical pin 39: GND        Physical pin 40: GPIO21
```

Verify the pin numbers against the Pi's header markings or the `pinout` command
before connecting anything. Do not count pins from memory.

## Control wiring

The app enables internal pull-up resistors for the buttons and switch. An open
input reads high; pressing a button or selecting the grounded switch position
pulls the input low.

No external button pull-up resistors and no 3.3 V button connections are
required.

### Identify the tactile-button legs

On a typical four-leg tactile button:

- the two legs on one side are permanently connected;
- the two legs on the opposite side are permanently connected; and
- pressing the button connects the two sides.

Button package layouts vary. With all power disconnected, use the multimeter's
continuity mode to identify the two permanent pairs. Select one leg from each
different pair. If both wires are attached to the same permanent pair, the
input will appear permanently pressed or the button will do nothing useful.

### BTN1: capture/start/stop

Connect:

```text
Pi physical pin 36 (GPIO16) ---- BTN1 ---- Pi physical pin 34 (GND)
```

BTN1 must be normally open. Pressing it grounds GPIO16. The software acts on
the press edge, so holding it does not repeatedly trigger captures.

### BTN2: LED-strip on/off toggle

Connect:

```text
Pi physical pin 11 (GPIO17) ---- BTN2 ---- Pi physical pin 9 (GND)
```

BTN2 must be normally open. Each press directly toggles the LED strip between
steady on and steady off. Photo countdowns, video countdowns, recording, and
ending flashes never change the strip's selected state. The strip starts on
when the app starts.

BTN2 does not affect the small pattern LED; only that small LED displays
capture patterns.

### Small two-leg pattern LED

Connect:

```text
Pi physical pin 38 (GPIO20) ---- 330 ohm ---- LED anode (+)
Pi physical pin 39 (GND) -------------------- LED cathode (-)
```

The resistor may be placed on either side of the LED, but it must be in series;
never connect the LED directly between GPIO20 and ground.

The longer LED leg is commonly the anode. The shorter leg and flat edge on the
LED body commonly mark the cathode, but verify the specific LED. If it does not
light, disconnect power and recheck polarity rather than bypassing the
resistor.

GPIO20 follows the app's requested LED pattern directly. It is on during the
normal steady-on and recording states and follows all slow and fast capture
flashes. BTN2 independently toggles the MOSFET and 12 V strip, so the small LED
continues to show every pattern regardless of the strip's on/off state.

### Three-leg mode switch

First use continuity mode to identify the common leg. It is usually the center
leg, but verify the actual switch.

Connect:

```text
Pi physical pin 37 (GPIO26) ---- switch common
Pi physical pin 39 (GND) ------- one outside switch leg
Other outside switch leg ------- not connected and insulated
```

With the default configuration:

- common connected to the grounded outer leg selects video mode;
- common connected to the unconnected outer leg selects photo mode through
  the Pi's internal pull-up.

If the physical lever points the opposite way from the label you want, move
the ground wire to the other outside leg. Do not connect either outer leg to
5 V. Connecting the unused outer leg to 3.3 V is unnecessary.

## IRLB8721 and LED-strip wiring

### Confirm the MOSFET pinout

For the Infineon IRLB8721 TO-220AB package, viewed from the front with the flat
printed face toward you and the legs pointing downward:

```text
Left leg       Center leg       Right leg
Pin 1          Pin 2            Pin 3
Gate (G)       Drain (D)        Source (S)
```

The exposed metal tab is also electrically connected to the **drain**. Keep it
insulated from the Pi, grounded metal, enclosure hardware, and other
conductors unless a correctly insulated mounting arrangement is used.

Confirm the part number and its manufacturer datasheet before soldering.
Different packages or substitute parts may have a different pinout.

### Gate network

Wire the gate exactly as follows:

```text
Pi physical pin 40 (GPIO21) ---- 330 ohm ---- Gate
                                                |
                                             10 kilohm
                                                |
Source / power ground --------------------------+
```

The 330 ohm resistor limits the brief GPIO current used to charge and discharge
the MOSFET gate. The app switches only a few times per second, so there is no
need for a smaller high-speed gate resistor.

The 10 kilohm gate-to-source resistor keeps the MOSFET off while the Pi boots,
shuts down, or leaves GPIO21 floating. Place it physically near the MOSFET.
It must connect from gate to **source**, not from drain to source.

### Low-side load connection

The MOSFET switches the 12 V strip's negative return:

```text
Boost converter OUT+ (+12 V) ---- LED strip positive (+)
LED strip negative (-) ---------- MOSFET drain
MOSFET source ------------------- Boost converter OUT-
GPIO21 -------- 330 ohm --------- MOSFET gate
MOSFET gate ---- 10 kilohm ------ MOSFET source
Pi ground ----------------------- MOSFET source / converter ground
```

Do not reverse drain and source. The circuit may appear partly functional
through the MOSFET's body diode but will not switch correctly.

The Pi and LED supply must share a ground so the MOSFET sees the correct
gate-to-source voltage. A shared ground does not mean that LED load current
should travel through a thin GPIO jumper; use a proper power-ground conductor
for the LED current.

An LED strip is not an inductive relay or motor, so this circuit does not
normally require a flyback diode.

## 5 V-to-12 V boost-converter wiring

Use a USB power breakout or a properly modified USB extension cable between
the Pi's USB port and the converter input. Do not modify the Pi itself.

Typical USB 2.0 wire colors are red for +5 V and black for ground, but colors
are not guaranteed. Verify every conductor with a meter. Do not rely only on
wire color.

Wire the complete power path:

```text
Pi USB +5 V ---------------- Boost converter IN+
Pi USB ground -------------- Boost converter IN-

Boost converter OUT+ ------- LED strip positive (+12 V)
LED strip negative --------- IRLB8721 drain
IRLB8721 source ------------ Boost converter OUT-

Pi GPIO ground ------------- IRLB8721 source / converter ground
GPIO21 ---- 330 ohm -------- IRLB8721 gate
Gate ------- 10 kilohm ----- IRLB8721 source
```

If the cable has data wires, leave D+ and D- disconnected from the LED power
circuit and insulate them individually. Do not use the USB shield as the LED
return conductor.

Most non-isolated boost modules have a common negative node, meaning IN- and
OUT- are electrically connected. Verify this with the module documentation or
a continuity measurement while it is completely unpowered. The direct GPIO
gate circuit requires the MOSFET source and Pi ground to share a reference.
If IN- and OUT- are not common and the converter documentation does not
explicitly permit bonding OUT- to Pi ground, do not use that converter with
this direct gate circuit.

The strip's negative lead must connect only to the MOSFET drain. A direct wire
from strip negative to converter OUT-, USB ground, or Pi ground would bypass
the MOSFET and leave the strip permanently on.

### Converter setup

Before connecting the LED strip, power the converter input and set its output
to 12.0 V using a multimeter. Adjustable boost modules can arrive set above
12 V. Disconnect power after adjustment, then attach the strip.

The converter must be rated for:

- a 5 V input;
- a regulated 12 V output;
- at least the strip's measured full-brightness output current continuously;
- the calculated 5 V input current continuously; and
- operation inside the enclosure at its real temperature.

Do not rely on an advertised peak rating. Small boost modules often require
substantial derating or airflow for continuous operation.

### 5 V input-current calculation

A boost converter draws more current at 5 V than the strip uses at 12 V. Use:

```text
5 V input current =
    (12 V × strip current at 12 V) / (5 V × converter efficiency)
```

For example, a strip drawing 0.5 A at 12 V consumes 6 W. At 85% converter
efficiency, the converter needs approximately:

```text
6 W / (5 V × 0.85) = 1.41 A from the Pi USB port
```

The Pi 3A+ documentation recommends a 2.5 A Pi supply, but the board has no
simple fixed USB-current guarantee for this use: available current is limited
by the PSU, board circuitry, connector, cable, display, camera, and Pi load.
The Camera Module alone can add approximately 250 mA according to Raspberry Pi
power guidance. A DSI display and illuminated strip add further load.

USB power is acceptable only after measuring the strip's 12 V current,
calculating the required 5 V current, and confirming the complete power budget
with margin. Undervoltage can reset the Pi or corrupt captures even when the
strip appears to work.

This build has no dedicated LED-branch fuse. Therefore its fault protection
depends on the Pi supply, Pi board, USB path, and boost converter. Use a
converter with documented input current limiting, output short-circuit
protection, and over-temperature shutdown. Without those protections, a
no-fuse circuit cannot be treated as protected against a wiring or strip
short.

If the calculated input current is too high for the Pi USB path, power the
boost converter from a separate regulated 5 V supply of adequate capacity.
Join that supply's ground to Pi ground for the GPIO reference, but do not join
the external +5 V output to the Pi's 5 V rail.

Use short, adequately rated power conductors, secure screw terminals or
soldered joints, heat-shrink over exposed connections, and strain relief where
the USB cable enters the enclosure.

## Camera and DSI display

The camera and display use separate ribbon connectors:

- Camera Module 3 Wide connects to the Pi's CSI/camera connector.
- The display connects to the Pi's DSI/display connector.

Never insert or remove either ribbon while the Pi or display is powered. Open
the connector latch gently, insert the ribbon fully and squarely, then close
the latch. Contact orientation differs between boards and cable ends, so
follow the markings for the exact Pi, camera, and display rather than assuming
that exposed contacts always face the same direction.

The DSI ribbon is not a substitute for the display's required 5 V power
connection. Keep the display's already working power arrangement specified by
its manufacturer. Do not route LED load current through a display power board
or small display-to-Pi jumper unless that board and wiring are explicitly
rated for the total current.

Keep the MOSFET power wiring and LED-current loop away from the CSI ribbon.
Secure all ribbons so enclosure movement cannot pull them from their
connectors.

## Recommended assembly order

1. Shut down the Pi and disconnect all power.
2. Verify the GPIO physical pin numbers.
3. Use continuity mode to identify the button pairs and switch common leg.
4. Wire BTN1, BTN2, the mode switch, and the small pattern LED.
5. Confirm none of those GPIO wires connects to 5 V or 12 V.
6. On an unpowered separate board, install the IRLB8721, 330 ohm gate resistor,
   and 10 kilohm gate-to-source resistor.
7. Verify the MOSFET gate, drain, source, and metal-tab identities.
8. Build the 5 V input, boost converter, 12 V output, and MOSFET power path
   using proper power wiring.
9. Inspect for solder bridges, loose strands, reversed MOSFET legs, and exposed
   conductors.
10. Power the Pi without the LED strip connected and verify the controls and
    small pattern LED.
11. Measure GPIO21 relative to MOSFET source:
    - BTN2 strip-off state: approximately 0 V
    - BTN2 strip-on state: approximately 3.1-3.3 V
12. Disconnect power again, connect the LED strip, and perform the controlled
    first-power checks below.
13. Only after electrical and thermal checks pass, secure the circuit in its
    ventilated enclosure with strain relief.

## First-power and thermal checks

For first power, use a current-limited bench supply if available. Otherwise,
use a converter with verified protection and remain ready to disconnect power.

1. Confirm the strip remains fully off before the app starts.
2. With the app running, press BTN2 to force the strip off.
3. Start a capture and confirm the small LED still follows every flash while
   the strip remains off.
4. Press BTN2 again and confirm the strip turns on and remains steadily on
   while the small LED continues its independent pattern.
5. Confirm the strip reaches normal brightness.
6. Measure the strip's current at full brightness.
7. Measure `VGS` from gate to source while on. It should be close to the GPIO
   high level.
8. Measure `VDS` from drain to source while on.
9. Estimate MOSFET dissipation as:

   ```text
   MOSFET power in watts = LED current in amps × VDS in volts
   ```

10. Leave the strip continuously on under supervision and monitor MOSFET,
    connector, wire, and cable temperatures.

If the MOSFET becomes hot, the strip is dim, `VDS` is unexpectedly high, or
any connector warms, disconnect power. Do not solve a poorly driven MOSFET
only by adding a heatsink. Use a MOSFET specified for 2.5-3.3 V gate drive or
a proper 5 V gate driver, and correct undersized wiring or connectors.

Check the Pi after exercising both capture modes:

```bash
vcgencmd get_throttled
```

`throttled=0x0` means no current or historical undervoltage/throttling flags
are set. Any nonzero value should be decoded and corrected before unattended
use. Also watch for low-voltage warnings, camera errors, USB resets, display
flicker, or spontaneous reboots when the strip turns on.

## Unpowered inspection checklist

Before final power-up, verify all of the following:

- GPIO16 connects to BTN1 and only reaches ground when BTN1 is pressed.
- GPIO17 connects to BTN2 and only reaches ground when BTN2 is pressed.
- GPIO20 reaches the small LED only through its 330 ohm resistor.
- The small LED anode faces GPIO20 and its cathode reaches ground.
- GPIO26 connects to switch common.
- Exactly one mode-switch outside leg connects to ground.
- GPIO21 reaches the MOSFET gate only through 330 ohms.
- The 10 kilohm resistor connects gate to source.
- MOSFET source connects to boost-converter OUT-.
- LED-strip negative connects only to MOSFET drain.
- LED-strip positive receives regulated +12 V from boost-converter OUT+.
- Converter IN+ receives 5 V from the USB power conductor.
- Converter IN- and the MOSFET source share the Pi ground reference.
- No GPIO pin connects to 5 V or 12 V.
- No wire bypasses drain-to-source and leaves the LED permanently grounded.
- The MOSFET metal tab cannot touch grounded or live metal.
- LED current does not pass through a breadboard or thin signal jumper.
- USB data conductors and unused switch legs are individually insulated.
- Camera and DSI ribbons are fully seated and latched.
- Power cables and ribbons have strain relief.

## References

- [IRLB8721 manufacturer datasheet](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irlb8721-datasheet-en.pdf)
- [Raspberry Pi power supply guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)
- [Raspberry Pi GPIO documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio)
