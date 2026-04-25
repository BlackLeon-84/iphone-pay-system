import asyncio
from playwright.async_api import async_playwright
import sys

async def keep_alive():
    url = "https://iphone-pay-system.streamlit.app"
    print(f"[*] Starting keep-alive script for {url}")
    
    async with async_playwright() as p:
        # 실제 브라우저처럼 보이기 위해 User-Agent 설정
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"[*] Navigating to {url}...")
            # 페이지 접속 및 로딩 대기
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 스트림릿 특유의 로딩 화면이 지나갈 때까지 잠시 대기
            print("[*] Page loaded. Waiting for 30 seconds to ensure session is active...")
            await asyncio.sleep(30)
            
            print(f"[*] Successfully visited {url}")
            print(f"[*] Page Title: {await page.title()}")
            
        except Exception as e:
            print(f"[!] Error occurred: {e}")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(keep_alive())
