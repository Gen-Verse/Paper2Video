from __future__ import annotations

import json
import os
import platform
import subprocess
import yaml
import time
from pathlib import Path
from typing import Dict, Optional

import requests
from tqdm import tqdm

# ---------- setting----------
TAVUS_API_ROOT = "https://tavusapi.com/v2/videos"
# --------------------------

class TavusClient:
    def __init__(self, config_path: Path = Path("config.yml"),):
        
        if config_path is not None:
            with open(config_path, "r") as f:
                self.cfg: dict = yaml.safe_load(f)
        else:
            self.cfg = None
        self.api_key = self.cfg["Tavus"]["API_KEY"]
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        self.replica_id = self.cfg["Tavus"]["REP_ID"]

    # ---------- 1. submit task ----------
    def create_video(self,  script: str, audio: str = "") -> str:
        """return video_id"""
        payload = {
            "replica_id": self.replica_id,
            "audio_url": audio,
            "callback_url": "",
        }
        resp = requests.post(TAVUS_API_ROOT, headers=self.headers, json=payload, timeout=30)
        resp.raise_for_status()
        data: Dict = resp.json()
        video_id = data.get("video_id") or data.get("id")
        if not video_id:
            raise KeyError("video_id is not found")
        return video_id

    # ---------- 2. query ----------
    def get_status(self, video_id: str) -> Dict:
        url = f"{TAVUS_API_ROOT}/{video_id}"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ---------- 3. until ready ----------
    def wait_until_ready(
        self,
        video_id: str,
        *,
        check_interval: int = 5,
        timeout: int = 1200,
    ) -> str:
        
        start = time.time()
        with tqdm(desc="waiting...", unit="s", leave=False) as pbar:
            while True:
                if time.time() - start > timeout:
                    raise RuntimeError("run time error")
                info = self.get_status(video_id)
                status = info.get("status", "").lower()
                if status == "ready":
                    return info["download_url"]
                if status == "failed":
                    raise RuntimeError(f"Tavus is failed: {info}")
                pbar.set_postfix(status=status)
                time.sleep(check_interval)
                pbar.update(check_interval)

    # ---------- 4. 下载 ----------
    def download(self, download_url: str, save_path: Path) -> Path:
        """with bar"""
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(save_path, "wb") as f, tqdm(
            desc="download",
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        return save_path

    --
    def generate_and_download(
        self,
        script: str,
        save_dir: Path,
        filename: Optional[str] = None,
    ) -> Path:
        video_id = self.create_video(self.replica_id, script)
        print(f"task is submitted ,video_id = {video_id}")
        download_url = self.wait_until_ready(video_id)
        #save_path = save_dir / (filename or f"{video_id}.mp4")
        #save_path.parent.mkdir(parents=True, exist_ok=True)

        return download_url#self.download(download_url, save_path)
