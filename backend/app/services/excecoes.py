"""Exceções da camada de serviço.

Os serviços não conhecem HTTP: só levantam estas exceções. Quem as transforma em resposta
JSON com o status certo é o handler registrado em ``app/errors.py``.
"""


class ErroAplicacao(Exception):
    status_code = 400

    def __init__(self, mensagem: str, *, como_lista: bool = True):
        super().__init__(mensagem)
        self.mensagem = mensagem
        # Formato da resposta: {"errors": [msg]} ou {"message": msg}, igual ao sistema original.
        self.como_lista = como_lista

    def to_dict(self) -> dict:
        return {"errors": [self.mensagem]} if self.como_lista else {"message": self.mensagem}


class NaoEncontrado(ErroAplicacao):
    status_code = 404


class AcessoNegado(ErroAplicacao):
    status_code = 403


class RegraNegocio(ErroAplicacao):
    """Violação de regra de negócio (ex.: item duplicado). Responde 422."""

    status_code = 422
