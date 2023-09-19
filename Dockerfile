FROM python:3.11-slim

RUN apt-get update && apt-get -y upgrade && apt-get install -y sudo && sudo apt-get install -y libopus0

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && cp /usr/bin/ffmpeg /app/

COPY . /app

RUN pip install -r requirements.txt

CMD ["python3", "run.py"]