# Frozen Git send-email recognizer

Authority: Git v2.53.0 git-send-email.perl (https://github.com/git/git/blob/v2.53.0/git-send-email.perl), Documentation/git-send-email.adoc, and Getopt::Long defaults with pass_through. This is finite defensive recognition, not a full mail client or Perl interpreter. Keep parser tables auditable.

## Tables (the suffix is arity, | introduces aliases, ! allows negation)

```json
[
  [
    "identity=s",
    "no-identity"
  ],
  [
    "h",
    "dump-aliases",
    "translate-aliases"
  ],
  [
    "sender|from=s",
    "in-reply-to=s",
    "reply-to=s",
    "subject=s",
    "to=s",
    "to-cmd=s",
    "no-to",
    "cc=s",
    "no-cc",
    "bcc=s",
    "no-bcc",
    "chain-reply-to!",
    "sendmail-cmd=s",
    "smtp-server=s",
    "smtp-server-option=s",
    "smtp-server-port=s",
    "smtp-user=s",
    "smtp-pass:s",
    "smtp-ssl",
    "smtp-encryption=s",
    "smtp-ssl-cert-path=s",
    "smtp-debug:i",
    "smtp-domain:s",
    "smtp-auth=s",
    "no-smtp-auth",
    "imap-sent-folder=s",
    "use-imap-only!",
    "annotate!",
    "compose",
    "quiet",
    "cc-cmd=s",
    "header-cmd=s",
    "no-header-cmd",
    "suppress-from!",
    "suppress-cc=s",
    "signed-off-cc|signed-off-by-cc!",
    "cc-cover!",
    "to-cover!",
    "confirm=s",
    "dry-run",
    "envelope-sender=s",
    "thread!",
    "validate!",
    "transfer-encoding=s",
    "mailmap!",
    "use-mailmap!",
    "format-patch!",
    "8bit-encoding=s",
    "compose-encoding=s",
    "force",
    "xmailer!",
    "batch-size=i",
    "relogin-delay=i",
    "git-completion-helper",
    "v=s",
    "outlook-id-fix!"
  ]
]
```

## Parser environment union

Evaluate all three passes twice: default permutation and POSIXLY_CORRECT require_order. The latter disables abbreviations and plus prefixes, and stops at the first unknown/non-option/invalid option. Reject if either reaches a protected selector. This is deliberately environment-independent; it can reject data consumed only in the default interpretation. Required-string and optional-string consumption otherwise retain their stated rules, with optional values recognizing only dash prefixes as option-like in require_order mode. Invalid equals-attached integers remain residual tokens in both modes. `--subject --identity=work --sendmail-cmd=DATA` and `--subject --identity --sendmail-cmd=DATA --sendmail-cmd=DATA2` are rejected, because require_order leaves a real selector reachable.

## Algorithm

1. Existing _git_subcommand_index resolves exact send-email; never scan operand strings to guess the subcommand. Run this recognizer on the tokens after it. Preserve all existing independent Git rejection scans unchanged.
2. Sequentially process the three tables over residual tokens. Start every pass at index zero of that pass's residual argv. Unknown, ambiguous, and ordinary tokens are retained and never consume an invented value; continue past operands. Recognized valid entries and their genuinely consumed values are removed before the next pass. Invalid options remain residual tokens: a no-value flag with `=...` (even empty), an empty equals-attached required string, and missing/invalid required values MUST NOT be discarded. They may become a later pass's option value; deleting them can hide a real selector. Main-pass protected-selector rejection still occurs before retaining its malformed/missing value. An unconsumed standalone -- and all its following tokens are retained unchanged and terminate that pass; later passes also see that barrier. No other token (not --end-of-options) is a terminator. A -- consumed as required string data is not a barrier.
3. Recognize --NAME, -NAME and +NAME (nonempty names); strip exactly one prefix, split the first =, ASCII case-fold names. No short clusters or attached-without-equals long values. Exact aliases win before prefix candidates. Build names for ! flags with both noNAME and no-NAME spellings and arity none. Explicit no-* entries have their stated arity. Canonical aliases resolving to the same option MUST deduplicate prefix candidates. Only a unique benign candidate consumes a value. Any main-pass ambiguous prefix with a prohibited-selector candidate rejects conservatively (smtp-server ambiguity rejects even when no absolute value is known).
4. Required string =s consumes attached/equal text or exactly one next token, even option-looking data and --. Do not scan that consumed value. Missing benign values must not hide a subsequent selector. Required int =i consumes a separated next token only if ASCII signed decimal (optional plus/minus then digits); invalid input remains nonconsuming and later selectors are scanned. No-value flags consume no next token.
5. Optional string :s consumes equals text or one ordinary non-option next token (neither --/-/+ prefix with nonempty following text, nor standalone --); else consumes none. Optional int :i consumes equals text or a valid ASCII signed decimal next token only; never swallow a selector. Empty equals values never consume a following token. Empty required-string `=s` options remain in the residual argv; optional-string `:s` empty values are valid. No-value flags with any equals attachment remain in the residual argv. Unknown/invalid tokens do not stop scanning. These rules are intentionally fail-closed around malformed numeric inputs, not an assertion that Git accepts them.
6. In the main pass, reject resolved sendmail-cmd/to-cmd/cc-cmd/header-cmd regardless of value, overrides, dry-run, or later suppressing flag. For resolved smtp-server obtain its required value; reject absent/empty, startswith '/' or '\', or ASCII /^[A-Za-z]:/. Do not inspect filesystem existence and do not collapse or resolve paths. State conservative drive-relative/rooted false positives in docs. Retain SMTP hostname/IP/relative values. Exact smtp-server-option and smtp-server-port are data options and take precedence.
7. Raise the existing GIT_EXTERNAL_PROGRAM_ERROR. No spawning, filesystem, config, or network lookup during validation. Keep earlier Git config/ext/upload/receive/exec rules; tests should not incorrectly demand relaxing their known broad behavior.

## Required regression inventory

Each line is relative to git send-email unless global context is stated. P is a fixture-only absolute helper path; no test may send mail.

Reject:
- --smtp-server=P, --smtp-server P, -SMTP-SERVER=P, +smtp-server=P.
- --sendmail-cmd=P, --sendmail-cmd P, -SENDM=P, +sendm=P; to-cmd/cc-cmd/header-cmd equal and separate.
- Each target with missing/empty value, dry-run, later replacement, or no-header-cmd (smtp-server missing/empty is explicitly conservative).
- Unique prefixes --sendm and --header-c; ambiguous --cc-c, --to-c, --smtp-serv and --send conservatively (not claims that those ambiguous tokens execute in Git).
- PATCH --sendmail-cmd=P; --subject -- --sendmail-cmd=P; --smtp-pass --sendmail-cmd=P; --smtp-debug --sendmail-cmd=P; --batch-size --sendmail-cmd=P; unknown argument followed by target; --end-of-options followed by target.
- --subject --sendmail-cmd=DATA --sendmail-cmd=P and --identity harmless --sendmail-cmd=P.
- --identity= --sendmail-cmd=P and --subject= --sendmail-cmd=P: empty equals must not consume the next token.
- Global git -C DIR --no-pager send-email target, bare/absolute executable, exact/pattern allowlisting, pipeline start/end.
- SMTP program-like /x, \x, C:\x, c:/x, C:x, UNC; all rejected without real program execution.

Allow subject to other existing rules:
- git status and all existing regression controls.
- -h / --dump-aliases / --dry-run PATCH.
- --smtp-server=smtp.example.invalid, localhost, 127.0.0.1, [::1], relative-host.
- --smtp-server-port 2525, --smtp-server-option --sendmail-cmd=DATA, --subject --sendmail-cmd=DATA, --subject=--smtp-server=DATA.
- --identity --sendmail-cmd=DATA, including abbreviation/case. Early-pass removal must occur before main required-value consumption.
- --identity=work --subject --sendmail-cmd=DATA remains data in both modes. In contrast, --subject --identity --sendmail-cmd=DATA --sendmail-cmd=DATA2 and --subject --identity=work --sendmail-cmd=DATA MUST reject: require_order leaves a selector reachable.
- -- --sendmail-cmd=DATA (validator-only data, not a claim Git succeeds).
- Ordinary optional string/numeric values and boolean negations; confirm they do not swallow a later real target in paired negative tests.

Add at least one early-pass conflict negative where removing an early flag reveals a real target, e.g. --subject --no-identity VALUE --sendmail-cmd=P. Compare these fixed cases with upstream parser semantics during review. Keep source references next to static grammar data. No runtime dependency on Perl or a specific Git installation for the repository-local gate.
