"""Clip persistence: builds the MP4 with FFmpeg and stores it encrypted in S3."""

import asyncio
from typing import Any, Protocol

from te_tengo_deteccion.clips.buffer import Clip
from te_tengo_deteccion.clips.codificar import codificar_mp4


class AlmacenClips(Protocol):
    async def guardar(self, camara_id: str, clip: Clip) -> str:
        """Stores the clip and returns its key in the storage."""
        ...


class S3AlmacenClips:
    """Clip storage in Amazon S3 (or a compatible service, such as SeaweedFS locally)."""

    def __init__(self, bucket: str, region: str, endpoint_url: str | None = None) -> None:
        import boto3

        self._bucket = bucket
        self._s3: Any = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    async def guardar(self, camara_id: str, clip: Clip) -> str:
        clave = f"clips/{camara_id}/{clip.evento_id}.mp4"
        video = await asyncio.to_thread(codificar_mp4, clip.fotogramas)
        await asyncio.to_thread(
            self._s3.put_object,
            Bucket=self._bucket,
            Key=clave,
            Body=video,
            ContentType="video/mp4",
            ServerSideEncryption="AES256",
        )
        return clave
