from src.spotify import SpotifyManager
from src.yt_music import YT_Music
# initialize the yt music and spotify manager classes
yt = YT_Music()
spot = SpotifyManager()

# get the liked songs from spotify
liked, _ = spot.get_liked()

# search for the equivalents yt music video
video_ids = []
for song in liked:
    # search for the song and get the video id
    search_result, _, _, vid_id = yt.search_one(song)
    video_ids.append(vid_id)
    print(f"We Chose {search_result} for equivalent: {song}")

# create a playlist and add the songs
print("Success" if yt.create_and_add("Liked", "Insane stuff", video_ids) else "rip")