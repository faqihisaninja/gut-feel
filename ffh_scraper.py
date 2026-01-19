import requests
from telegram import Update
from playwright.async_api import async_playwright, expect
from playwright_stealth import Stealth
from dotenv import load_dotenv
import os
import asyncio  # For running async in sync contexts if needed

load_dotenv()


async def get_text_from_ffh(update: Update):
    email = os.getenv("FFH_EMAIL")
    password = os.getenv("FFH_PASSWORD")

    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            await page.goto("https://www.fantasyfootballhub.co.uk/auth/login")
            await update.message.reply_text(
                "Navigating to Fantasy Football Hub auth page..."
            )
            print("Navigating to Fantasy Football Hub auth page...")

            await page.wait_for_timeout(3000)  # Extra buffer for JS rendering
            await update.message.reply_text("Page loaded. Proceeding to login...")

            # Enter email and password
            await page.locator('input[name="username"]').fill(email)
            await page.locator('input[name="password"]').fill(password)
            await update.message.reply_text("Entering email and password...")
            await page.wait_for_timeout(2000)

            # Submit the form
            await page.locator('button[type="submit"]').first.click()
            await update.message.reply_text("Submitting form...")
            await page.wait_for_url(
                "https://www.fantasyfootballhub.co.uk/", timeout=15000
            )
            await update.message.reply_text("Login redirect complete.")

            # Go to Matthew's team reveals page
            await page.goto("https://www.fantasyfootballhub.co.uk/team-reveals/mj6987")
            await update.message.reply_text(
                "Navigating to Matthew's team reveals page..."
            )
            await page.wait_for_timeout(3000)

            article_link = page.locator(
                '.content a[data-cy="article-preview-link"]'
            ).first
            # Enhanced: Chain visible + enabled for interactability (replaces your expect + wait_for)
            await expect(article_link).to_be_visible(timeout=30000)
            await expect(article_link).to_be_enabled(timeout=15000)  # Ensures clickable
            await update.message.reply_text("Article link located.")
            h3_text = await article_link.locator("h3").text_content()
            await update.message.reply_text(f"Article name: {h3_text}")

            # Handle cookie overlay if present (conditional for regions)
            accept_button = page.locator(".cky-btn.cky-btn-accept").first
            if await accept_button.count() > 0:
                await update.message.reply_text(
                    "Cookie overlay detected. Clicking accept..."
                )
                # Replace wait_for with expect
                await expect(accept_button).to_be_visible(timeout=15000)
                await accept_button.click()
                await update.message.reply_text(
                    "Waiting for cookie overlay to disappear..."
                )
                # Replace wait_for_selector(state="hidden") with expect hidden
                await expect(page.locator(".cky-overlay")).to_be_hidden(timeout=15000)
                await update.message.reply_text("Cookie overlay handled.")
            else:
                await update.message.reply_text(
                    "No cookie overlay detected. Proceeding..."
                )

            # Navigate to the article
            await article_link.click(force=True, timeout=15000)
            await update.message.reply_text("Navigating to article...")

            # Wait for article content div
            content_div = page.locator(
                "article.article div.mt-3.text-base.content-body.text-black-400"
            )
            # Replace wait_for with chained expects: visible
            await expect(content_div).to_be_visible(timeout=15000)
            await update.message.reply_text("Article content div visible.")

            await page.wait_for_timeout(3000)  # Extra buffer for JS rendering

            # Extract text from the article
            article_text = await content_div.text_content()
            await update.message.reply_text("Article text extracted successfully.")
            return article_text

    except Exception as e:
        await update.message.reply_text(f"Error extracting text from page: {e}")
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
