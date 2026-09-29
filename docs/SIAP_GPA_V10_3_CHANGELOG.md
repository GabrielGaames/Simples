# ScoreView 10.3 — compatibilidade SIAP/GPA

- Mantida a lista completa da turma na preparação do lançamento, inclusive alunos sem resultado.
- A cópia principal para o Plugin GPA passou a usar o nome do aluno como chave e somente a lista de questões acertadas, sem matrícula, presença, percentual ou cabeçalho.
- O número da chamada continua disponível na conferência visual e é usado para validar/ordenar a turma, mas não é enviado como prefixo no payload principal do plugin.
- Adicionada uma cópia secundária em formato de grade TSV/HTML para conferência em planilhas.
- O botão principal continua sendo somente “Copiar para o Plugin GPA”; a colagem no SIAP permanece responsabilidade da extensão.
- Scanner, correção, revisão manual e relatórios existentes não foram alterados.

## Observação
A documentação pública do PLUGIN GPA informa que a versão nova organiza a cópia por nome do aluno e oferece as ações Copiar/Colar. O formato interno exato do payload não é publicado na documentação disponível; por isso o ScoreView usa um payload compacto por nome + números das questões acertadas e mantém uma grade TSV/HTML como fallback de diagnóstico.
