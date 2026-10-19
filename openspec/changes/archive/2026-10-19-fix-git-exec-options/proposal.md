---
change_type: implementation
priority: high
dependencies: []
verifications:
  - id: git-exec-grammar-regression
    requirement: Explicit Git pager, rebase execution, filter-branch and bisect run paths are rejected before process creation
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
# Close explicit Git execution-option gaps

**Change Type**: implementation

## Problem / Context
The documented finite Git external-program hardening misses grep pager selection, rebase short exec forms, filter-branch and bisect run. Harmless real Git 2.53.0 helper markers reproduced all four paths through the released executor. This is a documented-boundary defect, not a claim of complete Git sandboxing.

## Proposed Solution
Implement the fixed contextual algorithm and tables below in command_validator.py, using existing normalization and git external program error. No new dependency, generic parser or runtime Git introspection. The Git 2.53.0 upstream sources builtin/{grep,rebase,bisect}.c, git.c and parse-options.c are the finite grammar authority. Reject grep pager spellings, rebase exec spellings, every filter-branch invocation, and exact bisect run dispatch. Preserve other existing Git rejection rules; only the broad --exec scan moves into the rebase-specific walker so consumed values and real -- operands are not misclassified. Existing upload/receive/config/ext checks are not loosened.

### 3.1 global prefix / subcommand

既存 `_git_subcommand_index` を利用する。global prefix だけを左から走査し、最初の非 `-` token を subcommand とする。現在の required-value table `-C, --attr-source, --config-env, --git-dir, --namespace, --shallow-file, --super-prefix, --work-tree` の exact separated 形は次 token を無条件に1個消費する。`--name=value` は1 token。値を subcommand/option として再走査しない。global `-c` / `-c...` は既存通り即拒否。繰返し/reorder を許容する。global `--` は現在通り subcommand 未確定（Git 自身も拒否）とする。

この patch で global options の全 validation を作り直さない。unknown global option を既存通り1 token skipして subcommand policy を厳しめに適用してもよいが、その形式が実 Git で実行可能と主張しない。subcommand 未確定なら新4規則は適用しない。既存 generic checks は維持。

subcommand が:
- exact `filter-branch`: 引数を問わず即拒否（`--help` も拒否。categorical 互換影響を明記）。
- exact `bisect`: 直後の token が exact `run` なら即拒否。argv 全域から run を検索しない。
- exact `grep` / `rebase`: 以下の専用 walker。
- その他: 新規判定なし。

### 3.2 専用 option walker

walker は subcommand **以後**のみを処理する。option を検出する前に required 値を消費し、値に dangerous option 文字列が含まれていても再検査しない。

1. 未消費の exact `--` / `--end-of-options` で終了。
2. long token は最初の `=` で name/value を分ける。正の target は grep `open-files-in-pager`、rebase `exec`。full name および **空でない prefix** を検出し即拒否。exact `only-matching/or/empty/edit-todo` 等は target ではない。`--o` / `--e` のような target を含む ambiguous prefix も保守的に拒否してよい（ここでは拒否を固定する）。これらは Git 自身も実行しない入力であり、unique と偽って記載しない。
3. `no-` / `no-no-` 形を正の target prefix として扱わない。target の negation は値を消費しない。他の benign long required option は下表で exact-first、次に unique-prefix resolution。full-name table 全体で ambiguous/unknown の場合には次 token を skip **しない**。invalid argv を Git に任せてもよいし、明示的に policy 拒否してもよい。消費推測で実行指定を隠すことは禁止。
4. required long option は `=...` がなければ次 token を1個消費する。`--no-<required-option>` は unset であり次 token を消費しない。optional long `color` / `gpg-sign` / `rebase-merges` は `=...` のみ。値の合法性までは validator で検証しない。
5. short cluster は左から1文字ずつ。grep `O` / rebase `x` へ到達した時点で即拒否。required/optional-value letter へ到達したら cluster の残りは全て値として消費してその token を終了。required letter が末尾なら次 token を1個消費。optional letter が末尾でも次 token は消費しない。grep 数字の連続は `-NUM` context shorthand として消費し、その後 cluster の文字を続ける（`-1O...` を見逃さない）。
6. 非option / lone `-`: grep は終了。ただし standalone `(` / `)` は通過して続行。rebase は operand として通過して続行。
7. unknown short letter MUST be rejected rather than guessed as a value-taking option; only known no-value letters continue. Git source の特殊 single-dash typo 診断まで再実装しない。 場所については、`--exec` family **のみ**を subcommand 後へ移す。他の既存 broad checks (`--exec-path`, `--config-env`, `--receive-pack`, `--upload-pack`, `--upl`, `--rece`, clone checks, `ext::`) は引き続き全 argv を走査する。

