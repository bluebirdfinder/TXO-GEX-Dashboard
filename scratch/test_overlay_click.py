import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        file_path = os.path.abspath("index.html")
        await page.goto(f"file:///{file_path}")
        
        await page.evaluate("sessionStorage.setItem('gex_unlocked', 'true');")
        await page.reload()
        await page.wait_for_timeout(1000)
        
        # Take screenshot 1: With Net GEX curve line
        chart_el = await page.query_selector("#gex-chart")
        if chart_el:
            await chart_el.screenshot(path="scratch/chart_with_curve.png")
            print("[OK] Saved scratch/chart_with_curve.png")
        
        # Click overlay compare button
        await page.click("#overlay-compare-btn")
        await page.wait_for_timeout(500)
        
        if chart_el:
            await chart_el.screenshot(path="scratch/chart_overlay_mode.png")
            print("[OK] Saved scratch/chart_overlay_mode.png")
            
        await browser.close()

asyncio.run(main())
