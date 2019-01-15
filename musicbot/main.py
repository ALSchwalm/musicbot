import spotipy
import spotipy.util as util
from flask import Flask, request, jsonify
from slackclient import SlackClient
from pprint import pprint
import json
import os

slash_app = Flask(__name__)
spotify_token = util.prompt_for_user_token(os.environ["SPOTIFY_USERNAME"],
                                           "user-modify-playback-state streaming user-read-playback-state",
                                           client_id=os.environ["SPOTIFY_CLIENT_ID"],
                                           client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                                           redirect_uri='http://localhost/')

sp = spotipy.Spotify(auth=spotify_token)
sc = SlackClient(os.environ["SLACK_TOKEN"])

radio_uri = None
tracks = []

def tracks_after_uri(tracks, uri, include=False):
    track_uris = [t["uri"] for t in tracks]
    offset = 1 if not include else 0
    if uri in track_uris:
        return tracks[track_uris.index(uri)+offset:]
    else:
        return []

def get_current_track():
    return sp.current_playback()["item"]

def format_artist(track):
    #TODO: detect multiple artists
    artist = track["artists"][0]["name"]
    return artist

def format_tracks(tracks):
    first_songs = ["{} - {}".format(t["name"], format_artist(t))
                   for t in tracks]
    first_songs = "\n".join(first_songs)
    return first_songs

@slash_app.route("/radio", methods=["POST"])
def radio():
    radio = request.form["text"]
    if len(radio) == 0:
        return jsonify({
            "response_type": "in_channel",
            "text": "Error: missing required parameter [which radio to start]"
        })
    res = sp.search(radio, limit=1, type="playlist")
    items = res["playlists"]["items"]
    if len(items) == 0:
        return jsonify({
            "response_type": "in_channel",
            "text": "Error: no matching station found for '{}'".format(radio)
        })
    selection = items[0]
    radio_tracks = sp.user_playlist_tracks(sp.me()["id"], selection["uri"])["items"]
    first_songs = format_tracks([t["track"] for t in radio_tracks[:10]])
    return jsonify(
        {
            "text": "Would you like to start the '{}' radio?".format(selection["name"]),
            "response_type": "in_channel",
            "attachments": [
                {
                    "text": first_songs,
                    "fallback": "Cannot start radio",
                    "callback_id": "start_radio",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [
                        {
                            "name": "action",
                            "text": "Yes",
                            "type": "button",
                            "value": json.dumps({
                                "uri": selection["uri"],
                                "name": selection["name"]
                            })
                        },
                        {
                            "name": "action",
                            "text": "Cancel",
                            "style": "danger",
                            "type": "button",
                            "value": "cancel"
                        }
                    ]
                }
            ]
        })


@slash_app.route("/play", methods=["POST"])
def play():
    song = request.form["text"]
    if len(song) == 0:
        return jsonify({
            "response_type": "in_channel",
            "text": "Error: missing required parameter [which song to play]"
        })
    res = sp.search(song, limit=1)
    items = res["tracks"]["items"]
    if len(items) == 0:
        return jsonify({
            "response_type": "in_channel",
            "text": "Error: no matching songs found for '{}'".format(song)
        })
    selection = items[0]
    artist = format_artist(selection)

    return jsonify(
        {
            "text": "Would you like to play '{} - {}'?".format(selection["name"], artist),
            "response_type": "in_channel",
            "attachments": [
                {
                    "text": "",
                    "fallback": "Cannot play song",
                    "callback_id": "play_song",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [
                        {
                            "name": "action",
                            "text": "Yes",
                            "type": "button",
                            "value": json.dumps({
                                "uri": selection["uri"],
                                "name": selection["name"],
                                "artist": artist
                            })
                        },
                        {
                            "name": "action",
                            "text": "Cancel",
                            "style": "danger",
                            "type": "button",
                            "value": "cancel"
                        }
                    ]
                }
            ]
        })

