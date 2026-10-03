.DEFAULT_GOAL := ayuda
.PHONY: ayuda instalar modelo ejecutar formatear revisar probar imagen

PUERTO ?= 8001
IMAGEN ?= te-tengo-service-detection-worker

ayuda: ## Lista los comandos disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

instalar: ## Instala dependencias y hooks de pre-commit
	uv sync
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

modelo: ## Descarga el modelo de MediaPipe en models/
	./scripts/descargar_modelo.sh

ejecutar: ## Levanta el servicio en local con recarga automática
	uv run uvicorn detection_worker.main:create_app --factory --reload --port $(PUERTO)

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
