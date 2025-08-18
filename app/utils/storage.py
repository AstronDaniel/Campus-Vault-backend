from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from app.core.config import get_settings


@dataclass
class DownloadResolution:
    kind: Literal["path", "redirect"]
    value: str


class StorageBase:
    def save_resource(self, *, course_unit_id: int, digest: str, filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
        raise NotImplementedError

    def save_avatar(self, *, user_id: int, filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
        raise NotImplementedError

    def delete(self, storage_path: str) -> None:
        raise NotImplementedError

    def resolve_download(self, storage_path: str, url: str) -> DownloadResolution:
        raise NotImplementedError


class LocalStorage(StorageBase):
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)

    def save_resource(self, *, course_unit_id: int, digest: str, filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
        from pathlib import Path as _P
        ext = _P(filename or "").suffix or ""
        stored_name = f"{digest}{ext}"
        base_dir = self.base / "resources" / str(course_unit_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        dest_path = base_dir / stored_name
        with dest_path.open("wb") as f:
            f.write(content)
        storage_path = str(dest_path)
        url = f"/static/resources/{course_unit_id}/{stored_name}"
        return storage_path, url

    def save_avatar(self, *, user_id: int, filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
        from pathlib import Path as _P
        ext = (_P(filename or "").suffix or "").lower()
        if not ext:
            # default by content type
            if "jpeg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
        base_dir = self.base / "avatars"
        base_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"user_{user_id}{ext}"
        dest_path = base_dir / stored_name
        with dest_path.open("wb") as f:
            f.write(content)
        storage_path = str(dest_path)
        url = f"/static/avatars/{stored_name}"
        return storage_path, url

    def delete(self, storage_path: str) -> None:
        try:
            Path(storage_path).unlink(missing_ok=True)
        except Exception:
            pass

    def resolve_download(self, storage_path: str, url: str) -> DownloadResolution:
        # For local, return the absolute file path to stream
        return DownloadResolution(kind="path", value=storage_path)


class GoogleDriveStorage(StorageBase):
    def __init__(
        self,
        service_account_json_path: str | None,
        parent_folder_id: str | None,
        public_read: bool,
        oauth_client_id: str | None = None,
        oauth_client_secret: str | None = None,
        oauth_refresh_token: str | None = None,
    ):
        self.service_account_json_path = service_account_json_path
        self.parent_folder_id = parent_folder_id
        self.public_read = public_read
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_refresh_token = oauth_refresh_token
        self._svc: Any = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from googleapiclient.discovery import build
        except Exception as e:
            raise RuntimeError("Google Drive client libraries are not installed. Please add google-api-python-client and google-auth to requirements.") from e

        scopes = [
            "https://www.googleapis.com/auth/drive",
        ]

        creds = None
        # Prefer user OAuth if refresh token is provided
        if self.oauth_client_id and self.oauth_client_secret and self.oauth_refresh_token:
            try:
                from google.oauth2.credentials import Credentials
                creds = Credentials(
                    token=None,
                    refresh_token=self.oauth_refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.oauth_client_id,
                    client_secret=self.oauth_client_secret,
                    scopes=scopes,
                )
            except Exception as e:  # pragma: no cover
                raise RuntimeError("Failed to initialize OAuth credentials for Google Drive") from e
        elif self.service_account_json_path:
            try:
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(self.service_account_json_path, scopes=scopes)
            except Exception as e:
                raise RuntimeError("Failed to initialize Service Account credentials for Google Drive") from e
        else:
            raise RuntimeError("No Google Drive credentials configured. Provide OAuth client_id/secret/refresh_token or a service account JSON path.")

        self._svc = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _ensure_child_folder(self, name: str) -> str | None:
        if not self.parent_folder_id:
            return None
        q = (
            f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{self.parent_folder_id}' in parents and trashed = false"
        )
        res = self._svc.files().list(q=q, fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]
        metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if self.parent_folder_id:
            metadata["parents"] = [self.parent_folder_id]
        created = self._svc.files().create(body=metadata, fields="id", supportsAllDrives=True).execute()
        return created["id"]

    def _ensure_course_folder(self, course_unit_id: int) -> str | None:
        return self._ensure_child_folder(f"course_unit_{course_unit_id}")

    def _ensure_avatars_folder(self) -> str | None:
        return self._ensure_child_folder("avatars")

    def save_resource(self, *, course_unit_id: int, digest: str, filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
        from googleapiclient.http import MediaIoBaseUpload
        folder_id = self._ensure_course_folder(course_unit_id)
        stored_name = filename or digest
        metadata: dict[str, Any] = {"name": stored_name}
        if folder_id:
            metadata["parents"] = [folder_id]
        media = MediaIoBaseUpload(BytesIO(content), mimetype=content_type, resumable=False)
        created = self._svc.files().create(body=metadata, media_body=media, fields="id,webContentLink,webViewLink", supportsAllDrives=True).execute()
        file_id = created["id"]

        if self.public_read:
            try:
                self._svc.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}, supportsAllDrives=True).execute()
            except Exception:
                pass
        url = created.get("webContentLink") or created.get("webViewLink") or f"https://drive.google.com/uc?id={file_id}&export=download"
        return file_id, url

    def save_avatar(self, *, user_id: int, filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
        from googleapiclient.http import MediaIoBaseUpload
        folder_id = self._ensure_avatars_folder()
        stored_name = filename or f"user_{user_id}"
        metadata: dict[str, Any] = {"name": stored_name}
        if folder_id:
            metadata["parents"] = [folder_id]
        media = MediaIoBaseUpload(BytesIO(content), mimetype=content_type, resumable=False)
        created = self._svc.files().create(body=metadata, media_body=media, fields="id,webContentLink,webViewLink", supportsAllDrives=True).execute()
        file_id = created["id"]
        if self.public_read:
            try:
                self._svc.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}, supportsAllDrives=True).execute()
            except Exception:
                pass
        url = created.get("webContentLink") or created.get("webViewLink") or f"https://drive.google.com/uc?id={file_id}&export=download"
        return file_id, url

    def delete(self, storage_path: str) -> None:
        try:
            self._svc.files().delete(fileId=storage_path, supportsAllDrives=True).execute()
        except Exception:
            pass

    def resolve_download(self, storage_path: str, url: str) -> DownloadResolution:
        return DownloadResolution(kind="redirect", value=url)


def get_storage() -> StorageBase:
    settings = get_settings()
    provider = (settings.DRIVE_PROVIDER or "local").lower()
    if provider == "gdrive":
        return GoogleDriveStorage(
            settings.GDRIVE_SERVICE_ACCOUNT_JSON_PATH,
            settings.GDRIVE_PARENT_FOLDER_ID,
            bool(getattr(settings, "GDRIVE_PUBLIC_READ", False)),
            oauth_client_id=settings.GDRIVE_CLIENT_ID,
            oauth_client_secret=settings.GDRIVE_CLIENT_SECRET,
            oauth_refresh_token=settings.GDRIVE_REFRESH_TOKEN,
        )
    return LocalStorage(settings.FILE_STORAGE_DIR)
