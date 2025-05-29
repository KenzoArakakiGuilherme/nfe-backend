FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    ghostscript \
    python3-tk \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta usada pelo Flask
EXPOSE 10000

# Comando para rodar o app
CMD ["python", "app.py"]
