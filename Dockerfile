FROM python:2.7-alpine

RUN pip install cherrypy

COPY ./cherrypy/tutorial /tutorial

WORKDIR /tutorial

