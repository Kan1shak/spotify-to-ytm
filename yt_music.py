import os, json
import ytmusicapi
from setup import SetupManager

class YT_Music:
    def __init__(self):
        if not os.path.exists('yt_headers.json'):
            self.session = SetupManager()
            self.cookies = self.session.yt_cookies
            with open('yt_headers.json', 'w') as f:
                json.dump(self.cookies,f)

        self.yt_sess = ytmusicapi.YTMusic("yt_headers.json")
    
    def search(self,q):
        return self.yt_sess.search(q,limit=10)

        