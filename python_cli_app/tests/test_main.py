import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Adjust import path if necessary, assuming tests are run from repository root
# or python_cli_app is in PYTHONPATH.
# For the subtask environment, this might require sys.path manipulation if python_cli_app
# is not automatically discoverable. However, the tool often sets up the CWD at repo root.
try:
    from python_cli_app import main
except ImportError:
    # If running test_main.py directly and python_cli_app is not in path
    import sys
    import os
    # Add the parent directory of python_cli_app (which is the repo root) to sys.path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from python_cli_app import main


class TestCLIArgs(unittest.TestCase):

    @patch('python_cli_app.main.do_login_flow', new_callable=AsyncMock)
    @patch('python_cli_app.main.fetch_articles_command', new_callable=AsyncMock)
    def test_login_arg(self, mock_fetch_articles, mock_do_login):
        """Test that --login calls do_login_flow."""
        # Configure mock_do_login to return a dictionary to avoid RuntimeWarning with .get()
        mock_do_login.return_value = {'token': 't', 'fakeid': 'f', 'nickname': 'n'}
        async def run_test():
            with patch('sys.argv', ['main.py', '--login']):
                await main.main_cli()
        asyncio.run(run_test())
        mock_do_login.assert_called_once()
        mock_fetch_articles.assert_not_called()

    @patch('python_cli_app.main.do_login_flow', new_callable=AsyncMock)
    @patch('python_cli_app.main.fetch_articles_command', new_callable=AsyncMock)
    def test_get_articles_arg_with_token_fakeid(self, mock_fetch_articles, mock_do_login):
        """Test --get-articles with token and fakeid calls fetch_articles_command."""
        test_token = "testtoken123"
        test_fakeid = "testfakeid456"
        async def run_test():
            with patch('sys.argv', ['main.py', '--get-articles', '--token', test_token, '--fakeid', test_fakeid]):
                await main.main_cli()
        asyncio.run(run_test())
        mock_do_login.assert_not_called() # Should not call login if token/fakeid provided
        mock_fetch_articles.assert_called_once_with(test_token, test_fakeid)

    @patch('python_cli_app.main.do_login_flow', new_callable=AsyncMock)
    @patch('python_cli_app.main.fetch_articles_command', new_callable=AsyncMock)
    def test_get_articles_arg_triggers_login(self, mock_fetch_articles, mock_do_login):
        """Test --get-articles without token/fakeid calls do_login_flow."""
        # Simulate do_login_flow returning some details
        mock_do_login.return_value = {'token': 'logintoken', 'fakeid': 'loginfakeid', 'nickname': 'loginuser'}
        async def run_test():
            with patch('sys.argv', ['main.py', '--get-articles']):
                await main.main_cli()
        asyncio.run(run_test())
        mock_do_login.assert_called_once()
        mock_fetch_articles.assert_called_once_with('logintoken', 'loginfakeid')

    @patch('python_cli_app.main.do_login_flow', new_callable=AsyncMock)
    @patch('python_cli_app.main.fetch_articles_command', new_callable=AsyncMock)
    @patch('argparse.ArgumentParser.print_help') # Mock print_help
    def test_no_args(self, mock_print_help, mock_fetch_articles, mock_do_login):
        """Test no arguments calls print_help (or default action)."""
        async def run_test():
            with patch('sys.argv', ['main.py']):
                await main.main_cli()
        asyncio.run(run_test())
        mock_print_help.assert_called_once()
        mock_do_login.assert_not_called()
        mock_fetch_articles.assert_not_called()

    @patch('logging.Logger.debug') # Check if logger.debug is called
    @patch('python_cli_app.main.do_login_flow', new_callable=AsyncMock) # Mock to prevent execution
    def test_debug_arg(self, mock_do_login, mock_logger_debug):
        """Test --debug enables debug logging."""
        # Configure mock_do_login for the combined command
        mock_do_login.return_value = {'token': 't', 'fakeid': 'f', 'nickname': 'n'}
        async def run_test():
            with patch('sys.argv', ['main.py', '--debug', '--login']): # combine with login to run some path
                await main.main_cli()
        asyncio.run(run_test())
        # Check if logger.debug was called. This assumes that enabling debug logging
        # will result in at least one logger.debug call, e.g., "Debug logging enabled."
        self.assertGreater(mock_logger_debug.call_count, 0)


