# Security Policy

## Supported Versions

Security fixes are provided for the latest released version of `mcp-shell-server` and the current `main` branch. Older releases may contain known execution-boundary weaknesses and should be upgraded before being exposed to untrusted clients.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories for this repository when available, or by contacting the maintainer listed in the package metadata. Do not open a public issue with exploit details until a fix is available.

When reporting, include:

- affected version or commit,
- server configuration relevant to execution policy (`ALLOW_COMMANDS`, `ALLOW_PATTERNS`, timeout/output/env settings),
- a minimal reproduction command payload,
- expected and observed behavior,
- whether sensitive output, path escape, or command execution outside policy occurred.

The project treats command allowlist bypass, shell interpretation of user-controlled input, redirection path escape, parent environment secret exposure, missing execution limits, and missing auditability as security-sensitive issues.

## Security Model

`mcp-shell-server` validates command names and arguments, executes normal commands and pipelines through argv-based subprocess APIs, constrains redirection targets to the requested working directory, supplies a minimal child environment, enforces timeout/output limits, and emits structured audit logs with secret-like argv redaction.

This is not a complete sandbox. Allowed programs still run with the privileges of the server process. Deploy the server with least-privilege OS users, tightly scoped working directories, conservative allowlists, and external sandboxing when clients are not fully trusted.
