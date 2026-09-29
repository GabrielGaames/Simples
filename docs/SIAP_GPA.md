# ScoreView — integração SIAP / PLUGIN GPA

A integração usa o formato real da extensão PLUGIN GPA 1.0 enviada para análise. O ScoreView não tenta controlar o SIAP diretamente.

## Como funciona

1. O ScoreView prepara a turma inteira.
2. Uma tabela de compatibilidade é mantida no DOM com `tr.linhaAluno`.
3. Cada linha possui `data-number` com o número da chamada.
4. A ordem dos checkboxes é: 1ª presença, 1ª ausência, 2ª presença, 2ª ausência e depois Q1...Q45.
5. O professor usa **PLUGIN GPA → Copiar (GPA)** na própria página do ScoreView.
6. A extensão guarda os dados no armazenamento local dela.
7. O professor abre o SIAP e usa **PLUGIN GPA → Colar (SIAP)**.

## Por que não usamos Ctrl+C

O código da extensão não lê o clipboard do navegador. O botão **Copiar (GPA)** executa um script na página ativa, coleta os elementos `tr.linhaAluno` e salva o resultado em `chrome.storage.local`. Portanto, copiar texto/TSV do ScoreView não era suficiente para integrar com a extensão oficial.

## Alunos sem resultado

Todos os alunos cadastrados na turma permanecem no modo compatível. Quando não há resultado, as questões ficam desmarcadas. Isso preserva a quantidade de linhas do SIAP.
