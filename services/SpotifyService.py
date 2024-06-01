import tekore as tk
import os
from dotenv import load_dotenv
from typing import List, Optional

from models.Song import SpotifySong

load_dotenv()

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

app_token = tk.request_client_token(CLIENT_ID, CLIENT_SECRET)

spotify = tk.Spotify(app_token)

class SpotifyService:
    @staticmethod
    def get_track(url: str) -> Optional[SpotifySong]:
        if not url:
            return

        track = spotify.track(tk.from_url(url)[1])

        return SpotifySong(
            title=track.name,
            url=track.external_urls['spotify'],
            image_url=track.album.images[0].url,
            album=track.album.name,
            artist=track.artists[0].name
        )

    @staticmethod
    def get_playlist_tracks(url: str) -> List[SpotifySong]:
        if not url:
            return []

        playlist_id = tk.from_url(url)[1]
        playlist = spotify.playlist(playlist_id)
        tracks = [playlist_track.track for playlist_track in playlist.tracks.items]

        return [
            SpotifySong(
                title=track.name,
                url=track.external_urls['spotify'],
                image_url=track.album.images[0].url,
                album=track.album.name,
                artist=track.artists[0].name
            )
            for track in tracks]

    @staticmethod
    def get_album_tracks(url: str) -> List[SpotifySong]:
        if not url:
            return []

        album_id = tk.from_url(url)[1]
        album = spotify.album(album_id)

        tracks = album.tracks.items

        return [
            SpotifySong(
                title=track.name,
                url=track.external_urls['spotify'],
                image_url=album.images[0].url,
                album=album.name,
                artist=track.artists[0].name
            )
            for track in tracks]

    @staticmethod
    def search_playlist(query: str):
        result = spotify.search(query=query, types=('playlist',), limit=1)[
            0].items[0]
        return result.name, result.external_urls['spotify']

    @staticmethod
    def search_album(query: str):
        result = spotify.search(query=query, types=('album',), limit=1)[
            0].items[0]
        return result.name, result.external_urls['spotify']