from fasthtml.common import *
from spotify import SpotifyManager
from yt_music import YT_Music
import threading
from dataclasses import dataclass
from urllib.parse import quote, urlencode

icon_link = Link(rel="stylesheet", href="https://www.nerdfonts.com/assets/css/webfont.css")
app, rt = fast_app(debug=True,hdrs=(picolink,icon_link))

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
    global is_initialized
    if not is_initialized:
            return P("Please wait while we load your spotify library...", 
             hx_trigger="every 1s", 
             hx_get="/is_library_built",
             hx_swap="innerHTML",hx_target=".main-view"
             )
    else:
        return RedirectResponse("/library")

@app.get("/library")
def get():
    global spot
    library = spot.library
    layout = Div(
        H3("Misc."),
        A("Liked Songs", hx_get="/uri/liked", hx_target=".main-view"),
        H3("Albums"),
        Ol(*[Li(A(al['name'],hx_get=f"/uri/{al['uri']}?title={al['name']}", hx_target=".main-view")) for al in library['Albums']]),
        H3("Playlists"),
        Ol(*[Li(A(pt['name'],hx_get=f"/uri/{pt['uri']}?title={pt['name']}", hx_target=".main-view")) for pt in library['Playlists']]),
        H3("Artists"),
        Ol(*[Li(A(at['name'],hx_get=f"/uri/{at['uri']}?title={at['name']}", hx_target=".main-view")) for at in library['Artists']])
    )
    return Titled("Spotify Library"), layout

@app.get("/initialized")
def get():
    global is_initialized
    is_initialized = True
    return {"status": "success"}

@app.get("/uri/{uri}")
def get(uri:str, title:str="Liked Songs"):
    if "playlist" in uri:
        return LibraryItem(title,uri,"playlist")
    if "album" in uri:
        return LibraryItem(title,uri,"album")
    if "artist" in uri:
        return LibraryItem(title,uri,"artist")
    else:
        return LibraryItem(title,uri,"liked")


def fetch_equivalents(uri: str):
    global spot, yt, new_playlist
    new_playlist = {"title" : "", "desc" : "", "items" : []} # they didnt...
    if "playlist" in uri:
        items, _ = spot.get_playlist(uri)
    elif "album" in uri:
        items, _ = spot.get_albums(uri)
    elif "artist" in uri:
        items, _ = spot.get_artists(uri)
    else:
        items, _ = spot.get_liked()
    for item in items:
        song_title, artist_name = item
        title, artist, _, vid_id = yt.search_one(f"{song_title} {artist_name}")
        new_playlist['items'].append([title,artist,False,vid_id])


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
                            Td(Input(type="checkbox", data_idx=NotStr(str(idx)),checked=True if len(new_playlist["items"]) >= idx+1 else False)),
                            Td(item[0]), Td(item[1]), 
                            Td(new_playlist["items"][idx][0] if len(new_playlist["items"]) >= idx+1 else "",cls="yt-title"), 
                            Td(new_playlist["items"][idx][1] if len(new_playlist["items"]) >= idx+1 else "", cls="yt-artists"),
                            Td(Button(I(cls="nf nf-md-reload"),title="Redo-Prediction",
                                      hx_get = f"/refetch_item?title={quote(item[0])}&artist={quote(item[1])}&filter_str={quote(new_playlist['items'][idx][0] + ',' + new_playlist['items'][idx][1])}&idx={idx}",
                                      hx_swap="outerHTML",
                                      hx_target="table")) if len(new_playlist["items"]) >= idx+1 else None
                        ) 
                        for idx, item in enumerate(old_playlist)
                    ],
                    id="#item-table"
                )
    if len(new_playlist["items"]) == len(old_playlist):
        selected_ids = [cnt for cnt, _ in enumerate(new_playlist["items"])]
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
            updateBtn.setAttribute('hx-get', newUrl);
            htmx.process(updateBtn);
            updateBtn.disabled = false;
            updateBtn.classList.remove('disabled');
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
    new_title, new_artist, _, _ = yt.search_one_except(f"{title} {artist}",filter_str)
    new_playlist['items'][idx] = (new_title,new_artist)
    return RedirectResponse("/new_table")

@app.get('/save_selection')
def save_selection(req):
    # Gets automatically as list
    global new_playlist
    selected_ids = req.query_params.multi_items()
    selected_ids = [int(value) for key, value in selected_ids if key == 'selectedIds']
    for idx,_ in enumerate(new_playlist["items"]):
        if idx in selected_ids:
            new_playlist["items"][idx][2] = True
    
    form = Form(Label('Playlist Title',Input(type="text", name="title")),
                Label('Description (Optional)',Input(type="textarea", name="desc")),
                Button("Submit"),
                action="/make_playlist", method="post")

    return P(f"Saved!"), form


@app.post('/make_playlist')
def make_playlist(title:str,desc:str=""):
    global new_playlist, yt
    vid_ids = [item[-1] for item in new_playlist["items"] if item[2] == True]
    if yt.create_and_add(title,desc,vid_ids):
        return P("Success!")
    else:
        return P("Some error occured.")

if __name__ == '__main__':
    serve()