import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wake_streamlit():
    url = "https://coc-area51.streamlit.app/"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Run without a window
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait up to 20 seconds for the "Wake Up" button to appear
        wait = WebDriverWait(driver, 20)
        button_xpath = "//button[contains(text(), 'Yes, get this app back up')]"
        
        wake_button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        wake_button.click()
        print("✅ Clicked the 'Wake Up' button!")
        
    except Exception as e:
        print("ℹ️ Button not found. The app might already be awake or the page changed.")
    finally:
        driver.quit()

if __name__ == "__main__":
    wake_streamlit()
