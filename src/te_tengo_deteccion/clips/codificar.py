"""MP4 encoding of an event clip with FFmpeg."""

import subprocess


class ErrorCodificacionError(RuntimeError):
    """FFmpeg could not build the clip's MP4."""


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
