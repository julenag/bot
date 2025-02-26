# Usa la imagen oficial de Python
FROM python:3.11

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias primero para aprovechar la caché
COPY requirements.txt requirements.txt

# Crea un entorno virtual e instala las dependencias
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos del proyecto
COPY . .

# Define el comando de inicio del bot
CMD ["/opt/venv/bin/python", "bot.py"]
