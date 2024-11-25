# Spotify to YouTube Music Playlist Converter

Effortlessly transfer your entire Spotify music library to YouTube Music with a powerful, user-friendly Python conversion tool.

*Sync your favorite playlists, albums, and liked songs across platforms in just a few clicks.*

**No API Keys Required!** Unlike other conversion tools, this project allows you to transfer your music library without the hassle of obtaining API keys from Spotify or YouTube Music. Simply log in through the web interface, and you're ready to go.

## Features

- Convert Spotify playlists to YouTube Music playlists
- Support for playlists, albums, artists, and liked songs
- Interactive web interface for selecting and matching songs
- Advanced fuzzy matching to find the best song equivalents
- Refine the search results by refetching individual songs
- Customizable playlist titles and descriptions
- Seamless transfer without complex API configurations
- Your music library and login data never leave your machine

## Prerequisites

- Python 3.x
- Spotify account
- YouTube Music account
- Google-Chrome or Chromium

## Installation

1. Clone the repository:

```shell
git clone https://github.com/Kan1shak/spotify-to-ytm.git
cd spotify-to-ytm
```

2. Install dependencies:

```shell
pip install -r requirements.txt
```

## Usage

1. Start the application:

```shell
python gui.py
```

2. Open your web browser and navigate to `http://localhost:5001/` or click on the link displayed in the console

3. Authorization and Setup Process:
   - Click "Start" to begin the authorization process
   - Log in to both your Spotify and Google (YouTube Music) accounts in the new browser window
   - Note: You only need to do this authentication once

4. Library Synchronization:
   - Wait 20-30 seconds for the browser to fetch your library
   - Your Spotify library will be displayed in the GUI
   - You can close the Selenium browser window after the library is displyed

5. Playlist Conversion:
   - Choose any playlist, album, artist, or `Liked Songs` to convert
   - Click `Fetch All YouTube Equivalents` to start searching for matches
   - Refetch individual songs if matches are incorrect
   - Deselect any unwanted songs
   - Click `Save Selection`

6. Create YouTube Music Playlist:
   - Enter a title (optional description)
   - Click Submit to create the playlist on YouTube Music

## FAQ

#### Q: I am getting this error: ModuleNotFoundError: No module named 'distutils'
**A:** There seems to be an issue with the latest Python version removing the distutils package. To fix this, you can run this command in your terminal:

```bash
pip install setuptools
```

After this, it should work as normal.

#### Q: I am totally new to Python, how do I get started?
**A:** First of all, make sure you have Python installed. If you don't, you can download the installer from [the official Python website](https://www.python.org/downloads/release/python-3127/). I would recommend watching [this 2-minute tutorial](https://www.youtube.com/watch?v=vXbEju8Fo3c) on how to properly install Python.

After it's installed, follow these steps:

1. Open the project folder from GitHub in your file explorer
2. Right-click anywhere inside that folder and choose the "Open in Terminal" option
3. Run these two commands in order:

```bash
pip install -r requirements.txt
python gui.py
```

**Note:** You only need to run the first command (`pip install -r requirements.txt`) once.

To run the app again in the future:
- Open the project folder
- Right-click to open in terminal
- Run the command: `python gui.py`


## Dependencies

### External Libraries
- python-fasthtml
- ytmusicapi
- thefuzz
- requests
- undetected_chromedriver
- selenium

### Standard Python Libraries
- threading
- dataclasses
- urllib
- json
- os
- time

## Contributing

Contributions are welcome! For major changes, please open an issue first to discuss proposed modifications.

## License

[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
