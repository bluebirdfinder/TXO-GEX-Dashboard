import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err.name}: {err.message}\n{err.stack}"))
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text} (Location: {msg.location})"))
        
        file_path = os.path.abspath("index.html")
        await page.goto(f"file:///{file_path}")
        await page.wait_for_timeout(1000)
        
        await browser.close()

asyncio.run(main())
