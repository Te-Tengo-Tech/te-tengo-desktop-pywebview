"""Clip persistence: builds the MP4 with FFmpeg and stores it encrypted in S3."""

import asyncio
import subprocess
from typing import Any, Protocol

from detection_worker.ingesta.buffer import Clip


class ErrorCodificacionError(RuntimeError):
    """FFmpeg could not build the clip's MP4."""


class AlmacenClips(Protocol):
    async def guardar(self, camara_id: str, clip: Clip) -> str:
        """Stores the clip and returns its key in the storage."""
        ...


def codificar_mp4(fotogramas: list[tuple[float, bytes]]) -> bytes:
    """Converts JPEG frames into an H.264 MP4 using FFmpeg (it must be installed)."""
    if len(fotogramas) < 2:
        raise ValueError("Se necesitan al menos dos fotogramas")
    duracion = fotogramas[-1][0] - fotogramas[0][0]
    fps = max(1.0, (len(fotogramas) - 1) / duracion) if duracion > 0 else 5.0
    comando = [
        "ffmpeg", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", f"{fps:.2f}", "-c:v", "mjpeg", "-i", "pipe:0",
        # H.264 with yuv420p requires an even width and height (a 16:9 webcam at 480p gives 853 px).
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "frag_keyframe+empty_moov",
        "-f", "mp4", "pipe:1",
    ]  # fmt: skip
    entrada = b"".join(jpeg for _, jpeg in fotogramas)
    resultado = subprocess.run(comando, input=entrada, capture_output=True, check=False)
    if resultado.returncode != 0:
        detalle = resultado.stderr.decode(errors="replace").strip().splitlines()[-1:]
        raise ErrorCodificacionError(f"FFmpeg terminó con código {resultado.returncode}: {detalle}")
    return resultado.stdout


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
