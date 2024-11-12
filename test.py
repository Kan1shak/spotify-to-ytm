import time
from spotify import SpotifyManager
from yt_music import YT_Music
yt = YT_Music()
spot = SpotifyManager()
based, _ = spot.get_liked()
based = based[:64]
video_ids = []
for song in based:
    search_result, _, vid_id = yt.search_one(song)
    video_ids.append(vid_id)
    print(f"chose {search_result} for equivalent: {song}")
print("Success" if yt.create_and_add("Liked", "Insane stuff", video_ids) else "rip")