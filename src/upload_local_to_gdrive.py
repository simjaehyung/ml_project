"""
upload_local_to_gdrive.py
로컬 data/ + results/ 파일 → tokyojj33 Google Drive hotel-dss 폴더 업로드

실행:
    python src/upload_local_to_gdrive.py
"""

import os
import pickle
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT       = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".gdrive_token.pkl"

SD_LIST  = dict(supportsAllDrives=True, includeItemsFromAllDrives=True)
SD_WRITE = dict(supportsAllDrives=True)

UPLOAD_FILES = [
    ("data/train.csv",               "data"),
    ("data/test.csv",                "data"),
    ("data/train_processed.csv",     "data"),
    ("data/test_processed.csv",      "data"),
    ("results/model_final.pkl",      "results"),
    ("results/model_lgbm.pkl",       "results"),
    ("results/model_xgb.pkl",        "results"),
    ("results/sim_sweep_results.csv","results"),
]


def get_service():
    with open(TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, name: str, parent_id: str) -> str:
    q = (
        "name='" + name + "' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "'" + parent_id + "' in parents and trashed=false"
    )
    res   = service.files().list(q=q, fields="files(id,name)", **SD_LIST).execute()
    files = res.get("files", [])
    if files:
        print(f"  [존재] {name}")
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id", **SD_WRITE).execute()
    print(f"  [생성] {name}")
    return folder["id"]


def upload_file(service, local_path: Path, name: str, parent_id: str):
    q = "name='" + name + "' and '" + parent_id + "' in parents and trashed=false"
    res = service.files().list(q=q, fields="files(id)", **SD_LIST).execute()
    if res.get("files"):
        print(f"  [SKIP] {name}")
        return

    size_mb = local_path.stat().st_size / 1024 / 1024
    print(f"  [UP]   {name} ({size_mb:.1f} MB)")
    media = MediaFileUpload(str(local_path), resumable=True)
    meta  = {"name": name, "parents": [parent_id]}
    service.files().create(body=meta, media_body=media, fields="id", **SD_WRITE).execute()
    print(f"  [OK]   {name}")


def main():
    print("=" * 55)
    print("  로컬 파일 → tokyojj33 Google Drive 업로드")
    print("=" * 55)

    service = get_service()

    # 인증 계정 확인
    about = service.about().get(fields="user").execute()
    print(f"\n인증 계정: {about['user']['emailAddress']}\n")

    # Drive 루트에 hotel-dss 폴더 생성
    root_folder_id = get_or_create_folder(service, "hotel-dss", "root")

    # 하위 폴더 생성
    subfolders = {}
    for sub in set(sub for _, sub in UPLOAD_FILES):
        subfolders[sub] = get_or_create_folder(service, sub, root_folder_id)

    # 파일 업로드
    print()
    for rel_path, sub in UPLOAD_FILES:
        local = ROOT / rel_path
        if not local.exists():
            print(f"  [MISS] {rel_path}")
            continue
        upload_file(service, local, local.name, subfolders[sub])

    print(f"\n완료!")
    print(f"  https://drive.google.com/drive/folders/{root_folder_id}")
    print("=" * 55)


if __name__ == "__main__":
    main()
