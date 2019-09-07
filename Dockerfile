FROM python:3.6.9-slim
MAINTAINER Tahsin Kurc

RUN apt-get -q update && \
	apt-get install -y openslide-tools build-essential && \
	pip install openslide-python pandas

WORKDIR /home

COPY . /home/.
RUN chmod 0755 run_metadata
ENV PATH=$PATH:/home/

CMD ["run_metadata"]

