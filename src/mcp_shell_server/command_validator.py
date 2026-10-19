"""Command validation for argv-based shell execution."""

import os
import re
import string
from typing import Dict, FrozenSet, List, NamedTuple

SHELL_METACHAR_PATTERN = re.compile(r"[\s;&|<>`\n\r]")
DANGEROUS_COMMANDS = {
    "sh",
    "bash",
    "zsh",
    "fish",
    "csh",
    "ksh",
    "python",
    "python3",
    "perl",
    "ruby",
    "node",
    "php",
    "lua",
    "env",
    "chroot",
    "ex",
    "flock",
    "gdb",
    "ionice",
    "less",
    "man",
    "more",
    "mysql",
    "nice",
    "nohup",
    "pg",
    "psql",
    "rsync",
    "script",
    "sed",
    "setsid",
    "sqlite3",
    "ssh",
    "stdbuf",
    "taskset",
    "time",
    "timeout",
    "unshare",
    "vi",
    "view",
    "vim",
    "watch",
    "xargs",
    "zip",
    # Known execution wrappers and JS runtimes that launch arbitrary programs
    # or code. Rejected categorically, including version/attach-only forms.
    "setarch",
    "strace",
    "valgrind",
    "deno",
    "bun",
}

FIND_EXECUTION_PRIMARIES = {"-exec", "-execdir", "-ok", "-okdir"}

COMMAND_POLICY_ALIASES = {
    "bfind": "find",
    "bsdtar": "tar",
    "gawk": "awk",
    "gfind": "find",
    "gsort": "sort",
    "gtar": "tar",
    "mawk": "awk",
    "nawk": "awk",
}

# GNU coreutils `sort` long options mapped to whether they consume a separate
# value argument. The table exists so abbreviated options can be resolved the
# way getopt_long resolves them, and so benign option values are never rescanned
# as options themselves.
SORT_LONG_OPTIONS: Dict[str, bool] = {
    "batch-size": True,
    "buffer-size": True,
    "check": False,  # value is optional and only accepted as `--check=DIAG`
    "compress-program": True,
    "debug": False,
    "dictionary-order": False,
    "field-separator": True,
    "files0-from": True,
    "general-numeric-sort": False,
    "help": False,
    "human-numeric-sort": False,
    "ignore-case": False,
    "ignore-leading-blanks": False,
    "ignore-nonprinting": False,
    "key": True,
    "merge": False,
    "month-sort": False,
    "numeric-sort": False,
    "output": True,
    "parallel": True,
    "random-sort": False,
    "random-source": True,
    "reverse": False,
    "sort": True,
    "stable": False,
    "temporary-directory": True,
    "unique": False,
    "version": False,
    "version-sort": False,
    "zero-terminated": False,
}
# Options that select an external program, an output path, an external input
# file list, or an external temporary directory.
SORT_PROHIBITED_LONG_OPTIONS = {
    "compress-program",
    "files0-from",
    "output",
    "temporary-directory",
}
SORT_SHORT_OPTIONS_WITH_VALUE = {"k", "o", "S", "t", "T"}
SORT_PROHIBITED_SHORT_OPTIONS = {"o", "T"}
SORT_POLICY_ERROR = (
    "Command rejected by default security policy: sort external program or path option"
)

AWK_LONG_OPTIONS = {
    "assign",
    "bignum",
    "characters-as-bytes",
    "copyright",
    "csv",
    "debug",
    "dump-variables",
    "exec",
    "field-separator",
    "file",
    "gen-pot",
    "help",
    "include",
    "lint",
    "load",
    "no-optimize",
    "non-decimal-data",
    "optimize",
    "posix",
    "pretty-print",
    "profile",
    "sandbox",
    "source",
    "trace",
    "traditional",
    "use-lc-numeric",
    "version",
}
AWK_PROHIBITED_LONG_OPTIONS = {"exec", "file", "include", "load", "source"}
AWK_PROHIBITED_SHORT_OPTIONS = {"E", "e", "f", "i", "l"}
AWK_SHORT_OPTIONS_WITH_REQUIRED_VALUE = {"E", "e", "f", "F", "i", "l", "v"}
AWK_SHORT_OPTIONS_WITH_OPTIONAL_ATTACHED_VALUE = {"d", "D", "L", "o", "p"}
AWK_LONG_OPTIONS_WITH_REQUIRED_VALUE = {"assign", "field-separator"}
AWK_EXTERNAL_DIRECTIVE_PATTERN = re.compile(r"(^|\s)@(include|nsinclude|load)\b")

