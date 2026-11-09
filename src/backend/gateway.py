"""Entrada REST pública: encaminha requisições sem acessar bancos de dados."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml
from flask import Response, abort, jsonify, redirect, request
from flask_swagger_ui import get_swaggerui_blueprint

from .comum import criar_aplicacao, endereco_servico

app = criar_aplicacao(__name__)
app.register_blueprint(get_swaggerui_blueprint(
    "/docs", "/openapi.json",
    config={"app_name": "Acesso a quartos", "validatorUrl": None, "defaultModelsExpandDepth": -1},
))
SERVICOS = {
    "quartos": endereco_servico("quartos", 5001),
    "pessoas": endereco_servico("pessoas", 5002),
    "senhas": endereco_servico("senhas", 5003),
    "acessos": endereco_servico("acessos", 5004),
}


@app.get("/")
def abrir_documentacao():
    """Abre a interface Swagger UI ao acessar a raiz do Gateway."""
    return redirect("/docs/")


@app.get("/openapi.json")
def consultar_documentacao():
    """Documenta as rotas públicas e fornece exemplos de validade próximos de agora."""
    especificacao = yaml.safe_load(Path(__file__).with_name("openapi.yaml").read_text(encoding="utf-8"))
    agora = datetime.now(timezone.utc)
    for esquema in ("SenhaCadastro", "SenhasLoteCadastro"):
        exemplo = especificacao["components"]["schemas"][esquema]["example"]
        exemplo["inicio"] = (agora - timedelta(hours=1)).isoformat()
        exemplo["fim"] = (agora + timedelta(hours=1)).isoformat()
    return jsonify(especificacao)


@app.route("/<path:caminho>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def encaminhar_requisicao(caminho):
    """Preserva corpo, consulta e status; validação de senha é uma rota interna."""
    servico = caminho.split("/")[0]
    if servico not in SERVICOS or caminho.rstrip("/") == "senhas/validar":
        abort(404, description="Rota não encontrada no Gateway.")
    resposta = requests.request(
        method=request.method,
        url=f"{SERVICOS[servico]}/{caminho}",
        params=request.args,
        data=request.get_data(),
        headers={"Content-Type": request.headers.get("Content-Type", "application/json")},
        timeout=15,
        allow_redirects=False,
    )
    return Response(resposta.content, status=resposta.status_code,
                    content_type=resposta.headers.get("Content-Type", "application/json"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
