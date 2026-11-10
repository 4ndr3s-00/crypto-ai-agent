.PHONY: help up down ps logs test ingest venv clean

help:
	@echo "Comandos disponibles en Crypto AI Agent Platform:"
	@echo "  make up       - Levanta el lago de datos MinIO en segundo plano"
	@echo "  make down     - Detiene los contenedores de MinIO"
	@echo "  make ps       - Muestra el estado de los contenedores"
	@echo "  make logs     - Muestra los logs de MinIO"
	@echo "  make ingest   - Ejecuta catch-up histórico desde Binance hacia MinIO"
	@echo "  make test     - Ejecuta la suite de pruebas unitarias e integración"
	@echo "  make venv     - Crea el virtualenv e instala dependencias con uv"
	@echo "  make clean    - Limpia cachés de Python y temporales"

venv:
	uv venv .venv
	uv pip install -e ".[dev]"

up:
	docker compose up -d
	@echo "MinIO listo en http://localhost:9000 (Consola: http://localhost:9001)"

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f

ingest:
	.venv/bin/python -m ingestion.catchup_historical --symbols BTCUSDT,ETHUSDT,SOLUSDT --days 7

test:
	.venv/bin/pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

api:
	.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build
