# Digifant EFI System Overview (1986-1991)

STATUS: seeded
SYSTEM: fuel
BENTLEY: p.24-35 (Fuel Injection)
UPDATED: 2026-04-11
TAGS: Digifant, EFI, fuel injection, ECU, idle, fuel system

RELATED: [[fuel/idle-system]], [[fuel/fuel-pump]], [[cooling/temperature-sensors]], [[engine/ignition]]

---

## What is Digifant?

Digifant is the Bosch/VW electronic fuel injection and ignition management
system used on all 1986-1991 2.1L Wasserboxer Vanagons. It controls:
- Fuel injection timing and duration
- Ignition timing
- Idle speed
- Cold start enrichment

## Key Sensors

| Sensor | Function | Failure Symptoms |
|--------|----------|-----------------|
| Temp II | Engine coolant temp for ECU | Rich running, poor idle |
| Throttle switch | Idle detection | Hunting idle, no idle control |
| Air Flow Meter (AFM) | Measures intake air | Rough running, poor power |
| Hall sender | Crankshaft position | No start, misfires |
| Oxygen sensor | Exhaust gas feedback | Poor fuel economy, rough idle |

See [[cooling/temperature-sensors]] for Temp II sensor details.

## Idle Control System

The Digifant idle system is one of the most common sources of problems
on the 2.1L WBX. It consists of:

1. **Idle Control Unit (ICU)** — electronic controller
2. **Idle Air Control Valve (IACV)** — electric valve that bypasses
   air around the closed throttle

A normal IACV buzzes continuously with the key on. If it doesn't buzz,
the valve or ICU may be faulty.

See [[fuel/idle-system]] for detailed diagnosis.

## ECU (Electronic Control Unit)

The Digifant ECU is located in the engine compartment. It is generally
reliable but can develop faults. Before replacing the ECU (expensive),
check all sensors and wiring connections thoroughly.

**ECU grounding is critical.** A poor ECU ground causes a wide range
of intermittent problems that are very difficult to diagnose.

## Common Digifant Problems

1. **Idle surge** — Classic WBX complaint. Usually vacuum leaks or
   Temp II sensor. See [[fuel/idle-system]]
2. **Rich running** — Failed Temp II sensor. Cheap fix.
3. **No start when hot** — Hall sender failure, or vapor lock in fuel
   system. See [[fuel/fuel-pump]]
4. **Poor fuel economy** — O2 sensor, Temp II, or AFM

## GoWesty EFI Replacement Kit

GoWesty developed a modern replacement for the entire Digifant system
that addresses all of the aging component issues:
- Replaces corroded wiring harness
- Modern sealed connectors
- Modern throttle position sensor (replaces throttle switch)
- Modern MAP sensor (replaces AFM)
- Sequential injection (vs batch-fire stock)
- Coil-on-plug ignition (eliminates distributor)

This is a significant improvement in reliability and is worth considering
for any major engine rebuild. Not cheap but addresses root causes.

## Digifant Training Manual

The Digifant Pro OCR manual is available as a source document in
`raw/digifant_pro_ocr.pdf`. It covers the system in detail including
wiring diagrams and diagnostic procedures.
