# ScoreView — módulo SIAP / GPA

## Fluxo

**ScoreView → Copiar para o Plugin GPA → Plugin GPA → Colar (SIAP)**

O ScoreView não acessa nem altera diretamente o SIAP.

## Lista de alunos

A preparação sempre usa **todos os alunos cadastrados na turma**, não apenas os alunos com resultado salvo. Isso preserva a quantidade de alunos apresentada pelo SIAP e evita que alunos sem prova desapareçam da lista.

## Cópia principal para o Plugin GPA

O botão **Copiar para o Plugin GPA** publica como `text/plain` uma linha por aluno:

```text
NOME DO ALUNO<TAB>1,3,7,10
OUTRO ALUNO<TAB>2,4,5
ALUNO SEM RESULTADO<TAB>
```

- primeira coluna: nome do aluno;
- segunda coluna: números das questões acertadas, separados por vírgula;
- aluno sem resultado: mantém a linha, mas sem questões;
- matrícula não é enviada;
- presença não é enviada;
- percentual não é enviado;
- cabeçalho não é enviado.

Quando o navegador suporta `ClipboardItem`, a mesma ação também publica uma grade TSV/HTML em formatos auxiliares, sem alterar o `text/plain` principal.

## Grade de conferência

O botão **Copiar grade (planilha)** copia a tabela completa com aluno, presença, questões e totais. Serve para conferência/diagnóstico e não é o formato principal do Plugin GPA.

## Fonte externa consultada

A documentação pública do PLUGIN GPA informa que a versão nova passou a organizar a cópia por nome do aluno e oferece ações separadas de copiar e colar. A política do plugin também descreve a coleta de marcações de checkboxes/textos e o uso de armazenamento local temporário.
