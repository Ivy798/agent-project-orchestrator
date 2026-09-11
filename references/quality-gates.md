# Quality Gates

## State-machine intent

The CLI enforces legal task transitions and anchors evidence to the current task commit.

### ready_for_merge

Requires locally:
- current state `review`;
- configured task branch exists;
- configured commit exists and equals task branch HEAD;
- task worktree exists and is clean;
- every `required_check` is `pass` for the current commit;
- independent review is `passed` for the current commit.

If GitHub policy is enabled, the transition performs a **live** GitHub lookup and can additionally require:
- an OPEN non-draft PR;
- PR head SHA equal to the current task commit;
- PR base equal to the stable branch;
- no reported merge conflict;
- all GitHub required checks passing;
- optional GitHub `APPROVED` review decision.

### approved

Requires:
- `ready_for_merge`;
- explicit human `--by` value recorded with timestamp and current commit.

GitHub approval does not replace this final project-owner gate.

### merged

Requires:
- `approved`;
- recorded task commit is integrated into the stable branch.

APO intentionally does not auto-merge the stable branch.

### deployed

Requires:
- `merged`;
- explicit deployment evidence.

## GitHub integration

Use `gh` through:

```bash
apo github preflight
apo github configure --enabled --require-pr --require-checks
apo pr create TASK-001 --push
apo pr status TASK-001
apo pr checks TASK-001
```

Do not trust a stale PR snapshot for `ready_for_merge`; the gate performs a live lookup when remote gating is enabled.

## Independent review

For non-trivial changes use a separate reviewer perspective. Review acceptance criteria, architecture drift, security, migrations, stale code, error handling, operator impact and regressions.

The reviewer should construct failure cases, not only inspect the happy path.

## Frontend runtime gate

Run the actual app. Inspect browser console/network and representative desktop/tablet/phone widths. Compare to approved UI reference if present. Build success alone is not acceptance.
