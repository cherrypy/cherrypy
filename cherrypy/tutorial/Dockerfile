FROM python:3-alpine

COPY . /tutorial

WORKDIR /tutorial

RUN pip install cherrypy && \
  sed -i 's/^server\.socket_host.*$/server.\socket_host = "0.0.0.0"/' \
    tutorial.conf


ENTRYPOINT ["python"]

CMD ["tut01_helloworld.py"]

EXPOSE 8080
