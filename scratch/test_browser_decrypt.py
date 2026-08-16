import os
import time
import subprocess
import asyncio
from playwright.async_api import async_playwright

async def run():
    proc = subprocess.Popen(["python", "-m", "http.server", "8087"], cwd=os.getcwd())
    time.sleep(1.0)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1400, "height": 2600})
            
            page.on("console", lambda msg: print(f"[Console] {msg.type}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"[PageError] {err}"))

            await page.goto("http://127.0.0.1:8087/index.html", wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)

            # Fill passcode input and click unlock button
            await page.fill("#passcode-input", "GEX2026")
            await page.click("#unlock-btn")
            await page.wait_for_timeout(2000)

            artifacts_dir = r"C:\Users\TWLaiAl\.gemini\antigravity-ide\brain\3a015dd1-c51f-4624-a0fa-ece6a75df799"
            shot = os.path.join(artifacts_dir, "v36_unlocked_full_page.png")
            await page.screenshot(path=shot, full_page=True)
            print(f"[OK] Saved full unlocked page screenshot to: {shot}")

            await browser.close()
    finally:
        proc.terminate()

asyncio.run(run())
