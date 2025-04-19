FROM python:3.6-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y gcc
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 6029

CMD ["python3", "main.py"]