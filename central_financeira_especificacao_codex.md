# Central Financeira Pessoal — especificação inicial para o Codex

> **Estado:** planejamento; nenhuma implementação foi validada.  
> **Objetivo imediato:** prova de conceito da integração Meu Pluggy/Nubank.  
> **Público inicial:** uso pessoal.  
> **Restrição:** sem serviços pagos obrigatórios.

## 1. Visão do produto

Construir uma aplicação web para consolidar informações financeiras pessoais obtidas, preferencialmente, por sincronização bancária automática; acompanhar saldos, movimentações e compromissos; projetar saldo disponível; e simular decisões financeiras. Posteriormente incorporar análise de notas fiscais de supermercado e histórico de preços (ideia 88), com identificação e normalização de produtos (ideia 103).

**Problemas centrais:**
1. Saber quanto dinheiro existe e quanto está comprometido, sem lançar manualmente cada transação.
2. Entender quanto estará disponível após vencimentos e receitas futuras.
3. Comparar alternativas como consórcio, financiamento, investimento e compra à vista/parcelada/adiada com premissas explícitas.
4. Futuramente, entender o preço efetivamente pago por produtos de supermercado a partir de notas fiscais.

**Diferencial pretendido:** integração de dados bancários reais, obrigações futuras e simulações transparentes; não apenas um catálogo de despesas.

## 2. Decisões e premissas

| Item | Estado |
|---|---|
| Projeto principal | Central Financeira Pessoal — escolhido |
| Escopo inicial | Uso pessoal, execução local |
| Custos | Evitar APIs, hospedagem e outros serviços pagos obrigatórios |
| Fonte prioritária | Sincronização bancária automática, em vez de importação manual recorrente |
| Primeira instituição | Nubank, via Meu Pluggy (a validar em código) |
| Plataforma | Web inicialmente |
| Backend | Python + FastAPI — escolhido; usuário já tem experiência com ambos |
| Frontend | React + TypeScript — sugestão técnica |
| Persistência | PostgreSQL — confirmado |
| Ambiente local | Docker Compose para o PostgreSQL; backend e frontend executados diretamente na máquina — confirmado |
| Gerenciamento Python | uv para dependências e ambiente virtual — confirmado |
| Arquitetura | Monólito modular, com conector bancário isolado |
| Primeiro entregável | Prova de conceito de leitura de dados bancários |
| Funcionalidade posterior | Notas fiscais (88) e identificação de produtos (103) |

**Direção confirmada:** seguir com Pluggy como integração inicial. Alternativas serão avaliadas somente se surgir uma limitação concreta; não é necessário definir uma fonte alternativa agora. A validação técnica da Fase 0 continua necessária.

**Primeiro objetivo utilizável confirmado:** contas, saldos, movimentações e estado da sincronização (Fase 2). Obrigações e projeções entram no incremento seguinte (Fase 3).

**Estado real da integração:** o usuário **já conectou o Nubank ao Meu Pluggy** e **já criou Client ID/Client Secret**. Ainda **não foram validados** autenticação programática, acesso às conexões, contas, saldos, transações, cartões, limites, frequência de atualização ou condições de gratuidade. **Não pressupor que a criação de chaves garante acesso a todos os endpoints.**

## 3. Escopo funcional por módulo

### A. Visão financeira consolidada (núcleo do MVP)
- Contas/instituições conectadas e seus saldos.
- Histórico de transações com data, descrição, valor, origem e conta.
- Receitas, despesas e transferências (transferência interna não é receita nem despesa nova).
- Dados de cartão/faturas/compras **somente se disponibilizados pela integração**.
- Filtros por período, conta, tipo e eventualmente categoria.
- Data/hora e estado da última sincronização; identificar dados potencialmente desatualizados.
- Evolução histórica de saldos e gastos, conforme disponibilidade de dados.
- Evitar duplicação entre registros sincronizados e, futuramente, notas fiscais.

### B. Contas futuras e projeções
- Obrigações com valor, vencimento, estado e recorrência.
- Faturas e parcelas, evitando contabilizar a mesma obrigação duas vezes.
- Receitas futuras estimadas, diferenciadas de recebimentos confirmados.
- Saldo projetado por data/período: saldo inicial + entradas previstas - saídas previstas.
- Identificar premissas, incerteza e a origem dos valores.
- Regras para transferências internas, parcelamentos e despesas recorrentes.

