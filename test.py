import random
from spotify import SpotifyManager
from yt_music import YT_Music
spot = SpotifyManager()
yt = YT_Music()
random_playlist = random.choice(spot.library['Playlists'])
yt_playlist = yt.yt_sess.create_playlist(random_playlist['name'], "test")
spot_songs, _ = spot.get_playlist(random_playlist['uri'])
video_ids = []
for song in spot_songs:
    search_results = yt.search(song)
    video_ids.append(search_results[0]['videoId'])
    print(f"chose {search_results[0]['title']} for equivalent: {song}]")
    
print(yt.yt_sess.add_playlist_items(yt_playlist, video_ids,duplicates=True)['status'])