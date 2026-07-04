.PHONY: install data train evaluate test api clean

install:
	pip install -r requirements.txt

data:
	python src/data/make_dataset.py
	python src/features/build_features.py

train:
	python src/models/train_model.py
	python src/models/train_classifier.py

evaluate:
	python src/models/evaluate_results.py
	python src/visualization/visualize.py

test:
	pytest tests/ -v --cov=src 

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	rm -rf __pycache__ .pytest_cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -delete

all: install data train evaluate test