**既存 broad `--exec` check の処理:** Keep --exec/--exec= in the broad external-program rejection set for every subcommand other than exact rebase, including push/send-pack/archive/ls-remote where it selects a real helper. Only exact rebase delegates --exec handling to its contextual walker. For non-rebase, scan tokens after the resolved subcommand; unresolved subcommands retain conservative broad checking. Global required values such as -C --exec status are not rescanned as helper options. Preserve all other broad option checks/ext:: without relaxation. Add rejection tests for push --exec=sh /tmp/repo, push --exec sh /tmp/repo, archive --remote=/tmp/repo --exec=sh HEAD, send-pack --exec=sh /tmp/repo main, ls-remote --exec=sh /tmp/repo. Cover every non-empty --exec prefix (--e, --ex, --exe, each with or without =), on these four known external-helper subcommands. Add push --e=sh /tmp/repo and archive --remote=/tmp/repo --e sh HEAD rejection controls; do not weaken an existing true rejection. Rebase --onto --exec and rebase -- --exec remain data controls. These rules do not promise to remove unrelated pre-existing operand false positives.

### 3.3 必要な arity / resolution tables

runtime Git subprocess で parser 情報を問い合わせない。以下の小さな静的 table で十分。no-value long names も unique-prefix resolution の競合を正しく計算するために使う（help の表示だけでは hidden names が欠ける）。

| command | required short | optional attached-only short | required long | optional equals-only long |
|---|---|---|---|---|
| grep | `A B C e f m` | `O`（即拒否） | `after-context before-context context max-count max-depth threads` | `color open-files-in-pager`（後者即拒否） |
| rebase | `C s X x`（x即拒否） | `S r` | `onto whitespace empty strategy strategy-option exec`（exec即拒否） | `gpg-sign rebase-merges` |

Known no-value short:
- grep: `v i w a I r E G F P n h H l L z o c p W q`、dashless `(` / `)`、number shorthand。
- rebase: `q v n f m i p k`（p/k は hidden/removed option を含む。妥当な Git operation を保証する意味ではない）。

Long canonical names（required/optional は上表、それ以外 no-value）:
- grep: `cached no-index untracked exclude-standard recurse-submodules invert-match ignore-case word-regexp text textconv recursive max-depth extended-regexp basic-regexp fixed-strings perl-regexp line-number column full-name files-with-matches name-only files-without-match null only-matching count color break heading context before-context after-context threads show-function function-context and or not quiet all-match open-files-in-pager ext-grep max-count`。
- rebase: `onto keep-base no-verify quiet verbose no-stat signoff committer-date-is-author-date reset-author-date ignore-date ignore-whitespace whitespace force-rebase no-ff continue skip abort quit edit-todo show-current-patch apply merge interactive preserve-merges rerere-autoupdate empty keep-empty autosquash update-refs gpg-sign autostash exec allow-empty-message rebase-merges fork-point strategy strategy-option root reschedule-failed-exec reapply-cherry-picks`。

negative spelling 解決では canonical が `no-` で始まる option は Git と同様に基底へ正規化する（`no-index/index`, `no-stat/stat`, `no-verify/verify`, `no-ff/ff`）。unset は required 値を消費しない。`PARSE_OPT_NONEG` の完全再現は不要: invalid negations は実 Git が拒否し、walker は値を skipしなければ bypass しない。`--help`, `--help-all`, completion-only option は次 token を消費しない。help があるから後続正指定を許可する最適化はしない。

## 4. 最低限のテスト（実装時の gate）

表記は argv list の `git` 以後。`P` は shell 演算子を含まない helper path。allow は **validator policy 上**の許可であり、Git がその argv/revision/value を有効と認める保証ではない。tests は現在の pytest parametrize を使い、独立 framework/大規模 fixture を作らない。

### A. 単体・拒否（parameterize）

1. grep pager:
   - `grep -O -e MATCH`, `grep -OP -e MATCH`, `grep -nO P`, `grep -nOP`, `grep -1OP`。
   - `grep --open-files-in-pager -e MATCH`, `grep --open-files-in-pager=P`, `grep --op=P`, `grep --op P`。
   - `grep ( -e MATCH ) -OP`（dashless parentheses 後も検査）。
2. rebase exec:
   - `rebase -x P HEAD~1`, `rebase -xP HEAD~1`, `rebase -qx P`, `rebase -qxP`。
   - `rebase --exec P`, `rebase --exec=P`, `rebase --ex P`, `rebase --ex=P`。
   - `rebase HEAD~1 -xP`（operand 後）、`rebase -xP --no-exec`（reset で解除しない）。
