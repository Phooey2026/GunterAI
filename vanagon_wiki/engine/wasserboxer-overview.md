# Wasserboxer Engine Overview

STATUS: seeded
SYSTEM: engine
BENTLEY: p.10-15 (Engine Mechanical)
UPDATED: 2026-04-11
TAGS: engine, wasserboxer, WBX, specs, overview

RELATED: [[engine/head-gasket]], [[engine/oil-system]], [[cooling/overview]], [[cooling/aux-water-pump]]

---

## What is the Wasserboxer?

The Wasserboxer (WBX) is a water-cooled horizontally-opposed (boxer) 4-cylinder engine
used in Vanagons from 1983.5 through 1991. "Wasser" is German for water — distinguishing
it from the earlier air-cooled engines. The engine sits in the rear of the van, under
the floor of the cargo/living area.

## Variants

| Engine | Displacement | Years | Code | Fuel System |
|--------|-------------|-------|------|-------------|
| 1.9L WBX | 1915cc | 1983.5-1985 | DH | Bosch AFC |
| 2.1L WBX | 2110cc | 1986-1991 | MV | Digifant EFI |

The 2.1L is the most common in the US. The increase from 1.9 to 2.1L was achieved
with a longer crankshaft throw (74mm vs 69mm), not a larger bore.

## Key Specifications — 2.1L MV (1986-1991)

| Spec | Value |
|------|-------|
| Displacement | 2110cc |
| Bore x Stroke | 94mm x 76mm (approx) |
| Compression ratio | 8.6:1 |
| Power | 95 hp @ 4800 rpm |
| Torque | 117 ft-lb @ 3000 rpm |
| Oil capacity | 4.0 qts with filter |
| Firing order | 1-4-3-2 |
| Spark plug gap | 0.7-0.8mm (0.028-0.031 in) |

## Known Issues & Reputation

The WBX has a mixed reputation. It is not a bad engine, but it has specific
vulnerabilities that kill engines when neglected:

1. **Head gasket failure** — The #1 killer. Often caused by overheating from aux
   water pump failure. See [[engine/head-gasket]]
2. **Auxiliary water pump failure** — Silent killer. See [[cooling/aux-water-pump]]
3. **Pushrod tube leaks** — Oil leaks from pushrod tube o-rings are common on
   high-mileage engines. See [[engine/valve-train]]
4. **Hydraulic lifter noise** — Common on cold starts. Usually resolves when warm.
   Persistent noise may indicate oil pressure issues. See [[engine/valve-train]]

## The Failure Cascade

Understanding this cascade prevents most catastrophic WBX failures:

```
Aux water pump fails silently
    → Coolant doesn't circulate after shutdown
    → Localized boiling in cylinder heads
    → Head gasket fails
    → Coolant enters cylinders or oil
    → Engine destruction
```

**Prevention:** Test aux pump at every service. Replace proactively at 100K miles.

## Engine Access

The WBX is accessed from below the van through the engine hatch in the floor.
On Westfalia models, this is under the dinette/bed area. The engine is
notoriously difficult to work on due to tight access — many procedures require
removing the engine completely.

## GoWesty Engine Upgrades

GoWesty offers a 2.3L stroker version with improved reliability. Worth considering
for a rebuild, but expensive. Their EFI kit also replaces the aging Digifant
components with modern equivalents. See [[fuel/digifant-overview]]
