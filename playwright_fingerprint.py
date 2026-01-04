from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import asyncio
import time


async def get_fingerprint():
    # initiate playwright
    async with Stealth().use_async(async_playwright()) as p:
        # launch headless browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://bot.sannysoft.com/")

        # wait for the page to load completely
        time.sleep(5)
        await page.screenshot(path="screenshot.png", full_page=True)
        await browser.close()


# run the scraper
if __name__ == "__main__":
    asyncio.run(get_fingerprint())
