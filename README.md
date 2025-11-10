# Playwright Python Project

Version: **1.5.14**

This project uses [Playwright](https://playwright.dev/python/) for end-to-end testing of web applications.  
It is written in Python and provides a foundation for building reliable, fast, and maintainable UI tests.

---

## Features

- Cross-browser testing (Chromium, Firefox, WebKit)
- Headless and headed execution modes
- Automatic waiting for elements
- Playwright Trace Viewer support (screenshots, video, and trace logs)
- Configurable test reports (HTML, JSON, and trace files)

---

## Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (required for Playwright installation)
- [pip](https://pip.pypa.io/en/stable/)

---

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/vadymmerezhko/SmartPythonTest.git
   cd SmartPythonTest
   
2. Create a virtual env in your project root:

   ```bash
   python -m venv .venv
 
3. Activate it with Windows PowerShell:

   ```bash
   .venv\Scripts\Activate.ps1

4. Or activate it with Windows CMD:

   ```bash
   .venv\Scripts\activate.bat

5. Or activate it with Linux/macOS:

   ```bash
   source .venv/bin/activate

6. Install dependencies into this env:

   ```bash
   pip install -r requirements.txt

7. Run all tests:

   ```bash
   pytest

8. Run all tests in test file:

   ```bash
   pytest tests/test_login_positive.py

9. Run specific test in test file:

   ```bash
   pytest -k "test_login_with_valid_credentials"

10. Show detailed logs in console:

   ```bash
   pytest -v
   
11. Generate an HTML report:

   ```bash
   pytest --html=report.html --self-contained-html

12. Run tests in headed mode (see the browser window):

   ```bash
   pytest --headed

13. Run tests in record mode for debug purpose:

   ```bash
   pytest --record_mode=true
   
14. Run tests on specific base URL:

   ```bash
   pytest --base-url=https://staging.saucedemo.com/