3. `filter-branch`、`filter-branch --tree-filter P HEAD`、`filter-branch --help`。
4. `bisect run P`、`bisect run -- P`。
5. ambiguous conservative policy: `grep --o=P` / `rebase --e=P` は拒否。実 Git unique prefix と呼ばない。
6. required `--` 値の bypass regression: `grep -e -- -OP data`、`rebase --strategy -- -xP` を拒否。
7. global prefix の発見: 4経路を各1件ずつ `-C repo`、`--git-dir=repo/.git --work-tree repo`、`--attr-source HEAD --namespace ns -C repo`、`--shallow-file x` へ割り当てる。少なくとも1件は global options 繰返し/reorder。`-C -x grep -OP` では -x は global path 値、grep の O を拒否。

### B. 単体・許可（parameterize）

1. `status --short`, `log --oneline`, `grep -n -e MATCH -- data`, `rebase --onto main topic`, `bisect start`, `bisect log`, `bisect reset`。
2. `grep -e -O data`, `grep -e--open-files-in-pager data`, `grep -ne -O data`, `grep -f -O data`（ファイルの存在は unit で不要）、`grep --context -O data`（numeric validation は Git の責務）。
3. `grep --con 1 -e MATCH data`（unique benign required long）、`grep --color -e -O data`（optional long は次 token を消費しない）。
4. `rebase -Xx`, `rebase -s -x`, `rebase -Sx`, `rebase -rx`, `rebase --onto --exec`, `rebase --strategy-option=-x`, `rebase --strategy-o -x`, `rebase --empty -x`。target-like data を再走査しない。
5. `grep -- -O data`, `grep --end-of-options -O data`, `rebase -- -xP`, `rebase -- --exec=P`。
6. `grep MATCH -OP` は新規 pager policy では拒否しない（Git 自身は operand 後 option として拒否）。`grep -e MATCH -- --open-files-in-pager=P` も data。
7. `grep --no-open-files-in-pager -e MATCH`, `grep --no-op -e MATCH`, `rebase --no-exec`。
8. `bisect log run`, `bisect start -- run`, `bisect ru`, `bisect -- run` は新規 run policy では拒否しない。
9. global 消費: `-C filter-branch status`, `--namespace bisect status`, `--attr-source grep status`, `-C --exec status`。値を subcommand/`--exec` として再走査しない。
10. `commit -c HEAD --dry-run` は引続き許可。global `-c user.name=Example status` / attached `-cuser.name=Example status` は既存 test の通り拒否。
11. `--config-env=...` / `--exec-path=...` / clone upload/config / persistent config の既存拒否テストをそのまま全通過させる。

さらに table-driven arity regression を最小1本: 上記 required short/long 各 entry の値として target-like token を置き、その token だけでは拒否されず、続けた独立 target 指定は拒否されることを確認。optional-value short `r/S` の直後に独立 `-xP`、optional `color` の直後に独立 `-OP` は拒否し、誤 skip を検出する。no-value `--only-matching/--or/--empty` と exact-first resolution の対照を入れる（empty は required 値）。

### C. 完全 executor・起動前（mock boundary）

新4経路の全 syntactic classes（short/attached/cluster/long/prefix/operand-after/global/required-`--`）を上の parameter list から共用。`ALLOW_COMMANDS=git`、空の他 allow settings。`ShellExecutor.execute()` の result が status 1、error に `git external program`、`ProcessManager.create_process` と `execute_pipeline` の両方が not awaited。; や shell fragments を含む payload は使わない。これで前処理の別拒否による偽greenを防ぐ。

4経路各1件を既存 pipeline validator 経路にも通し、別 segment も含めて process 未作成を確認。1代表を絶対 Git executable path の exact allowlist と `ALLOW_PATTERNS` の双方で確認し、basename policy/allowlist override を回帰保護する。


## Acceptance Criteria
All A/B/C cases above pass, including arity-table coverage, ordinary status/grep and pipeline/absolute-name/pattern policy dominance. Tests use tests/test_command_validator.py and tests/test_shell_executor.py only. Required values and standalone end-of-options are distinct. No real process reaches a blocked path; mock create_process and execute_pipeline and assert the specific policy error. Canonical command-policy gains the four explicit obligations without replacing newer wrapper/tar/sort obligations. README/SECURITY/changelog state exact finite behavior and categorical filter-branch compatibility impact, not a complete Git safety claim.

## Change Boundary
command_validator.py, the two declared test files, README.md, SECURITY.md, CHANGELOG.md, command-policy delta and canonical promotion. No tar/PATH or wrapper-name changes, dependencies, release version, hooks/editor/strategy/textconv containment or public writes.

## Explicit Completion Conditions
Focused and full tests, lint/typecheck, diff check and archive gate pass. Parent owns independent integration review and isolated installed-artifact replay of the four already-proven real helper paths plus normal commands. Public release/disclosure is not performed by implementation.

## Out of Scope
All Git versions, generic subprocess confinement, generic Git config/hook/plugin security, removal of unrelated pre-existing strictness.

## Final Validation
uv run pytest tests/test_command_validator.py tests/test_shell_executor.py; uv run pytest; make lint typecheck; cflx openspec validate fix-git-exec-options --archive-gate.
