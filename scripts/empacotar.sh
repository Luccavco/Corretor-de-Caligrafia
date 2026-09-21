#!/usr/bin/env bash
# Gera o pacote de distribuicao Calligraphos-<versao>-linux.zip na pasta dist/:
# codigo do pacote, modelo treinado, instalador, atalho e documentacao.
# Nao inclui venv, credenciais, sessao, dados de treino nem imagens de teste.
set -e
cd "$(dirname "$(readlink -f "$0")")/.."
VERSAO=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
NOME="Calligraphos-$VERSAO-linux"
rm -rf "dist/$NOME" "dist/$NOME.zip"; mkdir -p "dist/$NOME"
cp -r calligraphos tests scripts "dist/$NOME/"
cp main_ui.py config.json pyproject.toml requirements.txt Readme.md calligraphos.png calligraphos.desktop calligraphos.sh instalar.sh modelo_caligrafia.pth "dist/$NOME/"
find "dist/$NOME" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -f "dist/$NOME/scripts/empacotar.sh"
(cd dist && zip -qr "$NOME.zip" "$NOME" && rm -rf "$NOME")
echo "dist/$NOME.zip ($(du -h "dist/$NOME.zip" | cut -f1))"
