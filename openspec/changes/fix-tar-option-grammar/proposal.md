---
change_type: implementation
priority: high
dependencies: []
verifications:
  - id: tar-policy-regression
    requirement: Known tar external-program surfaces are rejected before process creation without rescanning benign values
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: tests/test_command_validator.py
    evidence: uv run pytest tests/test_command_validator.py tests/test_shell_executor.py
    rerun: uv run pytest tests/test_command_validator.py tests/test_shell_executor.py
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
---
# Fix tar option grammar

**Change Type**: implementation

## Problem / Context
Current tar hardening matches exact long names and a leading -I token, missing GNU abbreviations, short-option clusters and old-style option words. Isolated GNU tar 1.34 and full ShellExecutor reproduced markers with abbreviated checkpoint/compression/to-command/rsh options and -I clusters. Adjacent info-script/new-volume-script/-F also execute helpers. The same parser mechanism owns all these forms. tar remains allowed; this is not a sandbox.

## Proposed Solution
Add one tar-specific scanner parameterized by finite GNU and BSD option tables in command_validator.py. Run both interpretations independently and reject if either reaches a forbidden option; reuse existing basename normalization for tar/gtar/bsdtar and current policy error. Do not select a dialect by executable spelling or runtime subprocess. Do not create a generic parsing framework or dependency.

Long-option resolution MUST use the GNU tar 1.34 option-name/arity table and a separate libarchive bsdtar 3.5.3/3.7.4 union table: exact name wins; otherwise all prefix candidates participate. Block a token with any forbidden candidate. For benign abbreviation, consume the next token ONLY if it resolves uniquely to a required-value option; ambiguous unknown options do not consume. All benign options with required values skip attached/equal or following values; optional values consume only equals/attached form, never the next token. Unknown names must not manufacture value consumption. Include the no-argument names checkpoint, list, sparse and xattrs so they cannot be confused with required-value prefixes.

Forbidden long options: checkpoint-action (reject every action, including non-exec, to avoid a hidden secondary action grammar), use-compress-program, to-command, rsh-command, rmt-command, info-script, new-volume-script. Cover separated/equal and all GNU-accepted prefixes. Reject short I and F anywhere in real short-option clusters, including attached/separate values and first-position old-style words without a hyphen.

GNU ordinary short options with required values are g,f,L,F,b,H,V,I,K,N,C,T,X. For hyphen clusters, a required-value option consumes the remaining suffix or next argv token and stops scanning that cluster; do not rescan the value. First-position old-style word parses all letters as options and consumes each required argument from subsequent tokens in order, even when a value is --. For old-style words reject I/F before skipping their values. Continue option scanning after non-option operands because GNU tar permutes options; old-style parsing applies only to argv[1]. Only a standalone -- not already consumed as an option value ends option scanning. GNU tar -W means verify and MUST NOT consume the following token in the GNU walk. The BSD walk uses required short b,C,f,I,s,T,W,X; H/L are no-value. BSD parsing stops at the first ordinary operand. A bare - token not consumed as a required value is an empty short group in BSD and MUST NOT end scanning. GNU treats it as an ordinary operand but continues due to permutation. BSD hyphen-style W consumes its attached or next text as a long option (with exact/prefix/arity resolution); old-style W merely consumes its argument and does not dispatch a long option. Preserve independent cursor state for the two walks. Required values are not rescanned within the same dialect, but a value in one dialect may be an actual option in the other. Never replace the two walks with a merged short-arity table.

Use upstream option tables as the reviewed finite source, comment their provenance/versions. GNU argp hidden program-name/HANG remain unknown (no guessed consumption). BSD long names and arities use the table below; BSD has no optional long values. The common exact totals flag is optional in GNU but no-value in BSD; --mo/--mod resolve to required mode in GNU and no-value modification-time in BSD, so independent walks are mandatory. Table size is justified by exact-name/arity shadows; a required-only table would swallow real bypasses. Do not parse file-list contents or every tar filesystem action. Do not remove unrelated helpers still used by git.

