import json
import requests
from threading import Thread


class OcrWorker:
    def __init__(self, api_url_getter, auth_getter, on_done, on_error, timeout=(3, 30)):
        self.api_url_getter = api_url_getter  # () -> url
        self.auth_getter = auth_getter        # () -> (headers, data)
        self.on_done = on_done                # (result_text, raw_json)
        self.on_error = on_error              # (exc)
        self.timeout = timeout

    def submit(self, image_path: str):
        Thread(target=self._do_request, args=(image_path,), daemon=True).start()

    def _do_request(self, image_path: str):
        try:
            api_url = self.api_url_getter()
            headers, data = self.auth_getter()
            with open(image_path, 'rb') as f:
                files = {"file": f}
                res = requests.post(api_url, files=files, data=data, headers=headers, timeout=self.timeout)
            obj = json.loads(res.text)
            text = obj["res"]["latex"]
            if callable(self.on_done):
                self.on_done(text, obj)
        except Exception as e:
            if callable(self.on_error):
                self.on_error(e) 