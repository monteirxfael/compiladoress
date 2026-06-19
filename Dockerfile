FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 python3-pip gcc make nasm binutils git \
    && apt-get clean
WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install -r requirements.txt
RUN git clone https://github.com/pm-avila/simples-compiler.git /compiler && \
    cd /compiler && make all
ENV SIMPLESC_PATH=/compiler/build/simplesc
COPY backend/ .
EXPOSE 5000
CMD ["python3", "app.py"]
