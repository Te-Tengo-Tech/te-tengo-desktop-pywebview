"""Uploads to Azure Blob Storage SAS URLs (te-tengo-general-api ADR 0013): the agent sends exactly the
headers the API returns, and ``x-ms-blob-type: BlockBlob`` for an Azure Blob URL when they lack it.
S3 and R2 pre-signed URLs keep their headers untouched."""

from datetime import UTC, datetime

import httpx
import pytest

from te_tengo_captura.backend.cliente import (
    ClienteBackend,
    cabeceras_de_subida,
    es_url_de_azure_blob,
)
from te_tengo_captura.backend.modelos import SubidaClip

URL_AZURE = (
    "https://tetengoproddata.blob.core.windows.net/clips/hogares/h/alertas/a/e"
    "?sv=2025-11-05&se=2026-10-31T12%3A10%3A00Z&sr=b&sp=cw&spr=https&sig=abc%3D"
)
URL_AZURITE = (
    "http://127.0.0.1:10000/devstoreaccount1/movements/movimientos/h/c/2026/10/31/12/05.parquet"
    "?sv=2025-11-05&se=2026-10-31T12%3A10%3A00Z&sr=b&sp=cw&spr=https%2Chttp&sig=abc%3D"
)
URL_R2 = (
    "https://0123456789abcdef.r2.cloudflarestorage.com/te-tengo-clips/hogares/h/alertas/a/e"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Signature=f00"
)


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        (URL_AZURE, True),
        (URL_AZURITE, True),
        ("https://cuenta.blob.core.usgovcloudapi.net/c/b?x=1", True),
        (URL_R2, False),
        ("https://te-tengo-clips.s3.us-east-1.amazonaws.com/clave?X-Amz-Signature=f00", False),
        ("https://almacen.invalid/clips/x.mp4?firma=secreta", False),
    ],
)
def test_reconoce_las_urls_de_azure_blob(url: str, esperado: bool) -> None:
    assert es_url_de_azure_blob(url) is esperado


def test_agrega_el_tipo_de_blob_a_una_url_de_azure() -> None:
    assert cabeceras_de_subida(URL_AZURE, {"Content-Type": "video/mp4"}) == {
        "Content-Type": "video/mp4",
        "x-ms-blob-type": "BlockBlob",
    }


def test_respeta_el_tipo_de_blob_que_devuelve_el_backend() -> None:
    cabeceras = {"Content-Type": "video/mp4", "X-Ms-Blob-Type": "BlockBlob"}
    assert cabeceras_de_subida(URL_AZURE, cabeceras) == cabeceras


def test_no_toca_las_cabeceras_de_s3_ni_de_r2() -> None:
    assert cabeceras_de_subida(URL_R2, {"Content-Type": "video/mp4"}) == {
        "Content-Type": "video/mp4"
    }


def _cliente_que_captura(
    puts: list[httpx.Request],
) -> ClienteBackend:
    def responder(solicitud: httpx.Request) -> httpx.Response:
        puts.append(solicitud)
        return httpx.Response(201)

    return ClienteBackend(
        "https://api.invalid",
        "credencial",
        "Sala",
        "1.0.0",
        transporte=httpx.MockTransport(responder),
    )


def test_el_clip_se_sube_a_azure_con_las_cabeceras_devueltas() -> None:
    puts: list[httpx.Request] = []
    subida = SubidaClip(
        url_subida=URL_AZURE,
        cabeceras={"Content-Type": "video/mp4", "x-ms-blob-type": "BlockBlob"},
        expira_en=datetime(2026, 10, 31, 12, 10, tzinfo=UTC),
    )

    _cliente_que_captura(puts).subir_clip(subida, b"mp4!")

    (put,) = puts
    assert put.method == "PUT"
    assert str(put.url) == URL_AZURE
    assert put.headers["Content-Type"] == "video/mp4"
    assert put.headers["x-ms-blob-type"] == "BlockBlob"
    assert "Authorization" not in put.headers
    assert put.read() == b"mp4!"


def test_un_archivo_a_azure_lleva_el_tipo_de_blob_aunque_el_backend_no_lo_envie() -> None:
    puts: list[httpx.Request] = []

    _cliente_que_captura(puts).subir_archivo(
        URL_AZURITE, {"Content-Type": "application/vnd.apache.parquet"}, b"par1", "el archivo"
    )

    (put,) = puts
    assert put.headers["Content-Type"] == "application/vnd.apache.parquet"
    assert put.headers["x-ms-blob-type"] == "BlockBlob"


def test_un_archivo_a_r2_no_lleva_cabeceras_de_azure() -> None:
    puts: list[httpx.Request] = []

    _cliente_que_captura(puts).subir_archivo(
        URL_R2, {"Content-Type": "application/gzip"}, b"gz", "el archivo ligero"
    )

    (put,) = puts
    assert put.headers["Content-Type"] == "application/gzip"
    assert "x-ms-blob-type" not in put.headers
