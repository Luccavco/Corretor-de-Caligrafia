#!/usr/bin/env bash
# Instalador do Calligraphos (Linux). Cria o ambiente virtual, instala as
# dependencias e registra o atalho no menu de aplicativos.
# Uso: ./instalar.sh   (de dentro da pasta extraida do pacote)
set -e
cd "$(dirname "$(readlink -f "$0")")"
AQUI="$PWD"

echo "== Calligraphos: instalação =="
if ! command -v python3 >/dev/null; then echo "Python 3 não encontrado. Instale o Python 3.11 e rode de novo."; exit 1; fi
VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "Python $VER"

[ -d venv ] || python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip >/dev/null
echo "Instalando dependências (pode demorar alguns minutos na primeira vez)..."
pip install -r requirements.txt

# Atalho no menu (KDE/GNOME) com os caminhos desta instalação
mkdir -p "$HOME/.local/share/applications"
sed -e "s#^Exec=.*#Exec=$AQUI/calligraphos.sh#" -e "s#^Icon=.*#Icon=$AQUI/calligraphos.png#" calligraphos.desktop > "$HOME/.local/share/applications/calligraphos.desktop"
chmod +x calligraphos.sh
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo
echo "Pronto. Para abrir: ./calligraphos.sh  (ou 'Calligraphos' no menu de aplicativos)"
echo
if [ ! -f google_credentials.json ] || [ ! -f firebase_credentials.json ]; then
  echo "Aviso: coloque google_credentials.json e firebase_credentials.json nesta pasta"
  echo "para habilitar a transcrição online e o login (veja o Readme.md)."
fi
