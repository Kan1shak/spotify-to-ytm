import time
from spotify import SpotifyManager
from yt_music import YT_Music
spot = SpotifyManager()
yt = YT_Music()
yt.search("Kabes ghosts")
# print(spot.library)

# print(spot.get_artists('spotify:artist:483Rl4WY6iIJ9czOrOgymb'))
# print(spot.get_albums('spotify:album:19WTqbdqDMWMthZfkmxSbx'))
# print(spot.get_playlist('spotify:playlist:40oOh5dfVHTxsz7xzd3OD5'))

# songs, _  = spot.get_liked()

# len(songs)

# all_music = set()
# for playlist in spot.library['Playlists'][1:]:
#     time.sleep(0.5)
#     print(f"Done {playlist['name']}")
#     songs, _ = spot.get_playlist(playlist['uri'])
#     for song in songs:
#         all_music.add(song)

# print(len(all_music))