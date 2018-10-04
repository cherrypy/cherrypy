FROM python:3-alpine

RUN pip install cherrypy

COPY . /tutorial

WORKDIR /tutorial

ENTRYPOINT ["python"]

CMD ["tut01_helloworld.py"]

EXPOSE 8080
