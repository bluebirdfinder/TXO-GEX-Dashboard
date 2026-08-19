import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        file_path = os.path.abspath("index.html")
        await page.goto(f"file:///{file_path}")
        
        # Clear sessionStorage to force modal to show
        await page.evaluate("sessionStorage.clear(); localStorage.clear();")
        await page.reload()
        
        await page.wait_for_selector("#passcode-modal", state="visible")
        input_type_before = await page.get_attribute("#passcode-input", "type")
        print(f"Type before click: {input_type_before}")
        
        # Click the eye button
        await page.click("#toggle-pass-vis-btn")
        await page.wait_for_timeout(300)
        
        input_type_after = await page.get_attribute("#passcode-input", "type")
        print(f"Type after click: {input_type_after}")
        assert input_type_after == "text", "Expected type='text' after eye click!"
        
        # Click eye button again to toggle back
        await page.click("#toggle-pass-vis-btn")
        await page.wait_for_timeout(300)
        input_type_after_second = await page.get_attribute("#passcode-input", "type")
        print(f"Type after second click: {input_type_after_second}")
        assert input_type_after_second == "password", "Expected type='password' after second eye click!"
        
        # Type passcode
        await page.fill("#passcode-input", "gex2026")
        await page.click("#unlock-btn")
        await page.wait_for_selector("#passcode-modal", state="hidden")
        print("[SUCCESS] Password Eye Toggle works & case-insensitive GEX2026 unlocks page perfectly!")
        
        await browser.close()

asyncio.run(main())
