import spotipy
import spotipy.util as util
from spotipy import oauth2
import os

sp_oauth = oauth2.SpotifyOAuth(client_id=os.environ["SPOTIFY_CLIENT_ID"],
                               client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                               redirect_uri='http://localhost/',
                               scope="user-modify-playback-state streaming user-read-playback-state")
token_info = sp_oauth.get_cached_token()
if not token_info:
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    response = input('Paste the above link into your browser, then paste the redirect url here: ')
    code = sp_oauth.parse_response_code(response)
    token_info = sp_oauth.get_access_token(code)

print("export SPOTIFY_ACCESS_TOKEN={}".format(token_info["access_token"]))
print("export SPOTIFY_REFRESH_TOKEN={}".format(token_info["refresh_token"]))
