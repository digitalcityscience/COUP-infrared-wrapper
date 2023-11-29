FROM python:3.11

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app

CMD ["uvicorn", "infrared_wrapper_api.api.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]