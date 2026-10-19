## ADDED Requirements

### Requirement: Tar external-program policy MUST account for GNU and BSD option grammar

For the tar family including existing aliases, the server MUST reject checkpoint-action, use-compress-program, to-command, rsh-command, rmt-command, info-script and new-volume-script, including equal/separate values and abbreviations whose possible candidates include a forbidden option. All checkpoint actions are denied; numeric checkpoint intervals remain permitted. It MUST reject I/F short options in ordinary clusters and first-position old-style option words. Independent finite GNU and BSD interpretations MUST both be checked and either may reject. GNU H/L consume required values but BSD H/L do not; BSD W aliases a long option in hyphen form, GNU W does not. BSD --mo/--mod MUST NOT consume the next option. Benign required options MUST consume values without rescanning them within each dialect; optional values MUST NOT consume a following token. Exact known long names MUST take precedence over their prefix extensions. A discrete unconsumed -- MUST end parsing, whereas -- consumed as an option value MUST NOT. GNU parsing MUST continue after operands, whereas the BSD interpretation stops at the first ordinary operand, where a bare - is not an operand and MUST NOT terminate scanning. A forbidden option reached only in one dialect still MUST be rejected. These are finite defense-in-depth rules, not a complete sandbox or a guarantee about future program syntax.

#### Scenario: Alternate execution-option spelling is rejected

**Given**: tar or an existing tar alias is allowed
**When**: an external-program option uses a long prefix, short cluster, attached value, or old-style word
**Then**: the server rejects before process creation and neither marker nor archive output is created

#### Scenario: Option-looking value is not scanned

**Given**: a benign required-value option takes an argument containing I/F or a forbidden-looking option name
**When**: tar arguments are validated
**Then**: the consumed value is data within that dialect and a later real option is still checked, while a conflicting executable interpretation in the other dialect is deliberately rejected

#### Scenario: Exact no-value name does not swallow the next option

**Given**: a no-value or optional-value exact long option such as checkpoint/list/sparse/xattrs
**When**: a prohibited option follows without being an equals-attached value
**Then**: the prohibited option is rejected before process creation

#### Scenario: End of options is grammar aware

**Given**: a tar invocation includes --
**When**: -- is a required option value rather than a delimiter
**Then**: later prohibited options remain rejected

#### Scenario: Ordinary archive operations remain supported

**Given**: tar is allowed
**When**: ordinary create/list/extract or built-in compression arguments are supplied without prohibited helper options
**Then**: validation permits the invocation subject to other existing controls
