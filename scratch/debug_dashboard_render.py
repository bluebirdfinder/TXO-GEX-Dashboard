import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on("pageerror", lambda err: print(f"❌ PAGE ERROR: {err}"))
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
        
        file_path = os.path.abspath("index.html")
        await page.goto(f"file:///{file_path}")
        
        # Unlock modal
        await page.evaluate("""() => {
            sessionStorage.setItem('gex_unlocked', 'true');
            const modal = document.getElementById('passcode-modal');
            if (modal) modal.style.display = 'none';
        }""")
        await page.wait_for_timeout(1000)
        
        # Take screenshot of page
        await page.screenshot(path="scratch/render_test.png", full_page=True)
        print("[OK] Render test screenshot saved to scratch/render_test.png")
        await browser.close()

asyncio.run(main())
