FROM python:3.7.5-slim
MAINTAINER Tahsin Kurc

RUN apt-get -q update && \
	apt-get install -y openslide-tools build-essential && \
	pip install openslide-python pandas

WORKDIR /root

COPY . /root/.
RUN chmod 0755 slide_extract_metadata
ENV PATH=.:$PATH:/root/

CMD ["slide_extract_metadata"]

