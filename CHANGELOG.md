# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
