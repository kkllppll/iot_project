from google.cloud import storage

def upload_to_gcs(local_path: str, bucket_name: str, object_name: str, content_type: str | None = None) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path, content_type=content_type)
    return f"gs://{bucket_name}/{object_name}"
