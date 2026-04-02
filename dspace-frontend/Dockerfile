FROM docker.io/nginx:1.27-alpine

RUN apk add --no-cache python3

COPY nginx.observatorio.conf /etc/nginx/conf.d/default.conf
COPY site /usr/share/nginx/html
COPY docker-entrypoint.py /docker-entrypoint.py

ENV DSPACE_REST_SSL=false \
    DSPACE_REST_HOST=localhost \
    DSPACE_REST_PORT=8080 \
    DSPACE_REST_NAMESPACE=/server \
    DSPACE_REST_BASE_URL=http://localhost:8080/server \
    DSPACE_UI_SSL=false \
    DSPACE_UI_HOST=localhost \
    DSPACE_UI_PORT=4000 \
    DSPACE_UI_NAMESPACE=/ \
    DSPACE_UI_BASE_URL=http://localhost:4000

EXPOSE 80

ENTRYPOINT ["python3", "/docker-entrypoint.py"]
