import os
import time
import subprocess
import asyncio
from playwright.async_api import async_playwright

async def run():
    # Start HTTP server
    proc = subprocess.Popen(["python", "-m", "http.server", "8085"], cwd=os.getcwd())
    time.sleep(1.5)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1400, "height": 2400})
            
            await page.goto("http://127.0.0.1:8085/index.html", wait_until="networkidle")
            await page.wait_for_timeout(1000)

            # Fill passcode modal if visible
            modal = await page.query_selector("#passcode-modal")
            if modal and await modal.is_visible():
                await page.fill("#passcode-input", "GEX2026")
                await page.click("#unlock-btn")
                await page.wait_for_timeout(1500)

            artifacts_dir = r"C:\Users\TWLaiAl\.gemini\antigravity-ide\brain\3a015dd1-c51f-4624-a0fa-ece6a75df799"
            
            shot1 = os.path.join(artifacts_dir, "v36_http_full_page.png")
            await page.screenshot(path=shot1, full_page=True)
            print(f"[OK] Saved HTTP screenshot: {shot1}")

            await browser.close()
    finally:
        proc.terminate()

asyncio.run(run())
