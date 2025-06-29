from flask import Flask, request, jsonify
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
import requests
from bs4 import BeautifulSoup
import os
import glob
import urllib.parse

app = Flask(__name__)

def wvd_check():
    extracted_device = glob.glob(f'{os.getcwd()}/WVDs/*.wvd')
    if not extracted_device:
        raise FileNotFoundError("No WVD files found.")
    return extracted_device[0]

# Function to generate DRM keys
def generate_drm_keys(video_url, cptoken):
    wvd = wvd_check()

    headers = {
        'x-access-token': cptoken
    }

    # URL encode the video_url
    encoded_video_url = urllib.parse.quote(video_url)
    response = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={encoded_video_url}', headers=headers)
    
    if response.status_code != 200:
        return {"error": f"Failed to fetch DRM URLs: {response.text}"}

    response_json = response.json()
    if response_json.get('status') != 'ok':
        return {"error": "Failed to fetch DRM URLs"}

    mpd = response_json['drmUrls'].get('manifestUrl')
    lic = response_json['drmUrls'].get('licenseUrl')

    if not mpd or not lic:
        return {"error": "Missing DRM URLs in response"}

    mpd_response = requests.get(mpd)
    soup = BeautifulSoup(mpd_response.text, 'xml')

    uuid = soup.find('ContentProtection', attrs={'schemeIdUri': 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed'})
    if uuid is None:
        return {"error": "ContentProtection not found in MPD"}

    pssh = uuid.find('cenc:pssh').text

    ipssh = PSSH(pssh)
    device = Device.load(wvd)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    challenge = cdm.get_license_challenge(session_id, ipssh)
    licence = requests.post(lic, data=challenge, headers=headers)
    licence.raise_for_status()

    cdm.parse_license(session_id, licence.content)

    keys = []
    for key in cdm.get_keys(session_id):
        if key.type != 'SIGNING':
            keys.append(f'{key.kid.hex}:{key.key.hex()}')

    cdm.close(session_id)

    return {"mpd_url": mpd, "keys": keys}

# API endpoint
@app.route('/api', methods=['GET'])
def api():
    video_url = request.args.get('url')
    cptoken = request.args.get('token')
    if not video_url:
        return jsonify({"error": "URL parameter is required"}), 400

    try:
        result = generate_drm_keys(video_url, cptoken)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
