import os
import json
import base64
import requests

CLIENT_ID     = '6566f74b6b414cdbbe66820466f44010'
CLIENT_SECRET = '1e24ab20909c41609d46d2721f58a0dc'
PLAYLIST_ID   = '0BREJVH369rRzD9dvU43MD'

def get_access_token():
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()
    
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(url, headers=headers, data=data)
    return response.json().get('access_token')

def fetch_playlist_tracks(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
    
    tracks = []
    print(f"Fetching tracks for {PLAYLIST_ID}...")
    
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            break
        
        data = response.json()
        for item in data.get('items', []):
            track = item.get('track')
            if track:
                tracks.append({
                    "name": track.get('name'),
                    "artist": track.get('artists', [{}])[0].get('name'),
                    "album": track.get('album', {}).get('name'),
                    "duration_ms": track.get('duration_ms')
                })
        
        url = data.get('next')
        
    return tracks

if __name__ == "__main__":
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token.")
    else:
        print("✅ Access token retrieved.")
        inventory = fetch_playlist_tracks(token)
        
        with open('spotify_inventory.json', 'w') as f:
            json.dump(inventory, f, indent=2)
            
        print(f"✅ Successfully harvested {len(inventory)} tracks to spotify_inventory.json")
