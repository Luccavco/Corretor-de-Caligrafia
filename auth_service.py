"""Servico de autenticacao: registro, login, logout e sessao persistente.
A sessao (email + token de refresh) fica em disco para o usuario nao
precisar logar de novo toda vez que abrir o programa."""

import json
import os
from firebase_config import get_pyrebase_auth


# Arquivo de sessao resolvido a partir da pasta deste arquivo, para
# funcionar nao importa de onde o programa foi iniciado.
ARQUIVO_SESSAO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sessao.json"
)


class ErroAuth(Exception):
    """Erro amigavel para exibir na interface."""
    pass


# ── Traducao de erros do Firebase ──────────────────────────────────────

MENSAGENS = {
    "EMAIL_EXISTS": "Este email ja esta cadastrado.",
    "INVALID_EMAIL": "Email invalido.",
    "WEAK_PASSWORD": "A senha precisa ter no minimo 6 caracteres.",
    "EMAIL_NOT_FOUND": "Nao encontramos uma conta com esse email.",
    "INVALID_PASSWORD": "Senha incorreta.",
    "INVALID_LOGIN_CREDENTIALS": "Email ou senha incorretos.",
    "USER_DISABLED": "Esta conta foi desativada.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Muitas tentativas. Tente novamente em alguns minutos.",
    "MISSING_PASSWORD": "Digite a senha.",
    "MISSING_EMAIL": "Digite o email.",
}


def _extrair_erro(exc):
    """Firebase devolve erros como JSON dentro da mensagem. Tenta extrair
    a chave conhecida e traduzir; se falhar, devolve uma mensagem generica."""
    txt = str(exc)
    for chave, mensagem in MENSAGENS.items():
        if chave in txt:
            return mensagem
    if "Network" in txt or "timeout" in txt.lower():
        return "Sem conexao com a internet."
    return "Erro ao se conectar com o servidor. Tente novamente."


# ── Registro / Login / Logout ──────────────────────────────────────────

def registrar(email, senha):
    """Cria uma conta nova. Devolve dict com uid, email e tokens."""
    if not email or "@" not in email:
        raise ErroAuth("Digite um email valido.")
    if len(senha) < 6:
        raise ErroAuth("A senha precisa ter no minimo 6 caracteres.")
    try:
        auth = get_pyrebase_auth()
        user = auth.create_user_with_email_and_password(email, senha)
        _salvar_sessao(user)
        return user
    except Exception as e:
        raise ErroAuth(_extrair_erro(e))


def login(email, senha):
    """Autentica um usuario existente."""
    if not email:
        raise ErroAuth("Digite o email.")
    if not senha:
        raise ErroAuth("Digite a senha.")
    try:
        auth = get_pyrebase_auth()
        user = auth.sign_in_with_email_and_password(email, senha)
        _salvar_sessao(user)
        return user
    except Exception as e:
        raise ErroAuth(_extrair_erro(e))


def logout():
    """Encerra a sessao local."""
    try:
        if os.path.exists(ARQUIVO_SESSAO):
            os.remove(ARQUIVO_SESSAO)
    except OSError:
        pass


# ── Sessao persistente ─────────────────────────────────────────────────

def _salvar_sessao(user):
    """Guarda dados minimos da sessao em disco para autologin."""
    try:
        with open(ARQUIVO_SESSAO, "w", encoding="utf-8") as f:
            json.dump({
                "email": user.get("email"),
                "uid": user.get("localId"),
                "refreshToken": user.get("refreshToken"),
                "idToken": user.get("idToken"),
            }, f)
    except OSError:
        pass


def carregar_sessao():
    """Tenta restaurar uma sessao anterior. Devolve None se nao houver
    sessao valida (arquivo ausente ou token expirado sem forma de renovar)."""
    if not os.path.exists(ARQUIVO_SESSAO):
        return None
    try:
        with open(ARQUIVO_SESSAO, "r", encoding="utf-8") as f:
            dados = json.load(f)
        # Renova o token para garantir que ainda esta valido
        auth = get_pyrebase_auth()
        renovado = auth.refresh(dados["refreshToken"])
        # Atualiza o arquivo com os tokens novos
        dados["idToken"] = renovado["idToken"]
        dados["refreshToken"] = renovado["refreshToken"]
        with open(ARQUIVO_SESSAO, "w", encoding="utf-8") as f:
            json.dump(dados, f)
        return dados
    except Exception:
        # Token expirou de vez ou arquivo corrompido — descarta a sessao
        try:
            os.remove(ARQUIVO_SESSAO)
        except OSError:
            pass
        return None


# ── Alteracao de credenciais ───────────────────────────────────────────

def alterar_senha(id_token, nova_senha):
    """Muda a senha do usuario logado."""
    if len(nova_senha) < 6:
        raise ErroAuth("A nova senha precisa ter no minimo 6 caracteres.")
    try:
        auth = get_pyrebase_auth()
        # O Pyrebase nao expoe troca de senha diretamente; chamamos o
        # endpoint accounts:update da Identity Toolkit do Firebase.
        import requests
        resp = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={auth.api_key}",
            json={"idToken": id_token, "password": nova_senha, "returnSecureToken": True},
            timeout=10,
        )
        resp.raise_for_status()
        # Atualiza a sessao salva com os novos tokens
        dados_novos = resp.json()
        _atualizar_sessao_tokens(dados_novos)
    except ErroAuth:
        raise
    except Exception as e:
        raise ErroAuth(_extrair_erro(e))


def alterar_email(id_token, novo_email):
    """Muda o email do usuario logado."""
    if not novo_email or "@" not in novo_email:
        raise ErroAuth("Digite um email valido.")
    try:
        import requests
        auth = get_pyrebase_auth()
        resp = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={auth.api_key}",
            json={"idToken": id_token, "email": novo_email, "returnSecureToken": True},
            timeout=10,
        )
        resp.raise_for_status()
        dados_novos = resp.json()
        _atualizar_sessao_tokens(dados_novos, novo_email=novo_email)
    except ErroAuth:
        raise
    except Exception as e:
        raise ErroAuth(_extrair_erro(e))


def _atualizar_sessao_tokens(dados_api, novo_email=None):
    """Atualiza os tokens (e opcionalmente o email) na sessao salva."""
    if not os.path.exists(ARQUIVO_SESSAO):
        return
    try:
        with open(ARQUIVO_SESSAO, "r", encoding="utf-8") as f:
            atual = json.load(f)
        if "idToken" in dados_api:
            atual["idToken"] = dados_api["idToken"]
        if "refreshToken" in dados_api:
            atual["refreshToken"] = dados_api["refreshToken"]
        if novo_email:
            atual["email"] = novo_email
        with open(ARQUIVO_SESSAO, "w", encoding="utf-8") as f:
            json.dump(atual, f)
    except OSError:
        pass
