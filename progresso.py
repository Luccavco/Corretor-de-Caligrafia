"""Persiste o progresso do usuario no Firestore em usuarios/{uid}.

Campos guardados:
- letras / letras_cursiva: nivel 0-5 de cada letra (A-Z)
- fases_completas: quantas fases de palavras foram concluidas
- palavras_customizadas: lista de palavras do proprio usuario
- iniciou_letras, onboarding_visto, estilo_letras: flags de fluxo
- exercicios_feitos: total de tentativas corretas ja registradas
- streak_dias: sequencia atual de dias consecutivos praticando
- streak_recorde: maior sequencia ja alcancada
- ultima_pratica: data (YYYY-MM-DD) da ultima pratica
- ultima_pratica_letra: dict letra -> data da ultima pratica daquela letra
- conquistas: lista de ids de conquistas ja desbloqueadas
"""

from datetime import date, datetime, timedelta
from firebase_config import get_firestore


def _letras_zeradas():
    return {chr(c): 0 for c in range(ord("A"), ord("Z") + 1)}


ESTADO_PADRAO = {
    "letras": {},
    "letras_cursiva": {},
    "fases_completas": 0,
    "iniciou_letras": False,
    "onboarding_visto": False,
    "estilo_letras": "forma",
    "palavras_customizadas": [],
    "exercicios_feitos": 0,
    "streak_dias": 0,
    "streak_recorde": 0,
    "ultima_pratica": "",
    "ultima_pratica_letra": {},
    "conquistas": [],
    "meta_diaria": 5,               # exercicios por dia que o usuario busca
    "feitos_hoje": 0,              # exercicios feitos na data de hoje
    "data_feitos_hoje": "",       # data a que 'feitos_hoje' se refere
}


def _estado_novo():
    estado = dict(ESTADO_PADRAO)
    estado["letras"] = _letras_zeradas()
    estado["letras_cursiva"] = _letras_zeradas()
    estado["palavras_customizadas"] = []
    estado["ultima_pratica_letra"] = {}
    estado["conquistas"] = []
    return estado


def carregar(uid):
    try:
        db = get_firestore()
        ref = db.collection("usuarios").document(uid)
        doc = ref.get()
        if not doc.exists:
            estado = _estado_novo()
            ref.set(estado)
            return estado
        dados = doc.to_dict() or {}
        letras = _letras_zeradas()
        letras.update(dados.get("letras", {}))
        letras_cursiva = _letras_zeradas()
        letras_cursiva.update(dados.get("letras_cursiva", {}))
        return {
            "letras": letras,
            "letras_cursiva": letras_cursiva,
            "fases_completas": dados.get("fases_completas", 0),
            "iniciou_letras": dados.get("iniciou_letras", False),
            "onboarding_visto": dados.get("onboarding_visto", False),
            "estilo_letras": dados.get("estilo_letras", "forma"),
            "palavras_customizadas": dados.get("palavras_customizadas", []),
            "exercicios_feitos": dados.get("exercicios_feitos", 0),
            "streak_dias": dados.get("streak_dias", 0),
            "streak_recorde": dados.get("streak_recorde", 0),
            "ultima_pratica": dados.get("ultima_pratica", ""),
            "ultima_pratica_letra": dados.get("ultima_pratica_letra", {}),
            "conquistas": dados.get("conquistas", []),
            "meta_diaria": dados.get("meta_diaria", 5),
            "feitos_hoje": dados.get("feitos_hoje", 0),
            "data_feitos_hoje": dados.get("data_feitos_hoje", ""),
        }
    except Exception:
        # Falha de leitura (ex: sem internet neste instante). Devolve um
        # estado zerado apenas para a interface abrir, mas marcado como
        # "somente leitura": o _salvar recusa gravar estados assim, para
        # NAO sobrescrever o progresso real no Firestore com zeros caso a
        # conexao volte no meio da sessao.
        estado = _estado_novo()
        estado["_somente_leitura"] = True
        return estado


def _salvar(uid, estado):
    # Nunca grava um estado que veio de falha de leitura (ver carregar):
    # isso apagaria o progresso real do usuario no Firestore.
    if estado.get("_somente_leitura"):
        return
    try:
        db = get_firestore()
        # O marcador interno nunca deve ir para o banco
        dados = {k: v for k, v in estado.items() if not k.startswith("_")}
        db.collection("usuarios").document(uid).set(dados, merge=True)
    except Exception:
        pass


def chave_letras(estilo):
    return "letras_cursiva" if estilo == "cursiva" else "letras"


# ─── STREAK (sequencia diaria) ───────────────────────────────────────────────

