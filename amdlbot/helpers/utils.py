
import re
import requests
import os
import base64

def get_url_info(url: str):
    VALID_URL_RE = r"/([a-z]{2})/(artist|album|playlist|song|music-video|post)/([^/]*)(?:/([^/?]*))?(?:\?i=)?([0-9a-z]*)?"
    if match := re.search(VALID_URL_RE, url):
        return ("song" if match.group(5) else match.group(2), match.group(5) or match.group(4) or match.group(3))

class FileUploader:
    def __init__(self, base_url="https://w.buzzheavier.com"):
        self.base_url = base_url

    def upload_file(self, file_path, note=""):
        file_name = os.path.basename(file_path)
        encoded_note = base64.b64encode(note.encode()).decode()
        url = f"{self.base_url}/{file_name}?note={encoded_note}"
        with open(file_path, 'rb') as file:
            response = requests.put(url, data=file)
            response.raise_for_status()
            return "https://buzzheavier.com/" + response.json()['data']['id']




