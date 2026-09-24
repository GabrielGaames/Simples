# EDUSCANNER

Versão simples com o scanner de 40 questões preservado e módulos de turmas, alunos e resultados.

## Funcionalidades
- Scanner do cartão físico de 40 questões (motor preservado)
- Provas de 20, 30 ou 40 questões; posições excedentes são ignoradas
- Importação de alunos por Excel (.xlsx/.xlsm)
- Colunas aceitas: `Nome do aluno`, `Turma`, `Matrícula`
- Turmas criadas automaticamente na importação
- Matrícula é única; uma nova importação atualiza nome/turma do aluno existente
- Seleção Turma -> Aluno antes de salvar
- Resultado salvo com respostas, gabarito, acertos, erros, anuladas, brancos e nota
- Relatório básico por turma

## Banco
Localmente, sem variável de ambiente, usa SQLite (`eduscanner.db`).
No Render, use PostgreSQL e configure `DATABASE_URL` com a **Internal Database URL**.

## Render
Build command:
`pip install -r requirements.txt`

Start command:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Environment Variable:
`DATABASE_URL=<Internal Database URL do PostgreSQL>`

## Planilha
A primeira linha deve conter as colunas:

| Nome do aluno | Turma | Matrícula |
|---|---|---|
| Ana Silva | 7º A | 12345 |
| João Souza | 7º A | 12346 |

## Rodar local
`pip install -r requirements.txt`
`uvicorn app.main:app --reload`

## Scanner V4 — 45Q mobile

The scanner is calibrated for the PUC Goiás / ENEM PARA TODOS 45-question response card. V4 detects the three printed response blocks (01–15, 16–30 and 31–45), rectifies each block independently, and samples only the 225 answer cells. The header and the “COMO PREENCHER” examples are outside the reading regions.

The result includes a confidence value per detected answer and a list of low-confidence questions so the teacher can review before saving.
