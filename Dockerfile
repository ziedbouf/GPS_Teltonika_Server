FROM python:3.8-slim
RUN mkdir /app

RUN apt-get update \
    && apt-get -y install libpq-dev gcc

ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt

# Expose port 9980 in the container
EXPOSE 9980

CMD ["python", "/app/collector/snifr.py"]