@slash_app.route("/volume", methods=["POST"])
def volume():
    level = request.form["text"]
    if len(level) == 0:
        return jsonify({
            "response_type": "in_channel",
            "text": "Missing required parameter [volume level]"
        })
    elif int(level) < 0 or int(level) > 100:
        return jsonify({
            "response_type": "in_channel",
            "text": "Invalid volume value '{}'".format(level)
        })
    else:
        sp.volume(int(level))
        return jsonify({
            "response_type": "in_channel",
            "text": "Volume set to {}%".format(level)
        })

@slash_app.route("/pause", methods=["POST"])
def pause():
    sp.pause_playback()
    return jsonify({
        "response_type": "in_channel",
        "text": "Playback paused"
    })

@slash_app.route("/resume", methods=["POST"])
def resume():
    sp.start_playback()
    return jsonify({
        "response_type": "in_channel",
        "text": "Playback resumed"
    })

@slash_app.route("/skip", methods=["POST"])
def skip():
    sp.next_track()
    track = get_current_track()
    artist = format_artist(track)
    return jsonify({
        "response_type": "in_channel",
        "text": "Now playing {} - {}".format(track["name"], artist)
    })

@slash_app.route("/prev", methods=["POST"])
def prev():
    sp.previous_track()
    track = get_current_track()
    artist = format_artist(track)
    return jsonify({
        "response_type": "in_channel",
        "text": "Now playing {} - {}".format(track["name"], artist)
    })

@slash_app.route("/current", methods=["POST"])
def current():
    global tracks, radio_uri

    command = request.form["text"]
    if command == "song":
        track = get_current_track()
        name = track["name"]
        artist = format_artist(track)
        return jsonify({
            "response_type": "in_channel",
            "text": "Listening to '{} - {}'".format(name, artist)
        })
    elif command == "radio":
        track = get_current_track()
        tracks = tracks_after_uri(tracks, track["uri"], include=True)[:10]
        formatted_tracks = format_tracks(tracks)
        radio_name = sp.user_playlist(sp.me()["id"], radio_uri)["name"]
        return jsonify({
            "response_type": "in_channel",
            "text": "Listening to '{}' radio:\n{}".format(radio_name, formatted_tracks)
        })
    else:
        return jsonify({
            "response_type": "in_channel",
            "text": "Unknown parameter {}".format(command)
        })


@slash_app.route("/interactive", methods=["POST"])
def interactive():
    global tracks, radio_uri

    payload = json.loads(request.form["payload"])
    action = payload["actions"][0]["value"]
    callback_id = payload["callback_id"]

    if action == "cancel":
        return jsonify({"text":"Request cancelled"})
    elif callback_id == "play_song":
        action = json.loads(action)
        devices = sp.devices()["devices"]
        if len(devices) == 0:
            return jsonify({
                "response_type": "in_channel",
                "text": "Error: no active playback device"
            })
        device = devices[0]["id"]
        current_track = get_current_track()
        tracks = tracks_after_uri(tracks, current_track["uri"])
        track_uris = [action["uri"]] + [t["uri"] for t in tracks]
        sp.start_playback(device, uris=track_uris)

        return jsonify({
            "text": "Now playing {} - {}".format(action["name"], action["artist"])
        })
    elif callback_id == "start_radio":
        action = json.loads(action)
        devices = sp.devices()["devices"]
        if len(devices) == 0:
            return jsonify({
                "response_type": "in_channel",
                "text": "Error: no active playback device"
            })
        device = devices[0]["id"]
        tracks = [t["track"] for t in
                  sp.user_playlist_tracks(sp.me()["id"], action["uri"])["items"]]
        radio_uri = action["uri"]
        sp.start_playback(device, context_uri=action["uri"])
        return jsonify({
            "response_type": "in_channel",
            "text": "Starting {} radio".format(action["name"])
        })

slash_app.run(host="0.0.0.0", port=54322)
