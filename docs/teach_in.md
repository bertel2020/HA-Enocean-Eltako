# Learn functions of Eltako series 14 actuators

[Deutsch](teach_in.de.md)

Which learn function to set on the actuator for each teach-in button of a device page.
Taken from the German operating manuals FSR14-4x (30014001-6), FUD14 (30014005-3),
FSB14 (30014004-7) and FHK14 (30014014-1). Other revisions and the series 61/62 actuators
number their functions differently: check the manual of your device.

## Procedure

1. FSR14-4x only: pick the channel (1 to 4, or 1..4) with the lower rotary switch.
2. Turn the upper rotary switch to the learn function from the table.
3. Turn the middle rotary switch to **LRN**; the LED flashes slowly.
4. Press the teach-in button on the device page in Home Assistant. The LED goes off.
5. For more senders, turn the middle switch briefly away from LRN and start again at 2.
   Afterwards set the rotary switches back to their operating positions (AUTO, times).

For the actuator to answer with a confirmation telegram, it needs a device address and the
FAM14's upper rotary switch must be at position 2 while teaching in.

## Table

"Any" means the manual asks for no learn position for this sender.

| Teach-in button | FSR14-4x | FUD14 | FSB14 | FHK14 |
|---|---|---|---|---|
| Teach-in rocker (switch, dimmer) | 0 direction rocker; 5 universal ES; 10 universal ER | LC2 direction rocker; EC2 universal | – | – |
| Teach-in central command | any (controller) | PCT | – | – |
| Teach-in direction rocker (cover) | – | – | 10 motor 1; 30 motor 2 | – |
| Teach-in controller (cover) | – | – | 180 motor 1; 200 motor 2 | – |
| Teach-in controller (heating) | – | – | – | right stop (4.5) |
| Virtual rocker as central button | 45 on, 90 off; 15 on, 20 off with priority | LC1 central on; EC1 central off | 60 without priority; 90 with priority (pressing toggles it) | – |
| Teach in window contact | any (the middle switch AUTO 1–4 sets the logic) | LC2 make contact; LC3 break contact | 20 motor 1; 40 motor 2, also sets up the lock-out protection | right stop (4.5) |
| Teach in motion | any | – | – | – |
| Teach in temperature | – | – | – | the hysteresis switch sets the setpoint while teaching in (2.5 = 21 °C, 0.5 = 17 °C, 4.5 = 25 °C) |
| Teach in brightness sensor | any; the upper switch then sets the threshold | – | 150 (motor 1 and 2) | – |
| Teach in weather station | – | – | any; either an FAH60 or an FWS61 | – |
| Scene buttons | 30 | LC4 | 180 motor 1; 200 motor 2 | – |

A dash means the manual names no learn function for this sender; the actuator may still
accept it through the PC tool PCT14.

## Which virtual sensor which actuator accepts

Read from the table above (manual of the actuator, not tested on hardware). **Yes** means the
manual names a learn function, **no** that it names none (PCT14 may still allow it).

| Virtual device | FSR14-4x | FUD14 | FSB14 | FHK14 |
|---|---|---|---|---|
| Window contact | yes | yes | yes (lock-out protection) | yes |
| Motion sensor | yes | no | no | no |
| Temperature sensor | no | no | no | yes (also sets the setpoint) |
| Brightness sensor (FAH60 format) | yes | no | yes | no |
| Weather station (FWS61 format) | no | no | yes | no |
| Rocker as central button | yes | yes | yes | no |
| Scene button | yes | yes | yes | no |

Not covered yet: FAE14SSR and the series 61/62 actuators (FSR61, FSB61, FUD61, FD62, FJ62).
Their manuals differ in the learn positions; add a column when you have checked them.

## Lock-out protection

Once a window contact is taught into an FSB14, the actuator blocks central down and scene
down while the contact reports open. For a virtual contact, turn on **Send with priority**
in its options: its telegram then overtakes every command waiting in the send queue, so an
"open" reaches the actuator before a central down command sent at the same moment.
