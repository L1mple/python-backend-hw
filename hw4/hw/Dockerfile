FROM python:3.12

# Variables d'environnement pour optimiser Python
ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

# Mettre à jour et installer gcc (nécessaire pour certaines dépendances)
RUN apt-get update && apt-get install -y gcc

# Mettre à jour pip
RUN python -m pip install --upgrade pip

# Créer et définir le répertoire de travail
WORKDIR /app

# Copier d'abord requirements.txt pour optimiser le cache Docker
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste de l'application
COPY . .

# Exposer le port 8080
EXPOSE 8080

# Commande pour lancer l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]