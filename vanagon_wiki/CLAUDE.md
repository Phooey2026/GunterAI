# Gunter AI — Vanagon Wiki
## Schema, Workflows & Instructions for Claude Code

This wiki is a living knowledge base for the Gunter AI Vanagon diagnostic assistant.
It is organized by mechanical system, mirroring the Bentley Manual chapter structure.
Claude Code maintains this wiki — reading from it to answer questions and writing to it
when new knowledge is discovered or gaps are identified.

---

## Directory Structure

```
vanagon_wiki/
├── CLAUDE.md                  # This file — schema and workflows
├── index.md                   # Master catalog of all pages
├── log.md                     # Append-only change log
│
├── engine/                    # Engine mechanical
├── cooling/                   # Cooling system
├── fuel/                      # Fuel system and Digifant EFI
├── transmission/              # Transmission and drivetrain
├── brakes/                    # Brakes
├── suspension/                # Suspension, steering, wheels, bearings
├── electrical/                # Electrical, wiring, charging
├── body/                      # Body, interior, Westfalia camper systems
├── parts/                     # Parts cross-reference and suppliers
└── raw/                       # Source documents (PDFs, scraped content)
    ├── bentley_ocr.pdf        # Copy or symlink from Manuals/
    ├── digifant_pro_ocr.pdf   # Copy or symlink from Manuals/
    └── samba_full_content.md  # Copy or symlink from project root
```

---

## Page Schema

Every wiki page uses this frontmatter format:

```markdown
# Page Title

STATUS: [seeded|verified|community|confirmed]
SYSTEM: [engine|cooling|fuel|transmission|brakes|suspension|electrical|body|parts]
BENTLEY: [page numbers if applicable, e.g. "p.450-460"]
UPDATED: [YYYY-MM-DD]
TAGS: [comma-separated tags]

RELATED: [[system/page]], [[system/page]]
```

### STATUS values:
- **seeded** — initial content from training knowledge, needs Bentley verification
- **verified** — cross-referenced with Bentley manual, page numbers cited
- **community** — sourced from TheSamba, treat as experienced owner advice
- **confirmed** — verified by owner real-world experience (Jay/Luna)
- **stub** — placeholder page, needs content

---

## WikiLink Format

Use `[[system/page]]` for cross-references between pages.
Example: `[[cooling/aux-water-pump]]`, `[[parts/cross-reference]]`

Always add cross-links when a page mentions another system's component.
Example: aux-water-pump failure → head gasket failure should link both ways.

---

## Workflows for Claude Code

### When answering a Gunter question:
1. Check relevant wiki pages for the system involved
2. Cross-reference with `[[parts/cross-reference]]` for part numbers
3. Note any gaps — information needed but not in the wiki

### When a gap is found:
1. Research from `raw/` source documents if available
2. Create or update the relevant wiki page
3. Update `index.md` if a new page was created
4. Append an entry to `log.md`
5. Add cross-links to/from related pages

### When seeding from raw sources:
1. Read `raw/samba_full_content.md` — extract by THREAD_TITLE
2. Read `raw/bentley_ocr.pdf` — extract by chapter/page
3. File extracted knowledge into the appropriate system page
4. Change STATUS from `seeded` to `verified` or `community`
5. Always cite the source (Bentley page number, TheSamba thread title)

### Page creation checklist:
- [ ] Frontmatter complete (STATUS, SYSTEM, BENTLEY, UPDATED, TAGS)
- [ ] RELATED links added
- [ ] Reciprocal links added to related pages
- [ ] index.md updated
- [ ] log.md entry appended

---

## Source Priority (highest to lowest)
1. Bentley Manual (official factory spec)
2. Digifant Training Manual (fuel injection specific)
3. Owner verified experience (Jay/Luna — 1987 Westfalia, 200K+ miles)
4. GoWesty technical articles (expert but commercially motivated)
5. TheSamba FAQ threads (community curated)
6. TheSamba general threads (use with caution — verify key facts)

---

## Vehicle Context
The primary vehicle this wiki is built around:
- 1987 VW Vanagon Westfalia
- 2.1L Wasserboxer (WBX) engine
- Automatic transmission
- 2WD
- Named: Luna
- Owner: Jay, full-time van life, Eastern Sierra Nevada
- Current mileage: ~202,000+

Most content should be applicable to all 1980-1991 Vanagons.
Note Syncro (4WD) differences where known.

---

## Vanagon Model Years Quick Reference
- **1980-1982** — Air-cooled 2.0L CT/CU engine
- **1983-1985** — 1.9L Wasserboxer DH engine (early WBX)
- **1986-1991** — 2.1L Wasserboxer MV engine + Digifant EFI (late WBX)
- **1986-1991** — Syncro 4WD available
- All years: 2WD unless noted as Syncro
