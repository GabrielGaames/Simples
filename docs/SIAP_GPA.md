# ScoreView — módulo SIAP / GPA

## Fluxo desta versão

O ScoreView prepara os dados e o professor faz a etapa final manualmente no navegador:

**ScoreView → Copiar para GPA → Plugin GPA → SIAP**

O ScoreView não acessa nem altera diretamente o SIAP.

## Formato da cópia para o GPA

A cópia para a área de transferência contém **somente as linhas dos alunos, sem cabeçalho**, na ordem do número da chamada/ID:

```text
ALUNO | 1ª Pres. | 1ª Aus. | 2ª Pres. | 2ª Aus. | 1 | ... | N | Qtde Acertos | % Acertos
```

O primeiro campo segue o padrão visual da lista do SIAP:

```text
1 - NOME DO ALUNO
2 - OUTRO ALUNO
3 - OUTRO ALUNO
```

Não são enviados para a cópia:

- matrícula;
- status escolar;
- ID interno do banco;
- cabeçalho da tabela.

Para cada questão, `1` significa que o aluno acertou; célula vazia significa que a questão não deve ser marcada como acerto.

## Compatibilidade e validação

- A ordenação é numérica pelo ID da chamada: `1, 2, 3 ... 10, 11 ...`.
- IDs ausentes bloqueiam a cópia.
- IDs duplicados bloqueiam a cópia.
- O ID `1.0` recebido de uma célula numérica do Excel é normalizado para `1`.
- A tela mantém a conferência visual antes da cópia.

## Observação sobre quantidade de alunos

O SIAP/Plugin GPA precisa trabalhar com a mesma lista de alunos. Por isso o ScoreView mantém uma linha para cada aluno cadastrado na turma, mesmo quando ele ainda não possui resultado da prova. A quantidade de linhas é mostrada na tela para conferência antes da cópia.
