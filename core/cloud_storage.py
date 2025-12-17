from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlparse

from google.cloud import storage
from google.auth import default
from google.auth.transport import requests


def upload_to_gcs(
    local_path: str,
    bucket_name: str,
    object_name: str,
    content_type: str | None = None,
) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path, content_type=content_type)
    return f"gs://{bucket_name}/{object_name}"


def _parse_gs_uri(gs_uri: str) -> tuple[str, str]:
    # gs://bucket-name/path/to/object
    if not gs_uri or not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid gs uri: {gs_uri!r}")

    parsed = urlparse(gs_uri)
    bucket = parsed.netloc
    obj = parsed.path.lstrip("/")
    if not bucket or not obj:
        raise ValueError(f"Invalid gs uri: {gs_uri!r}")
    return bucket, obj


def download_from_gcs(gs_uri: str, local_path: str) -> None:
    client = storage.Client()
    bucket_name, object_name = _parse_gs_uri(gs_uri)
    blob = client.bucket(bucket_name).blob(object_name)
    blob.download_to_filename(local_path)


def make_signed_url(gs_uri: str, minutes: int = 30, method: str = "GET") -> str:
    
    bucket_name, object_name = _parse_gs_uri(gs_uri)

    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)

    # ADC creds (на Cloud Run це metadata creds)
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

    # інколи треба refresh перед підписом
    auth_req = requests.Request()
    credentials.refresh(auth_req)

    # дістаємо email service account
    service_account_email = (
        getattr(credentials, "service_account_email", None)
        or getattr(credentials, "_service_account_email", None)
    )
    if not service_account_email:
        raise RuntimeError(
            "Could not determine service account email for signing. "
            "Make sure the service is running on Cloud Run with a service account."
        )

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=minutes),
        method=method,
        credentials=credentials,
        service_account_email=service_account_email,
    )


def make_public_url(gs_uri: str) -> str:
    bucket, obj = _parse_gs_uri(gs_uri)
    return f"https://storage.googleapis.com/{bucket}/{obj}"
