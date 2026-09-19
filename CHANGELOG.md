# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Emit one operator warning during server startup stating that allowed commands run with the server process's OS authority and that untrusted input requires external OS isolation. The warning goes through the existing logger (stderr); MCP stdout framing, tool names, request/response schemas, and environment variables are unchanged.

### Changed
- Define the trusted-execution security contract in README.md, SECURITY.md, and the `shell_execute` tool description. `ALLOW_COMMANDS` and `ALLOW_PATTERNS` are documented as controlling only the executable names the server launches directly, not as containment of an allowed program's child processes, interpreters, configuration, filesystem access, or network access. Existing command-specific rejection rules are retained and described as non-exhaustive defense in depth, and the introductory description no longer presents the package itself as a complete secure sandbox.
- SECURITY.md now separates guarantees from non-guarantees, states that a trusted MCP client does not make the content it processes trusted, gives concrete external-isolation requirements (least-privilege identity, filesystem scope, network restrictions, credential exclusion, descendant-process containment, resource limits), and defines the vulnerability-reporting scope against the same threat model.

## [1.1.12] - 2026-09-19

### Security
- Reject persistent `git config` invocations prefixed by the value-taking `--attr-source` or `--shallow-file` global options. This closes argument-parser mismatches that could bypass the existing `git config` policy and persist an executable Git alias. Tracked as [GHSA-7v25-vcp6-4hcr](https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-7v25-vcp6-4hcr). Versions `<=1.1.11` are affected; upgrade to `1.1.12` or later.

## [1.1.11] - 2026-09-18

### Security
- Reject GNU awk `@nsinclude` program-source directives, completing the external-source hardening introduced in 1.1.10. Versions `<=1.1.10` are affected; upgrade to `1.1.11` or later.

### Fixed
- Preserve AWK option-parser state so option terminators, inline program boundaries, and values consumed by safe options are not misclassified as dangerous options.

## [1.1.10] - 2026-09-18

### Security
- Reject AWK program-source and extension-loading options that bypass argv program inspection, including GNU long options, accepted abbreviations, short forms and clusters, `-W` aliases, and `@include`/`@load` directives. Tracked as [GHSA-8wm7-jvxq-2r3m](https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-8wm7-jvxq-2r3m). Versions `<=1.1.9` are affected; upgrade to `1.1.10` or later.

## [1.1.9] - 2026-08-15

### Security
- Reject GNU `sort` arguments that escape the command-name allowlist or the requested working directory. When `sort` (or its `gsort` alias) is allowlisted, `--compress-program` could launch a non-allowlisted executable once sorting spilled to temporary files, `-o`/`--output` could write directly to any process-accessible path without passing through the server's contained redirection handler, `--files0-from` could read an attacker-selected file list, and `-T`/`--temporary-directory` could place temporary files outside the requested working directory. These options are now rejected before subprocess creation in separated, attached, equals, clustered, and uniquely abbreviated GNU forms (`--co`, `--o`, `--fil`, `--t`, `-oFILE`, `-ro FILE`, `-TDIR`, `-rT DIR`), including options permuted after operands; parsing stops at a discrete `--` so option-like filename operands remain data. Ordinary sorting, `-S`/`--buffer-size`, and other ordering options are unaffected. Tracked as [GHSA-74g6-ch7r-v7jr](https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-74g6-ch7r-v7jr). Versions `<=1.1.8` are affected; upgrade to `1.1.9` or later.

## [1.1.8] - 2026-08-08

### Security
- Preserve literal pipe characters inside argv arguments. `CommandPreProcessor.preprocess_command()` split any argument containing `|` and inserted a synthetic pipeline boundary, which corrupted argument data such as regular expressions, URLs, and JSON, let a trailing pipe like `"text|"` smuggle a following argument into an independently executed pipeline stage, and stripped pipe characters before command-specific policies (for example `awk`) could inspect them. Pipeline syntax is now recognized only from a discrete `|` argv element. Reported as [GHSA-q8pm-q3r2-q7cg](https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-q8pm-q3r2-q7cg) and [GHSA-7wg7-jj87-qp4c](https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-7wg7-jj87-qp4c). Versions `<=1.1.7` are affected; upgrade to `1.1.8` or later.

### Changed
- **Breaking:** An attached pipe such as `["ls|", "grep", "x"]` is no longer implicitly converted into a pipeline. Clients MUST express pipelines with a discrete `|` argv element, for example `["ls", "|", "grep", "x"]`.

