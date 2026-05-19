"""
sync_wandb_to_gdrive.py
wandb cannon 프로젝트 모델 → tokyojj33 Google Drive 자동 업로드

Drive 구조:
  (내 드라이브 루트)
  └── cannon/
      ├── mobilenet-small-simple/
      │   └── <artifact>-<version>/
      │       └── model.pt ...
      ├── effb0-aux/
      ...

실행:
    python src/sync_wandb_to_gdrive.py
"""

import os
import pickle
import sys
import tempfile
import time
from pathlib import Path

import wandb
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

sys.stdout.reconfigure(encoding="utf-8")

# ── 설정 ──────────────────────────────────────────────────────────────────────

WANDB_ENTITY = "tokyojj33-hanyang-university"

# hotel-dss 는 upload_local_to_gdrive.py 로 별도 관리
PROJECTS = {
    "cannon-mobilenet-small-simple": "mobilenet-small-simple",
    "cannon-effb0-aux":              "effb0-aux",
    "cannon-mobilenet-large-simple": "mobilenet-large-simple",
    "cannon-mobilenet-small":        "mobilenet-small",
    "cannon-effb0":                  "effb0",
    "cannon-mobilenet-large":        "mobilenet-large",
    "cannon-project":                "cannon-project",
}

SCOPES     = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = Path(__file__).parent.parent / ".gdrive_token.pkl"
CREDS_PATH = Path(__file__).parent.parent / "credentials.json"

SD_LIST  = dict(supportsAllDrives=True, includeItemsFromAllDrives=True)
SD_WRITE = dict(supportsAllDrives=True)


# ── Google Drive 인증 ──────────────────────────────────────────────────────────

def get_gdrive_service():
    creds = None

    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                print("[오류] credentials.json 없음. Google Cloud Console에서 생성 필요.")
                return None
            flow  = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("drive", "v3", credentials=creds)


# ── Drive 유틸 ─────────────────────────────────────────────────────────────────

def list_files(service, query: str, fields: str = "files(id,name)") -> list:
    results = service.files().list(q=query, fields=fields, **SD_LIST).execute()
    return results.get("files", [])


def get_or_create_folder(service, name: str, parent_id: str) -> str:
    q = (
        "name='" + name + "' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "'" + parent_id + "' in parents and trashed=false"
    )
    files = list_files(service, q)
    if files:
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id", **SD_WRITE).execute()
    print(f"    [생성] 폴더: {name}")
    return folder["id"]


def file_exists(service, name: str, parent_id: str) -> bool:
    q = "name='" + name + "' and '" + parent_id + "' in parents and trashed=false"
    return bool(list_files(service, q, fields="files(id)"))


def upload_file(service, local_path: str, name: str, parent_id: str, retries: int = 3) -> bool:
    if file_exists(service, name, parent_id):
        print(f"      [SKIP] {name}")
        return False

    for attempt in range(1, retries + 1):
        try:
            media = MediaFileUpload(local_path, resumable=True)
            meta  = {"name": name, "parents": [parent_id]}
            service.files().create(body=meta, media_body=media, fields="id", **SD_WRITE).execute()
            print(f"      [OK]   {name}")
            return True
        except HttpError as e:
            if attempt < retries:
                print(f"      [재시도 {attempt}/{retries}] {name}")
                time.sleep(2 ** attempt)
            else:
                print(f"      [실패] {name} — {e}")
                return False


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  wandb cannon -> tokyojj33 Google Drive")
    print("=" * 60)

    wandb.login()
    api = wandb.Api()

    service = get_gdrive_service()
    if service is None:
        return

    about = service.about().get(fields="user").execute()
    print(f"\n인증 계정: {about['user']['emailAddress']}")

    # tokyojj33 Drive 루트에 cannon/ 폴더 생성
    cannon_id = get_or_create_folder(service, "cannon", "root")
    print(f"cannon 폴더: https://drive.google.com/drive/folders/{cannon_id}\n")

    total_up = 0
    total_sk = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for project_name, folder_name in PROJECTS.items():
            print("-" * 50)
            print(f"[프로젝트] {project_name}")

            proj_id = get_or_create_folder(service, folder_name, cannon_id)

            try:
                runs = list(api.runs(f"{WANDB_ENTITY}/{project_name}"))
            except Exception as e:
                print(f"  접근 오류: {e}")
                continue

            finished = [r for r in runs if r.state == "finished"]
            print(f"  완료 run: {len(finished)} / 전체 {len(runs)}")

            uploaded_keys = set()
            for run in finished:
                try:
                    for artifact in run.logged_artifacts():
                        skip_keywords = ("history", "events", "run-", "job-")
                        if any(k in artifact.name for k in skip_keywords):
                            continue

                        art_key = f"{artifact.name}:{artifact.version}"
                        if art_key in uploaded_keys:
                            continue
                        uploaded_keys.add(art_key)

                        art_folder_id = get_or_create_folder(
                            service,
                            f"{artifact.name}-{artifact.version}",
                            proj_id,
                        )

                        print(f"\n  artifact: {art_key}")
                        artifact.download(root=tmpdir)

                        for fobj in artifact.files():
                            local_file = os.path.join(tmpdir, fobj.name)
                            if not os.path.exists(local_file):
                                continue
                            size_mb = os.path.getsize(local_file) / 1024 / 1024
                            print(f"      {fobj.name} ({size_mb:.1f} MB)")
                            ok = upload_file(service, local_file, fobj.name, art_folder_id)
                            if ok:
                                total_up += 1
                            else:
                                total_sk += 1

                except Exception as e:
                    print(f"  오류 ({run.name}): {e}")

    print("\n" + "=" * 60)
    print(f"  완료  업로드 {total_up}개  건너뜀 {total_sk}개")
    print(f"  https://drive.google.com/drive/folders/{cannon_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