GIT_EXTERNAL_PROGRAM_ERROR = (
    "Command rejected by default security policy: git external program"
)
# Finite Git 2.53.0 option grammar for the subcommands whose own options select
# an external program (`grep -O`, `rebase -x`). The tables only record what is
# needed to know which tokens are option values, so a value that looks like an
# option is never rescanned and a real option is never hidden as a value.
GIT_GREP_LONG_OPTIONS = {
    "after-context",
    "all-match",
    "and",
    "basic-regexp",
    "before-context",
    "break",
    "cached",
    "color",
    "column",
    "context",
    "count",
    "exclude-standard",
    "ext-grep",
    "extended-regexp",
    "files-with-matches",
    "files-without-match",
    "fixed-strings",
    "full-name",
    "function-context",
    "heading",
    "ignore-case",
    "invert-match",
    "line-number",
    "max-count",
    "max-depth",
    "name-only",
    "no-index",
    "not",
    "null",
    "only-matching",
    "open-files-in-pager",
    "or",
    "perl-regexp",
    "quiet",
    "recurse-submodules",
    "recursive",
    "show-function",
    "text",
    "textconv",
    "threads",
    "untracked",
    "word-regexp",
}
GIT_REBASE_LONG_OPTIONS = {
    "abort",
    "allow-empty-message",
    "apply",
    "autosquash",
    "autostash",
    "committer-date-is-author-date",
    "continue",
    "edit-todo",
    "empty",
    "exec",
    "force-rebase",
    "fork-point",
    "gpg-sign",
    "ignore-date",
    "ignore-whitespace",
    "interactive",
    "keep-base",
    "keep-empty",
    "merge",
    "no-ff",
    "no-stat",
    "no-verify",
    "onto",
    "preserve-merges",
    "quiet",
    "quit",
    "reapply-cherry-picks",
    "rebase-merges",
    "rerere-autoupdate",
    "reschedule-failed-exec",
    "reset-author-date",
    "root",
    "show-current-patch",
    "signoff",
    "skip",
    "strategy",
    "strategy-option",
    "update-refs",
    "verbose",
    "whitespace",
}
GIT_SUBCOMMAND_GRAMMARS: Dict[str, Dict] = {
    "grep": {
        "target_long": "open-files-in-pager",
        "target_short": "O",
        "long_options": GIT_GREP_LONG_OPTIONS,
        "required_long": {
            "after-context",
            "before-context",
            "context",
            "max-count",
            "max-depth",
            "threads",
        },
        "required_short": set("ABCefm"),
        "optional_short": set(),
        "no_value_short": set("viwaIrEGFPnhHlLzocpWq"),
        "numeric_short": True,
        "stop_at_operand": True,
    },
    "rebase": {
        "target_long": "exec",
        "target_short": "x",
        "long_options": GIT_REBASE_LONG_OPTIONS,
        "required_long": {
            "empty",
            "onto",
            "strategy",
            "strategy-option",
            "whitespace",
        },
        "required_short": set("CsX"),
        "optional_short": set("Sr"),
        "no_value_short": set("qvnfmipk"),
        "numeric_short": False,
        "stop_at_operand": False,
    },
}


# `git send-email` option tables, frozen from Git v2.53.0
# git-send-email.perl (https://github.com/git/git/blob/v2.53.0/git-send-email.perl).
# The script runs three Getopt::Long passes with pass_through over the residual
# argv: identity, then help/alias listing, then the main options. Spec suffixes
# follow Getopt::Long: `=s`/`=i` require a value, `:s`/`:i` take an optional
# one, `!` adds `no`/`no-` negations, and `|` separates aliases.
GIT_SEND_EMAIL_PASSES = (
    ("identity=s", "no-identity"),
    ("h", "dump-aliases", "translate-aliases"),
    (
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
        "outlook-id-fix!",
    ),
)
# Main-pass options whose selection runs a program. `smtp-server` only does so
# for a program-like value, see `_git_send_email_smtp_server_is_program`.
GIT_SEND_EMAIL_PROGRAM_OPTIONS = {"sendmail-cmd", "to-cmd", "cc-cmd", "header-cmd"}
GIT_SEND_EMAIL_INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+")
GIT_SEND_EMAIL_OPTION_LIKE_PATTERN = re.compile(r"(--|-|\+).+", re.DOTALL)
GIT_SEND_EMAIL_DRIVE_PATTERN = re.compile(r"[A-Za-z]:")
ASCII_LOWERCASE_TABLE = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


