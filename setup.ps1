uv venv
.venv\Scripts\activate
uv sync
Set-Location app
fastapi run main.py