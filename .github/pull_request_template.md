## DAG node and requirements
- Node: <!-- e.g. E1 -->
- Requirement IDs: <!-- e.g. RT-02, NFR-L3 -->

## What changed
<!-- Short description. Spec or design changes must update REQUIREMENTS.md / SDD.md in this PR (CLAUDE.md rule 2). -->

## TDD evidence
- [ ] Failing tests committed before implementation (link the `test(...)` commit)
- Test results: <!-- paste summary, including coverage -->

## Security-Agent report
<!-- Semgrep, gitleaks, Trivy, licence gate results; justify any accepted finding -->

## Validator-Agent report
<!-- Line-by-line check against the cited requirement IDs: nothing missing, no feature creep -->

## Checklist
- [ ] No personal or biometric data in code, fixtures, logs or snapshots
- [ ] Any new model is in `models/registry.yaml` and passes `make licence-check`
- [ ] ADRs and docs updated where decisions changed