class GitSendEmailOption(NamedTuple):
    """Getopt::Long identity of one send-email option name.

    `canonical` mirrors Getopt::Long's ambiguity check: aliases share it, and a
    negation is `no` plus the canonical name. `arity` is the spec suffix.
    """

    canonical: str
    arity: str


def _git_send_email_option_table(specs) -> Dict[str, GitSendEmailOption]:
    table: Dict[str, GitSendEmailOption] = {}
    for spec in specs:
        negatable = spec.endswith("!")
        match = re.fullmatch(r"([^=:!]+)([=:][si])?!?", spec)
        assert match is not None, spec
        names = match.group(1).split("|")
        canonical = names[0]
        for name in names:
            table[name] = GitSendEmailOption(canonical, match.group(2) or "")
            if negatable:
                negation = GitSendEmailOption(f"no{canonical}", "")
                table[f"no{name}"] = negation
                table[f"no-{name}"] = negation
    return table


GIT_SEND_EMAIL_OPTION_TABLES = tuple(
    _git_send_email_option_table(specs) for specs in GIT_SEND_EMAIL_PASSES
)


class TarDialect(NamedTuple):
    """Finite option grammar of one tar implementation.

    Only the arity of each option matters to the policy: a required value is
    data and is never rescanned as an option within the same dialect.
    """

    long_options_with_required_value: FrozenSet[str]
    # No-value and optional-value names. An optional value is only ever
    # attached with `=`, so neither kind consumes the following argv token.
    long_options_without_separate_value: FrozenSet[str]
    short_options_with_required_value: FrozenSet[str]
    # GNU argp permutes options after operands; bsdtar stops at the first one.
    stops_at_first_operand: bool
    # bsdtar `-W name[=value]` (hyphen form only) is the long option `--name`.
    hyphen_w_is_long_option: bool

    @property
    def long_options(self) -> FrozenSet[str]:
        return (
            self.long_options_with_required_value
            | self.long_options_without_separate_value
        )


# GNU tar 1.34 options[] table (src/tar.c), names grouped by arity. The argp
# hidden `program-name` and `HANG` options are deliberately absent so an
# abbreviation of them never manufactures value consumption.
GNU_TAR_DIALECT = TarDialect(
    long_options_with_required_value=frozenset("""
        add-file after-date blocking-factor checkpoint-action directory exclude
        exclude-from exclude-ignore exclude-ignore-recursive exclude-tag
        exclude-tag-all exclude-tag-under file files-from format group
        group-map hole-detection index-file info-script label level
        listed-incremental mode mtime new-volume-script newer newer-mtime
        no-quote-chars owner owner-map pax-option quote-chars quoting-style
        record-size rmt-command rsh-command sort sparse-version
        starting-file strip-components suffix tape-length to-command transform
        use-compress-program volno-file warning xattrs-exclude xattrs-include
        xform
        """.split()),
    long_options_without_separate_value=frozenset("""
        absolute-names acls anchored append auto-compress block-number bzip2
        catenate check-device check-links clamp-mtime compare compress
        concatenate confirmation create delay-directory-restore delete
        dereference diff exclude-backups exclude-caches exclude-caches-all
        exclude-caches-under exclude-vcs exclude-vcs-ignores extract
        force-local full-time get gunzip gzip hard-dereference help
        ignore-case ignore-command-error ignore-failed-read ignore-zeros
        incremental interactive keep-directory-symlink keep-newer-files
        keep-old-files list lzip lzma lzop multi-volume no-acls no-anchored
        no-auto-compress no-check-device no-delay-directory-restore
        no-ignore-case no-ignore-command-error no-null no-overwrite-dir
        no-recursion no-same-owner no-same-permissions no-seek no-selinux
        no-unquote no-verbatim-files-from no-wildcards
        no-wildcards-match-slash no-xattrs null numeric-owner old-archive
        one-file-system overwrite overwrite-dir portability posix preserve
        preserve-order preserve-permissions read-full-records recursion
        recursive-unlink remove-files restrict same-order same-owner
        same-permissions seek selinux show-defaults show-omitted-dirs
        show-snapshot-field-ranges show-stored-names show-transformed-names
        skip-old-files sparse test-label to-stdout touch uncompress ungzip
        unlink-first unquote update usage utc verbatim-files-from verbose
        verify version wildcards wildcards-match-slash xattrs xz zstd
        """.split())
    # Optional-value names, accepted only as `--name[=VALUE]`.
    | frozenset(
        "atime-preserve backup checkpoint occurrence one-top-level totals".split()
    ),
    short_options_with_required_value=frozenset("gfLFbHVIKNCTX"),
    stops_at_first_operand=False,
    hyphen_w_is_long_option=False,
)

