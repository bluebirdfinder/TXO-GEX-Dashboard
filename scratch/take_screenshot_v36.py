import os
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 2200})
        
        file_url = "file:///" + os.path.abspath("index.html").replace("\\", "/")
        await page.goto(file_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Fill passcode modal
        modal = await page.query_selector("#passcode-modal")
        if modal and await modal.is_visible():
            await page.fill("#passcode-input", "GEX2026")
            await page.click("#unlock-btn")
            await page.wait_for_timeout(1000)

        # Take screenshots of full page and key components
        artifacts_dir = r"C:\Users\TWLaiAl\.gemini\antigravity-ide\brain\3a015dd1-c51f-4624-a0fa-ece6a75df799"
        
        shot1 = os.path.join(artifacts_dir, "v36_top_and_hot_money.png")
        await page.screenshot(path=shot1, full_page=False)
        print(f"[OK] Saved screenshot 1: {shot1}")

        # Scroll to stock futures table
        stock_panel = await page.query_selector("#stock-futures-panel")
        if stock_panel:
            await stock_panel.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            shot2 = os.path.join(artifacts_dir, "v36_stock_futures_basis.png")
            await page.screenshot(path=shot2, full_page=False)
            print(f"[OK] Saved screenshot 2: {shot2}")

        await browser.close()

asyncio.run(run())
