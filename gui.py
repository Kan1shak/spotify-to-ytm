from fasthtml.common import *
from spotify import SpotifyManager
from yt_music import YT_Music
import threading

app, rt = fast_app(debug=True, pico=False)

is_logged_in = False
spot = yt = None

def start_sess():
    global is_logged_in,spot,yt
    spot = SpotifyManager()
    yt = YT_Music()
    is_logged_in = True

# @app.get("/setup")
# def get():
#     global is_initialized
#     if not is_initialized:
#         return RedirectResponse("/setup")
#     else:
#         library = spot.library
#         layout = Div(
#             H1("Albums"),
#             Ul(*[Li(A(album['name'],href=f"/uri/{album['uri']}")) for album in library['Albums']]),
#             H1("Playlists"),
#             Ul(*[Li(A(pt['name'],href=f"/uri/{pt['uri']}")) for pt in library['Playlists']]),
#             H1("Artists"),
#             Ul(*[Li(A(at['name'],href=f"/uri/{at['uri']}")) for at in library['Artists']])
#         )
#         return Titled("Lets go!"), layout


@rt("/")
def get():
    return Titled("Spotify to YTM", 
        Div(
            P("Click 'Start' to initiate the process."),
            Button("Start", hx_get="/start", hx_swap="outerHTML", hx_target=".main-view", id="start-button"),
            cls="main-view"
        )
    )

@app.get("/start")
def get():
    threading.Thread(target=start_sess, daemon=True).start()
    return Titled("Login Instructions",
        P("A new browser window will open. Please login with your account."),
        Button("Done", hx_get="/done", id="done-button"),
        Div(id="login-status", hx_get="/check_login", hx_trigger="every 1s")  # Poll every 1 second
    )


if __name__ == '__main__':
    serve()