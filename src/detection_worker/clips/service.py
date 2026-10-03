"""Persistencia de clips: arma el MP4 con FFmpeg y lo guarda cifrado en S3."""

import asyncio
import subprocess
from typing import Any, Protocol

from detection_worker.ingesta.buffer import Clip


class AlmacenClips(Protocol):
    async def guardar(self, camara_id: str, clip: Clip) -> str:
        """Guarda el clip y devuelve su clave en el almacenamiento."""
        ...


def codificar_mp4(fotogramas: list[tuple[float, bytes]]) -> bytes:
    """Convierte fotogramas JPEG en un MP4 H.264 usando FFmpeg (debe estar instalado)."""
    if len(fotogramas) < 2:
        raise ValueError("Se necesitan al menos dos fotogramas")
    duracion = fotogramas[-1][0] - fotogramas[0][0]
    fps = max(1.0, (len(fotogramas) - 1) / duracion) if duracion > 0 else 5.0
    comando = [
        "ffmpeg", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", f"{fps:.2f}", "-c:v", "mjpeg", "-i", "pipe:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "frag_keyframe+empty_moov",
        "-f", "mp4", "pipe:1",
    ]  # fmt: skip
    entrada = b"".join(jpeg for _, jpeg in fotogramas)
    resultado = subprocess.run(comando, input=entrada, capture_output=True, check=True)
    return resultado.stdout


class S3AlmacenClips:
    """Almacenamiento de clips en Amazon S3 (o compatible, como SeaweedFS en local)."""

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
