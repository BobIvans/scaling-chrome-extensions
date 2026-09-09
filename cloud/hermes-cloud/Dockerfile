FROM nousresearch/hermes-agent:latest

ENV API_SERVER_ENABLED=true \
    API_SERVER_HOST=0.0.0.0 \
    API_SERVER_PORT=8080 \
    HERMES_DASHBOARD=0

COPY config.yaml /opt/data/config.yaml
EXPOSE 8080
CMD ["gateway", "run"]
