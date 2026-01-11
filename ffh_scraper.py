import requests
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dotenv import load_dotenv
import os
import asyncio  # For running async in sync contexts if needed

load_dotenv()


async def get_text_from_ffh():
    email = os.getenv("FFH_EMAIL")
    password = os.getenv("FFH_PASSWORD")

    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            await page.goto("https://www.fantasyfootballhub.co.uk/")
            print("Navigating to Fantasy Football Hub page...")

            # Handle cookie overlay if present (conditional for regions)
            accept_button = page.locator(".cky-btn.cky-btn-accept").first
            if await accept_button.count() > 0:
                print("Cookie overlay detected. Clicking accept...")
                await accept_button.wait_for(
                    state="visible", timeout=15000
                )  # Increased timeout for cloud variability
                await accept_button.click()
                print("Waiting for cookie overlay to disappear...")
                await page.wait_for_selector(
                    ".cky-overlay", state="hidden", timeout=15000
                )
                print("Cookie overlay handled.")
            else:
                print("No cookie overlay detected. Proceeding...")

            # Click login link
            login_link = page.locator('a[data-cy="account-menu-login"]')
            await login_link.wait_for(state="visible", timeout=15000)
            print("Clicking login link...")
            await login_link.click()
            print("Waiting for login page to load...")
            await page.wait_for_url("**/u/login**", timeout=15000)
            print("Login page loaded.")

            # Enter email and password
            await page.locator('input[name="username"]').fill(email)
            await page.locator('input[name="password"]').fill(password)
            print("Entering email and password...")
            await page.wait_for_timeout(2000)

            # Submit the form
            await page.locator('button[type="submit"]').first.click()
            print("Submitting form...")
            await page.wait_for_url(
                "https://www.fantasyfootballhub.co.uk/", timeout=15000
            )
            print("Login redirect complete.")

            # Go to Matthew's team reveals page
            await page.goto("https://www.fantasyfootballhub.co.uk/team-reveals/mj6987")
            print("Navigating to Matthew's team reveals page...")

            article_link = page.locator(
                '.content a[data-cy="article-preview-link"]'
            ).first
            await article_link.wait_for(state="visible", timeout=15000)
            print("Article link located.")
            h3_text = await article_link.locator("h3").text_content()
            print(f"Article name: {h3_text}")

            # Navigate to the article
            await article_link.click()
            print("Navigating to article...")

            # Wait for article content div
            content_div = page.locator(
                "article.article div.mt-3.text-base.content-body.text-black-400"
            )
            await content_div.wait_for(state="visible", timeout=15000)
            print("Article content div visible.")

            # Explicit waits for full load (addresses the 'bump')
            await page.wait_for_load_state(
                "networkidle"
            )  # Wait for no network activity >500ms
            await page.wait_for_timeout(3000)  # Extra buffer for JS rendering

            # Extract text from the article
            article_text = await content_div.text_content()
            print("Article text extracted successfully.")
            return article_text

    except Exception as e:
        print(f"Error extracting text from page: {e}")
        return None


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

        # Extract deadline times
        current_deadline = (
            current_gameweek.get("deadline_time") if current_gameweek else None
        )
        next_deadline = next_gameweek.get("deadline_time") if next_gameweek else None

        return current_gameweek, next_gameweek, current_deadline, next_deadline
    except Exception as e:
        print(f"Error fetching FPL API data: {e}")
        return None, None, None, None


async def main_scraper():
    """Compare FPL API gameweek data with text from main.py"""
    print("Fetching gameweek data from FPL API...")
    current_gw, next_gw, current_deadline, next_deadline = get_fpl_gameweeks()
    USER_ID = 102528399

    if current_gw:
        print(f"\nCurrent Gameweek from FPL API:")
        print(f"  ID: {current_gw['id']}")
        print(f"  Name: {current_gw['name']}")
        print(f"  Deadline: {current_deadline or 'N/A'}")
    else:
        print("\nNo current gameweek found in FPL API")

    if next_gw:
        print(f"\nNext Gameweek from FPL API:")
        print(f"  ID: {next_gw['id']}")
        print(f"  Name: {next_gw['name']}")
        print(f"  Deadline: {next_deadline or 'N/A'}")
    else:
        print("\nNo next gameweek found in FPL API")

    print("\n" + "=" * 50)
    print("Extracting text from Fantasy Football Hub page...")
    hub_text = await get_text_from_ffh()

    if hub_text:
        print("Summarising FPL news...")
        from agent import summarise_fpl_news  # Import here if not global

        summary = summarise_fpl_news(
            hub_text, current_gw, next_gw, current_deadline, next_deadline, USER_ID
        )  # Note: summarise_fpl_news is sync
        print(f"Summary: {summary}")
    else:
        print("\nFailed to extract text from Fantasy Football Hub page")


if __name__ == "__main__":
    asyncio.run(main_scraper())
