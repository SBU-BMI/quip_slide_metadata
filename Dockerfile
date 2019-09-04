FROM python:3.6.9-slim
MAINTAINER Tahsin Kurc

RUN apt-get -q update && \
	apt-get install -y openslide-tools build-essential python3-openslide && \
	pip install openslide-python 

WORKDIR /home

COPY . /home/.
RUN chmod 0755 run_metadata
ENV PATH=$PATH:/home/

CMD ["bash", "run_metadata"]

