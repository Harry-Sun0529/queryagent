.PHONY: test lint typecheck unit demo-data demo-up demo-down

test: lint typecheck unit

lint:
	ruff check queryagent tests examples

typecheck:
	mypy queryagent

unit:
	pytest -q

demo-data:
	python examples/demo_ecommerce/generate_data.py

demo-up: demo-data
	docker compose -f examples/demo_ecommerce/docker-compose.yml up -d

demo-down:
	docker compose -f examples/demo_ecommerce/docker-compose.yml down -v
