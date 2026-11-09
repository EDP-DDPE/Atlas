#!/bin/bash
set -e  # Para abortar se qualquer comando falhar

# Ir para a pasta do projeto
cd /var/www/atlas/Atlas || exit 1

# Atualizar repositório
/usr/bin/git fetch --all
/usr/bin/git reset --hard origin/main

# Ativar virtualenv
source /var/www/atlas/venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Reiniciar serviço sem pedir senha
sudo /usr/bin/systemctl restart atlas