# Playwright Python Project

Version: **1.10.4**

This project uses [Playwright](https://playwright.dev/python/) for end-to-end testing of web applications.  
It is written in Python and provides a foundation for building reliable, fast, and maintainable UI tests.

---

## Features

- Cross-browser testing (Chromium, Firefox, WebKit, Chrome, Edge)
- Headless and headed execution modes
- Automatic waiting for elements
- Playwright Trace Viewer support (screenshots, video, and trace logs)
- Configurable test reports (HTML, JSON, and trace files)
- Record mode for element selectors, input and expected values initializing
- Self-healing element selectors and expected values in record mode  

---

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/vadymmerezhko/SmartPythonTest.git
   
2. Change directory:

    ```bash
    cd SmartPythonTest
 
3. Download and install Python 3.x.x (latest stable version):

   ```bash
   ttps://www.python.org/downloads/windows/

4. Install pip:
   
    ```bash
   python -m pip install --upgrade pip

5. Upgrade pip:

    ```bash
    python -m pip install --upgrade pip 

6. Activate virtual environment with Windows PowerShell:

   ```bash
   .venv\Scripts\Activate.ps1

7. Or activate it with Windows CMD:

   ```bash
   .venv\Scripts\activate.bat

8. Or activate it with Linux/macOS:

   ```bash
   source .venv/bin/activate

9. Install Playwright:

    ```bash
    playwright install --with-deps

10. Install dependencies into this venv:

   ```bash
   pip install -r requirements.txt

11. Run all tests:

   ```bash
   pytest

12. Run all tests in test file:

   ```bash
   pytest tests/test_login_demo.py

13. Run specific test in test file:

   ```bash
   pytest -k "test_login_with_valid_credentials"
   
14. Show detailed logs in console:

   ```bash
   pytest -v

15. Generate an HTML report:

   ```bash
   pytest --html=report.html --self-contained-html

16. Run tests in headed mode (see the browser window):

   ```bash
   pytest --headed

17. Run tests in record mode for debug purpose:

   ```bash
   pytest --record_mode=true
   
18. Run tests on specific base URL:

   ```bash
   pytest --base-url=https://staging.saucedemo.com/
   
19. Run tests and highlight the current element:

   ```bash
   pytest --highlight=true
   
20. Run tests and make delay before every test step in milliseconds:

   ```bash
   pytest --step_delay=500
   
21. Run tests and make screenshot after test failure and attach it to test report:

   ```bash
   pytest --screenshot_on_error=true

