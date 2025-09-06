"""Test cases for the CommandValidator class."""

import re
from unittest.mock import patch, MagicMock
import pytest

from mcp_shell_server.command_validator import CommandValidator


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOW_PATTERNS", raising=False)


@pytest.fixture
def validator():
    return CommandValidator()


def test_get_allowed_commands(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cmd1,cmd2")
    monkeypatch.setenv("ALLOWED_COMMANDS", "cmd3,cmd4")
    assert set(validator.get_allowed_commands()) == {"cmd1", "cmd2", "cmd3", "cmd4"}


def test_is_command_allowed_with_patterns(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")
    monkeypatch.setenv("ALLOW_PATTERNS", "^cmd[0-9]+$")

    assert validator.is_command_allowed("allowed_cmd")
    assert validator.is_command_allowed("cmd123")
    assert not validator.is_command_allowed("disallowed_cmd")
    assert not validator.is_command_allowed("cmdabc")
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")
    assert validator.is_command_allowed("allowed_cmd")
    assert not validator.is_command_allowed("disallowed_cmd")


def test_validate_no_shell_operators(validator):
    validator.validate_no_shell_operators("echo")  # Should not raise
    with pytest.raises(ValueError, match="Unexpected shell operator"):
        validator.validate_no_shell_operators(";")
    with pytest.raises(ValueError, match="Unexpected shell operator"):
        validator.validate_no_shell_operators("&&")


def test_validate_pipeline(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls,grep")

    # Valid pipeline
    validator.validate_pipeline(["ls", "|", "grep", "test"])

    # Empty command before pipe
    with pytest.raises(ValueError, match="Empty command before pipe operator"):
        validator.validate_pipeline(["|", "grep", "test"])

    # Command not allowed
    with pytest.raises(ValueError, match="Command not allowed"):
        validator.validate_pipeline(["invalid_cmd", "|", "grep", "test"])


def test_validate_command(validator, monkeypatch):
    clear_env(monkeypatch)

    # No allowed commands
    with pytest.raises(ValueError, match="No commands are allowed"):
        validator.validate_command(["cmd"])

    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")

    # Empty command
    with pytest.raises(ValueError, match="Empty command"):
        validator.validate_command([])

    # Command not allowed
    with pytest.raises(ValueError, match="Command not allowed"):
        validator.validate_command(["disallowed_cmd"])

    # Command allowed
    validator.validate_command(["allowed_cmd", "-arg"])  # Should not raise


def test_pattern_cache_initialized_once(validator, monkeypatch):
    """Test that regex patterns are compiled only once and cached"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "^test[0-9]+$,^cmd.*$")
    
    # First call should initialize cache
    patterns1 = validator.get_allowed_patterns()
    assert len(patterns1) == 2
    assert validator._pattern_cache_initialized is True
    
    # Store reference to first patterns to compare identity
    first_patterns = validator._compiled_patterns
    
    # Second call should use cached patterns
    patterns2 = validator.get_allowed_patterns()
    assert len(patterns2) == 2
    
    # Verify same objects are returned (identity check for caching)
    assert patterns1 is patterns2
    assert validator._compiled_patterns is first_patterns
    
    # Verify patterns work as expected
    assert validator.is_command_allowed("test123")
    assert validator.is_command_allowed("cmdtest")
    assert not validator.is_command_allowed("invalid")


def test_invalid_regex_pattern_handling(validator, monkeypatch, caplog):
    """Test that invalid regex patterns are handled gracefully"""
    clear_env(monkeypatch)
    # Set invalid regex patterns (unclosed bracket, invalid escape)
    monkeypatch.setenv("ALLOW_PATTERNS", "^test[,\\k,valid_pattern$")
    
    with caplog.at_level('WARNING'):
        patterns = validator.get_allowed_patterns()
        
        # Only the valid pattern should be compiled
        assert len(patterns) == 1
        assert patterns[0].pattern == "valid_pattern$"
        
        # Check that warnings were logged for invalid patterns
        assert "Invalid regex pattern '^test['" in caplog.text
        assert "Invalid regex pattern '\\k'" in caplog.text


def test_empty_patterns_environment(validator, monkeypatch):
    """Test behavior with empty ALLOW_PATTERNS environment variable"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "")
    
    patterns = validator.get_allowed_patterns()
    assert patterns == []
    
    # Should return False for any command when no patterns
    assert not validator.is_command_allowed("any_command")


def test_whitespace_in_patterns(validator, monkeypatch):
    """Test that whitespace is handled properly in patterns"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "  ^test$  , , ^valid.*$ ")
    
    patterns = validator.get_allowed_patterns()
    assert len(patterns) == 2
    
    # Test that patterns work correctly
    assert validator.is_command_allowed("test")
    assert validator.is_command_allowed("validcommand")
    assert not validator.is_command_allowed("invalid")


def test_cache_persistence_across_calls(validator, monkeypatch):
    """Test that the cache persists across multiple method calls"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "^cache_test$")
    
    # First call initializes cache
    result1 = validator.is_command_allowed("cache_test")
    assert result1 is True
    
    # Subsequent calls should use cached patterns
    result2 = validator.is_command_allowed("cache_test")
    assert result2 is True
    
    result3 = validator.is_command_allowed("other_command")
    assert result3 is False
    
    # Verify cache was initialized only once
    assert validator._pattern_cache_initialized is True
    assert len(validator._compiled_patterns) == 1
