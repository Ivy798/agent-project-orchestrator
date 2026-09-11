# Security Policy

## Supported version

Security fixes are applied to the latest release line.

## Reporting

Please do not publish an exploit, credential, or destructive proof-of-concept in a public issue. Use GitHub private vulnerability reporting when enabled for the repository, or contact the repository owner through the private security channel they publish.

## Trust model

Agent Project Orchestrator is a local project-control tool. It assumes the human owner controls the repository and local machine.

Important boundaries:
- the controller is the only writer to the operational ledger;
- task agents should not receive unnecessary production credentials;
- secrets must not be stored in task files, ledger state, logs, or PR bodies;
- GitHub integration shells out to the locally installed/authenticated `gh` CLI;
- APO never treats GitHub review as final permission to merge;
- APO does not automatically merge the stable branch or deploy production.

## Threats intentionally not solved in v1.2

- malicious local administrator/root;
- compromised Git executable or GitHub CLI;
- cryptographically verified human approver identity;
- hostile multi-tenant agents sharing one controller state;
- centralized remote scheduler compromise.

Use OS-level isolation, least-privilege credentials, protected branches, required status checks, and organization policy when deploying APO in higher-risk environments.
