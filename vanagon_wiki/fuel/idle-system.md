# Idle System — Surge Diagnosis

STATUS: seeded
SYSTEM: fuel
BENTLEY: p.28-30 (Idle System)
UPDATED: 2026-04-11
TAGS: idle surge, hunting idle, IACV, ICU, vacuum leak, Digifant

RELATED: [[fuel/digifant-overview]], [[cooling/temperature-sensors]], [[parts/cross-reference]]

---

## Overview

Idle surge (hunting idle, RPM oscillating between 500-1200 rpm) is one
of the most common complaints on 2.1L WBX Vanagons. It has several
possible causes that must be diagnosed systematically.

## Diagnostic Sequence

Work through these in order — cheapest/easiest first:

### 1. Check for vacuum leaks (most common cause)
Any vacuum leak causes the ECU to over-compensate, creating a hunting idle.

**Method:** With engine at idle, spray carb cleaner or use an unlit propane
torch near suspected vacuum connection points. If idle changes when you
approach a specific area, you found a leak.

**Common vacuum leak locations:**
- Intake runner boots (rubber cracks with age)
- Brake booster hose
- Throttle body gasket
- Idle air bypass hose
- Any small vacuum hose fitting

### 2. Check Temp II sensor
A failed Temp II sensor makes the ECU think the engine is always cold,
causing continuous over-enrichment. Replace this first if it hasn't been
done — it is a $15-25 part.
See [[cooling/temperature-sensors]]

### 3. Test the Idle Air Control Valve (IACV)
**Normal operation:** With key on (engine off), the IACV buzzes continuously.
If no buzzing, the valve may be stuck or the ICU may be faulty.

**Test:** Unplug the IACV while engine is idling. RPM should drop noticeably
and may get rough. If no change, the valve is stuck open or the ICU isn't
modulating it.

**Resistance check:** Measure across IACV terminals. Should read 7-9 ohms.
Open circuit or short indicates a failed valve.

### 4. Check throttle switch adjustment
With throttle fully closed, the throttle switch should click closed.
If the switch doesn't close, the ECU never enters idle mode and the
IACV will hunt continuously.

Test with a multimeter: continuity should be present ONLY when throttle
is fully closed.

### 5. Check Idle Control Unit (ICU)
The ICU is a known failure point. A failed transistor in the ICU causes
the IACV to lose controlled modulation. Only replace after ruling out
the above causes — the ICU is more expensive.

## Idle Speed Specification

- 2.1L MV (1986-1991): 850 ± 50 rpm with transmission in Park/Neutral
- A/C off for baseline measurement

## Digifant Manual Reference

Detailed diagnostic procedures are in the Digifant Training Manual,
available as `raw/digifant_pro_ocr.pdf`. The idle system diagnosis
starts around page 16.
