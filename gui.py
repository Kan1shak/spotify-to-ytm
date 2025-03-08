from fasthtml.common import *
from src.spotify import SpotifyManager
from src.yt_music import YT_Music
import threading
import concurrent.futures
from dataclasses import dataclass
from urllib.parse import quote, urlencode

icon_link = Link(rel="stylesheet", href="https://www.nerdfonts.com/assets/css/webfont.css")
app, rt = fast_app(debug=True,hdrs=(picolink,icon_link))

user_confirm_login_spot = is_initialized = False
is_logged_in = None
spot = yt = None
loaded_library = False
current_playlist_title = None

def start_sess():
    global is_logged_in,spot,yt
    spot = SpotifyManager()
    yt = YT_Music()
    is_logged_in = True

@app.get("/")
def get():
    return Titled("Spotify to YTM", 
        Div(
            P("Welcome! Click the 'Start' button to start the application."),
            Button("Start", hx_get="/start", hx_swap="innerHTML", hx_target=".main-view", id="start-button"),
            cls="main-view"
        )
    )

@app.get("/check_auth")
def get():
    global is_logged_in
    if is_logged_in == None:
        return P("A new browser window will open now.", Br(), "Please wait while we check your login status...",
                 hx_get="/check_auth",
                 hx_swap="outerHTML",
                 hx_trigger="every 1s")
    elif not is_logged_in:
        return (H2("Login Instructions"),
                Div(
                    P("It seems you are not logged in. Please follow the instructions below to login."),
                    Ul(
                        Li("Switch to the new chrome browser window that opened."),
                        Li("It will have the Spotify login page already opened. Login with your Spotify account in that tab."),
                        Li("After logging in to spotify, ", Strong("(Do not close the spotify tab!) "), "Open a new tab and login to your google account that you want to use for YouTube Music."),
                        Li("After logging in to both accounts, switch back to the spotify tab and click the 'Done' button below."),
                    ),
                ),
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
    return P(Strong("Thanks for logging In!"), Br(), "Please wait while we load your spotify library...", Br(),
            "This usually takes 30-40 seconds.",
             hx_trigger="every 1s", 
             hx_get="/is_library_built",
             hx_swap="innerHTML",hx_target=".main-view")

@app.get("/is_library_built")
def get():
    global is_initialized
    if not is_initialized:
            return P(Strong("Thanks for logging In!"), Br(), "Please wait while we load your spotify library...", Br(),
            "This usually takes 30-40 seconds.",
             hx_trigger="every 1s", 
             hx_get="/is_library_built",
             hx_swap="innerHTML",hx_target=".main-view")
    else:
        return RedirectResponse("/library")

@app.get("/library")
def get():
    global spot, loaded_library
    library = spot.library
    layout = Div(
        P("Thanks for waiting! Your library is ready.") if not loaded_library else None,
        P("Select any playlist to get started."),
        H3("Misc."),
        Ol(Li(A("Liked Songs", hx_get="/uri/liked", hx_target=".main-view"))),
        H3("Albums"),
        Ol(*[Li(A(al['name'],hx_get=f"/uri/{al['uri']}?title={al['name']}", hx_target=".main-view")) for al in library['Albums']]),
        H3("Playlists"),
        Ol(*[Li(A(pt['name'],hx_get=f"/uri/{pt['uri']}?title={pt['name']}", hx_target=".main-view")) for pt in library['Playlists']]),
        H3("Artists"),
        Ol(*[Li(A(at['name'],hx_get=f"/uri/{at['uri']}?title={at['name']}", hx_target=".main-view")) for at in library['Artists']])
    )
    loaded_library = True
    return Title("Spotify Library"), layout

@app.get("/initialized")
def get():
    global is_initialized
    is_initialized = True
    return {"status": "success"}

@app.get("/uri/{uri}")
def get(uri:str, title:str="Liked Songs"):
    global current_playlist_title
    current_playlist_title = title
    if "playlist" in uri:
        return LibraryItem(title,uri,"playlist")
    if "album" in uri:
        return LibraryItem(title,uri,"album")
    if "artist" in uri:
        return LibraryItem(title,uri,"artist")
    else:
        return LibraryItem(title,uri,"liked")

def fetch_song(item):
    song_title, artist_name = item
    title, artist, _, vid_id = yt.search_one(f"{song_title} ,{artist_name}")
    return [title, artist, True, vid_id]


def fetch_equivalents(uri: str):
    global spot, yt, new_playlist
    if "playlist" in uri:
        items, _ = spot.get_playlist(uri)
    elif "album" in uri:
        items, _ = spot.get_albums(uri)
    elif "artist" in uri:
        items, _ = spot.get_artists(uri)
    else:
        items, _ = spot.get_liked()
    
    new_playlist = {"title": "", "desc": "", "items": []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_song, items)
        new_playlist['items'].extend(results)


@dataclass
class LibraryItem:
    title: str
    uri: str
    uri_type:str

    def __ft__(self):
        global spot, old_playlist
        if self.uri_type == "playlist":
            items, _ = spot.get_playlist(self.uri)
        elif self.uri_type == "album":
            items, _ = spot.get_albums(self.uri)
        elif self.uri_type == "artist":
            items , _ = spot.get_artists(self.uri)
        else:
            items, _ = spot.get_liked()

        old_playlist = items
        layout = Div(
            Titled(f"{self.title} | {self.uri_type.title()}"),
            P("Click on the button at the end of the page to start the converting process."),
            P("Once you click it, wait until all the songs have been fetched. After that:"),
            Ul(
                Li("Deselct any songs you don't want to be added to the new playlist."),
                Li("Redo the prediction for any incorrect songs by clicking the refresh button."),
                Li("Once you are satisfied, click the 'Save Selection' button to save your selection."),
            ),
            # creating just a table for now, easy to debug
            Table(
                Tr(Th("Original Title"), Th("Original Artists"), Th("New Title"), Th("New Artists")),
                *[Tr(Td(item[0]), Td(item[1]), Td("",cls="yt-title"), Td("", cls="yt-artists")) for item in items],
                id="#item-table"
            ),
            Button("Go Back", hx_get="/library", hx_target=".main-view"),
            Button("Fetch All YouTube Equivalents", hx_get=f"/start_fetch_equi?uri={self.uri}", hx_swap="outerHTML"),
            Div(cls="yt-info-box")
        )
        return layout

@app.get("/new_table")
def get():
    global new_playlist, old_playlist
    table = Table(
                    Tr(Th("Selected"),Th("Original Title"), Th("Original Artists"), Th("New Title"), Th("New Artists")),
                    *[
                        Tr(
                            Td(Input(type="checkbox", data_idx=NotStr(str(idx)),checked=new_playlist["items"][idx][2] if len(new_playlist["items"]) >= idx+1 else False)),
                            Td(item[0]), Td(item[1]), 
                            Td(new_playlist["items"][idx][0] if len(new_playlist["items"]) >= idx+1 else "",cls="yt-title"), 
                            Td(new_playlist["items"][idx][1] if len(new_playlist["items"]) >= idx+1 else "", cls="yt-artists"),
                            Td(Button(I(cls="nf nf-md-reload"),title="Redo-Prediction",
                                      hx_get = f"/refetch_item?title={quote(item[0])}&artist={quote(item[1])}&filter_str={quote(new_playlist['items'][idx][0] + ', ' + new_playlist['items'][idx][1])}&idx={idx}",
                                      hx_swap="outerHTML",
                                      hx_target="table")) if len(new_playlist["items"]) >= idx+1 else None
                        ) 
                        for idx, item in enumerate(old_playlist)
                    ],
                    id="#item-table"
                )
    if len(new_playlist["items"]) == len(old_playlist):
        selected_ids = [idx for idx, item in enumerate(new_playlist["items"]) if item[2] == True]
        params = {'selectedIds': selected_ids}
        hx_get = f"/save_selection?{urlencode(params, doseq=True)}"
        script = """document.addEventListener('change', function(e) {
    if (e.target.type === 'checkbox') {
        const updateBtn = document.getElementById('update-btn');
        const checkedBoxes = document.querySelectorAll('input[type="checkbox"]:checked');
        const selectedIndices = Array.from(checkedBoxes).map(box => box.dataset.idx);
        if (selectedIndices.length > 0) {
            const params = new URLSearchParams();
            selectedIndices.forEach(idx => {
                params.append('selectedIds', idx);
            });
            const baseUrl = '/save_selection'; // replace with your base URL
            const newUrl = `${baseUrl}?${params.toString()}`;
            const bgUrl =  `/bg_save?${params.toString()}`;
            updateBtn.setAttribute('hx-get', newUrl);
            htmx.process(updateBtn);
            updateBtn.disabled = false;
            updateBtn.classList.remove('disabled');
            htmx.ajax('GET', bgUrl, { swap: 'none',target: 'body'});
        } else {
            updateBtn.disabled = true;
            updateBtn.classList.add('disabled');
            updateBtn.removeAttribute('hx-get');
            htmx.process(updateBtn);
        }
    }
});"""
        return table,Button("Save Selection",id ="update-btn",hx_swap_oob="true",
                            hx_get=hx_get,hx_target=".yt-info-box"),Script(script)
    else: return table,Button("Fetching...",id ="update-btn",hx_swap_oob="true", disabled=True,
                            hx_get="/new_table", 
                            hx_trigger="every 0.5s",
                            hx_swap="outerHTML",
                            hx_target="table")

@app.get("/start_fetch_equi")
def get(uri:str):
    threading.Thread(target=fetch_equivalents, daemon=True,kwargs={'uri':uri}).start()
    return Button("Fetching...",
                    hx_get="/new_table", 
                    hx_trigger="every 0.5s",
                    hx_swap="outerHTML",
                    hx_target="table",
                    id = "update-btn")

@app.get("/refetch_item")
def get(title:str,artist:str,filter_str:str,idx:int):
    global yt,new_playlist
    new_title, new_artist, _, video_id = yt.search_one_except(f"{title} {artist}",filter_str)
    new_playlist['items'][idx][0] = new_title
    new_playlist['items'][idx][1] = new_artist
    new_playlist['items'][idx][-1] = video_id
    return RedirectResponse("/new_table")

@app.get('/bg_save')
def save_selection(req):
    global new_playlist
    selected_ids = req.query_params.multi_items()
    selected_ids = [int(value) for key, value in selected_ids if key == 'selectedIds']
    for idx,_ in enumerate(new_playlist["items"]):
        if idx not in selected_ids:
            new_playlist["items"][idx][2] = False
        else:
            new_playlist["items"][idx][2] = True

@app.get('/save_selection')
def save_selection(req):
    # Gets automatically as list
    global new_playlist
    selected_ids = req.query_params.multi_items()
    selected_ids = [int(value) for key, value in selected_ids if key == 'selectedIds']
    for idx,_ in enumerate(new_playlist["items"]):
        if idx not in selected_ids:
            new_playlist["items"][idx][2] = False
        else:
            new_playlist["items"][idx][2] = True
    form = Form(Label('Playlist Title',Input(type="text", name="title", value=current_playlist_title)),
                Label('Description (Optional)',Input(type="textarea", name="desc")),
                Button("Submit"),
                action="/make_playlist", method="post")

    return P("Your selection has been saved. If required change the title and description of the playlist and click submit."), form


@app.post('/make_playlist')
def make_playlist(title:str,desc:str=""):
    global new_playlist, yt
    vid_ids = [item[-1] for item in new_playlist["items"] if item[2] == True]
    if yt.create_and_add(title,desc,vid_ids):
        return (H2("Successfully Created Your Playlist!"),
                P("You can now view your new playlist on YouTube Music."),
                P("You will be now redirected to the home page in 10 seconds."),
                Script("setTimeout(() => {window.location.href = '/';}, 10000)"))
    else:
        return P("Some error occured.")

if __name__ == '__main__':
    serve()