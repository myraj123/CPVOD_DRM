from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
import requests
from bs4 import BeautifulSoup
import os
import glob


def wvd_check():
    extracted_device = glob.glob(f'{os.getcwd()}/WVDs/*.wvd')[0]
    return extracted_device


wvd = wvd_check()

headers = { 'x-access-token': 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTI0MjA3NTkyLCJvcmdJZCI6NzExNTI4LCJvcmdDb2RlIjoidWphbGFmIiwib3JnTmFtZSI6IlNhcnJ0aGlJQVMiLCJuYW1lIjoiZ2hyaXRhY2hpIHRpd2FyaSIsImVtYWlsIjpudWxsLCJtb2JpbGUiOiI5MTc5ODc1Mzc1NDUiLCJ0eXBlIjoxLCJpc0RpeSI6dHJ1ZSwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiY291bnRyeUlTTyI6IjkxIiwiaXNEaXlTdWJhZG1pbiI6MCwiZmluZ2VycHJpbnRJZCI6ImU1NjExOGYyZDE3NThlYjZiNDAwNmUzZjMxZWVlNzVhIiwiaWF0IjoxNzMzNjU3MTgyLCJleHAiOjE3MzQyNjE5ODJ9._SSGS0dYJDwLjGmOQvEiPeTv8SJypWV0oJ_NgPPWGIcv_T9YmmdNH9-fZJLFMwhZ'}

url = input("url:")

response = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers=headers).json()

if response['status'] == 'ok':
    mpd = response['drmUrls']['manifestUrl']
    lic = response['drmUrls']['licenseUrl']
    response=requests.get(mpd)
    soup = BeautifulSoup(response.text, 'xml')
    uuid = soup.find('ContentProtection', attrs={'schemeIdUri': 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed'})
    pssh = uuid.find('cenc:pssh').text
    ipssh = PSSH(pssh)
    device = Device.load(wvd)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    challenge = cdm.get_license_challenge(session_id,ipssh)
    licence = requests.post(lic, data=challenge,headers=headers)
    licence.raise_for_status()
    cdm.parse_license(session_id, licence.content)

    keys = []
    for key in cdm.get_keys(session_id):
        if key.type != 'SIGNING':
            keys.append(f'{key.kid.hex}:{key.key.hex()}')

    cdm.close(session_id)
    print(f"\n{mpd}\n")
    for i in keys:
        print(f"--key {i}")

else:
    print("error, check again")
