FROM python:3.6.9-slim
MAINTAINER Tahsin Kurc

RUN apt-get -q update && \
	apt-get install -y openslide-tools build-essential && \
	pip install openslide-python pandas

WORKDIR /root

COPY . /root/.
RUN chmod 0755 run_metadata
ENV PATH=.:$PATH:/root/

CMD ["run_metadata"]

