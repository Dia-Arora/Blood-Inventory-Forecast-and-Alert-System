.PHONY: install train-demand train-supply api test clean

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

train-demand:
	cd backend && .venv/bin/python -c "from ml.train_demand import train; train()"

train-supply:
	cd backend && .venv/bin/python -c "from ml.train_supply import train; train()"

api:
	cd backend && .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && .venv/bin/pytest tests/ -v

clean:
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

all: install train-demand train-supply test
