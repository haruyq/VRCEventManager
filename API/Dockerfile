FROM python:3.10-slim

WORKDIR /manager/app

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["uvicorn", "app:VRCEvMngrAPI", "--host", "0.0.0.0", "--port", "8080", "--factory", "--reload"]