## Acceptance Criteria
- Unit rejection matrix covers every spelling/prefix of the seven forbidden long names, -I/-F clusters/attached/old style, aliases and options after operands.
- Benign tar create/list/extract, compression switches z/j/J, checkpoint numeric interval, optional-value flags, actual -- operands, safe values containing I/F or dangerous-looking option strings remain usable when both dialect interpretations treat them as data, subject to other checks. Dialect conflicts are deliberately rejected rather than risk helper execution; document this compatibility impact.
- Tests cover each required short value option, all benign required long options, and exact-name shadows checkpoint/list/sparse/xattrs followed by an otherwise blocked option. -f -- does not terminate scanning. -W does not swallow the next option.
- Real ShellExecutor rejection tests install harmless marker helpers and assert zero process launches and no archive/marker output. Normal success tests create/list an archive. Pipeline stages get the same policy.
- Tests of policy-only rejection must run without GNU tar or bsdtar. Real dialect execution smoke may skip only for an explicitly missing binary; parent runs real GNU tar in an offline disposable Linux container and bsdtar locally before release. Add H/L followed by forbidden long options, -cHWuse-compress-program=P, old cHf/cLf, -W attached/separated/prefix forms, --mo/--mod preceding helper options, totals, W benign required/no-value and old W controls. Include --rm spelling. Add -c - -L --use-compress-program P -f - x and the H variant as rejection cases; benign -c -f - - remains allowed.
- README/SECURITY/changelog and canonical command-policy describe this bounded hardening and compatibility impact: non-exec checkpoint actions are newly denied, ordinary checkpoint intervals stay allowed.

## Change Boundary
command_validator.py, relevant tests (only tests/test_command_validator.py and tests/test_shell_executor.py; no new test module), README, SECURITY.md, CHANGELOG.md, and command-policy delta/canonical only. No PATH, wrapper lists, broad filesystem containment, dependencies, transport or release version changes.

## Explicit Completion Conditions
Focused regression tests pass and include allowed controls and pre-launch side-effect assertions. Full suite, lint, typecheck and archive gate pass. Canonical specification retains existing git/sort/other requirements. No public disclosure, registry calls, or private evidence paths enter tracked proposal or changelog.

## Out of Scope
A complete tar sandbox, file-list recursive validation, fixed-operation APIs, exhaustive future GNU/bsdtar grammar guarantees, unrelated wrapper/path bugs. No new dependency or global refactor.

## Final Validation
uv run pytest tests/test_command_validator.py tests/test_shell_executor.py ; full suite, make lint, make typecheck, cflx openspec validate fix-tar-option-grammar --archive-gate. Parent owns independent exact-diff review and Linux/wheel/PyPI acceptance after integration.

## Fixed BSD long-option table
Sources: https://raw.githubusercontent.com/libarchive/libarchive/v3.5.3/tar/cmdline.c and https://raw.githubusercontent.com/libarchive/libarchive/v3.7.4/tar/cmdline.c. Union of known names; exact names before prefixes. Unknown/ambiguous benign options never consume a guessed next value. Either dialect may conservatively reject a dangerous-prefix ambiguity.

Required-value: `block-size blocking-factor cd directory exclude exclude-from file files-from format gid gname group include newer newer-ctime newer-ctime-than newer-mtime newer-mtime-than newer-than older older-ctime older-ctime-than older-mtime older-mtime-than older-than options owner passphrase strip-components uid uname use-compress-program`.

No-value: `absolute-paths acls append auto-compress b64encode bunzip2 bzip bzip2 check-links chroot clear-nochange-fflags compress confirmation create dereference disable-copyfile exclude-vcs extract fast-read fflags grzip gunzip gzip help hfsCompression ignore-zeros insecure interactive keep-newer-files keep-old-files list lrzip lz4 lzip lzma lzop mac-metadata modification-time no-acls no-fflags no-mac-metadata no-read-sparse no-recursion no-safe-writes no-same-owner no-same-permissions no-xattr no-xattrs nodump nopreserveHFSCompression norecurse null numeric-owner one-file-system posix preserve-permissions read-full-blocks read-sparse safe-writes same-owner same-permissions to-stdout totals uncompress unlink unlink-first update uuencode verbose version xattrs xz zstd`.

New tests must use only the two declared files. Cross-dialect false positives for incompatible grammar are intentional: required-value non-rescanning applies inside each walk, not permission to skip a real helper option in another supported dialect.
