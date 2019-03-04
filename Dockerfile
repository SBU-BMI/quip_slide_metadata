FROM	python:3.7.2 
MAINTAINER Tahsin Kurc

RUN 	apt-get -q update && \
	apt-get install -y openslide-tools python3-openslide && \
	pip install openslide-python 

COPY . /home/.

WORKDIR /home

CMD ["bash", "run.sh"]

