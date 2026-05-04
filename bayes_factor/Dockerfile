FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir scipy

CMD ["python", "-m", "unittest", "tests/test_bayes_factor.py"]