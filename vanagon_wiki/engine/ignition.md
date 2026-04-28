# Ignition System

STATUS: confirmed
SYSTEM: engine
BENTLEY: p.28-35 (Ignition)
UPDATED: 2026-04-11
TAGS: ignition, spark plugs, timing, distributor, NGK, Bosch

RELATED: [[fuel/digifant-overview]], [[parts/cross-reference]]

---

## Spark Plugs — 2.1L Wasserboxer (1986-1991)

| Brand | Part Number | Notes |
|-------|------------|-------|
| Bosch | WR7CC | OEM spec — hard to find in US |
| NGK | BR6ES | **Recommended US replacement** |

- Gap: 0.7-0.8mm (0.028-0.031 in)
- Torque: 25 Nm / 18 ft-lb into aluminum head — do not overtighten
- Quantity: 4 per engine
- Change interval: 15,000-20,000 miles

**Critical note on heat ranges:** Bosch and NGK number their heat ranges in
OPPOSITE directions. A higher Bosch number = hotter plug. A higher NGK number
= colder plug. Bosch W**7** ≈ NGK B**6**. Do not substitute by number alone.

**Why not platinum or iridium?** The WBX aluminum heads are sensitive to
overtorquing and the plug well depth makes removal of seized plugs difficult.
Stick to standard copper plugs and change them on schedule.

## Ignition Timing — 2.1L MV (1986-1991)

| Condition | Timing |
|-----------|--------|
| Base timing (vacuum disconnected) | 5° BTDC |
| Advance at 2000 rpm | ~20° BTDC |

**Note:** The Digifant ECU controls ignition timing electronically. Base timing
must be set correctly for the ECU to operate properly. See [[fuel/digifant-overview]]

## Distributor

The 2.1L WBX uses a Hall-effect distributor (no points). The Hall sender is a
common failure point — it can cause intermittent no-start conditions.

**Cap and rotor:** Replace every 30,000 miles or if any cracking is visible.
Cracked cap causes misfires and rough running.

## Ignition Wires

High-resistance or cracked ignition wires cause misfires. With the engine
in the rear of the van, wires run through the engine compartment and are
subject to heat damage. Inspect at every tune-up.

## GoWesty EFI Kit

GoWesty makes a complete modern replacement for the Digifant EFI system that
also replaces the distributor with coil-on-plug ignition. Eliminates the
distributor entirely and improves reliability significantly. Expensive but
worth considering at rebuild time. See [[fuel/digifant-overview]]
