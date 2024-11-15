from fasthtml.common import *
from spotify import SpotifyManager
from yt_music import YT_Music
import threading

app, rt = fast_app(debug=True, pico=False)

user_confirm_login_spot = is_initialized = False
is_logged_in = None
spot = yt = None

def start_sess():
    global is_logged_in,spot,yt
    spot = SpotifyManager()
    yt = YT_Music()
    is_logged_in = True

@app.get("/")
def get():
    return Titled("Spotify to YTM", 
        Div(
            P("Click 'Start' to initiate the process."),
            Button("Start", hx_get="/start", hx_swap="innerHTML", hx_target=".main-view", id="start-button"),
            cls="main-view"
        )
    )

@app.get("/check_auth")
def get():
    global is_logged_in
    if is_logged_in == None:
        return P("Please wait while we check if you are logged in...",
                 hx_get="/check_auth",
                 hx_swap="outerHTML",
                 hx_trigger="every 1s")
    elif not is_logged_in:
        return (H2("Login Instructions"),
                P("A new browser window will open. Please login with both your spotify and youtube music accounts.",
                  "After logging in, please click on the button below"),
                Button("Done", hx_get="/user_confirm_login", id="done-button",hx_swap="innerHTML",hx_target=".main-view"))
    else:
        return RedirectResponse("/user_confirm_login")


@app.get("/update_login")
def get(status:bool=None):
    global is_logged_in
    is_logged_in = status

@app.get("/start")
def get():
    threading.Thread(target=start_sess, daemon=True).start()
    return RedirectResponse("/check_auth")

@app.get("/check_user_confirmation")
def get():
    global user_confirm_login_spot
    return {"confirmed": user_confirm_login_spot}

@app.get("/user_confirm_login")
def get():
    global user_confirm_login_spot
    user_confirm_login_spot = True
    return P("Please wait while we load your spotify library...", 
             hx_trigger="every 1s", 
             hx_get="/is_library_built",
             hx_swap="innerHTML",hx_target=".main-view")

@app.get("/is_library_built")
def get():
    global spot,is_initialized
    if not is_initialized:
            return P("Please wait while we load your spotify library...", 
             hx_trigger="every 1s", 
             hx_get="/is_library_built",
             hx_swap="innerHTML",hx_target=".main-view"
             )
    else:
        library = spot.library
        layout = Div(
            H3("Misc."),
            A("Liked Songs", hx_get="/uri/liked", hx_target=".main-view"),
            H3("Albums"),
            Ol(*[Li(A(al['name'],hx_get=f"/uri/{al['uri']}", hx_target=".main-view")) for al in library['Albums']]),
            H3("Playlists"),
            Ol(*[Li(A(pt['name'],hx_get=f"/uri/{pt['uri']}", hx_target=".main-view")) for pt in library['Playlists']]),
            H3("Artists"),
            Ol(*[Li(A(at['name'],hx_get=f"/uri/{at['uri']}", hx_target=".main-view")) for at in library['Artists']])
        )
        return Titled("Spotify Library"), layout

@app.get("/initialized")
def get():
    global is_initialized
    is_initialized = True
    return {"status": "success"}

if __name__ == '__main__':
    serve()