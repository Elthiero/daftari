# DukaAI: Streamlit app powered by Gemma 4 via the Gemini API
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

# Install dependencies first so this layer is cached between builds
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the app (secrets are excluded by .dockerignore)
COPY app.py .
COPY .streamlit ./.streamlit

# Run as a non-root user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:%s/_stcore/health' % os.environ.get('PORT','8501'))" || exit 1

# GEMINI_API_KEY and GEMMA_MODEL are set in the platform's environment settings
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
