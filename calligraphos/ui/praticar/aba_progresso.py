"""Aba Progresso: anel, estatisticas, evolucao da nota, mapa de calor e conquistas."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout
from PyQt5.QtCore import Qt
from calligraphos.ui.ui_helpers import limpar_layout, cabecalho_aba, FlowLayout, rotulo
from calligraphos.ui.ui_theme import C_CARD, C_PANEL, C_TEXT, C_MUTED, C_BORDER, C_ACCENT, C_GOOD, C_OK, C_BAD, make_card
from calligraphos.nuvem import progresso as prog
from calligraphos.ui.praticar.cartoes import ConquistaCard
from calligraphos.ui.praticar.constantes import LETRAS


class AbaProgresso(QWidget):
    """Painel de progresso geral: anel de desempenho, estatisticas,
    mapa de calor das letras e conquistas."""

    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._raiz = QVBoxLayout(self)
        self._raiz.setContentsMargins(20, 20, 20, 20)
        self._raiz.setSpacing(14)
        self._construir()

    def _limpar(self):
        limpar_layout(self._raiz)

    def _construir(self):
        from calligraphos.ui.anel_progresso import AnelProgresso
        r = prog.resumo(self.estado)

        self._raiz.addWidget(
            cabecalho_aba("Seu Progresso", "acompanhe sua evolução na plataforma")
        )

        # Conteudo rolavel (pode ficar longo)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        container = QWidget()
        container.setObjectName("transparente")
        conteudo = QVBoxLayout(container)
        conteudo.setContentsMargins(0, 0, 8, 0)
        conteudo.setSpacing(18)

        # ── LINHA 1: anel + estatisticas ──
        topo = QHBoxLayout()
        topo.setSpacing(24)

        anel = AnelProgresso(r["percentual"], tamanho=220)
        topo.addWidget(anel, alignment=Qt.AlignTop)

        # Grade de estatisticas
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        cartoes = [
            ("Letras dominadas", f"{r['letras_dominadas']}/{r['letras_total']}", C_GOOD),
            ("Fases completas", f"{r['fases_completas']}/{r['fases_total']}", C_ACCENT),
            ("Minhas palavras", str(r["palavras"]), C_ACCENT),
            ("Exercícios feitos", str(r["exercicios_feitos"]), C_TEXT),
            ("Sequência atual", f"{r['streak_dias']} dia(s)", C_OK),
            ("Melhor sequência", f"{r['streak_recorde']} dia(s)", C_OK),
        ]
        for i, (rot, val, cor) in enumerate(cartoes):
            stats_grid.addWidget(self._stat_card(rot, val, cor), i // 3, i % 3)
        topo.addLayout(stats_grid, 1)
        conteudo.addLayout(topo)

        # ── LINHA 2: evolucao da nota ──
        conteudo.addWidget(self._titulo_secao("EVOLUÇÃO DA NOTA"))
        conteudo.addWidget(self._secao_evolucao())

        # ── LINHA 3: mapa de calor das letras ──
        conteudo.addWidget(self._titulo_secao("DOMÍNIO DO ALFABETO"))
        legenda = QLabel(
            "Cada quadrado mostra o nível de domínio da letra "
            "(cinza = não praticada, verde = dominada)."
        )
        legenda.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        conteudo.addWidget(legenda)
        conteudo.addWidget(self._mapa_calor())

        # ── LINHA 3: conquistas ──
        conqs = prog.conquistas_detalhadas(self.estado)
        feitas = sum(1 for c in conqs if c["desbloqueada"])
        conteudo.addWidget(
            self._titulo_secao(f"CONQUISTAS  ({feitas}/{len(conqs)})")
        )
        grid_conq = FlowLayout(espacamento=12)
        for c in conqs:
            grid_conq.addWidget(ConquistaCard(c))
        wrap_conq = QWidget()
        wrap_conq.setLayout(grid_conq)
        conteudo.addWidget(wrap_conq)

        conteudo.addStretch(1)
        scroll.setWidget(container)
        self._raiz.addWidget(scroll, 1)

    def _stat_card(self, rotulo, valor, cor):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 12px; }}"
        )
        card.setFixedHeight(92)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)
        lbl_val = QLabel(valor)
        lbl_val.setStyleSheet(
            f"color: {cor}; font-size: 26px; font-weight: 800;"
            f" border: none; background: transparent;"
        )
        lay.addWidget(lbl_val)
        lbl_rot = QLabel(rotulo)
        lbl_rot.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        lay.addWidget(lbl_rot)
        return card

    def _secao_evolucao(self):
        """Grafico da media diaria (30 dias) + resumo semana atual x anterior."""
        from calligraphos.ui.grafico_evolucao import GraficoEvolucao
        card, lay = make_card(None)
        atual, n_atual = prog.media_periodo(self.estado, 7)
        anterior, _ = prog.media_periodo(self.estado, 7, deslocamento=7)
        if atual is None:
            resumo = "Sua média dos últimos 7 dias aparece aqui depois das primeiras tentativas."
        else:
            resumo = f"Média dos últimos 7 dias: <b>{atual:.0f}</b> ({n_atual} tentativa(s))"
            if anterior is not None:
                delta = atual - anterior
                cor = C_GOOD if delta >= 0 else C_BAD
                resumo += f" · <span style='color:{cor}'>{delta:+.0f}</span> em relação à semana anterior"
        lbl = rotulo(resumo, C_MUTED)
        lay.addWidget(lbl)
        lay.addWidget(GraficoEvolucao(prog.evolucao_diaria(self.estado, 30), dias=30))

        # Letras com pior media recente: onde praticar
        por_letra = prog.evolucao_por_letra(self.estado)
        if por_letra:
            piores = sorted(por_letra.items(), key=lambda kv: kv[1][0])[:3]
            txt = "Letras para reforçar: " + "  ".join(
                f"<b>{l}</b> ({m:.0f})" for l, (m, _n) in piores
            )
            lbl2 = rotulo(txt, C_MUTED, 12)
            lay.addWidget(lbl2)
        return card

    def _titulo_secao(self, texto):
        lbl = QLabel(texto)
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 1.4px; border: none;"
        )
        return lbl

    def _mapa_calor(self):
        letras_estado = self.estado.get("letras", {})
        wrap = QWidget()
        grid = QGridLayout(wrap)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)
        cols = 13
        for i, letra in enumerate(LETRAS):
            nivel = letras_estado.get(letra, 0)
            cor = self._cor_nivel(nivel)
            quad = QLabel(letra)
            quad.setAlignment(Qt.AlignCenter)
            quad.setFixedSize(48, 48)
            cor_txt = "#ffffff" if nivel >= 1 else C_MUTED
            quad.setStyleSheet(
                f"background-color: {cor}; color: {cor_txt};"
                f" border-radius: 8px; font-size: 18px; font-weight: 700;"
            )
            quad.setToolTip(
                f"{letra}: dominada" if nivel >= 5
                else f"{letra}: nível {nivel} de 5"
            )
            grid.addWidget(quad, i // cols, i % cols)
        return wrap

    def _cor_nivel(self, n):
        # Gradiente discreto: cinza -> ambar -> azul -> verde
        if n >= 5:
            return C_GOOD
        elif n >= 3:
            return C_ACCENT
        elif n >= 1:
            return C_OK
        return C_CARD

    def reconstruir(self):
        self._limpar()
        self._construir()
