# ScoreView 10.6

Versão atual do EduScanner com scanner de 45 questões, turmas, alunos, resultados e relatórios.

## Funcionalidades
- Scanner do cartão físico CEPI-JBR de 45 questões
- Provas de 20, 30 ou 45 questões; posições excedentes são ignoradas
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

## Scanner V9 — 45Q mobile

The scanner is calibrated for the PUC Goiás / ENEM PARA TODOS 45-question response card. V9 detects the three printed response blocks (01–15, 16–30 and 31–45), rectifies each block independently, and samples only the 225 answer cells. The header and the “COMO PREENCHER” examples are outside the reading regions.

The result includes a confidence value per detected answer and a list of low-confidence questions so the teacher can review before saving.

## Atualização v6.1 — Relatório por turma e diagnóstico
- Relatórios filtrados por turma e por prova/bloco.
- PDF consolidado da turma.
- Diagnóstico automático com média, aproveitamento, distribuição dos resultados e médias de acertos/erros/brancos/anuladas.
- Quando uma única prova é selecionada, análise por questão com percentual de acertos, brancos e anuladas.
- Identificação de pontos de maior domínio e pontos para reforço para apoiar o feedback coletivo.

## Atualização v9 — novo cartão CEPI-JBR (45 questões)
- Scanner recalibrado para o novo modelo de cartão-resposta usado pela escola.
- A leitura agora localiza diretamente as três grades 01–15, 16–30 e 31–45 na fotografia.
- Cada grade é corrigida de perspectiva separadamente antes da leitura.
- A posição das bolhas foi recalibrada para o novo layout, reduzindo deslocamentos de leitura.
- A análise considera o centro da bolha e uma referência de iluminação local, ajudando com sombras e diferenças de exposição entre celulares.
- Marcação azul, preta e vermelha continua sendo aceita.
- Duas marcações na mesma questão continuam sendo classificadas como `MULT` / anulada.
- O mecanismo de revisão manual já existente permanece disponível para questões sinalizadas com baixa confiança.
- Não é necessário alterar o fluxo de uso no celular: o professor continua fotografando o cartão pelo próprio telefone.

## Versão 9.2 — sincronização automática
- Atualização imediata das listas após importação, criação/exclusão e alterações de resultados.
- Recarregamento sem cache para endpoints GET.
- Sincronização ao voltar para a aba/janela e a cada 60 segundos enquanto o usuário estiver logado.
- Preserva turma, aluno e prova selecionados durante a sincronização.


## Versão 10.0 — módulo SIAP / GPA
- Nova aba **SIAP / GPA** para preparar lançamentos a partir dos resultados já corrigidos.
- Seleção de turma e prova/bloco.
- Pré-visualização com aluno, matrícula, presença/ausência em 1ª e 2ª chamada, Q1–Q45, quantidade de acertos e percentual.
- Cada questão é marcada apenas quando o aluno realmente acertou.
- Alunos sem resultado permanecem visíveis para conferência e não recebem acertos automaticamente.
- Botão para copiar a tabela em formato tabular (TSV) para a área de transferência.
- Exportação do mesmo conjunto de dados em TSV para conferência/uso externo.
- O módulo não altera a lógica do scanner.
- A integração com o PLUGIN GPA usa o payload estruturado do ScoreView e a extensão compatível. A frequência de 1ª/2ª chamada é transferida do ScoreView para o SIAP, que inicia os alunos como ausentes.
- O plugin marca somente as questões corretas e mantém alunos sem resultado sem questões marcadas.

## Versão 10.6 — SIAP/GPA
- Frequência do ScoreView passa a ser enviada no payload estruturado para o plugin.
- O SIAP inicia todos como ausentes; a extensão primeiro ajusta Pres./Aus. das duas chamadas conforme o ScoreView e só depois lança as questões.
- Alunos presentes sem resultado continuam com a presença marcada, mas sem questões.

## Versão 10.3 — SIAP/GPA
- Preparação do lançamento usa todos os alunos da turma, inclusive sem resultado.
- Cópia principal para o Plugin GPA: nome do aluno + números das questões acertadas.
- Matrícula, presença, percentual e cabeçalho não entram no payload principal.
- Cópia secundária em grade TSV/HTML para conferência em planilha.
- Colagem no SIAP continua sendo feita pelo Plugin GPA.

## 10.7 — SIAP/GPA por disciplina no Bloco 06

Na tela SIAP / GPA, o Bloco 06 possui recorte por disciplina:
- Biologia: Q01–Q15;
- Sociologia: Q16–Q23;
- Filosofia: Q24–Q30.

O recorte é renumerado localmente para o lançamento da avaliação correspondente no SIAP.
