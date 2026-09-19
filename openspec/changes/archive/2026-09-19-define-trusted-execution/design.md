# Design

## Product boundary

The product remains a general-purpose MCP argv executor. Its enforceable in-process boundary is limited to server-controlled behavior: direct executable-name admission, argv-based process creation, contained server-managed redirection, child environment filtering, timeout/output caps, and structured audit logging.

Allowing a program is authority delegation to that program under the server process's OS identity. Program-defined options, configuration, plugins, child processes, filesystem access, and network access are not comprehensively modeled by the server.

## Defense in depth

Retain all current command-specific validators. Describe them as non-exhaustive protections against known dangerous forms, not as a proof that an allowed program is safe. Future documented-policy bypasses, direct allowlist bypasses, unintended shell interpretation, redirection escape, secret exposure, and execution-limit failures remain security-sensitive reports.

## Runtime communication

Emit one warning during server startup using the existing logger. The warning states that allowed commands run with server privileges and that untrusted requests or content require external OS isolation. Logging uses stderr under the existing configuration and must not alter MCP stdout framing.

Do not add an acknowledgement flag in this change. A mandatory opt-in would be a breaking configuration change and needs a separately announced major release.

## Documentation structure

README places the threat model before configuration examples and links operational guidance to SECURITY.md. SECURITY.md defines guarantees and non-guarantees separately, including the distinction between a trusted connection and untrusted content processed by an LLM.

External isolation guidance is concrete rather than saying only “use a container”: least-privilege identity, filesystem scope, network restrictions, credential exclusion, descendant-process containment, and CPU/memory/disk/time limits.

## Verification boundary

These contract-level requirements extend the existing `shell-execution-security` capability rather than creating a second overlapping capability.

Tests check observable contracts:

- startup warning reaches logging/stderr and is emitted once per server start;
- MCP stdout/tool schema remains unchanged except for clarified descriptive text;
- README and SECURITY.md retain required boundary statements;
- complete existing security regression tests continue to pass.
