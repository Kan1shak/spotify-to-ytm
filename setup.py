import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import urllib, json, requests

class SetupManager:
    def __init__(self):
        d = DesiredCapabilities.CHROME
        d['goog:loggingPrefs'] = { 'performance':'ALL' } # this took way too long
        self.driver = uc.Chrome(user_data_dir= "webdriver_profile",desired_capabilities=d) 
        self.login()

    def login(self):
        # opening the homepage
        self.driver.get('https://open.spotify.com')
        
        #checking if alraedy logged in
        logged_in = True
        try:
            # we wait for the login button
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="login-button"]'))
            )
            logged_in = False
        except TimeoutException:
            logged_in = True
        if not logged_in:
            input("Please log in first!\nPress any key after you have successfully logged in.")
        return True
    
    @staticmethod
    def extract_auth(url,headers):
        auth = headers['authorization']
        c_token = headers['client-token']
        temp_url = urllib.parse.unquote_plus(url)
        url_j = json.loads('{"id": ' + temp_url.split('&variables=')[1].replace('&extensions=', ',"extensions":') + '}')
        persisted =  json.dumps(url_j['extensions'])
        return c_token, auth, persisted


    def get_library_auth(self):
        # turning on network logs
        self.driver.execute_cdp_cmd("Network.enable", {})
        # we go back to homepage
        self.driver.get('https://open.spotify.com')
        
        # find the library button
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Expand Your Library"]'))
            )
            library_button = self.driver.find_element(By.CSS_SELECTOR,'[aria-label="Expand Your Library"]')
        except TimeoutException:
            print("woopsies!")
        library_button.click()

        # get them logs
        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `fetchPlaylist` is what we need
                if "operationName=libraryV3" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self.extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        break
            
        if client_token and authorization and persisted_query:
            print(f"{client_token=},\n{authorization=},\n{persisted_query=}")

test = SetupManager()
test.get_library_auth()

