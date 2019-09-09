FROM python:3-alpine

RUN pip install cherrypy && \
  sed -i 's/^server\.socket_host.*$/server.\socket_host = "0.0.0.0"/' \
    tutorial.conf

COPY . /tutorial

WORKDIR /tutorial

ENTRYPOINT ["python"]

CMD ["tut01_helloworld.py"]

EXPOSE 8080
