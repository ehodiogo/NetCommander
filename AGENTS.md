# AGENTS.md — NetCommander

## Objetivo

O NetCommander é um sistema web para gerenciamento remoto de computadores em redes locais. O projeto utiliza Django e permite organizar máquinas em salas, executar comandos remotos, enviar Wake-on-LAN, acompanhar o status das máquinas e administrar execuções de forma centralizada.

Este documento define as regras que qualquer agente de IA deve seguir durante o desenvolvimento.

---

# Fluxo de Trabalho

## Regra principal

Implementar apenas **uma funcionalidade por vez**.

Cada entrega deve conter:

* implementação completa;
* testes quando aplicáveis;
* correções necessárias;
* atualização da documentação.

Nunca iniciar outra funcionalidade antes da anterior estar concluída.

---

## Ordem obrigatória

1. Entender a solicitação.
2. Planejar a implementação.
3. Implementar apenas o escopo solicitado.
4. Executar validações.
5. Corrigir erros encontrados.
6. Atualizar este AGENTS.md caso novas convenções tenham sido adotadas.

---

# Stack Atual

## Backend

* Python 3
* Django
* SQLite (desenvolvimento)
* python-decouple
* impacket (Wake-on-LAN)

## Estrutura atual

O projeto é composto pelos aplicativos:

* core
* maquinas
* salas
* execucoes

O projeto Django está em:

```
netcommander/
```

---

# Organização do Código

Cada aplicação possui responsabilidade única.

## core

Responsável por:

* utilidades
* funções compartilhadas
* executor remoto
* views principais

## maquinas

Responsável exclusivamente pelo gerenciamento das máquinas cadastradas.

## salas

Responsável pela organização lógica das máquinas.

## execucoes

Responsável pelo cadastro e execução de comandos remotos.

Nunca misturar responsabilidades entre aplicativos.

---

# Convenções

## Código

* Utilizar PEP-8.
* Métodos pequenos.
* Uma responsabilidade por função.
* Evitar duplicação.
* Evitar comentários desnecessários.
* Priorizar código legível.
* Utilizar nomes descritivos.

---

## Models

Sempre utilizar:

* verbose_name quando necessário
* relacionamentos corretos
* métodos simples
* lógica complexa fora dos Models

---

## Views

As Views devem apenas:

* validar requisições;
* chamar funções auxiliares;
* montar o contexto;
* retornar respostas.

Toda lógica reutilizável deve permanecer em:

```
core/
```

ou em módulos específicos da aplicação correspondente.

---

## Forms

Toda validação de entrada deve ocorrer através dos Forms do Django.

Nunca validar diretamente dentro das Views quando um Form puder ser utilizado.

---

# Templates

Priorizar:

* interface limpa;
* layout responsivo;
* componentes reutilizáveis;
* HTML sem duplicação;
* utilização de template inheritance.

Convenções de UX:

* Erros de validação dos formulários devem ser renderizados via o partial `templates/campo.html` (label + widget + help + erros visíveis). Nunca usar `form.as_p` nem renderizar só o widget.
* Todo disparo de execução em massa (dashboard e terminal coletivo) deve passar por um modal de confirmação mostrando alvo, SO e comando.
* Confirmação de ações destrutivas deve usar modal Bootstrap; não usar `confirm()` nativo.

---

# Frontend (F1)

Estrutura de assets:

* `static/css/tokens.css` — design tokens (cores, raio, espaçamento, fontes, sombras) via variáveis CSS `--nc-*`.
* `static/css/app.css` — estilos globais e componentes; sempre usar os tokens, nunca valores hardcoded.
* `static/js/*.js` — módulos ES (`<script type="module">`): `app.js` (utils: `fetchJSON`, `escapeHtml`, `showToast`, `lerDadosJSON`), `execucao-poller.js` (classe `ExecucaoPoller`), `execucao.js` (console de disparo), `biblioteca.js` (exclusão de scripts), `historico.js` (chevron de colapso), `terminal.js`, `forms.js`.

Convenções:

