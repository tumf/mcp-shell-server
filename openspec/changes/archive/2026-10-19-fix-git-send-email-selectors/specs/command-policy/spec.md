## ADDED Requirements

### Requirement: Git send-email external-program selectors MUST be rejected before execution

For exact send-email after global Git options, the server MUST recognize the finite Git 2.53.0 three-pass Getopt::Long grammar and reject reachable sendmail-cmd, to-cmd, cc-cmd and header-cmd selections. It MUST reject smtp-server values that are missing, empty, rooted by slash/backslash or ASCII drive-letter-colon prefixed, while permitting ordinary SMTP host values subject to other policy. Names MUST be case-insensitive, accept double/single-dash and plus prefixes, resolve exact aliases before unique prefixes, and preserve early-pass residual argv and required/optional value consumption. Ambiguous prefixes with a protected candidate MAY reject conservatively. An unconsumed -- MUST terminate each pass, while a consumed -- MUST remain data; --end-of-options is not a terminator for this grammar. Permutation continues after operands. Selection MUST reject even if dry-run, overrides or later flags could suppress execution. This is a finite defense-in-depth rule, not generic Git confinement or a promise of Windows runtime isolation.

#### Scenario: Explicit helper selection is rejected

**Given**: Git is admitted through an exact, absolute-name or pattern allowlist
**When**: any protected send-email program selector is supplied, including supported prefix/case/dash variants or a pipeline stage
**Then**: the specific Git policy rejects before process creation and no helper or output marker is created

#### Scenario: SMTP and data-value neighbors remain allowed

**Given**: an ordinary SMTP host, help/dry-run, benign exact neighboring option or option-looking consumed value
**When**: no protected selector remains after the three recognition passes
**Then**: this selector policy permits it subject to all existing independent controls

#### Scenario: Early passes and delimiter consumption do not hide selectors

**Given**: identity/help passes, option-looking required values, optional flags, malformed numeric values or operands before a selector
**When**: the frozen grammar leaves a reachable protected selector
**Then**: the selector is rejected, while data after an unconsumed -- is not rescanned
