# Electrical System Overview

STATUS: seeded
SYSTEM: electrical
BENTLEY: p.474-549 (Electrical)
UPDATED: 2026-04-11
TAGS: electrical, wiring, relays, fuses, gremlins

RELATED: [[electrical/charging]], [[fuel/digifant-overview]], [[cooling/aux-water-pump]]

---

## Overview

The Vanagon electrical system is a 12V negative ground system. It has
a reputation for electrical gremlins, mostly attributable to:
- 35+ year old wiring with hardened insulation
- Corroded connectors and grounds
- Relay failures (VW used many relays)
- Fuse box corrosion

The good news: most Vanagon electrical problems are ground issues
or relay failures — cheap and fixable.

## Fuse Box

Located under the dashboard on the driver's side. The fuse box is
a common source of problems — corrosion on the fuse contacts causes
intermittent failures that are difficult to diagnose.

**Maintenance:** Remove each fuse, clean contacts with electrical
contact cleaner, apply dielectric grease. Do this every few years.

## Common Relays

VW used standardized relays throughout the Vanagon. Many are interchangeable.
Always carry a selection of spare relays — they are cheap and a common
roadside failure.

| System | Relay Location | Notes |
|--------|--------------|-------|
| Fuel pump | Under dash/engine area | Check first on no-start |
| Aux water pump | Engine compartment | VW 251-906-381 |
| Radiator fan (low speed) | Under dash | |
| Radiator fan (high speed) | Under dash | |
| Digifant ECU | Under dash | |

## Grounding Issues

Poor grounds are the #1 cause of Vanagon electrical gremlins.
Key ground points to inspect and clean:
- Battery negative to chassis
- Engine to chassis (the long ground strap)
- ECU ground (critical for Digifant operation)
- Body grounds under the dashboard

Symptoms of poor ground: intermittent electrical failures, dim lights,
erratic gauge behavior, ECU faults.

## Wiring Harness

On high-mileage vans, the original wiring harness insulation becomes
brittle. Cracked insulation causes shorts and intermittent failures.
Inspect wiring routing for any areas where harnesses rub against
metal edges.

The GoWesty EFI kit replaces the engine harness with modern sealed
connectors — worth considering at rebuild time.

## Wiring Diagrams

Wiring diagrams are in the Bentley at p.474 (water-cooled 1991) and
p.549 (earlier models). These are essential for any electrical diagnosis.
