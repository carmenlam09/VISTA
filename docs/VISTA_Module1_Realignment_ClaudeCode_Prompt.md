# Prompt for Claude Code — Redevelop Module 1 for Alignment with Modules 2-7

> Paste everything below this line into Claude Code, working inside the project root: `C:\Users\tongc\claude_base\vista`

---

## Role

You are the lead engineer on **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process, built module by module in this repo (`C:\Users\tongc\claude_base\vista`). Modules 2 through 7 now exist:

- **Module 2** — Unified Screening Intelligence View
- **Module 3** — Adverse Media Screening Engine
- **Module 4** — Risk Signal Intelligence Engine
- **Module 5** — Risk Assessment Engine
- **Module 6** — Smart Report Generation Engine
- **Module 7** — Vendor Risk Knowledge Repository

Each was built with instructions to inspect and align with whatever came before it. **Module 1 (Digital Intake & Entity Extraction) was built first, before any of those conventions existed, and has never been brought into line with them.** This task is to bring Module 1 up to the same standard — without breaking the six modules that already depend on it.

## Important: This Is a Refactor of Working, Depended-Upon Code — Not a Greenfield Build

Treat this task with more caution than a new module:

- **Module 2 already consumes Module 1's output** (the entity profile: name, aliases, ID numbers, nationality, related entities). Modules 3-7 transitively depend on that same profile flowing through correctly. **Nothing about Module 1's external output contract may change silently.** If aligning Module 1's conventions genuinely requires changing that contract, you must stop, clearly explain the proposed change and its downstream impact, and get my explicit approval before touching it — do not treat this the same as an internal styling choice.
- **Work on a separate git branch.** Before making any changes, confirm this repo is under git; if so, create a branch for this work (e.g. `refactor/module1-alignment`) rather than committing directly to whatever branch Module 1 currently lives on. If the repo isn't under git yet, tell me before proceeding — I want version control in place before this refactor starts, given the blast radius if something goes wrong.
- **Do not modify Module 2-7's code.** If something in Modules 2-7 needs to change to accommodate Module 1's alignment, flag it — don't make the change yourself in this task.

## Objective

Bring Module 1 into alignment with the conventions established across Modules 2-7 — folder structure, virtual environment/dependency setup, schema definition style, testing framework and structure, README format, coding style/linting, and cross-cutting patterns like audit logging and access control — while preserving Module 1's existing external behavior and output contract exactly, unless a change is explicitly discussed and approved.

## Phase A — Audit Only (do not modify any code in this phase)

1. **Read Modules 2 through 7** and build a table of the conventions they actually share: language/framework, folder layout pattern, venv and `requirements.txt` setup, how each defines data schemas (e.g. Pydantic models, dataclasses, JSON Schema), testing framework and test folder structure, README template/sections, linter/formatter configuration, logging and audit-trail pattern, access-control (RBAC) pattern, and configuration management approach (e.g. how config-driven rule/taxonomy files are structured, if Module 1 has an analogous need).
2. **Flag any inconsistencies among Modules 2-7 themselves** — if they don't all agree on something (e.g. two different testing conventions), tell me and ask which should be treated as the canonical house style before you use it as your target for Module 1.
3. **Read Module 1's current code as it stands today** and produce a structured gap report comparing it against the synthesized house style from steps 1-2. Call out every meaningful difference, not just the obvious ones.
4. **Document Module 1's current external output contract exactly as implemented** — the real shape of the entity profile it emits today, field by field. Cross-check it against what Module 2 (and, as far as you can tell, Modules 3-7 transitively) actually expect. If you find any existing mismatch between what Module 1 emits and what downstream modules assume — even before any refactor — report that as a pre-existing issue, separate from the alignment work.
5. **Present the full gap report and a proposed refactor plan to me.** Include, for each proposed change, whether it's purely internal (safe) or touches the output contract (needs my explicit approval). **Do not write any refactor code in this phase.** Wait for my go-ahead on the plan before moving to Phase B.

## Phase B — Execute the Refactor (only after I approve the Phase A plan)

1. Create the git branch (or confirm the one already created) before making any changes.
2. Before changing anything, **capture a contract baseline**: run Module 1 against a representative set of existing input fixtures and save the exact output profiles it produces today. This baseline is what you'll diff against after the refactor to prove zero drift in the output contract.
3. Align folder structure and venv/`requirements.txt` setup to match the pattern used by Modules 2-7 (module in its own top-level folder, its own `.venv`, isolated dependencies, consistent `.gitignore` treatment).
4. Migrate schema definitions, testing framework/structure, README format, and coding style/linter config to match the house style identified in Phase A.
5. Bring Module 1 up to the same cross-cutting standards the other modules follow where applicable — audit logging of extraction runs, and access control on uploaded documents/extracted profiles consistent with the RBAC approach Module 2 established — since Module 1 currently predates those patterns and likely lacks them.
6. **Re-run the contract baseline comparison**: feed the same fixtures through the refactored Module 1 and diff the output against the Phase B step 2 baseline. Any difference must be either zero, or an explicitly approved, intentional change you flag clearly — never an incidental side effect of restructuring.
7. Run Module 1's existing test suite (migrated to the new structure) and confirm nothing that previously passed now fails. If any existing test's *intent* genuinely needs to change because of an approved contract change, call that out explicitly rather than quietly editing the assertion.
8. If feasible, run a lightweight integration check: feed a fixture through the refactored Module 1 and confirm Module 2 can still consume its output without modification.

## Technical Requirements

- **Environment**: Module 1 should end up with its own `module1/.venv` and `requirements.txt`, matching the isolation pattern used by Modules 2-7, using the same Python version as the rest of the platform.
- **Testing**: in addition to migrating existing tests, add the contract-baseline regression test described above as a permanent test in the suite (not a one-off script) so future refactors of Module 1 are protected the same way.
- **Documentation**: update Module 1's README to match the format used by Modules 2-7, and add a section noting this alignment refactor took place, what changed, and — critically — confirming the output contract is unchanged (or documenting exactly how it changed, if approved).

## Assumptions & Ambiguity

Where a convention among Modules 2-7 is genuinely ambiguous or inconsistent, ask rather than guess (per step A2). Where something is a clear internal styling choice with no contract or behavioral impact, use your judgment and note it in the README. Anything touching the output contract, or Modules 2-7's own code, requires my explicit approval — no exceptions.

## Definition of Done

**Phase A:**
- [ ] Conventions used by Modules 2-7 are documented, with any inconsistencies among them flagged and resolved with me
- [ ] Module 1's current state is fully audited against that house style
- [ ] Module 1's current real output contract is documented and cross-checked against downstream expectations, with any pre-existing mismatches reported separately
- [ ] A refactor plan is presented, with contract-impacting changes clearly distinguished from internal-only changes, and I've approved it before Phase B begins

**Phase B:**
- [ ] Work happened on a dedicated git branch
- [ ] A pre-refactor output baseline was captured and used to verify zero unintended drift post-refactor
- [ ] Folder structure, venv/dependency setup, schema style, testing framework, README format, and lint/style config match Modules 2-7
- [ ] Audit logging and access control are in place consistent with Module 2's pattern
- [ ] All previously-passing tests still pass; any changed test intent is explicitly called out
- [ ] A permanent contract-regression test now guards Module 1's output shape going forward
- [ ] Module 2 can still consume Module 1's output without any change on Module 2's side (unless an approved contract change says otherwise, in which case that's documented)
- [ ] README updated to reflect the new structure and confirm (or document) the output contract status
