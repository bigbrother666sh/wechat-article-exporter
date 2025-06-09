import asyncio
import nodriver as uc
import time
import re # For token extraction
from urllib.parse import urlencode # Needed for constructing URLs with params
import json # For parsing JSON responses
import argparse # For CLI arguments
import logging # For logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def do_login_flow():
    """
    Handles the login process for WeChat MP, extracts information, and returns it.
    This function will manage its own browser session.
    Returns:
        dict: {'token': str, 'fakeid': str, 'nickname': str} or None if login fails.
    """
    login_info = None
    try:
        logger.info("Launching browser for login...")
        async with await uc.start(
            headless=True,
            browser_args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--enable-logging', '--v=1'],
            debug=True
        ) as driver:
            try:
                tab = await driver.get("https://mp.weixin.qq.com/")
                logger.info("Please scan the QR code on the WeChat MP login page (within 2 minutes).")
            except Exception as nav_e:
                logger.error(f"Error navigating to login page: {nav_e}")
                return None

            logged_in = False
            login_check_attempts = 0
            max_login_check_attempts = 120

            while not logged_in and login_check_attempts < max_login_check_attempts:
                try:
                    await tab.sleep(1)
                    current_url = tab.url
                    if "mp.weixin.qq.com/cgi-bin/home" in current_url:
                        logged_in = True
                        logger.info("Login successful!")
                    else:
                        login_check_attempts += 1
                        if login_check_attempts % 20 == 0:
                            logger.info(f"Still waiting for login... (Attempt {login_check_attempts}/{max_login_check_attempts})")
                except Exception as loop_e:
                    logger.warning(f"Exception during login wait loop: {loop_e}")
                    # Depending on the error, might break or continue
                    await asyncio.sleep(1) # prevent rapid spin on certain errors

            if not logged_in:
                logger.warning("Login timeout.")
                return None

            logger.info("Extracting information post-login...")
            current_url = tab.url # Ensure current_url is fresh

            token = None
            try:
                token_match = re.search(r"token=(\w+)", current_url)
                if token_match:
                    token = token_match.group(1)
                    logger.info(f"Extracted token: {token}")
                else:
                    logger.warning("Could not extract token from URL.")
            except Exception as e_token:
                logger.error(f"Error extracting token: {e_token}")

            fakeid = None
            js_scripts_for_fakeid = [
                "return typeof wx !== 'undefined' && wx.cgiData && wx.cgiData.user_attributes && wx.cgiData.user_attributes.fake_id ? wx.cgiData.user_attributes.fake_id : null;",
                "return typeof wx !== 'undefined' && wx.cgiData && wx.cgiData.fake_id ? wx.cgiData.fake_id : null;",
                "return typeof wx !== 'undefined' && wx.cgiData && wx.cgiData.appmsgstat && wx.cgiData.appmsgstat.fake_id ? wx.cgiData.appmsgstat.fake_id : null;"
            ]
            for i, script in enumerate(js_scripts_for_fakeid):
                try:
                    result = await tab.evaluate(script)
                    if result:
                        fakeid = str(result)
                        logger.info(f"Extracted fakeid (JS attempt {i+1}): {fakeid}")
                        break
                except Exception as e_js:
                    logger.warning(f"Error trying script for fakeid (attempt {i+1}, {script[:30]}...): {e_js}")

            if not fakeid:
                logger.warning("Could not automatically determine fakeid from JS.")

            nickname = None
            try:
                nickname_script_result = await tab.evaluate("return typeof wx !== 'undefined' && wx.cgiData && wx.cgiData.nick_name ? wx.cgiData.nick_name : null;")
                if nickname_script_result:
                    nickname = nickname_script_result
                    logger.info(f"Extracted nickname (JS): {nickname}")
                else:
                    logger.warning("Could not extract nickname using wx.cgiData.nick_name via JS.")
            except Exception as e_nick:
                logger.error(f"Error during nickname extraction (JS): {e_nick}")

            if token and fakeid and nickname: # Assuming all three are desirable for a "complete" login_info
                login_info = {'token': token, 'fakeid': fakeid, 'nickname': nickname}
                logger.info(f"Login successful for: {nickname}")
            elif token and fakeid: # If nickname is less critical for some operations
                login_info = {'token': token, 'fakeid': fakeid, 'nickname': None}
                logger.warning(f"Login succeeded (token/fakeid obtained) but nickname missing for: {fakeid}")
            else:
                logger.error("Essential information (token and/or fakeid) missing after login attempt.")

            logger.info("Login flow finished. Browser will close.")
            await tab.sleep(2)

        logger.info("Browser session for login finished and cleaned up.")
        return login_info

    except Exception as e: # Catch broader errors like uc.start() failing
        logger.critical(f"A critical error occurred during the login process: {e}", exc_info=True)
        return None