* Dados servidos ao JS devem usar `{{ dados|json_script:"id" }}` no template; nunca montar objetos JS com interpolação Django.
* Endpoints JSON retornam envelope `{ "ok": bool, "dados": ... }` em sucesso e `{ "ok": false, "erros": [...] }` em erro (com status HTTP adequado).
* Endpoints de mutação exigem CSRF via header `X-CSRFToken` (lido do cookie); não usar `@csrf_exempt`. Páginas que disparam requisições usam `@ensure_csrf_cookie`.
* Nunca usar `onclick=` inline nem `innerHTML` com dados do servidor sem `escapeHtml`/`textContent`.
* Acessibilidade: `skip-link`, `:focus-visible`, `aria-live` em áreas dinâmicas, `prefers-reduced-motion`.
* `block scripts` deve ficar no final do template filho e só deve conter `<script type="module">`.

---

# Organização de Views e Templates (F2)

## Views

Todas as views permanecem no app `core`, organizadas em pacote por domínio:

* `core/views/__init__.py` — re-exporta as views.
* `core/views/auth.py` — autenticação (`login_view`, `logout_view`).
* `core/views/dashboard.py` — landing/resumo (`dashboard`).
* `core/views/execucao.py` — área de execução (`execucao`, `terminal`), execução, terminal e cancelamento.
* `core/views/gerencia.py` — CRUD de salas, máquinas e comandos (`biblioteca`, `lista_salas`, `criar_*`, `editar_*`, `deletar_*`, `sala_detail`).
* `core/views/utils.py` — helpers compartilhados (`_resposta_bloqueio`, `_salas_para_json`, etc.).

O `core/urls.py` importa das subviews diretamente.

## Áreas do sistema

O sistema é dividido em 3 áreas de navegação + dashboard:

* **Dashboard** (`home`, `/`) — landing/resumo com contagens (salas, máquinas, scripts, execuções), atalhos para as áreas e histórico recente.
* **Biblioteca** (`biblioteca`, `/biblioteca/`) — listagem de scripts salvos, criar/editar/excluir (`/comandos/novo/`, `/comando/editar/<id>/`, `/comando/deletar/<id>/`).
* **Execução** (`execucao`, `/execucao/`) — console de disparo de scripts prontos + histórico; o Terminal (`/terminal/`) fica subordinado a esta área.
* **Salas** (`lista_salas`, `/salas/`) — listagem de salas, criar sala e CRUD de máquinas (`/salas/...`, `/maquinas/nova/`).

## Templates

* `templates/components/` — componentes reutilizáveis: `badge_status.html`, `modal_confirmacao.html`, `page_header.html`, `empty_state.html`, `toast_container.html`.
* `templates/core/dashboard.html` — landing/resumo.
* `templates/core/biblioteca.html` — biblioteca de scripts.
* `templates/core/execucao.html` — área de execução (console + histórico).
* `templates/core/dashboard/` — includes: `console.html` (disparo de scripts) e `historico.html` (últimos disparos), usados pelas páginas acima.
* Páginas grandes devem ser compostas por includes; o template principal apenas orquestra.
* Componentes com muitos parâmetros usam `{% include %}` com `with` em **linha única** — o lexer do Django não reconhece tags multilinha (sem flag DOTALL), que são renderizadas como texto literal.

---

# Cancelamento de Execução

Toda execução pode ser cancelada de forma cooperativa:

* Campo `Execucao.cancelado` (bool) + status `'cancelado'` em `Execucao` e `ResultadoMaquina`.
* O endpoint `cancelar_execucao` (POST) marca `cancelado=True`; só aceita status `pendente`/`em_andamento`.
* O `worker()` verifica `_execucao_cancelada(resultado_id)` em checkpoints (após verificar rede, após WoL e antes do SSH) e aborta marcando o resultado como `cancelado`.
* `_rodar_execucao_sala`/`_rodar_execucao_maquina` finalizam com status `'cancelado'` se `execucao.cancelado`.
* Consultas de bloqueio de execuções duplicadas devem excluir `cancelado=True`.

---

# Banco de Dados

Nunca alterar tabelas manualmente.

Sempre utilizar:

```
python manage.py makemigrations
python manage.py migrate
```

As migrations fazem parte da entrega.

---

# Wake-on-LAN

Toda lógica relacionada ao envio do Magic Packet deve permanecer isolada.

Antes de executar comandos remotos deve-se:

* verificar se a máquina está online;
* tentar ligá-la quando aplicável;
* aguardar disponibilidade antes da conexão.

