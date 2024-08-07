FROM python:3.11.2-slim-buster
WORKDIR /usr/src/application
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4555" ,"--reload"]