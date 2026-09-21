"""Dialogos da Analise Individual: texto reconhecido expandido (com verificacao
ortografica) e detalhe por letra expandido."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QScrollArea, QGridLayout, QDialog, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from calligraphos.ui.ui_theme import C_CARD, C_TEXT, C_MUTED, C_BORDER, C_GOOD, C_OK, C_BAD, C_ACCENT, com_alpha, C_BG, C_PANEL
from calligraphos.ui.ui_helpers import rotulo
from calligraphos.ui.analise.componentes import LetraChip


class TextoExpandidoDialog(QDialog):
    """Mostra o texto reconhecido em uma janela maior, com uma lista de
    palavras possivelmente escritas erradas (verificacao ortografica em
    portugues, se a biblioteca pyspellchecker estiver instalada)."""

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        self.texto = texto or ""
        self.setWindowTitle("Texto reconhecido")
        self.setMinimumSize(720, 560)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        titulo = rotulo("Texto reconhecido", C_TEXT, 18, peso=800)
        root.addWidget(titulo)

        corpo = QHBoxLayout()
        corpo.setSpacing(14)
        root.addLayout(corpo, 1)

        # Texto grande
        caixa = QTextEdit()
        caixa.setReadOnly(True)
        caixa.setText(self.texto)
        caixa.setStyleSheet(
            f"QTextEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" padding: 14px; font-size: 16px; line-height: 1.5; }}"
        )
        corpo.addWidget(caixa, 60)

        # Painel de ortografia
        painel = QVBoxLayout()
        painel.setSpacing(8)
        corpo.addLayout(painel, 40)

        lbl_orto = QLabel("POSSIVEIS ERROS DE ESCRITA")
        lbl_orto.setStyleSheet(
            f"color: {C_MUTED}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1.2px;"
        )
        painel.addWidget(lbl_orto)

        self.lista_erros = QListWidget()
        self.lista_erros.setStyleSheet(
            f"QListWidget {{ background-color: {C_PANEL}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" padding: 6px; font-size: 13px; }}"
            f"QListWidget::item {{ padding: 7px; border-radius: 6px; }}"
        )
        painel.addWidget(self.lista_erros, 1)

        self._verificar_ortografia()

        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("ghost")
        btn_fechar.clicked.connect(self.accept)
        root.addWidget(btn_fechar, alignment=Qt.AlignRight)

    def _verificar_ortografia(self):
        """Usa pyspellchecker (pt) se disponivel. As palavras marcadas
        como desconhecidas aparecem com a sugestao de correcao."""
        palavras = [
            "".join(c for c in t if c.isalpha())
            for t in self.texto.split()
        ]
        palavras = [p for p in palavras if len(p) >= 2]
        if not palavras:
            self.lista_erros.addItem(QListWidgetItem("Nenhum texto para verificar."))
            return
        try:
            from spellchecker import SpellChecker
            spell = SpellChecker(language="pt")
            desconhecidas = spell.unknown([p.lower() for p in palavras])
            if not desconhecidas:
                self.lista_erros.addItem(
                    QListWidgetItem("Nenhum erro aparente encontrado.")
                )
                return
            # Preserva a ordem em que aparecem no texto
            vistas = set()
            for p in palavras:
                pl = p.lower()
                if pl in desconhecidas and pl not in vistas:
                    vistas.add(pl)
                    sugestao = spell.correction(pl)
                    if sugestao and sugestao != pl:
                        item = QListWidgetItem(f"{p}  ->  {sugestao}")
                    else:
                        item = QListWidgetItem(f"{p}  (sem sugestão)")
                    self.lista_erros.addItem(item)
        except ImportError:
            self.lista_erros.addItem(QListWidgetItem(
                "Verificador ortográfico não instalado."
            ))
            self.lista_erros.addItem(QListWidgetItem(
                "Instale com: pip install pyspellchecker"
            ))
        except Exception as e:
            self.lista_erros.addItem(QListWidgetItem(f"Erro ao verificar: {e}"))

class DetalheExpandidoDialog(QDialog):
    """Versao ampliada do grid Detalhe por Letra, com mais colunas e
    espaco. Clicar em uma letra abre o mesmo popup de detalhe."""
    chip_clicado = pyqtSignal(int)

    def __init__(self, avaliacao, letras_por_indice, letras_manuais, parent=None):
        super().__init__(parent)
        self.avaliacao = avaliacao
        self.letras_por_indice = letras_por_indice
        self.letras_manuais = letras_manuais
        self.setWindowTitle("Detalhe por letra")
        self.setMinimumSize(760, 560)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        titulo = rotulo("Detalhe por letra", C_TEXT, 18, peso=800)
        root.addWidget(titulo)

        if self.avaliacao:
            resumo = QLabel(
                f"{self.avaliacao['total']} letras analisadas  ·  "
                f"{self.avaliacao['boas']} boas  ·  "
                f"{self.avaliacao['aceitaveis']} aceitáveis  ·  "
                f"{self.avaliacao['ruins']} precisam melhorar"
            )
            resumo.setStyleSheet(f"color: {C_MUTED}; font-size: 12px;")
            root.addWidget(resumo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("transparente")
        grid = QGridLayout(container)
        grid.setSpacing(8)
        grid.setAlignment(Qt.AlignTop)

        cores = {0: C_BAD, 1: C_OK, 2: C_GOOD}
        col_max = 6
        chips = []
        if self.avaliacao:
            for i, r in enumerate(self.avaliacao["caracteres"]):
                cor = cores[r["classe"]]
                letra = self.letras_por_indice.get(i, "?")
                if letra and letra != "?":
                    texto = f"{letra}  {r['confianca']:.0%}"
                else:
                    texto = f"L{r['indice']}  {r['confianca']:.0%}"
                chip = LetraChip(i, letra, cor, texto)
                chip.clicado.connect(self.chip_clicado.emit)
                chips.append(chip)
        for info in self.letras_manuais:
            chip = QLabel(f"{info['letra']}  manual")
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                f"background-color: {com_alpha(C_ACCENT, 0x18)}; color: {C_ACCENT};"
                f" border: 1px solid {com_alpha(C_ACCENT, 0x45)}; border-radius: 6px;"
                f" padding: 8px 4px; font-size: 12px; font-weight: 600;"
            )
            chips.append(chip)

        for k, chip in enumerate(chips):
            grid.addWidget(chip, k // col_max, k % col_max)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("ghost")
        btn_fechar.clicked.connect(self.accept)
        root.addWidget(btn_fechar, alignment=Qt.AlignRight)
