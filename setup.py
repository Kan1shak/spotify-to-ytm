import time
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
        self.driver = uc.Chrome(user_data_dir= "webdriver_profile2",desired_capabilities=d) 
        self.login()
        self.library = {
            'Albums' : [],
            'Artists' : [],
            'HasLikedSongs' : False,
            'Playlists' : [],
            'TrashItems' : 0
            # maybe `folders` later?
        }

        self.persisted_qs = {
            'Albums' : '',
            'Artists' : '',
            'LikedSongs' : '',
            'Playlists' : '',
        }

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
                    client_token, authorization, persisted_query = self.extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        return client_token, authorization, persisted_query
                    
        if client_token and authorization and persisted_query:
            print(f"{client_token=},\n{authorization=},\n{persisted_query=}")

    def get_library(self):
        client_token, authorization, persisted_query = self.get_library_auth()

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
        print('Success!' if response.status_code == 200 else f"Error! Code: {response.status_code}")
        
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

                if data['__typename'] == 'NotFound':
                    self.library['TrashItems'] += 1
                    continue
                
                if data['__typename'] == 'Artist':
                    print(f"{1+cnt}. {data['profile']['name']} ({data['__typename']})")
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

                print(f"{1+cnt}. {data['name']} ({data['__typename']})")
                self.library['Playlists'].append({
                    'name' : data['name'],
                    'uri' :  data['uri'],
                    # TODO: 'thumb'
                })
    
    def _get_persisted_liked(self):
        self.driver.get('https://open.spotify.com/collection/tracks')
        self.driver.implicitly_wait(3)

        logs = self.driver.get_log("performance")
        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
            print("found it!")
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
            print("found it!")
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
                    client_token, authorization, persisted_query = self.extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['LikedSongs'] = persisted_query
                        print(f"Liked_{persisted_query= :>10}")
                        return True
        input("rip likes? whty???")
        return False

    def _get_persisted_playlists(self):
        self.driver.get('https://open.spotify.com/playlist/37i9dQZF1DWWylYLMvjuRG')
        self.driver.implicitly_wait(3)

        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
            print("found it!")
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
                    client_token, authorization, persisted_query = self.extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['Playlists'] = persisted_query
                        print(f"Playlists_{persisted_query= :>10}")
                        return True
        return False

    def _get_persisted_albums(self):
        self.driver.get('https://open.spotify.com/album/19WTqbdqDMWMthZfkmxSbx')
        self.driver.implicitly_wait(3)
        
        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
            print("found it!")
        except TimeoutException:
            print("woopsies")

        logs = self.driver.get_log("performance")

        for log in logs:
            message = json.loads(log["message"])["message"]
            if message["method"] == "Network.requestWillBeSent":
                request = message["params"]["request"]
                url = request["url"]
                
                # `fetchPlaylist` is what we need for playlists
                if "operationName=getAlbum" in url:
                    headers = request["headers"]
                    client_token, authorization, persisted_query = self.extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['Albums'] = persisted_query
                        print(f"Albums_{persisted_query= :>10}")
                        return True
        return False        

    def _get_persisted_artists(self):
        self.driver.get('https://open.spotify.com/artist/483Rl4WY6iIJ9czOrOgymb')
        self.driver.implicitly_wait(3)

        try:
            WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="play-button"]'))
            )
            print("found it!")
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
                    client_token, authorization, persisted_query = self.extract_auth(url,headers)
                    if client_token and authorization and persisted_query:
                        self.persisted_qs['Artists'] = persisted_query
                        print(f"Artists_{persisted_query= :>10}")
                        return True
        return False

    def get_persist_queries(self):
        if self.library['Albums']:
            self._get_persisted_albums()
        if self.library['Artists']:
            self._get_persisted_artists()
        if self.library['Playlists']:
            self._get_persisted_playlists()
        if self.library['HasLikedSongs']:
            self._get_persisted_liked()
         