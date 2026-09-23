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


Atualização: scanner ajustado para cartão EduScanner 45Q com fallback de calibração de página inteira.
