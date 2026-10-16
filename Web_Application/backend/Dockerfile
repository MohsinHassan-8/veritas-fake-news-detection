FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=1000 -r requirements.txt

RUN python -c "import nltk; nltk.download('stopwords'); \
    nltk.download('punkt'); nltk.download('wordnet'); \
    nltk.download('omw-1.4')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]