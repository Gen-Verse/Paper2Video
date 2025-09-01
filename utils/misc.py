from pathlib import Path
from base64 import b64encode
from typing import Union
import base64
import os
import requests
from tqdm import tqdm

def encode_img(img_path: Union[Path, str]) -> str:
    """Encodes image to base64."""    
    with open(img_path, "rb") as img_file:
        b64code = b64encode(img_file.read()).decode()
        return f"data:image/jpeg;base64,{b64code}"

def encode_pdf(pdf_path: Union[Path, str]) -> str:
    with open(pdf_path, "rb") as doc_file:
        doc_data = base64.standard_b64encode(doc_file.read()).decode("utf-8")
        return doc_data


def sorted_glob(dir_path: Path, pattern: str = "*") -> list[Path]:
    assert dir_path.is_dir(), f"{dir_path} is not a directory."
    return sorted(list(dir_path.glob(pattern)))


def sorted_rglob(dir_path: Path, pattern: str = "*") -> list[Path]:
    assert dir_path.is_dir(), f"{dir_path} is not a directory."
    return sorted(list(dir_path.rglob(pattern)))


def download_file(url: str, local_path: Path, chunk_size: int = 8192) -> Path:
    # if os.path.exists(local_path):
    #     return local_path
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)  # 自动创建目录

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(local_path, "wb") as f, tqdm(
            desc=local_path.name,
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
    return local_path


def name_to_pdb_ids(name: str) -> list[str]:
    url = "https://search.rcsb.org/rcsbsearch/v2/query"
    payload = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {"value": name}
        },
        "return_type": "entry"
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return [hit["identifier"] for hit in r.json().get("result_set", [])]
    except Exception as e:
        print(f"[WARN] 检索失败：{e}")
        return []

def download_pdb(pdb_id: str, dest_file: str) -> str | bool:
    if os.path.exists(dest_file):
        print(f"[SKIP] {dest_file} already exists")
        return dest_file

    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    try:
        with requests.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(dest_file, "wb") as f, tqdm(
                desc=f"{pdb_id}.pdb",
                total=total,
                unit="B",
                unit_scale=True,
                disable=total == 0,
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        return dest_file
    except Exception as e:
        print(f"[ERROR] Failed to download {pdb_id}: {e}")
        return False



# 示例
if __name__ == "__main__":
    name = "Q192T"
    ids = name_to_pdb_ids(name)
    print("PDB ID(s):", ids)