### C. Simulador de decisões financeiras
- Consórcio vs. financiamento vs. juntar/investir dinheiro.
- Comparar custos totais, prazo, taxas, reajustes, parcelas e custo de oportunidade.
- Para consórcio, representar a **incerteza da contemplação**, não assumir data certa.
- Comprar agora à vista, parcelar ou adiar a compra.
- Cenários hipotéticos independentes dos dados reais, com opção de utilizar saldo e compromissos atuais como ponto de partida.
- Resultados reproduzíveis, fórmulas e hipóteses visíveis; não recomendar investimentos como certeza.

### D. Comparação de investimentos (posterior)
- Rentabilidade nominal, líquida e real (descontada a inflação).
- Tributos aplicáveis, liquidez, prazo, risco e cenários de taxas.
- Comparação por horizonte temporal e aporte; apresentar limitações das estimativas.
- **Fora de escopo:** executar operações, comprar ativos ou prometer rentabilidade.

### E. Notas fiscais e supermercado — futuro (ideias 88 + 103)
- Importação de NFC-e via QR Code/link, XML ou outro formato legalmente acessível.
- Extrair estabelecimento, data, produtos, quantidades, unidade e preços.
- Normalizar descrições abreviadas; reconhecer quando dois registros são do mesmo produto e quando são apenas similares.
- Diferenciar marca, peso, volume, tamanho, embalagem e unidade de medida.
- Histórico de preço efetivamente pago por produto e supermercado.
- Comparar preço unitário, evolução de preços e custo de uma cesta de compras.
- Relacionar nota fiscal a transação bancária sem duplicar despesas.
- **Risco:** páginas de consulta e formatos variam por estado; validar regras de acesso, sem contornar CAPTCHA ou proteções. Não iniciar este módulo antes do núcleo financeiro.

## 4. Integração Meu Pluggy — investigação obrigatória

### Por que este caminho
- Não há API pública geral do Nubank para consulta de extratos pessoais disponível como solução simples para este projeto.
- Bibliotecas não oficiais podem ser frágeis e criar riscos de autenticação.
- APIs comerciais de agregação financeira podem exigir pagamento.
- Meu Pluggy foi escolhido como **hipótese de caminho gratuito para uso pessoal**, sujeito a regras, escopo e limites atuais do serviço.

### Prova de conceito (primeiro trabalho do Codex)
1. Consultar **documentação oficial atual** do Meu Pluggy/Pluggy para autenticação, permissões e endpoints autorizados. Não inventar URLs, payloads ou disponibilidade de recursos.
2. Criar projeto mínimo isolado em Python (`poc-pluggy/`), sem frontend e sem banco; FastAPI não é necessário nesta etapa de consulta à integração.
3. Ler credenciais por variáveis de ambiente (por exemplo, `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET`), **nunca solicitar que sejam coladas em código, commits, logs ou nesta especificação**.
4. Autenticar conforme documentação e registrar somente estado e metadados não sensíveis.
5. Listar conexões/itens acessíveis e identificar a conexão autorizada do Nubank.
6. Testar, separadamente, consulta de contas, saldos, transações e dados de cartão/faturas, **quando suportados**.
7. Documentar permissões, campos disponíveis, paginação, histórico, limites, frequência de sincronização, renovação de consentimento, restrições de uso e custo efetivo.
8. Gerar `poc-pluggy/RESULTADOS.md` com tabela: recurso / endpoint oficial / disponível? / campos úteis / limitações / evidência do teste (sem dados pessoais).
9. Se a API pessoal não oferecer acesso suficiente, **interromper e relatar a limitação**, propondo alternativas seguras e gratuitas antes de construir a aplicação.

**Critério de sucesso da Fase 0:** autenticação programática autorizada e leitura confirmada dos dados essenciais de conta, saldo e transações sem custo obrigatório. Dados de cartão são desejáveis, mas devem ser verificados separadamente. Uma conexão bem-sucedida no Meu Pluggy, por si só, não cumpre o critério.

## 5. Arquitetura sugerida (após validação da API)

