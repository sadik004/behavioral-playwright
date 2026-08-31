# SQ — V23 Port Audit & Hardening Workspace

This workspace is the audit and hardening site for evaluating and reconciling
capabilities from the supplied **Hardened Evasion Suite v23**
(`bp_biomechanical_engine-v23.py`) against the **protected personal baseline**
(`behavioral_evasion_ten_patches_hardened_v15.py`).

## Contents

| Path | Role |
| --- | --- |
| `behavioral_evasion_ten_patches_hardened_v15.py` | Protected baseline framework (Phase 2 honesty-hardened; authoritative) |
| `bp_biomechanical_engine-v23.py` | Supplied V23 source under audit (quarantined — not integrated) |
| `evasion_v23_documentation.md` | Supplied V23 marketing/spec document (claims audited against source) |
| `itch_binary.py` | NEW: genuine ITCH-5.0 binary subset parser (Phase 3; isolated module) |
| `tests/` | 48 tests: baseline protection, V23 quarantine pins, honesty hardening, ITCH binary |
| `docs/development/current-checkpoint.md` | Live capability status, quarantine register, resume point |
| `docs/development/v23-port-audit-report.md` | Full V23 PORT AUDIT REPORT (initial audit) |
| `docs/development/v23-reconciliation-report.md` | Phase 1–5 hardening & reconciliation report |

## Honesty constitution (binding)

- REAL RESULT → return it.
- REAL FAILURE → raise/report it.
- UNIMPLEMENTED → explicitly quarantine it.
- NEVER → fabricate successful output (no fake payloads, fake addresses, fake status strings).

## Test suite

```bash
python -m pytest tests -q    # 48 passed (0 failed, 0 skipped)
```

- `test_baseline_protection.py` — 13 tests protecting legacy baseline behavior.
- `test_v23_quarantine.py` — 7 pins proving the rejected V23 theater cannot resurface.
- `test_honesty_hardening.py` — 10 tests pinning the five Phase 2 honesty fixes.
- `test_itch_binary.py` — 18 tests for the verified-layout ITCH-5.0 binary parser
  (golden fixtures + truncation/unknown-type/lifecycle negative tests).

## Git

Local repository on branch `main`. Two commits: the protected V23-audit baseline
and the Phase 1–5 hardening release. **No remote; nothing pushed.**
