# Coolant Temperature Sensors

STATUS: confirmed
SYSTEM: cooling
BENTLEY: p.22-23
UPDATED: 2026-04-11
TAGS: temperature sensor, Temp II, Digifant, gauge sender, overheating diagnosis

RELATED: [[cooling/overview]], [[fuel/digifant-overview]], [[engine/head-gasket]]

---

## Two Separate Sensors

The 2.1L WBX has TWO coolant temperature sensors with completely different
functions. Confusing them is a common diagnostic mistake.

| Sensor | Function | VW Part | Location |
|--------|----------|---------|----------|
| Gauge sender | Drives dashboard temp gauge | 251-919-501-A | Thermostat housing |
| Temp II (ECU) | Tells Digifant ECU engine temp | 025-906-041-A | Thermostat housing |

## Gauge Sender

Sends a variable resistance signal to the temperature gauge on the dashboard.
Failure causes incorrect gauge readings. A faulty sender can show normal
temperature while the engine is actually overheating — this is dangerous.

**Symptoms of failed gauge sender:**
- Gauge reads low or high at all times
- Gauge reads normal but engine actually overheating

## Temp II Sensor (Digifant ECU)

This is the critical one for engine management. The Digifant ECU uses this
sensor to determine fuel enrichment, idle speed, and ignition timing based
on engine temperature.

**Symptoms of failed Temp II sensor:**
- Rich running (black smoke, fuel smell)
- Poor idle when warm
- Increased fuel consumption
- ECU thinks engine is always cold — overenriches fuel mixture
- Can cause false overheating diagnosis (engine running rich = more heat)

**Important:** A failing Temp II sensor can mimic many other problems.
It is a cheap part ($15-25) and should be considered early in any
diagnosis of running issues on a 2.1L WBX.

## Diagnosis

To test the Temp II sensor, measure resistance across its terminals
with a multimeter at known temperatures:
- Cold (20°C / 68°F): approximately 2,200-2,800 ohms
- Warm (80°C / 176°F): approximately 270-390 ohms

A sensor reading out of these ranges or showing infinite resistance
(open circuit) should be replaced.

## Why the Gauge Doesn't Show Overheating

The gauge sender is located in the thermostat housing and measures
bulk coolant temperature. Localized boiling in the cylinder heads
(caused by aux pump failure) can occur without the bulk coolant
temperature rising significantly. This is why head gaskets can fail
without the temperature gauge ever showing a problem.

See [[engine/head-gasket]] and [[cooling/aux-water-pump]]
