# ScoreView 10.5 — integração SIAP / Plugin GPA

- Adiciona payload JSON estruturado `#scoreview-gpa-data` para o Plugin GPA.
- Mantém a tabela `tr.linhaAluno` como fallback de compatibilidade.
- A extensão obtém os números das questões acertadas diretamente do payload, evitando perda de marcações quando o estado dos checkboxes ocultos não é confiável.
- A frequência do ScoreView é mantida como parte do payload e passa a ser aplicada no SIAP a partir da versão 10.6/Plugin GPA 1.1.4.
