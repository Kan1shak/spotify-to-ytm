import json, requests, urllib
import time
import undetected_chromedriver as uc
from os import path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

class SetupManager:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._webdriver_running = False
        return cls._instance
    
    def __init__(self):
        if not self._webdriver_running:
            d = DesiredCapabilities.CHROME
            d['goog:loggingPrefs'] = { 'performance':'ALL' } # this took way too long
            pwd = path.dirname(__file__)
            self.driver = uc.Chrome(user_data_dir= f"{pwd}{path.sep}webdriver_profile2",desired_capabilities=d)
            self._webdriver_running = True

            self._login_spotify()
            self.library = {
                'Albums' : [],
                'Artists' : [],
                'Folders' : [],
                'HasLikedSongs' : False,
                'Playlists' : [],
                'TrashItems' : 0
            }

            self.has_p_keys = False

            self.persisted_qs = {
                'Albums' : '',
                'Artists' : '',
                'LikedSongs' : '',
                'Playlists' : '',
            }
            self.yt_cookies = None

        if not self.yt_cookies:
            self._get_ytm_cookies()

    def _login_spotify(self):
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
            user_confirm = False
            requests.get("http://localhost:5001/update_login?status=false")
            while not user_confirm:
                time.sleep(1)
                res = requests.get("http://localhost:5001/check_user_confirmation")
                user_confirm = "true" in res.text
        requests.get("http://localhost:5001/update_login?status=true")
        return logged_in
    
    @staticmethod
    def _extract_auth(url,headers):
        try:
            auth = headers['authorization']
            c_token = headers['client-token']
            temp_url = urllib.parse.unquote_plus(url)
            url_j = json.loads('{"id": ' + temp_url.split('&variables=')[1].replace('&extensions=', ',"extensions":') + '}')
            persisted =  json.dumps(url_j['extensions'])
            return c_token, auth, persisted
        except KeyError:
            temp_url = urllib.parse.unquote_plus(url)
            url_j = json.loads('{"id": ' + temp_url.split('&variables=')[1].replace('&extensions=', ',"extensions":') + '}')
            persisted =  json.dumps(url_j['extensions'])
            return None, None, json.dumps(url_j['extensions'])


    def _get_library_auth(self):
        # turning on network logs
        self.driver.execute_cdp_cmd("Network.enable", {})
        # we go back to homepage
        self.driver.get('https://open.spotify.com')
        
        # trigger the library request
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Expand Your Library"]'))
            )
            library_button = self.driver.find_element(By.CSS_SELECTOR,'[aria-label="Expand Your Library"]')
        except TimeoutException:
                collapse_button = self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Collapse Your Library"]')
                collapse_button.click()
                library_button = self.driver.find_element(By.CSS_SELECTOR,'[aria-label="Expand Your Library"]')
        library_button.click()

        # get them logs
        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `libraryV3` is what we need for library
                if "operationName=libraryV3" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self._extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        return client_token, authorization, persisted_query

    def get_library(self):
        client_token, authorization, persisted_query = self._get_library_auth()

        url = 'https://api-partner.spotify.com/pathfinder/v1/query'
        limit = 50
        params = {
            'operationName': 'libraryV3',
            'variables': f'{{"filters":[],"order":null,"textFilter":"","features":["LIKED_SONGS","YOUR_EPISODES"],"limit":{limit},"offset":0,"flatten":false,"expandedFolders":[],"folderUri":null,"includeFoldersWhenFlattening":true}}',
            'extensions': persisted_query
        }

        headers = {
            'accept': 'application/json',
            'authorization': authorization,
            'client-token': client_token,
            'content-type': 'application/json;charset=UTF-8'
        }

        response = requests.get(url, headers=headers, params=params)
        print('' if response.status_code == 200 else f"Error! Code: {response.status_code}")
        
        if response.status_code == 200:
            res_j = json.loads(response.text)
            total_count = res_j['data']['me']['libraryV3']['totalCount']
            if total_count > limit:
                params = {
                    'operationName': 'libraryV3',
                    'variables': f'{{"filters":[],"order":null,"textFilter":"","features":["LIKED_SONGS","YOUR_EPISODES"],"limit":{(2 + total_count//25)*25},"offset":0,"flatten":false,"expandedFolders":[],"folderUri":null,"includeFoldersWhenFlattening":true}}',
                    'extensions': persisted_query
                }
                response = requests.get(url, headers=headers, params=params)
                res_j = json.loads(response.text)
            
            for cnt, item in enumerate(res_j['data']['me']['libraryV3']['items']):
                data = item['item']['data']

                if data['__typename'] == 'PseudoPlaylist':
                    self.library['HasLikedSongs'] = True
                    continue

                if data['__typename'] == 'NotFound':
                    self.library['TrashItems'] += 1
                    continue
                
                if data['__typename'] == 'Folder':
                    self.library['Folders'].append({
                        'name' : data['name'],
                        'uri' :  data['uri'],
                    })
                    continue

                if data['__typename'] == 'Artist':
                    self.library['Artists'].append({
                        'name' : data['profile']['name'],
                        'uri' :  data['uri'],
                        # TODO: 'thumb'
                    })
                    continue
                
                if data['__typename'] == 'Album':
                    self.library['Albums'].append({
                        'name' : data['name'],
                        'uri' :  data['uri'],
                        # TODO: 'thumb'
                    })
                    continue 

                self.library['Playlists'].append({
                    'name' : data['name'],
                    'uri' :  data['uri'],
                    # TODO: 'thumb'
                })
        return client_token, authorization

    def _get_persisted_liked(self):
        self.driver.get('https://open.spotify.com/collection/tracks')
        self.driver.implicitly_wait(3)

        logs = self.driver.get_log("performance")
        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
        except TimeoutException:
            print("woopsies")

        # again
        self.driver.get('https://open.spotify.com/collection/tracks')
        self.driver.implicitly_wait(3)

        logs = self.driver.get_log("performance")
        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
        except TimeoutException:
            print("woopsies")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `fetchLibraryTracks` is what we need for liked songs
                if "operationName=fetchLibraryTracks" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self._extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['LikedSongs'] = persisted_query
                        return True
        return False

    def _get_persisted_playlists(self):
        self.driver.get('https://open.spotify.com/playlist/3QqoFD4Y4XaLoQBYkh2cAj')
        self.driver.implicitly_wait(3)

        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
        except TimeoutException:
            print("woopsies")

        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `fetchPlaylist` is what we need for playlists
                if "operationName=fetchPlaylist" in url or "operationName=fetchPlaylistWithGatedEntityRelations" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self._extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['Playlists'] = persisted_query
                        return True
        return False

    def _get_persisted_albums(self):
        self.driver.get('https://open.spotify.com/album/19WTqbdqDMWMthZfkmxSbx')
        self.driver.implicitly_wait(3)
        
        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
        except TimeoutException:
            print("woopsies")

        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `getAlbum` is what we need for playlists
                if "operationName=getAlbum" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self._extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['Albums'] = persisted_query
                        return True
        return False        

    def _get_persisted_artists(self):
        self.driver.get('https://open.spotify.com/artist/483Rl4WY6iIJ9czOrOgymb')
        self.driver.implicitly_wait(3)

        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
        except TimeoutException:
            print("woopsies")

        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `fetchPlaylist` is what we need for playlists
                if "operationName=queryArtistOverview" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self._extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['Artists'] = persisted_query
                        return True
        return False

    def get_persist_queries(self):
        if not self.has_p_keys:
            if self.library['Albums']:
                self._get_persisted_albums()
            if self.library['Artists']:
                self._get_persisted_artists()
            if self.library['Playlists']:
                self._get_persisted_playlists()
            if self.library['HasLikedSongs']:
                self._get_persisted_liked()
            self.has_p_keys = True

    def _login_ytm(self):
        self.driver.get("https://music.youtube.com/")
         
        # check if already logged in:
        logged_in = False
        try:
            WebDriverWait(self.driver,5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.settings-button'))
            )
            logged_in = True
        except TimeoutException:
            try:
                self.driver.find_element(By.CSS_SELECTOR, '.sign-in-link')
            except:
                raise "Network Error"
        if not logged_in:
            input("Please log in to Youtube Music first!\nYou only have to do this once.\n"
                  "Press any key after you have successfully logged in.")
        return logged_in
    
    def _get_cookies(self):
        return self.driver.get_cookies()

    def _get_ytm_cookies(self):
        self._login_ytm()
        # turning on network logs again just to be sure
        self.driver.execute_cdp_cmd("Network.enable", {})
        # the driver might be already on the home page but going back to ytm just in case
        self.driver.get('https://music.youtube.com/')

        WebDriverWait(self.driver,5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.settings-button'))
        )

        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.90);")

            time.sleep(0.5)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                # `browse?` is what we need for the cookies
                if "browse?" in url:
                    self.yt_cookies = request["headers"]
                    cookies_j = self._get_cookies()
                    extracted_c = ""
                    for cookie in cookies_j:
                        c = f"{cookie['name']}={cookie['value']}; "
                        extracted_c += c
                    self.yt_cookies['cookie'] = extracted_c[:-2]
                    return True