# Security and Data Handling

**Purpose:** describe responsible handling of data produced by the simulator.

## Authorization
- Obtain written approval from IT, HR, and Legal before running campaigns outside a test environment.
- Exclude sensitive groups (HR, Legal, executives, protected users).

## Data minimization & retention
- Store only minimal identifiers (email, cohort, employee_id).
- Rotate or anonymize tokens after reporting.
- Default retention: raw event data retained for 30 days unless otherwise required by policy. Exported CSVs should be removed or archived securely after use.

## Access control
- Protect `sim.db` and `exports/` with file system permissions.
- Admin endpoints must be protected before production use.

## Responsible disclosure
- If a security issue is found, contact the repository owner or the security contact listed in `CONTRIBUTING.md`.