def _atualizar_streak(estado):
    """Atualiza a sequencia de dias consecutivos com base na data de hoje.
    Regra: praticar hoje mantem/incrementa; um dia pulado zera a sequencia."""
    hoje = date.today()
    ultima_str = estado.get("ultima_pratica", "")
    if ultima_str:
        try:
            ultima = datetime.strptime(ultima_str, "%Y-%m-%d").date()
        except ValueError:
            ultima = None
    else:
        ultima = None

    if ultima == hoje:
        pass  # ja praticou hoje, streak nao muda
    elif ultima == hoje - timedelta(days=1):
        estado["streak_dias"] = estado.get("streak_dias", 0) + 1
    else:
        estado["streak_dias"] = 1  # primeiro dia ou sequencia quebrada

    estado["ultima_pratica"] = hoje.isoformat()
    if estado["streak_dias"] > estado.get("streak_recorde", 0):
        estado["streak_recorde"] = estado["streak_dias"]


def _contar_exercicio_hoje(estado):
    """Incrementa o contador de exercicios do dia, zerando se mudou o dia."""
    hoje = date.today().isoformat()
    if estado.get("data_feitos_hoje", "") != hoje:
        estado["data_feitos_hoje"] = hoje
        estado["feitos_hoje"] = 0
    estado["feitos_hoje"] = estado.get("feitos_hoje", 0) + 1


def progresso_meta_diaria(estado):
    """Devolve (feitos_hoje, meta) considerando o dia atual.
    Se a data guardada nao e hoje, o contador do dia e zero."""
    hoje = date.today().isoformat()
    meta = estado.get("meta_diaria", 5)
    if estado.get("data_feitos_hoje", "") != hoje:
        return 0, meta
    return estado.get("feitos_hoje", 0), meta


def definir_meta_diaria(uid, estado, meta):
    meta = max(1, min(50, int(meta)))
    estado["meta_diaria"] = meta
    _salvar(uid, estado)


# ─── REVISOES PENDENTES (repeticao espacada simples) ─────────────────────────

# Intervalo em dias ate a proxima revisao, por nivel (0 a 5).
# Nivel 0 = nunca praticou; niveis maiores = intervalos crescentes.
_INTERVALO_REVISAO = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}


def revisoes_pendentes(estado):
    """Lista as letras que estao 'na hora' de revisar, com base em quando
    foram praticadas pela ultima vez e no nivel atual (intervalo crescente).

    Uma letra e considerada pendente se:
    - ja foi praticada ao menos uma vez (nivel >= 1), e
    - passou tempo suficiente desde a ultima pratica para o seu nivel.

    Letras nivel 0 (nunca praticadas) NAO contam como revisao - sao
    'aprendizado novo', nao revisao."""
    letras = estado.get("letras", {})
    ultimas = estado.get("ultima_pratica_letra", {})
    hoje = date.today()
    pendentes = []
    for letra, nivel in letras.items():
        if nivel < 1:
            continue
        intervalo = _INTERVALO_REVISAO.get(nivel, 14)
        data_str = ultimas.get(letra, "")
        if not data_str:
            # praticada mas sem data registrada (dados antigos): revisar
            pendentes.append(letra)
            continue
        try:
            ultima = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            pendentes.append(letra)
            continue
        if (hoje - ultima).days >= intervalo:
            pendentes.append(letra)
    return sorted(pendentes)


# ─── CONQUISTAS ──────────────────────────────────────────────────────────────

# id -> (titulo, descricao, funcao que testa se foi desbloqueada)
CONQUISTAS = [
    ("primeiros_passos", "Primeiros passos", "Domine sua primeira letra",
     lambda e: sum(1 for n in e["letras"].values() if n >= 5) >= 1),
    ("aquecendo", "Aquecendo", "Domine 5 letras",
     lambda e: sum(1 for n in e["letras"].values() if n >= 5) >= 5),
    ("meio_caminho", "Meio caminho", "Domine 13 letras",
     lambda e: sum(1 for n in e["letras"].values() if n >= 5) >= 13),
    ("alfabeto_completo", "Alfabeto completo", "Domine todas as 26 letras",
     lambda e: sum(1 for n in e["letras"].values() if n >= 5) >= 26),
    ("primeira_fase", "Primeira fase", "Complete a primeira fase de palavras",
     lambda e: e["fases_completas"] >= 1),
    ("todas_fases", "Mestre das palavras", "Complete todas as fases",
     lambda e: e["fases_completas"] >= 3),
    ("colecionador", "Colecionador", "Adicione 5 palavras em Minhas Palavras",
     lambda e: len(e.get("palavras_customizadas", [])) >= 5),
    ("dedicado", "Dedicado", "Faca 50 exercicios corretos",
     lambda e: e.get("exercicios_feitos", 0) >= 50),
    ("sequencia_fogo", "Sequencia de fogo", "Pratique 7 dias seguidos",
     lambda e: e.get("streak_recorde", 0) >= 7),
    ("incansavel", "Incansavel", "Pratique 30 dias seguidos",
     lambda e: e.get("streak_recorde", 0) >= 30),
]


def _verificar_conquistas(estado):
    """Retorna a lista de conquistas recem-desbloqueadas (para avisar)."""
    ja = set(estado.get("conquistas", []))
    novas = []
    for cid, _titulo, _desc, teste in CONQUISTAS:
        if cid not in ja and teste(estado):
            ja.add(cid)
            novas.append(cid)
    estado["conquistas"] = list(ja)
    return novas


