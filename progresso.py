"""Persiste o progresso do usuario no Firestore em usuarios/{uid}.
O progresso de letras e separado por estilo: 'letras' (letra de forma)
e 'letras_cursiva' (cursiva)."""

from firebase_config import get_firestore


def _letras_zeradas():
    return {chr(c): 0 for c in range(ord("A"), ord("Z") + 1)}


ESTADO_PADRAO = {
    "letras": {},                 # preenchido em _estado_novo
    "letras_cursiva": {},
    "fases_completas": 0,
    "iniciou_letras": False,
    "onboarding_visto": False,
    "estilo_letras": "forma",
    "palavras_customizadas": [],
}


def _estado_novo():
    estado = dict(ESTADO_PADRAO)
    estado["letras"] = _letras_zeradas()
    estado["letras_cursiva"] = _letras_zeradas()
    estado["palavras_customizadas"] = []
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
        }
    except Exception:
        return _estado_novo()


def _salvar(uid, estado):
    try:
        db = get_firestore()
        db.collection("usuarios").document(uid).set(estado, merge=True)
    except Exception:
        pass


def chave_letras(estilo):
    """Nome do campo de letras conforme o estilo."""
    return "letras_cursiva" if estilo == "cursiva" else "letras"


def registrar_acerto_letra(uid, estado, letra, estilo="forma"):
    chave = chave_letras(estilo)
    if letra in estado[chave] and estado[chave][letra] < 5:
        estado[chave][letra] += 1
    _salvar(uid, estado)


def registrar_fase_completa(uid, estado, fase):
    if fase > estado["fases_completas"]:
        estado["fases_completas"] = fase
    _salvar(uid, estado)


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
    _salvar(uid, estado)
    return True


def remover_palavra_customizada(uid, estado, palavra):
    if palavra in estado["palavras_customizadas"]:
        estado["palavras_customizadas"].remove(palavra)
        _salvar(uid, estado)


def resetar(uid, estado):
    novo = _estado_novo()
    novo["onboarding_visto"] = estado.get("onboarding_visto", False)
    estado.clear()
    estado.update(novo)
    _salvar(uid, estado)
    return estado
