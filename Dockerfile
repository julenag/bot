FROM python:3.11

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m venv /opt/venv && . /opt/venv/bin/activate && pip install -r requirements.txt

COPY . .

CMD ["/opt/venv/bin/python", "main.py"]