def conquistas_detalhadas(estado):
    """Lista todas as conquistas com status (desbloqueada ou nao)."""
    desbloqueadas = set(estado.get("conquistas", []))
    resultado = []
    for cid, titulo, desc, _teste in CONQUISTAS:
        resultado.append({
            "id": cid,
            "titulo": titulo,
            "descricao": desc,
            "desbloqueada": cid in desbloqueadas,
        })
    return resultado


# ─── REGISTRO DE PROGRESSO ───────────────────────────────────────────────────

def registrar_acerto_letra(uid, estado, letra, estilo="forma"):
    chave = chave_letras(estilo)
    if letra in estado[chave] and estado[chave][letra] < 5:
        estado[chave][letra] += 1
    estado["exercicios_feitos"] = estado.get("exercicios_feitos", 0) + 1
    estado.setdefault("ultima_pratica_letra", {})[letra] = date.today().isoformat()
    _contar_exercicio_hoje(estado)
    _atualizar_streak(estado)
    novas = _verificar_conquistas(estado)
    _salvar(uid, estado)
    return novas


def registrar_fase_completa(uid, estado, fase):
    if fase > estado["fases_completas"]:
        estado["fases_completas"] = fase
    estado["exercicios_feitos"] = estado.get("exercicios_feitos", 0) + 1
    _contar_exercicio_hoje(estado)
    _atualizar_streak(estado)
    novas = _verificar_conquistas(estado)
    _salvar(uid, estado)
    return novas


def marcar_iniciou_letras(uid, estado):
    estado["iniciou_letras"] = True
    _salvar(uid, estado)


def marcar_onboarding_visto(uid, estado):
    estado["onboarding_visto"] = True
    _salvar(uid, estado)


def definir_estilo_letras(uid, estado, estilo):
    if estilo in ("forma", "cursiva"):
        estado["estilo_letras"] = estilo
        _salvar(uid, estado)


def adicionar_palavra_customizada(uid, estado, palavra):
    palavra = (palavra or "").strip().upper()
    if not palavra or not palavra.isalpha():
        return False
    if palavra in estado["palavras_customizadas"]:
        return False
    estado["palavras_customizadas"].append(palavra)
    _verificar_conquistas(estado)
    _salvar(uid, estado)
    return True


def remover_palavra_customizada(uid, estado, palavra):
    if palavra in estado["palavras_customizadas"]:
        estado["palavras_customizadas"].remove(palavra)
        _salvar(uid, estado)


# ─── RESUMO PARA O PAINEL DE PROGRESSO ───────────────────────────────────────

def _streak_efetiva(estado):
    """Streak como deve ser EXIBIDA agora. O valor salvo so e recalculado
    quando a pessoa pratica; entao, se a ultima pratica nao foi hoje nem
    ontem, a sequencia ja foi quebrada e deve aparecer como 0 - mesmo que
    o banco ainda guarde o numero antigo."""
    salva = estado.get("streak_dias", 0)
    ultima_str = estado.get("ultima_pratica", "")
    if not ultima_str:
        return 0
    try:
        ultima = datetime.strptime(ultima_str, "%Y-%m-%d").date()
    except ValueError:
        return 0
    hoje = date.today()
    if ultima == hoje or ultima == hoje - timedelta(days=1):
        return salva
    return 0


def resumo(estado):
    """Calcula as metricas gerais exibidas no painel de progresso."""
    letras = estado.get("letras", {})
    dominadas = sum(1 for n in letras.values() if n >= 5)
    niveis_totais = sum(letras.values())
    max_niveis = 5 * 26

    fases = estado.get("fases_completas", 0)
    max_fases = 3
    palavras = len(estado.get("palavras_customizadas", []))

    # Percentual geral: media ponderada entre letras (peso 70%) e fases (30%)
    pct_letras = (niveis_totais / max_niveis) if max_niveis else 0
    pct_fases = (fases / max_fases) if max_fases else 0
    percentual = round((pct_letras * 0.7 + pct_fases * 0.3) * 100)

    total_conquistas = len(CONQUISTAS)
    conquistas_feitas = len(estado.get("conquistas", []))

    return {
        "percentual": percentual,
        "letras_dominadas": dominadas,
        "letras_total": 26,
        "niveis_totais": niveis_totais,
        "niveis_max": max_niveis,
        "fases_completas": fases,
        "fases_total": max_fases,
        "palavras": palavras,
        "exercicios_feitos": estado.get("exercicios_feitos", 0),
        "streak_dias": _streak_efetiva(estado),
        "streak_recorde": estado.get("streak_recorde", 0),
        "conquistas_feitas": conquistas_feitas,
        "conquistas_total": total_conquistas,
    }


def resetar(uid, estado):
    novo = _estado_novo()
    novo["onboarding_visto"] = estado.get("onboarding_visto", False)
    estado.clear()
    estado.update(novo)
    _salvar(uid, estado)
    return estado
