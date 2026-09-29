# ScoreView 10.6 — frequência ScoreView → SIAP

- O payload `#scoreview-gpa-data` agora inclui presente/ausente da 1ª e 2ª chamada.
- A frequência registrada no ScoreView passa a ser a fonte de verdade para o lançamento no SIAP.
- O plugin deve ativar a presença antes de marcar as questões, pois o SIAP inicia os alunos como ausentes.
- Alunos sem resultado continuam tendo a frequência lançada normalmente.