class TestLoginFlow(unittest.TestCase):

    @patch('python_cli_app.main.uc') # Patch nodriver import alias 'uc'
    def test_do_login_flow_success(self, mock_uc):
        """Test successful login flow with mocked nodriver interactions."""

        # Configure mock uc.start() and its context manager
        mock_driver = AsyncMock()
        mock_tab = AsyncMock()

        # uc.start itself is an async coroutine that returns an async context manager
        mock_uc.start = AsyncMock()
        # Configure the __aenter__ and __aexit__ for the object returned by `await uc.start()`
        mock_uc.start.return_value.__aenter__.return_value = mock_driver
        mock_uc.start.return_value.__aexit__.return_value = AsyncMock() # Should also be an async mock or awaitable

        mock_driver.get.return_value = mock_tab # driver.get() returns the tab

        # Simulate URL changes
        # Initial URL for login page
        mock_tab.url = "https://mp.weixin.qq.com/"

        # Simulate login success by changing URL after some calls to sleep
        # This needs to be a bit more sophisticated if tab.url is accessed multiple times in a loop
        # Using side_effect for tab.url to change after a certain number of calls or specific conditions
        url_sequence = ["https://mp.weixin.qq.com/"] * 5 + \
                       ["https://mp.weixin.qq.com/cgi-bin/home?action=home&token=mocktoken123"]

        # We need to mock tab.sleep as well because it's awaited
        mock_tab.sleep = AsyncMock()

        # Mock tab.url to behave like a property that changes
        # This is tricky; simpler to mock the loop condition or the point where URL is checked.
        # For this test, let's assume the loop runs a few times then 'logged_in' becomes true
        # by directly mocking where 'current_url' is assigned or how 'logged_in' is set.
        # A simpler approach for the test: mock the "logged_in" state change directly.
        # To do this, we'd need to patch something inside the loop, or make the loop itself
        # controllable.

        # Simpler: Assume login occurs, and mock return values of evaluate
        # Patch the loop by ensuring `tab.url` will eventually be the logged-in URL
        async def get_url_side_effect(*args, **kwargs):
            if mock_driver.get.call_count <= 1: # First call to driver.get()
                 mock_tab.url = "https://mp.weixin.qq.com/"
            else: # Subsequent checks for tab.url (this part is tricky to mock precisely without more control)
                 mock_tab.url = "https://mp.weixin.qq.com/cgi-bin/home?action=home&token=mocktoken123"
            return mock_tab.url

        # Let's assume the test focuses on extraction AFTER login state is achieved.
        # We'll set the URL to the logged-in one directly for extraction part.
        mock_tab.url = "https://mp.weixin.qq.com/cgi-bin/home?action=home&token=mocktoken123"


        # Configure mock_tab.evaluate for different JS scripts
        expected_fakeid = "fakeid_12345"
        expected_nickname = "Test User"

        async def evaluate_side_effect(script):
            if "user_attributes.fake_id" in script:
                return expected_fakeid
            elif "wx.cgiData.fake_id" in script: # Fallback if first fails
                return None
            elif "wx.cgiData.appmsgstat.fake_id" in script: # Fallback
                return None
            elif "wx.cgiData.nick_name" in script:
                return expected_nickname
            return None

        mock_tab.evaluate = AsyncMock(side_effect=evaluate_side_effect)

        # Run the login flow
        result = asyncio.run(main.do_login_flow())

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['token'], "mocktoken123")
        self.assertEqual(result['fakeid'], expected_fakeid)
        self.assertEqual(result['nickname'], expected_nickname)

        mock_uc.start.assert_called_once()
        mock_driver.get.assert_called_with("https://mp.weixin.qq.com/")

        # Check that evaluate was called for fakeid and nickname
        # This requires checking the call_args_list
        # Example: any(call_args[0][0].startswith("return typeof wx !== 'undefined' && wx.cgiData && wx.cgiData.user_attributes") for call_args in mock_tab.evaluate.call_args_list)
        self.assertTrue(any("user_attributes.fake_id" in str(call[0]) for call in mock_tab.evaluate.call_args_list))
        self.assertTrue(any("wx.cgiData.nick_name" in str(call[0]) for call in mock_tab.evaluate.call_args_list))


if __name__ == '__main__':
    unittest.main()
