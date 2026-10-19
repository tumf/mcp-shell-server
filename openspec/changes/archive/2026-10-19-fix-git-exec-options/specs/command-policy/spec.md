## ADDED Requirements

### Requirement: Explicit Git execution subcommands and options MUST be rejected

The server MUST reject grep pager selection through -O, attached/clustered short forms and long open-files-in-pager prefixes; rebase execution through -x, attached/clustered forms and long exec prefixes; every filter-branch invocation; and exact bisect run dispatch. Rejection MUST occur before process creation, even under exact or pattern allowlisting and in any pipeline stage. Global prefix values and subcommand required values MUST NOT be rescanned as options. Unconsumed -- and --end-of-options terminate subcommand parsing. Grep stops parsing at ordinary operands except dashless expression parentheses; rebase continues after operands. Optional values consume attached/equal text only, not the following token. Exact long names take precedence; ambiguous target prefixes may be conservatively rejected without being described as valid executable Git syntax. Non-rebase subcommands MUST retain rejection of --exec and its non-empty prefixes as external-helper selectors; only exact rebase uses contextual exec parsing. Other existing broad Git configuration, upload/receive and external-protocol rules remain full-argv checks. These are finite defense-in-depth rules, not a guarantee of generic Git confinement.

#### Scenario: Reported Git helper paths are blocked

**Given**: Git is explicitly allowed
**When**: grep pager selection, rebase exec, filter-branch or bisect run is requested
**Then**: the specific Git policy rejects before process creation and no helper marker is created

#### Scenario: Option-looking values retain their meaning

**Given**: a benign required option consumes a token resembling -O or -x or --exec
**When**: the invocation is validated
**Then**: that value alone is not treated as a new execution option, while a later real execution option remains blocked

#### Scenario: Ordinary Git operations remain supported

**Given**: Git is allowed
**When**: status, ordinary grep/rebase, bisect start/log/reset or data after end-of-options are supplied without a forbidden operation
**Then**: the new policy permits them subject to existing independent controls
