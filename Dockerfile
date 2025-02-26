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

# Verifica que el entorno virtual se está utilizando
RUN /opt/venv/bin/python -m pip freeze

# Usa el entorno virtual para ejecutar el bot
CMD ["/opt/venv/bin/python", "bot.py"]
