# WeChat MP CLI Tool (Python Version)

This is a command-line interface (CLI) tool, written in Python, for interacting with the WeChat Official Accounts Platform (mp.weixin.qq.com). It uses `nodriver` to automate browser interactions for login and data fetching.

## Prerequisites

*   Python 3.8+
*   Google Chrome or Chromium browser installed (as `nodriver` will control it).

## Setup

1.  **Navigate to the application directory**:
    ```bash
    cd python_cli_app
    ```

2.  **Create and activate a Python virtual environment**:
    ```bash
    python -m venv .venv
    # On Windows
    # .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: `nodriver` might download or update browser driver components on its first run.*

## Usage

The script is run via `python main.py`.

```bash
python main.py [command] [options]
```

### Available Commands and Options:

*   **Login**: Initiates the login process. You will be prompted to scan a QR code using your WeChat app.
    ```bash
    python main.py --login
    ```

*   **Get Articles**: Fetches published articles for a WeChat Official Account.
    ```bash
    python main.py --get-articles [--fakeid YOUR_FAKEID] [--token YOUR_TOKEN]
    ```
    *   `--fakeid YOUR_FAKEID`: (Optional) The `fakeid` of the target WeChat Official Account. If not provided, the script will attempt to discover it after login (current discovery might be limited).
    *   `--token YOUR_TOKEN`: (Optional) Your session token. If not provided, you will be prompted to log in.
    *   If both `--fakeid` and `--token` are omitted, the script will first attempt a full login to obtain them.

*   **Debug Mode**: Enables detailed debug logging.
    ```bash
    python main.py --login --debug
    python main.py --get-articles --debug
    ```

*   **Help**: Shows the help message with all available commands and options.
    ```bash
    python main.py --help
    ```

### Login Process

When you use a command that requires login (like `--login` or `--get-articles` without providing a token), `nodriver` will open a browser window displaying the WeChat MP login page with a QR code. You need to scan this QR code with your WeChat mobile app to log in. After successful login, the CLI tool will proceed with the requested command.

## Notes

*   The `fakeid` is a unique identifier for WeChat Official Accounts. For your own account, it might be automatically detected after login. For other accounts, you might need to find it through other means if automatic detection fails.
*   Ensure your Chrome/Chromium browser is up to date.
