import os, json
import ytmusicapi
from thefuzz import process, fuzz
from setup import SetupManager

class YT_Music:
    def __init__(self):
        if not os.path.exists('yt_headers.json'):
            self.session = SetupManager()
            self.cookies = self.session.yt_cookies
            with open('yt_headers.json', 'w') as f:
                json.dump(self.cookies,f)

        self.yt_sess = ytmusicapi.YTMusic("yt_headers.json")
    
    # fuzzy still needs some work, aint working that well as is

    def search_one(self,q,search_from_limit=25):
        search_results = self.yt_sess.search(q,limit=search_from_limit)
        search_dict = {}
        search_arr = []
        for result in search_results:
            res_type = result['resultType']
            if  res_type == "video" or res_type == "song":
                search_dict[result['title']] = (result['videoId'], result['artists'])
                search_arr.append(result['title'])
        
        choice, confidence = process.extractOne(q, search_arr, scorer=fuzz.token_sort_ratio)
        # including artists aswell now
        return (choice,",".join([artist['name'] for artist in search_dict[choice][1]]),confidence,search_dict[choice][0])

    def search(self,q,limit=5,search_from_limit=25):
        search_results = self.yt_sess.search(q,limit=search_from_limit)
        search_dict = {}
        search_arr = []
        for result in search_results:
            cat = result['category']
            if  cat == "Top result" or cat == "Songs" or cat == "Videos":
                search_dict[result['title']] = result['videoId']
                search_arr.append(result['title'])
        choices = process.extract(q,search_arr,limit=limit,scorer=fuzz.token_sort_ratio)
        choices = [tuple(list(choice) + [search_dict[choice[0]]]) for choice in choices]
        return choices
        
    def add_multiple_to_playlist(self,playlist_id,songs):
        if isinstance(songs[-1],tuple):
            songs = [songs[-1] for song in songs]
        status = self.yt_sess.add_playlist_items(playlist_id,songs)
        if status['status'] == 'STATUS_FAILED':
            # either there are duplicates in the list or the api limit reached
            # TODO: show user the duplicate song here and ask them their choice
            status = self.yt_sess.add_playlist_items(playlist_id,songs,duplicates=True)
            if status['status'] == 'STATUS_FAILED':
                return False
        return True
    
    def create_playlist(self,name,desc):
        pl_id =  self.yt_sess.create_playlist(name, desc)
        if pl_id: return pl_id

    def create_and_add(self,playlist_name,desc,songs):
        playlist_id = self.create_playlist(playlist_name,desc)
        return self.add_multiple_to_playlist(playlist_id,songs)

