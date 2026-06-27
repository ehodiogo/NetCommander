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

# Autenticação

O sistema de login utiliza:

* credenciais definidas no `.env` (`AUTH_USERNAME`, `AUTH_PASSWORD`)
* `python-decouple` para ler as variáveis
* backend customizado em `core/backends.py` (`EnvAuthBackend`)
* `@login_required` em todas as views protegidas
* página de login em `/login/`
* redirecionamento automático via `LOGIN_URL`

Sempre utilizar o decorator `@login_required` para novas views que exigirem autenticação.

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
