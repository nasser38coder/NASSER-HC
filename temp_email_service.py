import requests
import json
import time
import random
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TempEmailService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.current_email = None
        self.email_token = None
        self.inbox = []
    
    def create_email(self):
        try:
            url = "https://api.guerrillamail.com/ajax.php"
            params = {
                'f': 'get_email_address',
                'ip': '127.0.0.1',
                'agent': 'Mozilla/5.0'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if data.get('email_addr'):
                self.current_email = data['email_addr']
                self.email_token = data.get('sid_token')
                logger.info(f"✅ تم إنشاء بريد: {self.current_email}")
                return {'email': self.current_email, 'token': self.email_token}
            
            return None
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء البريد: {e}")
            return None
    
    def check_inbox(self):
        try:
            if not self.email_token:
                return []
            
            url = "https://api.guerrillamail.com/ajax.php"
            params = {
                'f': 'get_email_list',
                'sid_token': self.email_token,
                'seq': 0
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if data.get('list'):
                self.inbox = data['list']
                return self.inbox
            
            return []
            
        except Exception as e:
            return []
    
    def get_verification_code(self, max_wait=120):
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            emails = self.check_inbox()
            
            if emails:
                for email in emails:
                    body = email.get('mail_body', '')
                    subject = email.get('mail_subject', '')
                    
                    patterns = [r'\b\d{6}\b', r'code:?\s*(\d{6})', r'verification code:?\s*(\d{6})']
                    
                    for pattern in patterns:
                        match = re.search(pattern, body + subject, re.IGNORECASE)
                        if match:
                            code = match.group(1) if match.group(1) else match.group(0)
                            logger.info(f"✅ تم العثور على كود: {code}")
                            return code
            
            time.sleep(5)
        
        return None
    
    def delete_email(self):
        try:
            if self.email_token:
                url = "https://api.guerrillamail.com/ajax.php"
                params = {'f': 'forget_me', 'sid_token': self.email_token}
                self.session.get(url, params=params)
            
            self.current_email = None
            self.email_token = None
            self.inbox = []
            return True
        except:
            return False
