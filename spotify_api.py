import tekore as tk
import random
import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

app_token = tk.request_client_token(CLIENT_ID, CLIENT_SECRET)

spotify = tk.Spotify(app_token)


def get_recommended_song(history):
    query_list = [song['title'] for song in history]
    track_ids = [spotify.search(
        query=query, types=['track'], limit=1)[0].items[0].id for query in query_list]

    recommendations = spotify.recommendations(
        track_ids=track_ids, limit=5).tracks

    filtered_recommendations = list(
        filter(lambda t: t.popularity > 15, recommendations))

    random.shuffle(filtered_recommendations)
    return {
        "title": filtered_recommendations[0].name,
        "artist": filtered_recommendations[0].artists[0].name,
    }


def get_videos_from_spotify_playlist(spotify_url: str):
    if not spotify_url:
        return
    playlist_id = tk.from_url(spotify_url)[1]
    tracks = [track.track for track in spotify.playlist(
        playlist_id).tracks.items]
    return [{
        "title": f"{track.name} - {', '.join([artist.name for artist in track.artists])}",
        "artist": track.artists[0].name,
        "url": f"{track.name} - {', '.join([artist.name for artist in track.artists])}",
        "image_url": track.album.images[0].url,
        "song_url": track.external_urls['spotify'],
        "type": "spotify"
    } for track in tracks]


def get_videos_from_spotify_album(spotify_url: str):
    if not spotify_url:
        return
    album_id = tk.from_url(spotify_url)[1]
    album = spotify.album(album_id)

    image_url = album.images[0].url

    tracks = album.tracks.items

    return [{
        "title": f"{track.name} - {', '.join([artist.name for artist in track.artists])}",
        "artist": track.artists[0].name,
        "url": f"{track.name} - {', '.join([artist.name for artist in track.artists])}",
        "image_url": image_url,
        "song_url": track.external_urls['spotify'],
        "type": "spotify"
    } for track in tracks]


def get_spotify_track(spotify_url: str):
    if not spotify_url:
        return
    try:
        track = spotify.track(tk.from_url(spotify_url)[1])
        return {
            "title": f"{track.name} - {', '.join([artist.name for artist in track.artists])}",
            "artist": track.artists[0].name,
            "image_url": track.album.images[0].url,
            "song_url": track.external_urls['spotify'],
            "type": "spotify"
        }
    except:
        return


def search_playlist(query: str):
    result = spotify.search(query=query, types=['playlist'], limit=1)[
        0].items[0]
    return result.name, result.external_urls['spotify']


def search_album(query: str):
    result = spotify.search(query=query, types=['album'], limit=1)[
        0].items[0]
    return result.name, result.external_urls['spotify']
