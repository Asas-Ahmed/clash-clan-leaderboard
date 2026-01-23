import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wake_streamlit():
    url = "https://coc-area51.streamlit.app/"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Add a real browser name so Streamlit doesn't block the bot
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"Opening {url}...")
        driver.get(url)
        time.sleep(5) # Wait for initial redirect
        
        # Look for the button
        wait = WebDriverWait(driver, 30)
        button_xpath = "//button[contains(text(), 'Yes, get this app back up')]"
        
        wake_button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        wake_button.click()
        print("✅ Clicked the 'Wake Up' button!")
        
        # CRITICAL: Wait 60 seconds to let the server start booting
        print("Waiting 60s for the 'oven' to start...")
        time.sleep(60)
        print("Done. Check the app now.")
        
    except Exception as e:
        print("ℹ️ App might already be awake or button not found.")
    finally:
        driver.quit()

if __name__ == "__main__":
    wake_streamlit()
