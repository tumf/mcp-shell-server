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

### Reporting scope

The project treats the following as security-sensitive, regardless of the trusted-execution definition below:

- bypass of the direct command-name allowlist (`ALLOW_COMMANDS` / `ALLOW_PATTERNS`),
- unintended shell interpretation of user-controlled input,
- escape from server-managed `<`, `>`, or `>>` redirection containment,
- exposure of parent-process environment secrets or of secret material in logs,
- failure of the timeout or output-byte execution limits,
- missing or unusable audit records,
- any demonstrated bypass of a boundary this documentation states the server enforces directly, including an explicitly documented command-specific rejection rule.

A documented limitation is a statement about what the server does not model. It never waives security treatment for a defect in a boundary the server claims to enforce.

Out of scope as a vulnerability report: behavior of an allowed program that stays within the server process's OS authority — for example an allowed program reading files the server process can read, opening a network connection, or spawning a child process — when no documented rejection rule or enforced boundary was bypassed. That is the delegated authority described below, and containing it is the deployment's responsibility.

## Security Model

### Trusted execution contract

`mcp-shell-server` is a trusted execution tool, not a sandbox. Allowing a command delegates that program the server process's existing OS authority: its user identity, filesystem access, network access, and credentials.

`ALLOW_COMMANDS` and `ALLOW_PATTERNS` restrict only the executable names the server launches directly. They do not guarantee containment of an allowed program's child processes, program-specific interpreters or plugins, configuration files it reads on its own, filesystem access outside server-managed redirection, or network access.

The server states this contract once at startup as an operator warning through its logger, which writes to stderr. MCP stdout framing is unchanged.

### Guarantees

Within the server's own behavior, `mcp-shell-server` validates command names and arguments, executes normal commands and pipelines through argv-based subprocess APIs, constrains redirection targets to the requested working directory, supplies a minimal child environment, enforces timeout/output limits, and emits structured audit logs with secret-like argv and per-call environment metadata redaction.

### Non-guarantees

The server does not guarantee, and does not attempt to model:

- what an allowed program does with its own options, expression languages, plugins, or configuration,
- the behavior or lifetime of child processes an allowed program spawns,
- filesystem reads and writes an allowed program performs itself,
- network access an allowed program performs itself,
- credential or secret material reachable from the server process's OS identity,
- resource consumption beyond the server's timeout and output-byte caps.

A trusted, authenticated MCP client does not make the content it processes trusted. Model-provided text, fetched pages, issue text, and repository contents are untrusted input even over a trusted connection, and an LLM can be induced to construct a request from that content. Client authentication is not a substitute for the deployment isolation described below.

### Defense in depth

Default argument hardening rejects known exec-capable bypass vectors before subprocess creation. These checks are non-exhaustive protections against known dangerous forms, not a proof that an allowed program is safe. They include `find -exec`, shell/interpreter launchers, `awk system()`, `tar --checkpoint-action=exec`, `env`, `xargs`, common alternate names such as `gawk`/`gfind`/`gtar`, command-wrapper tools such as `timeout`/`nice`/`nohup`, and shell-escape tools such as `sed`/`less`/`vim`/`ssh`. For an allowlisted GNU `sort` (or its `gsort` alias), options that select an external compression program, a direct output path, an external input file list, or an external temporary directory are rejected: `--compress-program`, `-o`/`--output`, `--files0-from`, and `-T`/`--temporary-directory`, in separated, attached, equals, clustered, and uniquely abbreviated forms such as `--co`, `--o`, `--fil`, `--t`, `-ro FILE`, and `-rT DIR`. Option parsing follows GNU permutation and stops only at a discrete `--`, so option-like filename operands after `--` remain data. Clients that need sorted output in a file should use the server's contained `>` redirection, which constrains the target to the requested working directory. Git command-scoped configuration overrides are rejected categorically: every `git -c <name=value>` and `git -c<name=value>` form is rejected when `git` is allowlisted, and persistent `git config` invocations are rejected by default.

### Audit logging

Audit events are structured `mcp-shell-server.audit` records for success, validation rejection, timeout, output-cap, and process-error outcomes. They include command metadata, resolved directory, redirection flags, timeout/output limits, output byte counts, return code when available, duration, and result type. They intentionally exclude raw stdout/stderr content. Secret-like names or values are replaced with `[REDACTED]`, and long non-numeric values are logged only as short SHA-256 digests.

## Deployment guidance

Containment of an allowed program is the deployment's responsibility. If any request, or any file the server can reach, may derive from untrusted input, run the server inside an independently enforced OS boundary (container, VM, jail, or OS policy) that provides:

- **Least-privilege identity** — a dedicated non-root user with no administrative rights on the host.
- **Filesystem scope** — only the directories the workload needs, mounted read-only where possible, with host configuration, SSH keys, and cloud credential files unreachable.
- **Network restrictions** — egress denied by default, allowing only the destinations the workload requires.
- **Credential exclusion** — no ambient tokens, cloud instance-metadata access, or agent sockets reachable from the server process.
- **Descendant-process containment** — a process/cgroup namespace so processes spawned by an allowed program are bounded and reaped with the sandbox.
- **Resource limits** — CPU, memory, disk, process-count, and wall-clock caps enforced outside this package.

Additionally keep allowlists conservative and working directories tightly scoped. These reduce exposure but do not replace the boundaries above.
