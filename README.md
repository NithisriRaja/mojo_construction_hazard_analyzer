# Construction Hazard Analyzer (Claude)

Upload a construction site photo; get the visible safety hazards as JSON
(`message` + `hazards` with title, description, severity, category).

Pipeline per image (Claude Opus 5.5, structured outputs): **detect → verify → PPE check**.
Prompts: `construction_hazards/prompts.py` · category guide: `construction_hazards/categories.py` ·
client output schema (hash-guarded): `construction_hazards/schema.py`.

## Setup
```
python -m venv venv
venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env      # then put your ANTHROPIC_API_KEY in .env
cd frontend && npm install && npm run build && cd ..
```

## Run
```
venv\Scripts\python -m uvicorn backend.main:app --port 8000   # UI at http://127.0.0.1:8000, API docs at /docs
venv\Scripts\python run_analysis.py                            # batch: all images in "Mojo Site image file" -> results/
venv\Scripts\python -m pytest tests -q                         # offline tests (no API cost)
venv\Scripts\python eval\evaluate.py results                   # score results against eval/ground_truth.json
```

Every Claude call is logged with tokens and estimated cost to `logs/api_usage.csv` (not committed).