async def fetch_articles_command(token: str, fakeid: str):
    """
    Command to fetch articles. Manages its own browser session.
    """
    if not token or not fakeid:
        logger.error("Token and FakeID are required to fetch articles.")
        return

    logger.info(f"\nLaunching browser to fetch articles for fakeid: {fakeid}...")
    try:
        async with await uc.start(
            headless=True,
            browser_args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
        ) as driver:
            # Get a tab object. Navigating to 'about:blank' is a safe way to get a tab.
            tab = await driver.get('about:blank')
            if not tab:
                logger.error("Failed to get a browser tab for fetching articles.")
                return
            await _fetch_and_print_articles(tab, token, fakeid)
            await tab.sleep(2)
        logger.info("Browser session for fetching articles finished and cleaned up.")
    except Exception as e:
        logger.critical(f"An error occurred during article fetching command: {e}", exc_info=True)


async def _fetch_and_print_articles(tab, token, fakeid):
    """
    Utility function to fetch and print articles using an existing tab.
    """
    articles_url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
    params = {
        "action": "list_ex", "begin": "0", "count": "5", "fakeid": fakeid,
        "type": "101_1", "token": token, "lang": "zh_CN", "f": "json", "ajax": "1"
    }

    logger.info(f"Fetching articles from: {articles_url} with params affecting URL directly.")

    try:
        full_url = f"{articles_url}?{urlencode(params)}"
        logger.debug(f"Constructed article fetch URL: {full_url}")
        await tab.get(full_url)

        # Get page content using tab.evaluate to get text content of the body
        json_text_content = await tab.evaluate("document.body.textContent")

        try:
            json_response = json.loads(json_text_content)
            logger.info(f"Raw JSON response from article fetch: {str(json_response)[:500]}...")
        except json.JSONDecodeError as json_e:
            logger.error(f"Failed to decode JSON from article fetch: {json_e}")
            logger.debug(f"Non-JSON content received: {json_text_content[:500]}...")
            return

        publish_list = json_response.get("publish_page", {}).get("publish_list", [])

        if not publish_list:
            logger.warning("No articles found or unexpected JSON structure in publish_list.")
            return

        logger.info("\n--- Fetched Articles ---")
        for i, item_wrapper in enumerate(publish_list):
            title = None
            publish_info = item_wrapper.get("publish_info")
            appmsg_info = item_wrapper.get("appmsg_info")

            if appmsg_info and appmsg_info.get("title"):
                title = appmsg_info['title']
                logger.info(f"- Article {i+1}: {title} (from appmsg_info)")
            elif publish_info:
                try:
                    article_details_list = json.loads(publish_info)
                    for article_detail in article_details_list: # Usually one item in this list for single posts
                        if isinstance(article_detail, dict):
                            if article_detail.get("title"):
                                title = article_detail['title']
                                logger.info(f"- Article {i+1}: {title} (from publish_info list)")
                                break # Assuming one title per publish_info entry
                            elif article_detail.get("appmsg_info", {}).get("title"):
                                title = article_detail['appmsg_info']['title']
                                logger.info(f"- Article {i+1}: {title} (from publish_info list's appmsg_info)")
                                break
                    if not title: # If loop finished and no title found in list
                         logger.warning(f"- Article {i+1}: Title not found in parsed publish_info: {publish_info[:100]}...")
                except json.JSONDecodeError as jde:
                    logger.error(f"Could not parse publish_info JSON for article {i+1}: {jde}. Content: {publish_info[:100]}")
            elif item_wrapper.get("title"):
                title = item_wrapper['title']
                logger.info(f"- Article {i+1}: {title} (direct from item_wrapper)")
            else:
                logger.warning(f"- Article {i+1}: Could not find title in item: {str(item_wrapper)[:100]}...")

    except Exception as e: # Catch network errors, tab.get errors, etc.
        logger.error(f"Error during fetching or parsing articles: {e}", exc_info=True)
        try:
            page_content_on_error = await tab.evaluate("document.body.textContent") # Corrected
            logger.debug(f"Page content on error during article fetch: {page_content_on_error[:500]}...")
        except Exception as e_pc:
            logger.error(f"Could not get page content on error: {e_pc}")

