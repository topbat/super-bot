from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

import boto3
from botocore.exceptions import ClientError


class ArtifactStore(Protocol):
    async def put_file(self, key: str, path: Path, media_type: str) -> None: ...


class LocalArtifactStore:
    async def put_file(self, key: str, path: Path, media_type: str) -> None:
        return None


class S3ArtifactStore:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    async def ensure_bucket(self) -> None:
        def ensure() -> None:
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except ClientError as error:
                code = error.response.get("Error", {}).get("Code")
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                self.client.create_bucket(Bucket=self.bucket)

        await asyncio.to_thread(ensure)

    async def put_file(self, key: str, path: Path, media_type: str) -> None:
        await asyncio.to_thread(
            self.client.upload_file,
            str(path),
            self.bucket,
            key,
            ExtraArgs={"ContentType": media_type},
        )
