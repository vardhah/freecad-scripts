FROM ubuntu:hirsute

WORKDIR /home
COPY . /home

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Chicago
RUN apt-get update
RUN apt-get install -y apt-utils 2>/dev/null
RUN apt-get install -y tzdata
RUN apt-get dist-upgrade -y

RUN apt-get install -y freecad gmsh git nano python3-pip
RUN pip3 install -e .

CMD ["/bin/bash"]
