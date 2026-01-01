import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from agent import summarise_fpl_news
import time
import os

load_dotenv()


def get_text_from_ffh():
    email = os.getenv("FFH_EMAIL")
    password = os.getenv("FFH_PASSWORD")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Optional, but helps in some setups
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://www.fantasyfootballhub.co.uk/")
        wait = WebDriverWait(driver, 10)
        print("Navigating to Fantasy Football Hub page...")

        # Handle cookie overlay if present
        accept_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".cky-btn.cky-btn-accept"))
        )
        print("Clicking accept button...")
        accept_button.click()
        print("Waiting for cookie overlay to disappear...")
        wait.until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".cky-overlay"))
        )
        print("Cookie overlay disappeared.")
        # Click login link
        login_link = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'a[data-cy="account-menu-login"]')
            )
        )
        print("Clicking login link...")
        login_link.click()
        print("Waiting for login page to load...")
        # Wait for login page to load
        wait.until(EC.url_contains("auth.fantasyfootballhub.co.uk/u/login"))
        print("Login page loaded.")
        # Enter email and password
        driver.find_element(By.NAME, "username").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        print("Entering email and password...")

        # Submit the form
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        print("Submitting form...")
        # Wait for login redirect
        wait.until(EC.url_contains("https://www.fantasyfootballhub.co.uk/"))
        print("Login redirect complete.")
        # Go to Matthew's team reveals page
        driver.get("https://www.fantasyfootballhub.co.uk/team-reveals/mj6987")
        print("Navigating to Matthew's team reveals page...")
        article_link = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".content a[data-cy='article-preview-link']")
            )
        )
        print("Article link located after wait.")
        h3_text = article_link.find_element(By.TAG_NAME, "h3").text
        print(f"Article name: {h3_text}")

        # Navigate to the article
        article_link.click()
        print("Navigating to article...")
        content_div = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "article.article div.mt-3.text-base.content-body.text-black-400",
                )
            )
        )
        print("Article page loaded.")

        # Wait for the text to stabilize
        time.sleep(2)

        # Extract text from the article
        article_text = content_div.text
        return article_text
    except Exception as e:
        print(f"Error extracting text from page: {e}")
        return None
    finally:
        driver.quit()


def get_fpl_gameweeks():
    """Fetch current and next gameweek from the official FPL API"""
    try:
        response = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/"
        )
        response.raise_for_status()
        data = response.json()

        # Extract gameweek information
        events = data.get("events", [])
        current_gameweek = next(
            (event for event in events if event.get("is_current")), None
        )
        next_gameweek = next((event for event in events if event.get("is_next")), None)

        return current_gameweek, next_gameweek
    except Exception as e:
        print(f"Error fetching FPL API data: {e}")
        return None, None


def check_gameweek_match():
    """Compare FPL API gameweek data with text from main.py"""
    print("Fetching gameweek data from FPL API...")
    current_gw, next_gw = get_fpl_gameweeks()

    if current_gw:
        print(f"\nCurrent Gameweek from FPL API:")
        print(f"  ID: {current_gw['id']}")
        print(f"  Name: {current_gw['name']}")
        print(f"  Deadline: {current_gw.get('deadline_time', 'N/A')}")
    else:
        print("\nNo current gameweek found in FPL API")

    if next_gw:
        print(f"\nNext Gameweek from FPL API:")
        print(f"  ID: {next_gw['id']}")
        print(f"  Name: {next_gw['name']}")
        print(f"  Deadline: {next_gw.get('deadline_time', 'N/A')}")
    else:
        print("\nNo next gameweek found in FPL API")

    print("\n" + "=" * 50)
    print("Extracting text from Fantasy Football Hub page...")
    hub_text = get_text_from_ffh()

    if hub_text:
        print("Summarising FPL news...")
        summary = summarise_fpl_news(hub_text, current_gw, next_gw)
        print(f"Summary: {summary}")
    else:
        print("\nFailed to extract text from Fantasy Football Hub page")


if __name__ == "__main__":
    check_gameweek_match()
