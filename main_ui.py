"""Atalho de compatibilidade: o aplicativo agora vive no pacote `calligraphos`.
Use `python -m calligraphos` (ou este arquivo, que faz o mesmo)."""

import sys

from calligraphos.ui.main_ui import main

if __name__ == "__main__":
    sys.exit(main())