```text
central-financeira/
├── README.md
├── docs/
│   ├── requisitos.md
│   ├── integracao-bancaria.md
│   ├── modelo-de-dados.md
│   └── decisoes-arquiteturais.md
├── poc-pluggy/              # primeiro entregável; independente
├── backend/                 # Python + FastAPI, monólito modular
│   └── [módulos: banking, accounts, transactions, obligations,
│       projections, simulations, receipts (futuro)]
├── frontend/                # React + TypeScript, depois do backend básico
└── .gitignore
```

**Responsabilidades:**
- **Frontend:** dashboards, filtros, compromissos, projeções e simuladores.
- **Backend (Python + FastAPI):** integrações, normalização de dados, regras financeiras, cálculo e API própria.
- **PostgreSQL:** contas, transações, sincronizações, obrigações, cenários e histórico.
- **Adaptador Pluggy:** comunicação com serviço externo, desacoplada do domínio.

**Ambiente de desenvolvimento:** usar uv para gerenciar dependências e ambiente virtual Python. Quando a persistência for introduzida, executar PostgreSQL via Docker Compose; backend e frontend serão executados diretamente na máquina. A PoC permanece independente de banco e Docker.

**Recomendações de implementação:**
- Valores monetários com `decimal.Decimal` no Python e `NUMERIC` no PostgreSQL; nunca `float` para dinheiro. Preservar a precisão na leitura e serialização de dados, com regras explícitas de arredondamento.
- Usar anotações de tipo e verificação estática; validar entradas e saídas da API com modelos Pydantic, mantendo as regras financeiras independentes do FastAPI.
- Moeda explícita; datas com fuso/semântica bem definidos.
- Identificadores externos + origem para deduplicação e sincronização incremental.
- Operações idempotentes e tratamento de paginação, falhas, expiração de tokens e rate limits.
- Distinguir saldos instantâneos de fluxos de transações e obrigações futuras.
- Evitar dupla contagem de pagamentos de cartão, transferências internas e notas fiscais.
- Preservar informações mínimas de origem para auditoria de cálculos.
- Testes de unidade para regras financeiras, além de testes de integração para persistência e adaptadores (com mocks/dados fictícios).

### Entidades candidatas — NÃO modelar tudo antes da PoC
`Institution`, `BankConnection`, `Account`, `BalanceSnapshot`, `Transaction`, `Card`, `CardStatement`, `Obligation`, `RecurringRule`, `ProjectedCashFlow`, `SimulationScenario`, `SyncExecution`; futuramente `Receipt`, `ReceiptItem`, `Product`, `ProductAlias`, `Merchant`.

Os nomes e limites das entidades serão revisados após observar os dados efetivamente retornados pela API. Não implementar tabelas para campos que ainda não sabemos se existem.

## 6. Segurança e privacidade

- Nunca armazenar credenciais bancárias do usuário.
- Segredos e tokens em ambiente seguro; `.env` local ignorado pelo Git; `.env.example` sem valores reais.
- Não registrar tokens, payloads completos, saldos, extratos ou dados pessoais em logs.
- Proteger tokens persistidos, se necessários; limitar acesso aos dados locais.
- HTTPS quando houver comunicação remota; sem exposição pública desnecessária.
- Permitir desconectar integrações e remover dados locais.
- Respeitar consentimento, termos de uso e limites da API.
- Sem login multiusuário, hospedagem pública, operações bancárias ou movimentação de dinheiro no MVP.

## 7. Roadmap e critérios de aceite

### Fase 0 — PoC Pluggy (AGORA)
**Entregas:** código mínimo de consulta, instruções de execução, `.env.example`, `RESULTADOS.md` sem informações sensíveis.  
**Aceite:** dados essenciais acessados com autorização, documentação dos limites e confirmação da viabilidade sem custo.

### Fase 1 — Backend financeiro
**Entregas:** modelo mínimo de contas/transações/sincronização, persistência, deduplicação, API de leitura e testes.  
**Aceite:** sincronizações repetidas não duplicam registros; falhas não corrompem o histórico.

### Fase 2 — Dashboard (MVP utilizável)
**Entregas:** saldo, contas, histórico de transações, filtros, atualização e estado da sincronização.  
**Aceite:** responder rapidamente “quanto tenho?”, “quais foram as últimas movimentações?” e “quão recentes são os dados?”.

