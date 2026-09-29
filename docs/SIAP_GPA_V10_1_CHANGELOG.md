# ScoreView 10.1 — ajuste de compatibilidade SIAP/GPA

## Alterações

- A lista SIAP/GPA agora é ordenada numericamente pelo ID/número da chamada: 1, 2, 3 ... 10, 11...
- O primeiro campo da cópia usa exatamente o padrão visual da lista: `ID - NOME DO ALUNO`.
- A cópia para o GPA não inclui cabeçalho.
- A cópia não inclui matrícula nem status escolar.
- Permanecem somente: aluno, 1ª chamada (pres./aus.), 2ª chamada (pres./aus.), questões, quantidade de acertos e percentual.
- IDs de chamada ausentes ou duplicados bloqueiam a cópia para evitar desalinhamento com o SIAP.
- IDs vindos do Excel como `1.0` são normalizados para `1`.
- A tela informa explicitamente que a ordem usada é a ordem de chamada.

## Fluxo

`ScoreView → Copiar para GPA → Plugin GPA → SIAP`

O ScoreView não acessa nem altera diretamente o SIAP.
