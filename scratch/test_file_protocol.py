import os
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 3200})
        
        file_url = "file:///" + os.path.abspath("index.html").replace("\\", "/")
        await page.goto(file_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        # Fill passcode input if visible
        modal = await page.query_selector("#passcode-modal")
        if modal and await modal.is_visible():
            await page.fill("#passcode-input", "GEX2026")
            await page.evaluate("document.getElementById('unlock-btn').click()")
            await page.wait_for_timeout(1500)

        artifacts_dir = r"C:\Users\TWLaiAl\.gemini\antigravity-ide\brain\3a015dd1-c51f-4624-a0fa-ece6a75df799"
        shot = os.path.join(artifacts_dir, "v36_file_protocol_full.png")
        await page.screenshot(path=shot, full_page=True)
        print(f"[OK] Saved file:/// protocol screenshot: {shot}")

        await browser.close()

asyncio.run(run())
