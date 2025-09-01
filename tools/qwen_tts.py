import os
import dashscope.audio
from pathlib import Path
import yaml

class Qwentts:
    def __init__(self, config_path: Path = Path("config.yml"),):
        
        if config_path is not None:
            with open(config_path, "r") as f:
                self.cfg: dict = yaml.safe_load(f)
        else:
            self.cfg = None
        self.api_key = self.cfg["alibaba"]["API_KEY"]
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        self.replica_id = self.cfg["Tavus"]["REP_ID"]

    def return_audio(self, text):
        response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
            model="qwen-tts",
            api_key=self.api_key,
            text=text,
            voice="Cherry",
        )
        print(response)
        return response["output"]["audio"]["url"]
    



    