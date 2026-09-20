from playwright.sync_api import sync_playwright

def take_screenshot(screenshot_name):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500)
        context = browser.new_context(storage_state="/data/state.json")

        page = context.new_page()
        page.goto("https://www.tradingview.com/")
        page.locator('[data-main-menu-root-track-id="products"]').click()
        page.get_by_role("radio", name="15 minutes").click()
        page.screenshot(path=f"{screenshot_name}.png")