### Fase 3 — Obrigações e projeções
**Entregas:** compromissos futuros, receitas previstas, recorrência e saldo projetado.  
**Aceite:** responder “quanto sobrará depois dos compromissos?” sem dupla contagem; distinguir confirmado de estimado.

### Fase 4 — Simuladores
**Entregas:** comprar agora/esperar, consórcio/financiamento/investimento e cenários de taxas, impostos e inflação.  
**Aceite:** fórmulas testadas, hipóteses editáveis, resultados auditáveis e incertezas explícitas.

### Fase 5 — Notas fiscais (88 + 103)
**Entregas:** pesquisa de acesso às NFC-e, importação viável, identificação de produtos, histórico e comparação de preços.  
**Aceite:** distinguir produtos iguais e similares, normalizar unidades e evitar despesas duplicadas.

## 8. Fora do escopo inicial

- Aplicação multiusuário/SaaS e monetização.
- Serviços pagos, infraestrutura cloud obrigatória ou aplicativos móveis nativos.
- IA obrigatória, recomendação automática de investimentos ou execução de operações financeiras.
- Notas fiscais antes de validar a sincronização bancária.
- Integração com todos os bancos de uma só vez.
- Construir dashboard completo antes da prova de conceito.

## 9. Riscos, decisões pendentes e perguntas a validar

1. A modalidade pessoal do Meu Pluggy permite efetivamente consultar dados por API própria? Quais limites e custos atuais?
2. Quais campos são disponibilizados para Nubank: contas, saldo, transações, cartão, fatura, compras parceladas?
3. Qual frequência real de atualização e como detectar dados desatualizados?
4. Como lidar com dados retroativos, mudanças em transações e identificadores externos?
5. O nível de atualização disponível atende às projeções desejadas?
6. Como identificar pagamentos de fatura e transferências internas sem dupla contagem?
7. Quais regras de recorrência e categorização são realmente necessárias para o MVP?
8. Quais hipóteses e fontes de taxas serão usadas nos simuladores?
9. Como importar NFC-e futuramente, respeitando regras dos portais estaduais?
10. A execução continuará local ou haverá hospedagem futura? (não decidido)

## 10. Instruções objetivas para o Codex

**Comece somente pela Fase 0.**

1. Leia esta especificação e proponha um plano curto para validar a API.
2. Verifique a documentação oficial atual antes de escolher endpoints ou bibliotecas.
3. Crie a menor PoC possível, com instruções para execução local e credenciais em variáveis de ambiente.
4. Não crie frontend, esquema completo de banco, autenticação de usuários ou simuladores agora.
5. Antes de qualquer ação que possa enviar dados pessoais para terceiros além da integração já autorizada, explique o que será enviado.
6. Não peça nem exponha Client Secret, tokens ou dados financeiros reais na conversa, nos commits ou nos resultados de teste.
7. Ao terminar, relate claramente o que funcionou, o que falhou, o que não foi testado e se o caminho gratuito é viável.
8. Só então proponha a modelagem mínima e o primeiro incremento do backend.

## 11. Histórico das escolhas

- O usuário considerou vários projetos, mas priorizou **utilidade prática, recorrência e custo zero**.
- Uma central financeira sem sincronização foi considerada menos atraente devido ao esforço de lançamento manual.
- A conexão do Nubank ao Meu Pluggy e a criação das chaves são os avanços já realizados.
- A ideia 88 (notas fiscais e histórico de preços) despertou interesse como projeto independente.
- A ideia 103 (reconhecimento de produtos em descrições de notas) foi incorporada à ideia 88.
- Decisão final: **desenvolver primeiro a central financeira; depois integrar notas fiscais como funcionalidade**.
- Stack do backend definida como **Python + FastAPI**, considerando a experiência prévia do usuário com ambos; substitui a sugestão inicial de Java + Spring Boot.
- Confirmados **PostgreSQL**, **Docker Compose para o banco**, execução direta de backend/frontend e **uv** para gerenciamento Python.
- Confirmada a Fase 2 como primeiro objetivo utilizável; obrigações e projeções ficam para o incremento seguinte.
- Pluggy permanece como caminho inicial; outras hipóteses serão avaliadas caso surjam limitações concretas.

---

**Princípio de desenvolvimento:** comprovar acesso a dados reais antes de investir em arquitetura e interface. Preservar simplicidade, privacidade, transparência dos cálculos e ausência de custos obrigatórios.
