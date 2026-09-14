# EDUSCANNER Simples

Versão mínima focada exclusivamente em ler o cartão físico EDUSCANNER de 40 questões por foto de celular.

## O que esta versão faz

- Usa a câmera nativa do celular.
- Lê 40 questões em duas colunas de 20.
- Aceita marcações vermelhas, azuis e pretas.
- Duas ou mais marcações na mesma questão = `ANULADA` e, se houver gabarito oficial, conta como errada.
- Questão sem marcação = em branco e errada.
- Recusa fotos muito inclinadas ou muito distantes em vez de tentar adivinhar.
- Gabarito oficial é opcional e pode ser digitado na própria tela para calcular acertos, erros e nota.

## Rodar localmente

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000`.

## Render

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Não há banco de dados, login, OAuth nem variáveis secretas nesta versão.

## Regra de uso

A prioridade desta versão é confiabilidade. Se o cartão estiver muito pequeno na foto ou inclinado demais, a API retorna uma mensagem pedindo nova foto.
