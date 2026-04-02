# CKAN Dockerfile overlay para el Observatorio 3 en 1.
# Usa el código fuente desde el submódulo `ckan-src` y mantiene la customización
# operativa versionada en este repositorio principal.
FROM python:3.9-slim

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    libpq-dev \
    postgresql-client \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    build-essential \
    curl \
    libmagic1 \
    libmagic-dev \
    gosu \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash ckan
WORKDIR /srv/app

COPY ckan-src /srv/app

RUN pip install --upgrade pip setuptools==65.5.1 wheel
RUN pip install -e .
RUN pip install -r requirements.txt
RUN pip install uwsgi

RUN ckan generate config /srv/app/ckan.ini
RUN mkdir -p /etc/ckan/default \
    && cp /srv/app/wsgi.py /etc/ckan/default/wsgi.py

RUN mkdir -p /srv/app/ckan/public/base/i18n \
    && chmod -R 777 /srv/app/ckan/public/base/i18n \
    && mkdir -p /var/lib/ckan/default \
    && chown -R ckan:ckan /var/lib/ckan

ENV CKAN_REDIS_URL=""
ENV CKAN_INI=/srv/app/ckan.ini

EXPOSE 5000

COPY ckan/bootstrap-and-start.sh /bootstrap-and-start.sh
COPY ckan/ckan-uwsgi.ini /srv/app/ckan-uwsgi.ini
RUN chmod +x /bootstrap-and-start.sh

ENTRYPOINT ["/bootstrap-and-start.sh"]
CMD ["uwsgi", "--ini", "ckan-uwsgi.ini"]
