FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8001

COPY app ./app

CMD ["python", "-u", "-m", "app.main"]
