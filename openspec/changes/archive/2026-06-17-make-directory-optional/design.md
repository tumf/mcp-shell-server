# Design: Optional directory with effective working directory

## Current State

The server currently exposes `directory` as a required MCP tool argument. `ExecuteToolHandler.run_tool()` also contains a hidden `/tmp` fallback, but schema validation and explicit empty-directory checks mean clients are expected to supply an absolute directory. `DirectoryManager.validate_directory()` rejects `None` and non-absolute paths. Redirection containment uses the working directory as its security boundary.

## Decision

Introduce an effective working directory resolution step before shell execution:

- omitted `directory` -> `os.getcwd()` from the server process
- relative `directory` -> `os.path.abspath(directory)` from the server process CWD
- absolute `directory` -> the supplied path
- empty or whitespace-only string -> reject

After resolution, the effective directory must pass the existing existence, directory, and accessibility checks. Downstream components should receive the effective directory rather than raw user input.

## Rationale

This preserves the current security model while improving client ergonomics. The server process CWD is deterministic from the server's perspective and can be documented. Treating relative paths as server-CWD-relative avoids pretending the MCP client CWD is available to the server.

## Security Considerations

Redirection containment remains tied to the validated effective directory. This proposal does not broaden redirection target rules: absolute redirection paths, parent traversal outside the effective directory, and symlink escapes remain rejected. Empty strings are rejected so clients cannot accidentally rely on ambiguous fallback behavior.

## Compatibility

Existing clients that pass absolute directories continue to work. Clients that omit `directory` or pass relative directories gain new behavior. The hidden `/tmp` default is removed because it is not reflected in the tool schema and would conflict with the proposed server-CWD default.
