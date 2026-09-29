# ScoreView 10.4 — integração real com o PLUGIN GPA

## Correção principal

Após analisar o código da extensão Chrome PLUGIN GPA 1.0 enviada pelo usuário, o fluxo foi alterado para usar exatamente a estrutura DOM que a extensão coleta.

O plugin procura `tr.linhaAluno`, lê `data-number` como número da chamada e coleta todos os `input[type="checkbox"]` em ordem. Os quatro primeiros representam as marcações de chamada e os seguintes representam as questões. A soma considera os checkboxes a partir do índice 4.

## ScoreView

- Mantém todos os alunos da turma, inclusive sem resultado.
- Gera uma tabela de compatibilidade oculta com `tr.linhaAluno`.
- Usa `data-number` com o ID/número da chamada.
- Cria 4 checkboxes de chamada + um checkbox por questão.
- Marca apenas as questões efetivamente acertadas.
- Não usa matrícula na integração.
- O botão do ScoreView agora prepara/valida a página; não tenta escrever no clipboard para o plugin.

## Extensão

Foi gerada uma cópia do PLUGIN GPA 1.0 com permissão adicional para os endereços atuais do ScoreView no Render. O código de coleta/colagem do plugin foi preservado; apenas a permissão de acesso ao ScoreView e os textos de identificação foram ajustados.

## Fluxo final

ScoreView → Preparar → botão direito → PLUGIN GPA → Copiar (GPA) → SIAP → PLUGIN GPA → Colar (SIAP).
