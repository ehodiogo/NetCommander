# Interface do NetCommander

O NetCommander é um console para operadores de redes locais. O Dashboard mostra o desempenho das execuções acima do histórico recente. Execução e Terminal dão destaque ao alvo, ao sistema operacional e ao comando antes do disparo. O Monitor identifica a sala e o horário dos resultados.

- Use as superfícies escuras e os tokens em `static/css/tokens.css`. Reserve azul para ações principais e seleção, verde para sucesso, vermelho para erro ou remoção e amarelo para avisos.
- Use Inter nos textos da interface e JetBrains Mono nos identificadores `ncc@…`, comandos, endereços e saídas. O nome da tela é o título principal.
- Use os componentes Bootstrap existentes para foco, modais e expansão. Exponha as escolhas exclusivas com rádios nativos e acompanhe o status com texto visível.
- Mantenha resultados anteriores identificados quando a atualização falhar. Permita repetir consultas de status sem disparar comandos.
- Em telas estreitas, permita a quebra de nomes longos e mantenha a rolagem horizontal dentro do contêiner da tabela.
