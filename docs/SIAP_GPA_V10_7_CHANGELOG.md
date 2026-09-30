# ScoreView 10.7 — recorte de questões por disciplina no Bloco 06

- Adicionado recorte de questões na tela **SIAP / GPA** quando a prova/bloco selecionado é o **Bloco 06**.
- **Biologia:** questões globais 01–15 → enviadas ao SIAP como questões locais 01–15 (15 questões).
- **Sociologia:** questões globais 16–23 → enviadas ao SIAP como questões locais 01–08 (8 questões).
- **Filosofia:** questões globais 24–30 → enviadas ao SIAP como questões locais 01–07 (7 questões).
- O relatório visual da tela GPA passa a mostrar somente as questões da disciplina selecionada.
- O payload estruturado usado pelo Plugin GPA também recebe somente as questões do recorte, com renumeração local para o SIAP.
- Frequência e identificação por número da chamada continuam sendo enviados normalmente.
- Para outros blocos, enquanto não houver um mapa específico cadastrado, o comportamento anterior (todas as questões) é mantido.
