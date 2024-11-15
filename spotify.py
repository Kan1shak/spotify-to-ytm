import requests, json, os, time
from setup import SetupManager

class SpotifyManager:
    def __init__(self):
        if os.path.exists('spotify_auth.json'):
            with open('spotify_auth.json', 'r') as f:
                saved_data = json.load(f)
            if time.time() > saved_data['expires']:
                os.remove('spotify_auth.json')
            else:
                self.authorization = saved_data['authorization']
                self.client_token = saved_data['client_token']
                self.persisted_queries = saved_data['persisted_queries']
                self.library = saved_data['library']
                self.session = None
                requests.get("http://localhost:5001/update_login?status=true")

        if not os.path.exists('spotify_auth.json'):
            self.session = SetupManager()
            self.client_token, self.authorization = self.session.get_library()
            self.library = self.session.library
            if not self.session.has_p_keys:
                self.session.get_persist_queries()
            self.persisted_queries = self.session.persisted_qs
            with open('spotify_auth.json', 'w') as f:
                json.dump({
                   'client_token'       :   self.client_token,
                   'authorization'      :   self.authorization,
                   'library'            :   self.library,
                   'persisted_queries'  :   self.persisted_queries,
                   'expires'            :   time.time() + 60*60 # 1 hour expiry for now
                },f)
        
        requests.get("http://localhost:5001/initialized")

    def _get_res_from_spot(self, operation, persisted, uri=None,limit=50):
        endpoint = 'https://api-partner.spotify.com/pathfinder/v1/query'
        params = {
            'operationName': f'{operation}',
            'variables': f'{{{uri + "," if uri else ""}"offset":0,"limit":{limit}}}',
            'extensions': persisted
        }
        headers = {
            'accept': 'application/json',
            'authorization': self.authorization,
            'client-token': self.client_token,
            'content-type': 'application/json;charset=UTF-8'
        }
        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code == 200:
            res_j = json.loads(response.text)
            return res_j, True
        return response.status_code, False
    
    @staticmethod
    def _extract_from_trackv2(tracks):
        extracted = []
        for track in tracks:
            track = track['track'] if 'track' in track else track['data']
            artists = "".join([","+artist['profile']['name'] for artist in track['artists']['items']]) if 'artists' in track else ""
            extracted.append(track['name']+artists)
        return extracted

    def get_playlist(self,uri,limit=50):
        res_j, success = self._get_res_from_spot('fetchPlaylist',self.persisted_queries['Playlists'], '"uri":"'+uri+'"',limit)
        if success:
            tracks = res_j['data']['playlistV2']['content']
            total_count = int(tracks['totalCount'])
            if total_count > limit:
                return self.get_playlist(uri,total_count + 50 - (total_count % 50))
            fixed_tracks = [track['itemV2'] for track in tracks['items']]
            extracted = self._extract_from_trackv2(fixed_tracks)
            return extracted, success
        return res_j, success
    
    def get_artists(self,uri):
        # currently only choosing the topTracks
        res_j, success = self._get_res_from_spot('queryArtistOverview',self.persisted_queries['Artists'], '"uri":"'+uri+'","locale":""')
        if success:
            top_tracks = res_j['data']['artistUnion']['discography']['topTracks']
            extracted = self._extract_from_trackv2(top_tracks['items'])
            return extracted, success
        return res_j, success

    def get_albums(self,uri,limit=50):
        res_j, success = self._get_res_from_spot('getAlbum',self.persisted_queries['Albums'], '"uri":"'+uri+'","locale":""',limit)
        if success:
            tracks = res_j['data']['albumUnion']['tracksV2']
            total_count = int(tracks['totalCount'])
            if total_count > limit:
                return self.get_albums(uri,total_count + 50 - (total_count % 50))
            extracted = self._extract_from_trackv2(tracks['items'])
            return extracted, success
        return res_j, success
    
    def get_liked(self,limit=50):
        res_j, success =  self._get_res_from_spot('fetchLibraryTracks',self.persisted_queries['LikedSongs'],limit=limit)
        if success:
            tracks = res_j['data']['me']['library']['tracks']
            total_count = int(tracks['totalCount'])
            if total_count > limit:
                return self.get_liked(total_count + 50 - (total_count % 50))
            fixed_tracks = [track['track'] for track in tracks['items']]
            extracted = self._extract_from_trackv2(fixed_tracks)
            return extracted, success
        return res_j, success