async def main_cli():
    # Configure basic logging within main_cli if preferred over global
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # global_logger = logging.getLogger(__name__) # Use the global logger

    parser = argparse.ArgumentParser(description="WeChat MP CLI tool using nodriver.")
    parser.add_argument('--login', action='store_true', help='Initiate the login process to WeChat MP.')
    parser.add_argument('--get-articles', action='store_true', help='Fetch articles. Requires login or token/fakeid.')
    parser.add_argument('--fakeid', type=str, help='The fakeid of the WeChat Official Account.')
    parser.add_argument('--token', type=str, help='The session token.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')


    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG) # Set root logger level
        logger.setLevel(logging.DEBUG) # Set specific logger level if needed
        logger.debug("Debug logging enabled.")


    try:
        if args.login:
            logger.info("Login process initiated by CLI command...")
            login_details = await do_login_flow()
            if login_details:
                logger.info(f"Login completed. Nickname: {login_details.get('nickname')}, Token: {login_details.get('token')}, FakeID: {login_details.get('fakeid')}")
            else:
                logger.warning("Login process failed or was aborted.")

        elif args.get_articles:
            logger.info("Get articles process initiated by CLI command...")
            token_to_use = args.token
            fakeid_to_use = args.fakeid

            if not token_to_use or not fakeid_to_use:
                logger.info("Token or FakeID not provided via CLI args, attempting login to retrieve them...")
                try:
                    login_details = await do_login_flow()
                    if login_details and login_details.get('token') and login_details.get('fakeid'):
                        token_to_use = login_details.get('token')
                        fakeid_to_use = login_details.get('fakeid')
                        logger.info("Token and FakeID retrieved successfully via login.")
                    else:
                        logger.error("Login failed or did not return necessary token/fakeid for fetching articles.")
                        return # Exit if login for info failed
                except Exception as e_login_get:
                    logger.critical(f"Exception during login attempt for get-articles: {e_login_get}", exc_info=True)
                    return # Exit on critical error

            if token_to_use and fakeid_to_use:
                await fetch_articles_command(token_to_use, fakeid_to_use)
            else:
                logger.error("Cannot fetch articles: Token or FakeID is missing.")

        else:
            import sys
            if len(sys.argv) == 1:
                 parser.print_help()
            else: # Some args were passed but not --login or --get-articles
                logger.warning("No specific command (--login or --get-articles) was prioritized. Use -h for help.")
    except Exception as e_main:
        logger.critical(f"A critical error occurred in main_cli: {e_main}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main_cli())
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user.")
    except Exception as e: # Catch any other unexpected top-level errors
        logger.critical(f"A top-level error occurred before asyncio.run could complete gracefully: {e}", exc_info=True)
# Imports moved to the top
