FROM python:3.7-alpine
WORKDIR /usr/src/app

COPY requirements.txt flight_optimizer.py ./

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "./flight_optimizer.py"]