## [1.1.7] - 2026-08-04

### Security
- Reject version-suffixed Python interpreter names such as `python2` and `python3.11`, including absolute-path forms, when admitted through command patterns.

## [1.1.6] - 2026-08-04

### Security
- Reject persistent `git config` invocations, common alternate binary names for hardened command families (`gawk`, `gfind`, `gtar`, `bsdtar`), and command-wrapper/shell-escape tools that can execute non-allowlisted commands through their arguments.
- Document that command hardening is best-effort defense in depth and not a complete sandbox for broad or untrusted command allowlists.

## [1.1.5] - 2026-08-02

### Security
- Require MCP Python SDK `>=1.28.1` to address [GHSA-vj7q-gjh5-988w](https://github.com/advisories/GHSA-vj7q-gjh5-988w), where the WebSocket server transport did not validate Host/Origin headers.

## [1.1.4] - 2026-08-01

### Fixed
- Pin the MCP Python SDK to the v1 line (`mcp>=1.1.2,<2`). Fresh installs resolved MCP SDK 2.x, which removes the low-level `Server.list_tools()` API and crashed the server at import with `AttributeError: 'Server' object has no attribute 'list_tools'` ([#47](https://github.com/tumf/mcp-shell-server/issues/47)).

## [1.1.3] - 2026-07-27

### Security
- Complete argument hardening for [GHSA-gvwf-5g64-3vvw](https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-gvwf-5g64-3vvw). Versions `<=1.1.2` are affected; upgrade to `1.1.3` or later.
- Reject `sed`, including embedded command execution and file access scripts.
- Reject GNU `find` file-output actions (`-fprintf`, `-fprint`, `-fprint0`, and `-fls`).
- Reject AWK external file access and script-file execution.

## [1.1.2] - 2026-07-18

### Security
- Reject all command-scoped Git configuration overrides (`git -c <name=value>` and `git -c<name=value>`). Versions `<=1.1.1` are affected.
- Reject Git external execution through `--config-env`, `--exec-path`, clone configuration, transport program options, and accepted abbreviated forms.

## [1.1.0] - 2026-06-17

### Added
- Made `directory` argument optional, defaulting to the current working directory (closes #11)
- Support for relative directory paths
- New `DirectoryManager` module for centralized directory resolution

### Changed
- Removed `asyncio` from explicit dependencies (standard library)

## [1.0.4] - 2026-06-17

### Security
- Replaced shell-string subprocess execution with argv-based `create_subprocess_exec()` for normal commands and pipelines.
- Hardened `ALLOW_PATTERNS` to use full command-name matching and reject unsafe shell metacharacter forms.
- Rejected default exec-capable bypass vectors including shells/interpreters, `env`, `xargs`, `find -exec`, `awk system()`, `tar --checkpoint-action=exec`, and git external aliases.
- Enforced redirection containment under the validated working directory before file open side effects.
- Isolated child process environments from parent secrets unless variables are explicitly allowlisted.
- Added default/max timeout handling, output byte caps, and structured redacted audit logging.

## [1.0.3] - 2024-12-23

### Added
- Interactive shell support for command execution

### Changed
- Improved login shell detection mechanism
- Enhanced process cleanup on error

### Fixed
- Improved test reliability and coverage
- Fixed pipeline timeout test cases
- Improved redirection handling and tests
## [1.0.2] - 2024-12-18

### Added
- Input/output redirection support in ShellExecutor
- Pipeline execution capabilities
- Process communication timeout handling
- Directory path validation

### Changed
- Improved process cleanup mechanisms
- Enhanced test configuration and organization
- Standardized error handling across the codebase
- Updated MCP dependency to version 1.1.2

### Fixed
- Proper timeout handling in process communication
- Edge case handling in shell command execution
- Warning suppression for cleaner output
- Pipeline command parsing and execution

### Security
- Enhanced directory permission validation
- Improved command validation and sanitization

## [1.0.1] - 2024-12-12

### Added
- Server version display in startup logs

### Changed
- Updated version management system

## [1.0.0] - 2024-12-12

### Added
- Initial release
- Basic shell command execution via MCP protocol
- Command whitelisting functionality
- Standard input support
- Command execution timeout control
- Working directory specification
- Comprehensive output handling (stdout, stderr, status)
- Shell operator validation
- Basic security measures
- GitHub Actions workflows for testing and publishing
