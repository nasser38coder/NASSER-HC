import random
import time
import logging
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoReporter:
    def __init__(self):
        self.accounts = []
        self.results = []
    
    def load_accounts(self):
        try:
            with open(config.ACCOUNTS_FILE, 'r') as f:
                for line in f:
                    parts = line.strip().split(':')
                    if len(parts) >= 3:
                        self.accounts.append({
                            'username': parts[0],
                            'password': parts[1],
                            'email': parts[2]
                        })
            return self.accounts
        except:
            return []
    
    def login(self, driver, username, password):
        try:
            driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(2)
            
            wait = WebDriverWait(driver, 10)
            username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            username_input.send_keys(username)
            
            password_input = driver.find_element(By.NAME, "password")
            password_input.send_keys(password)
            
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            time.sleep(3)
            
            return "login" not in driver.current_url
            
        except:
            return False
    
    def report_user(self, driver, target):
        try:
            profile_url = f"https://www.instagram.com/{target}/"
            driver.get(profile_url)
            time.sleep(3)
            
            wait = WebDriverWait(driver, 10)
            
            options_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'خيارات')]"))
            )
            options_button.click()
            time.sleep(1)
            
            report_option = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'إبلاغ')]"))
            )
            report_option.click()
            time.sleep(1)
            
            reason = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'بريد مزعج')]"))
            )
            reason.click()
            time.sleep(1)
            
            submit = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'إرسال')]"))
            )
            submit.click()
            time.sleep(2)
            
            return True
            
        except:
            return False
    
    def mass_report(self, target, max_accounts=10):
        self.load_accounts()
        
        if not self.accounts:
            logger.error("❌ لا توجد حسابات")
            return []
        
        results = []
        for account in self.accounts[:max_accounts]:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--headless')
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            try:
                if self.login(driver, account['username'], account['password']):
                    if self.report_user(driver, target):
                        results.append({
                            'account': account['username'],
                            'target': target,
                            'status': 'success'
                        })
                        logger.info(f"✅ بلاغ من {account['username']}")
                    else:
                        results.append({
                            'account': account['username'],
                            'target': target,
                            'status': 'failed'
                        })
                else:
                    results.append({
                        'account': account['username'],
                        'target': target,
                        'status': 'login_failed'
                    })
            except Exception as e:
                results.append({
                    'account': account['username'],
                    'target': target,
                    'status': 'error',
                    'error': str(e)
                })
            finally:
                driver.quit()
                time.sleep(random.uniform(3, 6))
        
        return results
