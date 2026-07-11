.PHONY: test lint typecheck unit eval demo-data demo-up demo-down

test: lint typecheck unit

lint:
	ruff check queryagent tests examples

eval:
	queryagent eval --config examples/demo_ecommerce/config.sqlite.yaml --cases eval/cases.yaml

typecheck:
	mypy queryagent

unit:
	pytest -q

demo-data:
	python examples/demo_ecommerce/generate_data.py

demo-up: demo-data
	docker compose -f examples/demo_ecommerce/docker-compose.yml up -d

demo-up-ch: demo-data
	docker compose -f examples/demo_ecommerce/docker-compose.yml --profile clickhouse up -d

demo-down:
	docker compose -f examples/demo_ecommerce/docker-compose.yml --profile clickhouse down -v
