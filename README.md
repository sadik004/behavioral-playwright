# SQ — V23 Port Audit Workspace

This workspace is the audit site for evaluating three capabilities from the supplied
**Hardened Evasion Suite v23** (`bp_biomechanical_engine-v23.py`) against the
**protected personal baseline** (`behavioral_evasion_ten_patches_hardened_v15.py`).

## Contents

| Path | Role |
| --- | --- |
| `behavioral_evasion_ten_patches_hardened_v15.py` | Protected baseline framework (DO NOT rewrite; additive changes only) |
| `bp_biomechanical_engine-v23.py` | Supplied V23 source under audit (quarantined — not integrated) |
| `evasion_v23_documentation.md` | Supplied V23 marketing/spec document (claims audited against source) |
| `tests/` | Regression + quarantine guard tests added by the audit |
| `docs/development/current-checkpoint.md` | Live capability status, quarantine register, resume point |
| `docs/development/v23-port-audit-report.md` | Full V23 PORT AUDIT REPORT |

## Honesty constitution (binding)

- REAL RESULT → return it.
- REAL FAILURE → raise/report it.
- UNIMPLEMENTED → explicitly quarantine it.
- NEVER → fabricate successful output (no fake payloads, fake addresses, fake status strings).

## Test suite

No test suite existed before the audit (baseline count: 0). Run with:

```bash
python -m pytest tests/ -v
```

The suite (a) protects the baseline's existing working capabilities and
(b) pins the quarantined V23 theater so it cannot silently resurface as a
"real" capability.

## Git

There is **no git repository** in this directory. No commits, no remote, nothing
pushed. See the checkpoint document for the recommended next-phase step.
