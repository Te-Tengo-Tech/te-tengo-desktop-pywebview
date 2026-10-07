.DEFAULT_GOAL := ayuda
.PHONY: ayuda instalar modelo camara datasets validar formatear revisar probar

ayuda: ## Lists the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

instalar: ## Installs dependencies and pre-commit hooks
	uv sync
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

modelo: ## Downloads the MediaPipe model into models/
	./scripts/descargar_modelo.sh

camara: ## Tests the classifier with the webcam or a video (ARGS="--video x.mp4 ...")
	uv run python scripts/probar_camara.py $(ARGS)

datasets: ## Downloads URFD and CAUCAFall into datos/ (about 220 MB, not versioned)
	uv run python scripts/descargar_datasets.py

validar: ## Extracts poses and validates the classifier with the datasets (report in resultados/)
	uv run python scripts/evaluar.py extraer
	uv run python scripts/evaluar.py evaluar --barrer 0.01 1.0 0.01

formatear: ## Formats code and sorts imports
	uv run ruff format .
	uv run ruff check --fix .

revisar: ## Lint, formatting and types
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

probar: ## Tests with coverage
	uv run pytest
