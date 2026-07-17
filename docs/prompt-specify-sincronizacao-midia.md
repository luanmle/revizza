# Prompt para `/speckit-specify`: sincronização de mídia no add-on Anki

Copie o conteúdo abaixo como argumento do comando `/speckit-specify`.

```text
Implemente suporte robusto à sincronização de imagens entre o add-on Anki
ankihub_br e a plataforma Revizza, corrigindo o fluxo de mídia já existente.

Antes de escrever a especificação:

1. Inspecione o repositório inteiro nas áreas relacionadas:
   - addon/ankihub_br/main/media.py
   - addon/ankihub_br/main/sync.py
   - addon/ankihub_br/main/publish.py
   - addon/ankihub_br/ankihub_br_client/client.py
   - backend/apps/sync/views.py
   - backend/apps/sync/media.py
   - backend/apps/notes/models.py
   - contratos e testes existentes em specs/001-ankihub-brasil-mvp e addon/tests/backend/tests

2. Preserve os princípios existentes:
   - sincronização oficial unidirecional: web → Anki;
   - publicação inicial create-only;
   - mídia armazenada no Supabase Storage, acessada somente por URLs assinadas;
   - deduplicação por SHA-256;
   - aplicação idempotente e retomável;
   - campos, tags e scheduling locais protegidos conforme os contratos atuais;
   - nenhuma alteração direta no schema interno da coleção do Anki;
   - compatibilidade com a versão de Anki declarada no manifest/config do add-on.

3. Verifique na fonte instalada do Anki ou na documentação oficial todos os
   símbolos usados para mídia e operações em background. Não invente nomes de
   métodos, hooks ou assinaturas. Se a API variar entre versões suportadas,
   isole a diferença em um adaptador pequeno.

Objetivo do recurso

Permitir que imagens referenciadas nos campos HTML das notas sejam publicadas,
baixadas e instaladas corretamente na coleção Anki, sem travar a interface,
sem sobrescrever mídia não relacionada e sem aceitar arquivos inválidos.

Problemas conhecidos a tratar

- O download atual grava diretamente com Path.write_bytes() na pasta de mídia.
- O nome recebido do servidor pode causar path traversal ou colisão com outro
  arquivo local de mesmo nome.
- O backup da coleção não reverte arquivos de mídia parcialmente gravados.
- O sync atual pode manter a coleção ocupada durante downloads HTTP demorados.
- O payload de mídia contém hash e filename, mas precisa de validação explícita
  antes de alterar a coleção.
- O publish pode concluir a transação dos metadados antes de todos os uploads
  de mídia terminarem; a especificação deve definir como evitar que uma mídia
  ainda indisponível seja servida como pronta.

Escopo funcional obrigatório

1. Publicação
   - identificar somente arquivos efetivamente referenciados nos campos das
     notas do deck;
   - calcular SHA-256 do conteúdo;
   - deduplicar o mesmo conteúdo no payload;
   - preservar a referência HTML válida no campo da nota;
   - fazer upload direto no Storage usando URL assinada;
   - tornar a publicação segura para repetição ou interrupção, sem expor
     credenciais do backend.

2. Sincronização
   - receber um manifesto de mídia associado ao delta/full;
   - baixar somente arquivos ausentes ou cujo hash local divergir;
   - validar basename, extensão/nome, tamanho e SHA-256;
   - gravar usando a API pública de mídia do Anki;
   - evitar colisões entre arquivos de decks diferentes, preferindo nomes
     determinísticos derivados do hash quando isso exigir atualização segura
     das referências HTML;
   - não deixar arquivo parcial com o nome final;
   - tolerar reexecução do mesmo delta sem duplicar ou corromper mídia.

3. Responsividade e falhas
   - executar HTTP e processamento pesado fora da thread da interface;
   - separar, quando compatível com as APIs verificadas, a etapa de rede da
     etapa que altera a coleção;
   - manter timeout, retry somente para erros transitórios, limite de tamanho,
     limite de concorrência e cancelamento/progresso quando aplicável;
   - se uma mídia falhar, não confirmar o cursor do sync como se tudo tivesse
     sido aplicado;
   - permitir retry posterior sem baixar novamente o que já foi validado;
   - limpar arquivos temporários e documentar o tratamento de órfãos.

4. API/backend
   - manter o endpoint atual se ele for suficiente para o primeiro incremento;
   - propor endpoint batch para resolver vários hashes somente se a análise
     demonstrar ganho real e sem ampliar desnecessariamente o escopo;
   - validar autorização por assinatura do deck;
   - não retornar URL de Storage para usuário sem acesso;
   - impedir que mídia publicada como metadado fique disponível antes de o
     upload estar confirmado, ou definir explicitamente um estado pendente;
   - preservar compatibilidade do contrato existente durante a migração.

Critérios de aceite

- Uma nota com imagem aparece corretamente no Anki após publicação e após
  sincronização em outro perfil.
- Dois decks com arquivos de mesmo nome e conteúdos diferentes não sobrescrevem
  a mídia um do outro.
- Arquivo com hash incorreto, nome inseguro, tamanho acima do limite ou resposta
  truncada é rejeitado e não altera a coleção.
- Repetir o sync não baixa nem grava novamente mídia já válida.
- Interromper o processo não deixa arquivo final corrompido e o próximo sync
  consegue concluir.
- Timeout, offline, URL expirada, 401/403, 404 e 429 geram erro acionável e
  permitem retry seguro.
- A interface do Anki continua responsiva durante download de imagens grandes.
- O scheduling dos cards e os campos/tags protegidos permanecem inalterados.
- A publicação não envia token Bearer para URLs assinadas do Storage.
- O comportamento é coberto por testes unitários/contratuais e por uma matriz
  de testes manuais em um Anki real.

Fora de escopo

- sincronização bidirecional de imagens;
- edição ou moderação de imagens na plataforma;
- thumbnails, conversão ou compressão automática;
- áudio e vídeo, salvo se a implementação atual já os suportar sem ampliar o
  contrato;
- limpeza agressiva de mídia não referenciada na coleção;
- migração ampla de arquitetura não necessária para este recurso.

Entregue uma especificação completa com:

- cenários de usuário prioritários;
- requisitos funcionais numerados e testáveis;
- regras de segurança e integridade;
- entidades e mudanças de contrato necessárias;
- critérios de sucesso mensuráveis;
- casos de erro e interrupção;
- premissas e riscos;
- compatibilidade Anki verificada;
- plano de testes automatizados e testes manuais;
- limites claros do primeiro incremento.

Não implemente código nesta etapa. Gere apenas a especificação do recurso e
os artefatos padrão do Spec Kit. Marque como [NEEDS CLARIFICATION] somente uma
decisão que realmente impeça definir o escopo; no máximo três marcadores.
```

Depois de gerar a especificação, execute `/speckit-plan`, `/speckit-tasks` e,
somente após revisar os contratos, `/speckit-implement`.
