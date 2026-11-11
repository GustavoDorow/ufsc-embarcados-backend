
from datetime import datetime, timezone

import requests
from flask import jsonify

from .comum import abrir_banco, criar_aplicacao, endereco_servico, ler_campos_json, validar_texto

app = criar_aplicacao(__name__)
QUARTOS_URL = endereco_servico("quartos", 5001)
SENHAS_URL = endereco_servico("senhas", 5003)
with abrir_banco("acessos") as banco:
    banco.execute("""
        CREATE TABLE IF NOT EXISTS acessos (
            id INTEGER PRIMARY KEY,
            fechadura_id TEXT NOT NULL,
            quarto_id INTEGER,
            pessoa_id INTEGER,
            instante TEXT NOT NULL,
            autorizado INTEGER NOT NULL,
            motivo TEXT NOT NULL
        )
    """)


@app.post("/acessos")
def verificar_acesso():
    dados = ler_campos_json("fechadura_id", "codigo")
    fechadura_id = validar_texto(dados["fechadura_id"], "fechadura_id")
    codigo = dados["codigo"]
    if not isinstance(codigo, str):
        raise ValueError("Informe o código como texto.")
    instante = datetime.now(timezone.utc).isoformat()
    quarto_id = None
    pessoa_id = None
    autorizado = False
    motivo = "codigo_invalido"
    status = 200

    if len(codigo) == 6 and codigo.isascii() and codigo.isdigit():
        try:
            resposta = requests.get(
                f"{QUARTOS_URL}/quartos", params={"fechadura_id": fechadura_id}, timeout=3
            )
            resposta.raise_for_status()
            quartos = resposta.json()
            motivo = "fechadura_desconhecida"
            if quartos:
                quarto_id = quartos[0]["id"]
                resposta = requests.post(
                    f"{SENHAS_URL}/senhas/validar",
                    json={"quarto_id": quarto_id, "codigo": codigo, "instante": instante},
                    timeout=3,
                )
                resposta.raise_for_status()
                resultado = resposta.json()
                autorizado = resultado["autorizado"]
                motivo = resultado["motivo"]
                pessoa_id = resultado["pessoa_id"]
        except requests.RequestException:
            motivo = "servico_indisponivel"
            status = 503

    with abrir_banco("acessos") as banco:
        cursor = banco.execute(
            """INSERT INTO acessos
               (fechadura_id, quarto_id, pessoa_id, instante, autorizado, motivo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fechadura_id, quarto_id, pessoa_id, instante, int(autorizado), motivo),
        )
        acesso_id = cursor.lastrowid
    return jsonify(id=acesso_id, autorizado=autorizado, motivo=motivo,
                   quarto_id=quarto_id, pessoa_id=pessoa_id, instante=instante), status


@app.get("/acessos")
def listar_acessos():
    with abrir_banco("acessos") as banco:
        registros = banco.execute("SELECT * FROM acessos ORDER BY id").fetchall()
    acessos = []
    for registro in registros:
        acesso = dict(registro)
        acesso["autorizado"] = bool(acesso["autorizado"])
        acessos.append(acesso)
    return jsonify(acessos)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5004)
