import spotipy
import spotipy.util as util
import os

spotify_token = util.prompt_for_user_token(os.environ["SPOTIFY_USERNAME"],
                                           "user-modify-playback-state streaming user-read-playback-state",
                                           client_id=os.environ["SPOTIFY_CLIENT_ID"],
                                           client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                                           redirect_uri='http://localhost/')
print("export SPOTIPY_TOKEN='{}'".format(spotify_token))
