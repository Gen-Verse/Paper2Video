from pathlib import Path
import requests
from typing import Optional
import time
from dashscope import ImageSynthesis
import yaml


IMAGE_SYNTHESIS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
TASK_STATUS_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/"

class Wanxiang_video():
    """Parameters when called: img_path_lst, prompt, format_check."""

    def __init__(self,
                 config_path: Path = Path("config.yml"),
                 model: Optional[str] = None
                 ):
        super().__init__(   )  # set attributes: cfg, logger, silent
        if config_path is not None:
            with open(config_path, "r") as f:
                self.cfg: dict = yaml.safe_load(f)
        else:
            self.cfg = None
        self.api_key = self.cfg["alibaba"]["API_KEY"]
        if model is None:
            self.model = self.cfg["alibaba"]["T2I_MODEL"]
        else:
            self.model = model
        self.video_size = self.cfg["alibaba"]["IMAGE_SIZE"]

        self.synthesizer = ImageSynthesis()

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
            }

    def create_task(self, prompt: str, model: str = "wanx2.1-t2v-turbo", size: str = "1280*720", n: int = 1) -> Optional[str]:
        payload = {
            "model": model,
            "input": {
            "prompt": prompt
            },
            "parameters": {
                "size": size,
                "n": n
            }
        }
        try:
            response = requests.post(IMAGE_SYNTHESIS_URL, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["output"]["task_id"]
        except requests.exceptions.RequestException as e:
            print(f"creating task failed: {e}")
            return None

    def check_task_status(self, task_id: str) -> Optional[str]:
        status_url = f"{TASK_STATUS_URL}{task_id}"
        try:
            response = requests.get(status_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if data["output"]["task_status"] == "SUCCEEDED":
                return data["output"]["video_url"] 
            elif data["output"]["task_status"]  == "FAILED":
                print(f"task is failed: {data["output"]["task_status"] }")
                return None
            else:
                print(f"task status: {data["output"]["task_status"] }")
                return None
        except requests.exceptions.RequestException as e:
            print(f"checking status failed: {e}")
            return None

    def query(self, prompt: str):
   
        print("creating task...")
        task_id = self.create_task(prompt)
        if not task_id:
            print("creating task failed, please check API key and internet")
            return

        print(f"task is created with ID: {task_id}")
        print("checking task status...")

        while True:
            result_url = self.check_task_status(task_id)
            if result_url:
                print(f"task is completed with URL: {result_url}")
                return result_url
            time.sleep(5)




    