# Union of the libarchive bsdtar 3.5.3 and 3.7.4 tar_longopts tables
# (tar/cmdline.c) and short_options "aBb:C:cf:HhI:JjkLlmnOoPpqrSs:T:tUuvW:wX:xyZz".
# bsdtar has no optional-value long options.
BSD_TAR_DIALECT = TarDialect(
    long_options_with_required_value=frozenset("""
        block-size blocking-factor cd directory exclude exclude-from file
        files-from format gid gname group include newer newer-ctime
        newer-ctime-than newer-mtime newer-mtime-than newer-than older
        older-ctime older-ctime-than older-mtime older-mtime-than older-than
        options owner passphrase strip-components uid uname
        use-compress-program
        """.split()),
    long_options_without_separate_value=frozenset("""
        absolute-paths acls append auto-compress b64encode bunzip2 bzip bzip2
        check-links chroot clear-nochange-fflags compress confirmation create
        dereference disable-copyfile exclude-vcs extract fast-read fflags
        grzip gunzip gzip help hfsCompression ignore-zeros insecure
        interactive keep-newer-files keep-old-files list lrzip lz4 lzip lzma
        lzop mac-metadata modification-time no-acls no-fflags no-mac-metadata
        no-read-sparse no-recursion no-safe-writes no-same-owner
        no-same-permissions no-xattr no-xattrs nodump nopreserveHFSCompression
        norecurse null numeric-owner one-file-system posix
        preserve-permissions read-full-blocks read-sparse safe-writes
        same-owner same-permissions to-stdout totals uncompress unlink
        unlink-first update uuencode verbose version xattrs xz zstd
        """.split()),
    short_options_with_required_value=frozenset("bCfIsTWX"),
    stops_at_first_operand=True,
    hyphen_w_is_long_option=True,
)

# Options that run an external program. Every checkpoint action is denied, not
# only `exec=`, so the secondary action grammar never needs to be parsed.
TAR_PROHIBITED_LONG_OPTIONS = frozenset(
    {
        "checkpoint-action",
        "info-script",
        "new-volume-script",
        "rmt-command",
        "rsh-command",
        "to-command",
        "use-compress-program",
    }
)
# GNU -I/--use-compress-program and -F/--info-script; bsdtar -I is rejected
# with the same rule because the policy does not depend on the dialect.
TAR_PROHIBITED_SHORT_OPTIONS = frozenset("IF")
TAR_POLICY_ERROR = (
    "Command rejected by default security policy: tar command execution option"
)


