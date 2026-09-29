# ScoreView — módulo SIAP / GPA

## Objetivo

Preparar os resultados já corrigidos no ScoreView para o fluxo de lançamento de avaliações objetivas do SIAP.

## O que o módulo faz

- Seleciona turma e prova/bloco.
- Lista todos os alunos da turma, inclusive quem ainda não possui resultado.
- Mostra presença/ausência da 1ª e 2ª chamada.
- Marca cada questão somente quando o aluno acertou.
- Mostra quantidade de acertos e percentual.
- Permite copiar a tabela como TSV para a área de transferência.
- Permite exportar a mesma estrutura como arquivo `.tsv`.

## O que ainda não é feito

A versão 10.0 não injeta dados diretamente no SIAP nem controla a extensão PLUGIN GPA. A interface pública da extensão descreve uma automação própria entre a plataforma GPA e o SIAP, mas não fornece um contrato público de integração do ScoreView.

A próxima etapa pode ser uma extensão própria do ScoreView ou um adaptador compatível, depois que o fluxo real do PLUGIN GPA/SIAP for validado no navegador utilizado pela escola.

## Estrutura do TSV

```text
ALUNO | MATRÍCULA | STATUS | PRESENTE 1ª | AUSENTE 1ª | PRESENTE 2ª | AUSENTE 2ª | 1 | ... | N | QTDE ACERTOS | % ACERTOS
```

Para as questões, `1` significa acerto e célula vazia significa que não deve ser marcada como acerto.

## Segurança

O módulo usa somente os resultados já armazenados no ScoreView e não altera o scanner.
