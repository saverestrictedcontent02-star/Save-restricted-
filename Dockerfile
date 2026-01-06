FROM python:3.10-slim

RUN apt update && apt install -y ffmpeg git curl wget

WORKDIR /app

# Requirements copy
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Install supervisor
RUN apt install -y supervisor

# Add supervisor config
RUN mkdir -p /etc/supervisor/conf.d

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8000

CMD ["/usr/bin/supervisord"]