---

# Execução Remota

Toda execução deve possuir tratamento para:

* timeout;
* falha de autenticação;
* máquina offline;
* erro de conexão;
* retorno do comando.

Nunca executar comandos diretamente dentro das Views.

---

# Terminal

O Terminal permite executar comandos livres em massa sem salvá-los na biblioteca.

Convenções adotadas:

* Execuções de terminal usam `Execucao.comando = None` e armazenam o comando digitado em `Execucao.comando_texto`, além do `Execucao.os_alvo`.
* `worker()` e `executar_em_paralelo()` aceitam `comando_texto`; quando informado, o comando executado é o texto digitado e `os_alvo` vale para todas as máquinas (não apenas dual boot).
* A escolha do comando a executar fica isolada em `_comando_a_executar()`.
* Validação via `TerminalForm` (os_alvo + comando_texto obrigatório).
* O endpoint `terminal_executar` bloqueia execuções duplicadas filtrando `comando__isnull=True` para a mesma sala/máquina, reutilizando `_resposta_bloqueio()`.

---

# Segurança

Nunca armazenar:

* senhas em texto puro;
* credenciais no código;
* endereços sensíveis hardcoded.

Toda configuração deve utilizar variáveis de ambiente sempre que possível.

Validar todas as entradas recebidas.

---

# Logs

Registrar sempre que possível:

* execuções;
* erros;
* falhas de conexão;
* Wake-on-LAN;
* eventos importantes.

Nunca registrar senhas ou informações sensíveis.

---

# Dependências

Adicionar novas dependências somente quando realmente necessárias.

Sempre priorizar funcionalidades nativas do Django antes de utilizar bibliotecas externas.

Para detecção de interfaces de rede, usar comandos nativos do sistema (`ipconfig` no Windows, `ip addr` no Linux) em vez de bibliotecas externas como `netifaces`.

Para SSH, utilizar `paramiko` em vez de `sshpass` + subprocess, pois funciona de forma nativa em Windows e dá melhor controle de timeout e tratamento de erros.

---

# Wake-on-LAN

Toda função `enviar_wol()` deve retornar tupla `(sucesso: bool, erro: str | None)`.

Toda chamada a `garantir_maquina_ligada()` dentro de `worker()` deve estar dentro de `try/except`.

O broadcast deve ser calculado dinamicamente com base nas interfaces de rede do servidor, com fallback para `255.255.255.255`.

MACs devem ser validados antes de enviar WOL — usar `_validar_mac()`.

---

# Logging

Utilizar o módulo `logging` do Python com um logger nomeado (`logger = logging.getLogger(__name__)`).

Eventos de WOL, erros de rede, falhas de conexão e resultados de ping devem ser registrados.

Configurar logging no `settings.py` com nível INFO para o app `core`.

Nunca usar `print()` para depuração.

---

# Testes

Sempre que houver alteração relevante executar:

```
python manage.py check
python manage.py test
```

Caso existam migrations novas:

```
python manage.py makemigrations
python manage.py migrate
```

Nenhuma entrega deve deixar erros ou warnings conhecidos.

---

# Padrão para Novas Funcionalidades

Toda nova funcionalidade deve seguir este fluxo:

1. Models (se necessário)
2. Migration
3. Forms
4. Views
5. URLs
6. Templates
7. Testes
8. Validação manual

---

# Interface

Priorizar:

* tema escuro;
* visual minimalista;
* poucas cores;
* boa responsividade;
* ações rápidas;
* consistência entre telas.

Evitar telas poluídas.

---

# Alterações Estruturais

Qualquer alteração que envolva:

* nova aplicação Django;
* reorganização de pastas;
* novo padrão arquitetural;
* novas dependências;
* mudanças no fluxo de desenvolvimento;

deve obrigatoriamente atualizar este arquivo.

---

# O que evitar

* Lógica complexa nas Views.
* Código duplicado.
* Consultas repetidas ao banco.
* Hardcode de configurações.
* Alterações diretas no banco.
* Dependências desnecessárias.
* Refatorações fora do escopo solicitado.

---

# Objetivo das Implementações

Cada alteração deve tornar o NetCommander:

* mais estável;
* mais simples de manter;
* mais seguro;
* mais modular;
* sem quebrar funcionalidades existentes.
