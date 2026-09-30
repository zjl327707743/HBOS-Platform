FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
WORKDIR /opt/hbos
COPY services/hbos_gateway/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/hb_knowledge_app/hb_knowledge_app hb_knowledge_app
COPY services/hbos_gateway hbos_gateway
ENV PYTHONPATH=/opt/hbos
RUN useradd --uid 1000 --create-home hbos
USER hbos
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "hbos_gateway.app:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
