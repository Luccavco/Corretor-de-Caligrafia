"""Constantes de cor e folha de estilo compartilhadas entre todas as telas."""

C_BG = "#12141a"
C_PANEL = "#1a1d26"
C_CARD = "#20242f"
C_BORDER = "#2c3140"
C_TEXT = "#e6e8ee"
C_MUTED = "#8b93a7"
C_ACCENT = "#4a9eff"
C_GOOD = "#4caf7d"
C_OK = "#e0a83a"
C_BAD = "#e05a5a"


def com_alpha(cor, alpha):
    """Devolve a cor com transparencia no formato que o Qt entende.

    Folhas de estilo do Qt leem cores de 8 digitos como #AARRGGBB (alpha
    primeiro), diferente da web (#RRGGBBAA). Escrever f"{cor}22" gerava
    uma cor totalmente diferente da pretendida. `alpha` vai de 0 a 255.
    """
    return f"#{alpha:02x}{cor.lstrip('#')}"

STYLE = f"""
QMainWindow, QWidget#root {{ background-color: {C_BG}; }}
QWidget {{ color: {C_TEXT}; font-family: 'Segoe UI', 'Noto Sans', sans-serif; }}
QLabel {{ color: {C_TEXT}; }}

QPushButton {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #2a2f3d; border-color: {C_ACCENT}; }}
QPushButton:disabled {{ color: #555c6e; background-color: {C_PANEL}; }}

QPushButton#primary {{
    background-color: {C_ACCENT};
    color: #ffffff;
    border: none;
}}
QPushButton#primary:hover {{ background-color: #62adff; }}
QPushButton#primary:disabled {{ background-color: #2a3a52; color: #6b7891; }}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {C_BORDER};
    padding: 8px 14px;
}}
QPushButton#ghost:hover {{ background-color: {C_CARD}; }}

QTextEdit {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 10px;
    font-size: 14px;
}}

QComboBox {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    min-width: 160px;
}}
QComboBox::drop-down {{ border: none; padding-right: 8px; }}
QComboBox QAbstractItemView {{
    background-color: {C_CARD}; color: {C_TEXT};
    selection-background-color: {C_ACCENT};
    border: 1px solid {C_BORDER};
}}

QProgressBar {{
    border: none;
    border-radius: 3px;
    background-color: {C_CARD};
    height: 6px;
}}
QProgressBar::chunk {{ background-color: {C_ACCENT}; border-radius: 3px; }}

QScrollArea {{ border: none; background: transparent; }}
QWidget#transparente {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: {C_PANEL}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {C_BORDER}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QTabWidget::pane {{
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    border-top-left-radius: 0;
    background-color: {C_PANEL};
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {C_MUTED};
    padding: 12px 26px;
    margin-right: 2px;
    min-width: 110px;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 15px;
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: {C_TEXT}; }}
QTabBar::tab:selected {{
    color: {C_TEXT};
    background-color: {C_PANEL};
    border-color: {C_BORDER};
}}
QTabBar::tab:!selected {{ margin-top: 3px; }}
"""


def make_card(parent_style, title=None):
    """Cria um painel padrao com titulo opcional. Devolve (widget, layout)."""
    from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {C_PANEL}; border: 1px solid {C_BORDER};"
        f" border-radius: 12px; }}"
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(8)
    if title:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; font-weight: 700;"
            f" letter-spacing: 1px; border: none;"
        )
        layout.addWidget(lbl)
    return card, layout


def stat_chip(cor, texto):
    from PyQt5.QtWidgets import QLabel
    lbl = QLabel(texto)
    lbl.setStyleSheet(
        f"background-color: {com_alpha(cor, 0x22)}; color: {cor};"
        f" border: 1px solid {com_alpha(cor, 0x55)};"
        f" border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600;"
    )
    return lbl
