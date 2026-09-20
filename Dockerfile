FROM ghcr.io/prefix-dev/pixi:latest

WORKDIR /app

# Copy dependency definition
COPY pixi.toml /app/

# Install dependencies into project prefix
RUN pixi install

# Copy source code and data target directory
COPY app /app/app
RUN mkdir -p /app/data

EXPOSE 8501

CMD ["pixi", "run", "start"]