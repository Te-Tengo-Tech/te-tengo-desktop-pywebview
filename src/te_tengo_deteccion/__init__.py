"""Validated detection core of Te Tengo: pose, kinematic classification and event clips.

Pure Python with no GUI and no network: it never imports ``te_tengo_captura``, pywebview,
pystray or httpx (``tests/test_dependencias.py`` enforces it).
"""
