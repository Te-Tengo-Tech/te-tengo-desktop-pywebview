.DEFAULT_GOAL := ayuda
.PHONY: ayuda instalar env modelo ejecutar camara agente datasets validar formatear revisar probar imagen

PUERTO ?= 8001
IMAGEN ?= te-tengo-desktop-pywebview

ayuda: ## Lista los comandos disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

instalar: ## Instala dependencias y hooks de pre-commit
	uv sync
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

env: ## Crea .env desde .env.example con tokens locales
	uv run python scripts/crear_env.py

modelo: ## Descarga el modelo de MediaPipe en models/
	./scripts/descargar_modelo.sh

ejecutar: ## Levanta el servicio en local con recarga automática
	uv run uvicorn detection_worker.main:create_app --factory --reload --port $(PUERTO)

camara: ## Prueba el clasificador con la webcam o un video (ARGS="--video x.mp4 ...")
	uv run python scripts/probar_camara.py $(ARGS)

agente: ## Envía la webcam o un video al worker como el agente real (ARGS="...")
	uv run python scripts/agente_simulado.py $(ARGS)

datasets: ## Descarga URFD y CAUCAFall en datos/ (unos 220 MB, no se versionan)
	uv run python scripts/descargar_datasets.py

validar: ## Extrae poses y valida el clasificador con los datasets (reporte en resultados/)
	uv run python scripts/evaluar.py extraer
	uv run python scripts/evaluar.py evaluar --barrer 0.01 1.0 0.01

formatear: ## Formatea y ordena imports
	uv run ruff format .
	uv run ruff check --fix .

revisar: ## Lint, formato y tipos
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

probar: ## Pruebas con cobertura
	uv run pytest

imagen: ## Construye la imagen Docker
	docker build -t $(IMAGEN) .
