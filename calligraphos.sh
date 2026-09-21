#!/usr/bin/env bash
# Inicializador do Calligraphos: ativa o venv e roda o programa.
# Este arquivo precisa ficar na RAIZ do projeto (junto com a pasta calligraphos/).

# Descobre a pasta onde este script esta, e entra nela - assim funciona
# nao importa de onde for chamado (menu do KDE, terminal, atalho, etc.)
cd "$(dirname "$(readlink -f "$0")")"

source venv/bin/activate
python -m calligraphos
