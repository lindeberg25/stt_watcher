FROM python:3.10-slim

USER root

WORKDIR /deployment

RUN mkdir /deployment/cache/
RUN mkdir /deployment/audio/

RUN chmod 777 /deployment/
RUN chmod 777 /deployment/cache/
RUN chmod 777 /deployment/audio/



RUN apt-get -qq update \
    && apt-get -qq install --no-install-recommends ffmpeg

COPY requirements.txt requirements.txt
RUN  apt-get -y install git


RUN pip install -r requirements.txt
RUN pip install "git+https://github.com/openai/whisper.git" 

COPY . .

#EXPOSE 5000

USER 1001

CMD [ "python3", "stt_watcher.py"]
