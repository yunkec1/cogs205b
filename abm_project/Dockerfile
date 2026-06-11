FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-numpy \
    python3-pandas \
    python3-matplotlib \
    bash \
    openssh-server \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /var/run/sshd && \
echo 'root:rootpassword' | chpasswd
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]