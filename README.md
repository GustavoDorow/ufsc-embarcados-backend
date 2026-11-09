# Acesso a quartos

Backend da Atividade 3, em Python, Flask e SQLite, com Swagger UI para testar a API.

## Executar com UV

Na raiz do projeto:

```bash
uv sync
uv run backend
```

Abra **http://localhost:5000/docs/** no navegador. Use **Try it out** e **Execute**
para enviar requisições. `Ctrl+C` encerra os cinco processos.

## Estrutura

```text
src/backend/
    __init__.py     Identificação do pacote Python
    iniciar.py      Inicia e encerra os cinco processos
    gateway.py      Entrada da API e Swagger UI (porta 5000)
    quartos.py      Cadastro de quartos e fechaduras (porta 5001)
    pessoas.py      Cadastro de hóspedes e funcionários (porta 5002)
    senhas.py       Senhas, validade e cadastro em lote (porta 5003)
    acessos.py      Verificação e histórico de entradas (porta 5004)
    comum.py        Banco, validações e respostas de erro
    openapi.yaml    Descrição da API para o Swagger UI
dados/             Bancos SQLite locais, ignorados pelo Git
pyproject.toml     Dependências e comando backend
uv.lock            Versões das dependências resolvidas pelo UV
```

Cada serviço abre apenas seu próprio banco. Consultas a outros serviços usam HTTP
com `requests`. O Gateway encaminha as chamadas externas. Para uma entrada, acessos
consulta quartos e senhas, grava a tentativa e devolve a autorização ou negação.

Os quatro bancos ficam em `dados/`, relativos à pasta de execução. Execute os
comandos na raiz para continuar usando os cadastros existentes. `DADOS_DIR` permite
usar outra pasta. `QUARTOS_URL`, `PESSOAS_URL`, `SENHAS_URL` e `ACESSOS_URL` permitem
configurar os endereços internos.

Para iniciar somente um componente, use por exemplo:

```bash
uv run python -m backend.quartos
```

## Demonstração

1. Cadastre um quarto e uma pessoa. Anote os IDs retornados.
2. Em `POST /senhas`, use esses IDs para cadastrar um código de seis dígitos.
   O exemplo do Swagger inclui um período válido próximo do horário atual.
3. Em `POST /acessos`, informe a fechadura do quarto e o código cadastrado.
4. Teste os exemplos de código incorreto e fechadura desconhecida.
5. Altere a validade com `PUT /senhas/{senha_id}` para testar datas futuras ou passadas.
6. Consulte `GET /acessos` para conferir as tentativas registradas.

Pessoas podem ser `hospede`, `limpeza` ou `manutencao`. Cada autorização vale para
uma pessoa em um quarto, com `inicio <= horário da tentativa < fim`. As datas devem
incluir fuso. O mesmo código não pode ter períodos sobrepostos no mesmo quarto.

Use `POST /senhas/lote` para receber `pessoa_id`, `quarto_ids` (uma lista sem
repetidos), `codigo`, `inicio` e `fim`. Isso concede acesso a vários quartos em um
POST. Se algum quarto não existir ou tiver conflito, nenhuma autorização é salva.

O Swagger carrega a descrição escrita em `openapi.yaml`. O Gateway a converte
para JSON em `/openapi.json`, atualizando os horários dos exemplos. As respostas
de erro comuns são definidas uma vez e referenciadas pelas operações.
