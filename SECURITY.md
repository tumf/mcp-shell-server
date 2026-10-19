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

Default argument hardening rejects known exec-capable bypass vectors before subprocess creation. These checks are non-exhaustive protections against known dangerous forms, not a proof that an allowed program is safe. They include `find -exec`/`-execdir`/`-ok`/`-okdir` (and the `gfind`/`bfind` aliases), shell/interpreter launchers, JS runtimes such as `deno`/`bun`, `awk system()`, tar external-program options such as `tar --checkpoint-action=exec` (every checkpoint action is denied), `env`, `xargs`, common alternate names such as `gawk`/`gfind`/`gtar`/`bsdtar`, command-wrapper tools such as `timeout`/`nice`/`nohup`/`setarch`/`strace`/`valgrind`, and shell-escape tools such as `sed`/`less`/`vim`/`ssh`. For an allowlisted GNU `sort` (or its `gsort` alias), options that select an external compression program, a direct output path, an external input file list, or an external temporary directory are rejected: `--compress-program`, `-o`/`--output`, `--files0-from`, and `-T`/`--temporary-directory`, in separated, attached, equals, clustered, and uniquely abbreviated forms such as `--co`, `--o`, `--fil`, `--t`, `-ro FILE`, and `-rT DIR`. Option parsing follows GNU permutation and stops only at a discrete `--`, so option-like filename operands after `--` remain data. Clients that need sorted output in a file should use the server's contained `>` redirection, which constrains the target to the requested working directory. For `tar` (and `gtar`/`bsdtar`), `--checkpoint-action` with any action, `--use-compress-program`/`-I`, `--to-command`, `--rsh-command`, `--rmt-command`, `--info-script`, `--new-volume-script`, and `-F` are rejected in separated, `=`, abbreviated, short-cluster, and first-position old-style forms, including after operands. Arguments are parsed with two finite option tables, GNU tar 1.34 and bsdtar 3.5.3/3.7.4, each with its own value consumption, and either interpretation reaching a helper option rejects the command; the executable name never selects a single dialect. Argument lists that one dialect treats as data but the other executes as a helper option are deliberately rejected, and non-`exec` checkpoint actions are denied too, while numeric checkpoint intervals and ordinary create/list/extract with built-in compression remain allowed. This does not validate file-list contents or other tar filesystem behavior and does not guarantee coverage of future tar option syntax. Git command-scoped configuration overrides are rejected categorically: every `git -c <name=value>` and `git -c<name=value>` form is rejected when `git` is allowlisted, and persistent `git config` invocations are rejected by default. Git subcommand execution options are rejected by a finite Git 2.53.0 option grammar: `git grep` pager selection (`-O`, attached and clustered forms such as `-OP`, `-nOP`, `-1OP`, and `--open-files-in-pager` with any non-empty prefix such as `--op`), `git rebase` execution (`-x`, attached and clustered forms such as `-xP`, `-qxP`, and `--exec` with any non-empty prefix such as `--ex`, including after operands), every `git filter-branch` invocation, and `git bisect run` when `run` directly follows `bisect`. On every other subcommand, `--exec` and its non-empty prefixes (`--e`, `--ex`, `--exe`) stay rejected as remote-helper selectors (for example `git push --exec=PROG`). Values consumed by global options (`-C`, `--git-dir`, `--work-tree`, `--namespace`, ...) and by value-taking grep/rebase options (`-e`, `-f`, `--context`, `--onto`, `-s`, `-X`, `--strategy-option`, ...) are data and are not rescanned, so `git grep -e -O data` and `git rebase --onto --exec` are allowed; an unconsumed `--` or `--end-of-options` ends grep/rebase option parsing, and grep also stops at its first operand except for `(`/`)`. Unknown short letters and ambiguous prefixes that include a target (such as `git grep --o=P`) are conservatively rejected. **Compatibility:** `git filter-branch` is rejected categorically, including `git filter-branch --help`. These are finite defense-in-depth rules, not complete Git confinement: hooks, editors, merge strategies, textconv drivers, and other Git configuration-driven helpers remain delegated authority. Dangerous names are rejected categorically, including version or attach-only forms, and no allowlist entry or flag overrides that rejection.

These rejections are a finite list of known names and argument forms; the policy does not recognize every program capable of launching helpers or other programs. Programs you allowlist keep their own delegated behavior: `make` recipes run their own commands, and `dd`/`tee` read and write the paths named in their own operands (`of=`, file arguments) with the server process's OS authority. Those program-owned operations are delegated, not contained, and are not blocked by validation. Hostile or untrusted workloads require external least-privilege OS/container isolation.

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
