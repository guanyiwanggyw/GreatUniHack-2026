.PHONY: dev backend frontend test eval check

dev:
	cd backend && python -m uvicorn app.main:app --reload --port 8000 & cd frontend && npm run dev -- --host 127.0.0.1

backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev -- --host 127.0.0.1

test:
	cd backend && pytest

eval:
	cd backend && python -m eval.run_eval

check:
	cd backend && pytest
	cd frontend && npm run build

