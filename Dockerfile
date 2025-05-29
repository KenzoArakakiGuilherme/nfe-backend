FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    ghostscript \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório da aplicação
WORKDIR /app

# Copia arquivos para dentro do container
COPY . .

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Porta que o Flask vai rodar
ENV PORT=10000

# Comando para iniciar o app
CMD ["python", "app.py"]
