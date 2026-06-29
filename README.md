# HR AI Recruitment Portal

A FastAPI-based web application that generates professional Job Descriptions (JDs) based on client demands using the Groq Cloud API.

## Restructured Layout

- `app/`: Contains the application source code.
  - `main.py`: The FastAPI application entrypoint.
  - `static/`: Static assets (HTML and CSS) for the web portal.
- `pyproject.toml`: Project metadata and dependencies.
- `.venv/`: Python virtual environment managed by `uv`.

## Installation and Setup

1. **Activate the Virtual Environment**:
   - On Windows (PowerShell):
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - On Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```

2. **Configure API Keys**:
   Create a `.env` file in the root directory and set your Groq API key:
   ```env
   GROQ_API_KEY=your_actual_api_key_here
   ```

3. **Install/Manage Dependencies with `uv`**:
   The virtual environment is pre-configured with dependencies. To install additional libraries, run:
   ```bash
   uv pip install <package_name>
   ```

## Running the Application

To start the FastAPI application server, run the following command from the root directory:

```bash
uvicorn app.main:app --reload
```

Then open your browser and navigate to `http://127.0.0.1:8000`.
