import asyncio


def test_main(mocker):
    """Test the main entry point"""
    # Mock asyncio.run
    mock_run = mocker.patch("asyncio.run")

    # Import main after mocking
    from mcp_shell_server import main

    # Call the main function
    main()

    # Verify that asyncio.run was called
    assert mock_run.call_count == 1
    # The first argument of the call should be a coroutine object
    args = mock_run.call_args[0]
    assert len(args) == 1
    coro = args[0]
    assert asyncio.iscoroutine(coro)
    # Clean up the coroutine
    coro.close()
