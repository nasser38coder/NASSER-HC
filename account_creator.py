import random
import string
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import logging
import config
from temp_email_service import TempEmailService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccountCreator:
    def __init__(self):
        self.ua = UserAgent()
        self.email_service = TempEmailService()
        self.accounts = []
        self.success = 0
        self.failed = 0
        os.makedirs("data", exist_ok=True)
    
    def setup_driver(self):
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'user-agent={self.ua.random}')
        
        if config.HEADLESS_MODE:
            options.add_argument('--headless')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def generate_data(self):
        first_names = ['Ahmed', 'Mohamed', 'Sara', 'Nora', 'Omar', 'Layla', 'Khalid', 'Nadia']
        last_names = ['Ali', 'Hassan', 'Khalid', 'Saeed', 'Omar', 'Nasser', 'Ibrahim']
        
        prefix = random.choice(['user', 'insta', 'real', 'cool', 'super'])
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        username = f"{prefix}_{suffix}"
        
        chars = string.ascii_letters + string.digits + "!@#$%"
        password = ''.join(random.choices(chars, k=14))
        
        return {
            'username': username,
            'password': password,
            'full_name': f"{random.choice(first_names)} {random.choice(last_names)}"
        }
    
    def create_account(self):
        try:
            data = self.generate_data()
            logger.info(f"🚀 إنشاء حساب: {data['username']}")
            
            email_data = self.email_service.create_email()
            if not email_data:
                return None
            email = email_data['email']
            
            driver = self.setup_driver()
            wait = WebDriverWait(driver, 20)
            
            driver.get("https://www.instagram.com/accounts/emailsignup/")
            time.sleep(2)
            
            # إدخال البريد
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
            email_input.send_keys(email)
            time.sleep(1)
            
            # إدخال الاسم
            name_input = driver.find_element(By.NAME, "fullName")
            name_input.send_keys(data['full_name'])
            time.sleep(1)
            
            # إدخال اسم المستخدم
            username_input = driver.find_element(By.NAME, "username")
            username_input.send_keys(data['username'])
            time.sleep(1)
            
            # إدخال كلمة المرور
            password_input = driver.find_element(By.NAME, "password")
            password_input.send_keys(data['password'])
            time.sleep(1)
            
            # الضغط على تسجيل
            signup_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            signup_button.click()
            time.sleep(5)
            
            # انتظار كود التفعيل
            code = self.email_service.get_verification_code(max_wait=120)
            
            if code:
                try:
                    code_input = wait.until(EC.presence_of_element_located((By.NAME, "code")))
                    code_input.send_keys(code)
                    time.sleep(1)
                    
                    verify_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                    verify_button.click()
                    time.sleep(3)
                    
                    data['email'] = email
                    data['status'] = 'active'
                    self.accounts.append(data)
                    self.success += 1
                    
                    logger.info(f"✅ تم إنشاء: {data['username']}")
                    return data
                    
                except:
                    logger.warning("⚠️ فشل إدخال الكود")
            
            driver.quit()
            return None
            
        except Exception as e:
            logger.error(f"❌ خطأ: {e}")
            self.failed += 1
            return None
    
    def create_bulk(self, count=10):
        results = []
        for i in range(count):
            logger.info(f"📌 الحساب {i+1}/{count}")
            acc = self.create_account()
            if acc:
                results.append(acc)
                self.save_accounts()
            time.sleep(random.uniform(10, 20))
        
        return results
    
    def save_accounts(self):
        with open(config.ACCOUNTS_FILE, 'w') as f:
            for acc in self.accounts:
                f.write(f"{acc['username']}:{acc['password']}:{acc['email']}\n")
        
        with open(config.ACCOUNTS_JSON, 'w') as f:
            json.dump(self.accounts, f, indent=2)
    
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
