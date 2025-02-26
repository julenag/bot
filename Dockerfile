# Usa la imagen oficial de Python
FROM python:3.11

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias primero para aprovechar la caché
COPY requirements.txt .

# Crea un entorno virtual y lo configura correctamente
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos del proyecto
COPY . .

# Establece el entorno virtual en el contenedor
ENV PATH="/opt/venv/bin:$PATH"

# Usa el entorno virtual para ejecutar el bot
CMD ["python", "bot.py"]

