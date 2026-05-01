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
            
            # 스트림릿 특유의 로딩 화면 또는 슬립 모드 버튼 대기
            print("[*] Page loaded. Checking for sleep mode...")
            
            # 슬립 모드 버튼이 나타날 수 있으므로 잠시 대기
            await asyncio.sleep(10)
            
            # 'Yes, get this app back up' 버튼 텍스트가 포함된 버튼 찾기
            wake_button = page.locator("button:has-text('Yes, get this app back up')")
            
            if await wake_button.count() > 0:
                print("[*] Sleep mode detected! Clicking the 'Wake Up' button...")
                await wake_button.first.click()
                print("[*] Button clicked. Waiting 60 seconds for the app to boot up...")
                await asyncio.sleep(60)
                print(f"[*] App should be awake now. Title: {await page.title()}")
            else:
                print("[*] App is already awake. Staying for 30 seconds to maintain session...")
                await asyncio.sleep(30)
                print(f"[*] Session maintained. Title: {await page.title()}")
            
            print(f"[*] Successfully processed {url}")
            
        except Exception as e:
            print(f"[!] Error occurred: {e}")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(keep_alive())