class CommandValidator:
    """Validates argv commands against allowlists and default deny rules."""

    def __init__(self):
        """Initialize the validator."""
        return None

    def _get_allowed_commands(self) -> set[str]:
        """Get the set of allowed commands from environment variables."""
        allow_commands = os.environ.get("ALLOW_COMMANDS", "")
        allowed_commands = os.environ.get("ALLOWED_COMMANDS", "")
        commands = allow_commands + "," + allowed_commands
        return {cmd.strip() for cmd in commands.split(",") if cmd.strip()}

    def _validate_pattern_source(self, pattern: str) -> None:
        if re.search(r"[\s;&|<>`\n\r]", pattern):
            raise ValueError(f"Unsafe allowed command pattern: {pattern}")

    def _get_allowed_patterns(self) -> List[re.Pattern]:
        """Get the list of allowed regex patterns from environment variables."""
        allow_patterns = os.environ.get("ALLOW_PATTERNS", "")
        patterns = [
            pattern.strip() for pattern in allow_patterns.split(",") if pattern.strip()
        ]
        compiled = []
        for pattern in patterns:
            self._validate_pattern_source(pattern)
            compiled.append(re.compile(pattern))
        return compiled

    def get_allowed_commands(self) -> list[str]:
        """Public API: return list form of allowed commands."""
        return list(self._get_allowed_commands())

    def _validate_command_name_form(self, command: str) -> str:
        cmd = command.strip()
        if not cmd:
            raise ValueError("Empty command")
        if SHELL_METACHAR_PATTERN.search(cmd):
            raise ValueError(f"Unsafe command name: {cmd}")
        return cmd

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is in the allowed list or fully matches a pattern."""
        cmd = self._validate_command_name_form(command)
        if cmd in self._get_allowed_commands():
            return True
        for pattern in self._get_allowed_patterns():
            if pattern.fullmatch(cmd):
                return True
        return False

    def validate_no_shell_operators(self, cmd: str) -> None:
        """Validate that a token is not a shell operator or shell fragment."""
        if cmd in [";", "&&", "||", "|"]:
            raise ValueError(f"Unexpected shell operator: {cmd}")
        if any(operator in cmd for operator in [";", "&&", "||", "`", "\n", "\r"]):
            raise ValueError(f"Unexpected shell operator: {cmd}")

    def _has_any_option(self, args: List[str], options: set[str]) -> bool:
        return any(
            arg in options or any(arg.startswith(f"{option}=") for option in options)
            for arg in args
        )

    def _has_short_option_prefix(self, args: List[str], option: str) -> bool:
        return any(arg == option or arg.startswith(option) for arg in args)

    def _git_subcommand_index(self, args: List[str]) -> int | None:
        options_with_value = {
            "-C",
            "--attr-source",
            "--config-env",
            "--git-dir",
            "--namespace",
            "--shallow-file",
            "--super-prefix",
            "--work-tree",
        }
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "--":
                return None
            if arg == "-c" or arg.startswith("-c"):
                raise ValueError(
                    "Command rejected by default security policy: git command-scoped config"
                )
            if not arg.startswith("-"):
                return index
            index += 2 if arg in options_with_value else 1
        return None

    def _git_long_option_takes_value(self, name: str, grammar: Dict) -> bool:
        """Return whether a separated Git long option consumes the next token.

        Exact names win, otherwise a unique prefix resolves the option. Unknown
        or ambiguous names never consume a value: Git rejects them itself, and
        guessing a value could hide a later execution option.
        """
        if name.startswith("no-"):
            # `--no-<option>` unsets an option and never takes a value.
            return False
        names = set(grammar["long_options"])
        # Options spelled `no-*` are also reachable through their positive base.
        names |= {option[3:] for option in names if option.startswith("no-")}
        if name in names:
            return name in grammar["required_long"]
        candidates = {option for option in names if option.startswith(name)}
        return len(candidates) == 1 and candidates <= grammar["required_long"]

    def _validate_git_subcommand_options(self, args: List[str], grammar: Dict) -> None:
        """Reject execution options of `git grep`/`git rebase` in `args`.

        `args` are the tokens after the subcommand name. Required values are
        consumed before option detection so they are never rescanned.
        """
        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if arg in {"--", "--end-of-options"}:
                return
            if arg.startswith("--"):
                name, separator, _value = arg[2:].partition("=")
                if name and grammar["target_long"].startswith(name):
                    raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)
                if not separator and self._git_long_option_takes_value(name, grammar):
                    index += 1
                continue
            if arg == "-" or not arg.startswith("-"):
                if grammar["stop_at_operand"] and arg not in {"(", ")"}:
                    return
                continue
            position = 1
            while position < len(arg):
                letter = arg[position]
                position += 1
                if grammar["numeric_short"] and letter.isdigit():
                    # `-NUM` context shorthand; later letters stay options.
                    continue
                if letter == grammar["target_short"]:
                    raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)
                if letter in grammar["required_short"]:
                    if position == len(arg):
                        index += 1
                    break
                if letter in grammar["optional_short"]:
                    break
                if letter not in grammar["no_value_short"]:
                    raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)

    def _git_send_email_smtp_server_is_program(self, value: str | None) -> bool:
        """Return whether an `--smtp-server` value may select a sendmail program.

        Git treats an absolute value as a program. Missing, empty, slash or
        backslash rooted, and drive-letter values are a conservative union of
        POSIX and Windows spellings; hostnames and relative strings stay data.
        """
        return (
            not value
            or value.startswith(("/", "\\"))
            or GIT_SEND_EMAIL_DRIVE_PATTERN.match(value) is not None
        )

    def _git_send_email_pass(
        self,
        args: List[str],
        table: Dict[str, GitSendEmailOption],
        main_pass: bool,
    ) -> List[str]:
        """Run one Getopt::Long pass_through pass and return the residual argv.

        Recognized options and their consumed values are removed. Unknown,
        ambiguous and ordinary tokens, and flags given an attached value, are
        retained and never consume a value.
        An unconsumed `--` ends the pass and is retained with what follows it.
        In the main pass a reachable program selector is rejected.
        """
        residual: List[str] = []
        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if arg == "--":
                residual.extend(args[index - 1 :])
                break
            body = arg[2:] if arg.startswith("--") else arg[1:]
            name, separator, attached = body.partition("=")
            if not arg.startswith(("-", "+")) or not name:
                residual.append(arg)
                continue
            name = name.translate(ASCII_LOWERCASE_TABLE)
            if name in table:
                candidates = {table[name]}
            else:
                candidates = {
                    option for key, option in table.items() if key.startswith(name)
                }
            if len(candidates) != 1:
                if main_pass and any(
                    option.canonical in GIT_SEND_EMAIL_PROGRAM_OPTIONS
                    or option.canonical == "smtp-server"
                    for option in candidates
                ):
                    raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)
                residual.append(arg)
                continue
            option = candidates.pop()
            if separator and not option.arity:
                # A flag given `=value` is an error that pass_through restores
                # to argv, so a later pass still parses it (`--h=P` reaches
                # header-cmd in the main pass).
                residual.append(arg)
                continue
            following = args[index] if index < len(args) else None
            value: str | None = attached if separator else None
            if not separator and following is not None:
                if option.arity == "=s" or (
                    option.arity == ":s"
                    and following != "--"
                    and not GIT_SEND_EMAIL_OPTION_LIKE_PATTERN.fullmatch(following)
                ):
                    value = following
                    index += 1
                elif option.arity in {"=i", ":i"} and (
                    GIT_SEND_EMAIL_INTEGER_PATTERN.fullmatch(following)
                ):
                    value = following
                    index += 1
            if main_pass and (
                option.canonical in GIT_SEND_EMAIL_PROGRAM_OPTIONS
                or (
                    option.canonical == "smtp-server"
                    and self._git_send_email_smtp_server_is_program(value)
                )
            ):
                raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)
            if option.arity.startswith("=") and (value is None or value == ""):
                # A required value is missing, invalid or attached empty
                # (`--identity=`): Getopt::Long keeps the token unrecognized
                # under pass_through.
                residual.append(arg)
        return residual

    def _validate_git_send_email_options(self, args: List[str]) -> None:
        """Reject `git send-email` options that select an external program.

        `args` are the tokens after the subcommand. The three passes of
        git-send-email.perl run in order, so values consumed by an earlier
        pass are never rescanned and removed flags never hide a selector.
        """
        residual = args
        for pass_index, table in enumerate(GIT_SEND_EMAIL_OPTION_TABLES):
            residual = self._git_send_email_pass(
                residual, table, pass_index == len(GIT_SEND_EMAIL_OPTION_TABLES) - 1
            )

    def _validate_git_execution_subcommand(
        self, args: List[str], subcommand_index: int | None
    ) -> None:
        """Reject Git subcommands and options that run an external program."""
        if subcommand_index is None:
            exec_scan_args = args
        else:
            subcommand = args[subcommand_index]
            subcommand_args = args[subcommand_index + 1 :]
            if subcommand == "filter-branch" or (
                subcommand == "bisect" and subcommand_args[:1] == ["run"]
            ):
                raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)
            if subcommand in GIT_SUBCOMMAND_GRAMMARS:
                self._validate_git_subcommand_options(
                    subcommand_args, GIT_SUBCOMMAND_GRAMMARS[subcommand]
                )
            if subcommand == "send-email":
                self._validate_git_send_email_options(subcommand_args)
            if subcommand == "rebase":
                # rebase's own --exec handling is contextual (see above).
                return
            exec_scan_args = subcommand_args
        # Elsewhere --exec selects a remote helper program (push, archive, ...).
        for arg in exec_scan_args:
            name = arg[2:].partition("=")[0] if arg.startswith("--") else ""
            if name and "exec".startswith(name):
                raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)

    def _sort_long_option_candidates(self, name: str) -> set[str]:
        """Resolve a `sort` long option name the way getopt_long resolves it.

        An exact name wins outright; otherwise every option the token
        abbreviates stays a candidate. GNU sort rejects ambiguous abbreviations,
        so treating each candidate as reachable only makes the policy stricter.
        """
        if name in SORT_LONG_OPTIONS:
            return {name}
        return {option for option in SORT_LONG_OPTIONS if option.startswith(name)}

    def _awk_uses_external_program_source(self, args: List[str]) -> bool:
        def prohibited_long_option(name: str) -> bool:
            candidates = (
                {name}
                if name in AWK_LONG_OPTIONS
                else {option for option in AWK_LONG_OPTIONS if option.startswith(name)}
            )
            return bool(candidates & AWK_PROHIBITED_LONG_OPTIONS)

        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if AWK_EXTERNAL_DIRECTIVE_PATTERN.search(arg):
                return True
            if arg == "--":
                return False
            if arg.startswith("--"):
                name = arg[2:].partition("=")[0]
                if prohibited_long_option(name):
                    return True
                if "=" not in arg and name in AWK_LONG_OPTIONS_WITH_REQUIRED_VALUE:
                    index += 1
            elif arg == "-W" and index < len(args):
                name = args[index].partition("=")[0]
                if prohibited_long_option(name):
                    return True
                index += 1
            elif arg.startswith("-W"):
                name = arg[2:].partition("=")[0]
                if prohibited_long_option(name):
                    return True
            elif len(arg) > 1 and arg[0] == "-":
                for position, letter in enumerate(arg[1:], start=1):
                    if letter in AWK_PROHIBITED_SHORT_OPTIONS:
                        return True
                    if letter in AWK_SHORT_OPTIONS_WITH_REQUIRED_VALUE:
                        if position == len(arg) - 1:
                            index += 1
                        break
                    if letter in AWK_SHORT_OPTIONS_WITH_OPTIONAL_ATTACHED_VALUE:
                        break
            else:
                return False
        return False

    def _tar_long_option_consumes_next(self, text: str, dialect: TarDialect) -> bool:
        """Reject a forbidden long option; return whether it takes the next token.

        `text` is the option without its `--` prefix (or the bsdtar `-W` text).
        An exact name wins; otherwise every name it abbreviates is a candidate
        and any forbidden candidate rejects. Only a unique required-value name
        written without `=` consumes the following token; unknown and ambiguous
        names never manufacture a value.
        """
        name, separator, _value = text.partition("=")
        candidates = (
            {name}
            if name in dialect.long_options
            else {option for option in dialect.long_options if option.startswith(name)}
        )
        if candidates & TAR_PROHIBITED_LONG_OPTIONS:
            raise ValueError(TAR_POLICY_ERROR)
        return (
            not separator
            and len(candidates) == 1
            and candidates <= dialect.long_options_with_required_value
        )

    def _validate_tar_arguments(self, args: List[str], dialect: TarDialect) -> None:
        """Reject tar external-program options reachable under one dialect.

        Each dialect keeps its own cursor: a token consumed as a value in one
        walk may be a real option in the other, so both walks must pass.
        """
        index = 0
        if args and not args[0].startswith("-"):
            # Old-style first word: every letter is an option and each
            # required value is taken from the following tokens in order,
            # even when that token is `--`. Old-style bsdtar W only takes
            # its argument; it does not dispatch a long option.
            index = 1
            for letter in args[0]:
                if letter in TAR_PROHIBITED_SHORT_OPTIONS:
                    raise ValueError(TAR_POLICY_ERROR)
                if letter in dialect.short_options_with_required_value:
                    index += 1
        while index < len(args):
            arg = args[index]
            index += 1
            if arg == "--":
                return
            if arg.startswith("--"):
                if self._tar_long_option_consumes_next(arg[2:], dialect):
                    index += 1
            elif arg.startswith("-"):
                # A bare `-` is an empty bsdtar short group and a GNU
                # operand; neither ends option scanning.
                for position, letter in enumerate(arg[1:], start=1):
                    if letter in TAR_PROHIBITED_SHORT_OPTIONS:
                        raise ValueError(TAR_POLICY_ERROR)
                    if letter not in dialect.short_options_with_required_value:
                        continue
                    value = arg[position + 1 :]
                    if not value:
                        value = args[index] if index < len(args) else ""
                        index += 1
                    if value and letter == "W" and dialect.hyphen_w_is_long_option:
                        if self._tar_long_option_consumes_next(value, dialect):
                            index += 1
                    # The rest of the cluster is the value, not options.
                    break
            elif dialect.stops_at_first_operand:
                return

    def _validate_sort_arguments(self, args: List[str]) -> None:
        """Reject `sort` options that reach outside the validated argv boundary.

        GNU option permutation allows options after operands, so every argument
        is scanned until a discrete `--`; tokens after it are filename operands
        even when they look like options.
        """
        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if arg == "--":
                return
            if arg == "-" or not arg.startswith("-"):
                continue
            if arg.startswith("--"):
                name, separator, _value = arg[2:].partition("=")
                candidates = self._sort_long_option_candidates(name)
                if candidates & SORT_PROHIBITED_LONG_OPTIONS:
                    raise ValueError(SORT_POLICY_ERROR)
                if not separator and len(candidates) == 1:
                    (resolved,) = candidates
                    if SORT_LONG_OPTIONS[resolved]:
                        index += 1
                continue
            for position, letter in enumerate(arg[1:], start=1):
                if letter in SORT_PROHIBITED_SHORT_OPTIONS:
                    raise ValueError(SORT_POLICY_ERROR)
                if letter in SORT_SHORT_OPTIONS_WITH_VALUE:
                    # The value is either the rest of this token or the next
                    # argument. Either way it is data, so it must not be
                    # rescanned as further clustered option letters.
                    if position == len(arg) - 1:
                        index += 1
                    break

    def _policy_command_name(self, command: str) -> str:
        cmd = os.path.basename(self._validate_command_name_form(command))
        if re.fullmatch(r"python\d+(?:\.\d+)*", cmd):
            return "python"
        return COMMAND_POLICY_ALIASES.get(cmd, cmd)

    def _validate_default_argument_policy(self, command: List[str]) -> None:
        cmd = self._policy_command_name(command[0])
        args = command[1:]
        if cmd in DANGEROUS_COMMANDS:
            raise ValueError(f"Command rejected by default security policy: {cmd}")

        if cmd == "find":
            if any(arg in FIND_EXECUTION_PRIMARIES for arg in args):
                raise ValueError(
                    "Command rejected by default security policy: find -exec"
                )
            if any(arg in {"-fprintf", "-fprint", "-fprint0", "-fls"} for arg in args):
                raise ValueError(
                    "Command rejected by default security policy: find file output"
                )

        if cmd == "awk" and (
            self._awk_uses_external_program_source(args)
            or any(
                "system(" in (compact := re.sub(r"\s+", "", arg))
                or "|" in compact
                or ">" in arg
                or "<" in arg
                for arg in args
            )
        ):
            raise ValueError(
                "Command rejected by default security policy: awk external access"
            )

        if cmd == "tar":
            # The executable spelling does not select a dialect: either
            # interpretation reaching a helper option rejects the command.
            self._validate_tar_arguments(args, GNU_TAR_DIALECT)
            self._validate_tar_arguments(args, BSD_TAR_DIALECT)

        if cmd == "sort":
            self._validate_sort_arguments(args)

        if cmd == "git":
            subcommand_index = self._git_subcommand_index(args)
            git_args = args if subcommand_index is None else args[subcommand_index:]
            clone_args = git_args[1:] if git_args and git_args[0] == "clone" else []
            if git_args and git_args[0] == "config":
                raise ValueError(
                    "Command rejected by default security policy: git config"
                )
            if (
                self._has_any_option(
                    args,
                    {
                        "--config-env",
                        "--exec-path",
                        "--receive-pack",
                        "--upload-pack",
                    },
                )
                or any(arg.startswith("--upl") for arg in args)
                or any(arg.startswith("--rece") for arg in args)
                or (
                    clone_args
                    and (
                        self._has_short_option_prefix(clone_args, "-c")
                        or self._has_short_option_prefix(clone_args, "-u")
                        or any(arg.startswith("--u") for arg in clone_args)
                        or any(
                            arg == "--co"
                            or arg.startswith("--co=")
                            or arg.startswith("--con")
                            for arg in clone_args
                        )
                    )
                )
                or any(arg.startswith("ext::") for arg in args)
            ):
                raise ValueError(GIT_EXTERNAL_PROGRAM_ERROR)
            self._validate_git_execution_subcommand(args, subcommand_index)

    def validate_pipeline(self, commands: List[str]) -> Dict[str, str]:
        """Validate pipeline tokens and ensure all command segments are allowed."""
        current_cmd: List[str] = []

        for token in commands:
            if token == "|":
                if not current_cmd:
                    raise ValueError("Empty command before pipe operator")
                self.validate_command(current_cmd)
                current_cmd = []
            elif token in [";", "&&", "||"]:
                raise ValueError(f"Unexpected shell operator in pipeline: {token}")
            else:
                if not current_cmd:
                    self.validate_no_shell_operators(token)
                current_cmd.append(token)

        if current_cmd:
            self.validate_command(current_cmd)

        return {}

    def validate_command(self, command: List[str]) -> None:
        """Validate if the argv command is allowed to be executed."""
        if not command:
            raise ValueError("Empty command")

        if not self._get_allowed_commands() and not self._get_allowed_patterns():
            raise ValueError(
                "No commands are allowed. Please set ALLOW_COMMANDS environment variable."
            )

        cleaned_cmd = self._validate_command_name_form(command[0])
        self._validate_default_argument_policy([cleaned_cmd, *command[1:]])
        if not self.is_command_allowed(cleaned_cmd):
            raise ValueError(f"Command not allowed: {cleaned_cmd}")
