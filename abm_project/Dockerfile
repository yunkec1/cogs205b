FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-numpy \
    python3-pandas \
    python3-matplotlib \
    bash \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python3", "run_simulation.py"]