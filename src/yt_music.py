import os
import json 
import requests
import ytmusicapi
import ytmusicapi.mixins.search as yt_search_mixin
import ytmusicapi.parsers.search as yt_search_parser
from thefuzz import process, fuzz
from ytmusicapi.navigation import TITLE_TEXT, nav
from src.setup import SetupManager


def _artist_names(result):
    return [artist["name"] for artist in (result.get("artists") or []) if artist.get("name")]


def _tolerate_missing_search_header():
    """YouTube Music no longer sends musicCardShelfHeaderBasicRenderer on every top result."""
    original = yt_search_parser.parse_top_result

    def parse_top_result(data, search_result_types):
        header = data.get("header") or {}
        if "musicCardShelfHeaderBasicRenderer" not in header:
            title = nav(data, TITLE_TEXT, True) or ""
            data = {
                **data,
                "header": {
                    "musicCardShelfHeaderBasicRenderer": {
                        "title": {"runs": [{"text": title}]}
                    }
                },
            }
        return original(data, search_result_types)

    yt_search_parser.parse_top_result = parse_top_result
    yt_search_mixin.parse_top_result = parse_top_result


_tolerate_missing_search_header()

class YT_Music:
    def __init__(self):
        if not os.path.exists('yt_headers.json'):
            self.session = SetupManager()
            self.cookies = self.session.yt_cookies
            with open('yt_headers.json', 'w') as f:
                json.dump(self.cookies,f)

        try:
            self.yt_sess = ytmusicapi.YTMusic("yt_headers.json")
        except Exception as e:
            print(e)
        requests.get("http://localhost:5001/update_login?status=true")
        self.filter_list = {}

    def search_one(self,q,search_from_limit=25,filter='songs'):
        search_results = self.yt_sess.search(q,limit=search_from_limit,filter=filter if filter != '' else None)
        # only search from the `topResult`, 2nd and third result
        search_dict = {}
        search_arr = []
        for result in search_results:
            res_type = result['resultType']
            if res_type == "video" or res_type == "song":
                artist_names = _artist_names(result)
                searchable_text = result['title'] + (", " + ", ".join(artist_names) if artist_names else "")
                search_dict[searchable_text] = (result['videoId'], result.get('artists') or [], result['title'])
                search_arr.append(searchable_text)
                if (len(search_arr)) >= 3: break
        if len(search_arr) == 0:
            # this is probably because the query is too long
            # so we remove the last artist in the query and try again
            if len(q.split(',')) > 1:
                q = q.split(',')
                q = ", ".join(q[:-1])
                return self.search_one(q,search_from_limit,filter=filter)
            else:
                return self.search_one(q,search_from_limit,filter='')
        choice, confidence = process.extractOne(q, search_arr)
        if confidence < 85 and filter != '':
            return self.search_one(q,search_from_limit,filter='')
        # including artists aswell now
        return (search_dict[choice][2],", ".join([artist['name'] for artist in search_dict[choice][1]]),confidence,search_dict[choice][0])

    def search_one_except(self,q,filter_str, search_from_limit=25,retries=0,filter='songs'):
        search_results = self.yt_sess.search(q,limit=search_from_limit,filter=filter if filter != '' else None)
        # remove the result that contains `filter_str`
        # only search from the `topResult`, 2nd and third result
        if not q in self.filter_list:
            self.filter_list[q] = {filter_str,}
        else:
            self.filter_list[q].add(filter_str)
        search_dict = {}
        search_arr = []
        for result in search_results:
            res_type = result['resultType']
            if res_type == "video" or res_type == "song":
                artist_names = _artist_names(result)
                current_str = result['title'] + (", " + ", ".join(artist_names) if artist_names else "")
                if current_str in self.filter_list[q]:
                    continue
                search_dict[current_str] = (result['videoId'], result.get('artists') or [], result['title'])
                search_arr.append(current_str)
                if (len(search_arr)) >= 3: break
        if len(search_arr) == 0:
            if retries > 2:
                self.filter_list[q] = set()
            return self.search_one_except(q,filter_str,search_from_limit+25,retries+1)
        choice, confidence = process.extractOne(q, search_arr)
        if confidence < 85 and filter != '':
            return self.search_one_except(q,filter_str, search_from_limit,filter='')
        # including artists aswell now
        return (search_dict[choice][2],", ".join([artist['name'] for artist in search_dict[choice][1]]),confidence,search_dict[choice][0])

    def search(self,q,limit=5,search_from_limit=25):
        search_results = self.yt_sess.search(q,limit=search_from_limit,ignore_spelling=True)
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
            # if duplicates, then prolly duplicates in user's library too, so just add it aswell
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

