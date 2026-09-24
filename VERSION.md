# EduScanner — Nova versão de interface

## Alterações
- Novo frontend **Noir Education** com visual profissional e responsivo.
- Modo escuro e claro com preferência salva no navegador.
- Correção dos campos de login, inputs, selects, cards e tabelas no modo escuro.
- Navegação desktop com sidebar e navegação mobile inferior.
- Menu mobile retrátil com controles adequados para toque.
- Layout adaptado para telas pequenas, incluindo referência de 360x800 px.
- Botões e campos com áreas de toque maiores.
- Sem scroll horizontal desnecessário na interface principal.
- Scanner e sua lógica de processamento preservados.
- Backend/API preservados nesta versão.

## Verificações
- `python -m py_compile` concluído.
- JavaScript do frontend validado com `node --check`.
- `/health` retornou HTTP 200.
- `/` retornou HTTP 200.
- `app/scanner.py` permaneceu byte a byte igual ao ZIP recebido.
