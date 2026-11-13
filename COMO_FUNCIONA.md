# Como funciona

Resumo para estudar antes de uma entrevista técnica.

## 1. O contexto

- **DNS** traduz nomes (`github.com`) em endereços IP. Todo aparelho pergunta ao DNS antes de abrir qualquer site ou app.
- O **Blocky** é um servidor DNS que responde `0.0.0.0` para domínios de anúncio e rastreamento. Assim, o aparelho nem chega a baixar o anúncio. Vale para a casa toda, inclusive TVs, onde não dá para instalar bloqueador.
- Com o `queryLog` em CSV ligado, o Blocky grava uma linha por consulta:

```
hora                 IP do aparelho  nome     ms  motivo                                 pergunta              resposta
2026-11-01 20:58:01  192.168.0.12    tv-sala  12  RESOLVED (https://1.1.1.1/dns-query)   ad.doubleclick.net.   A (1.2.3.4)
```

O motivo diz o que aconteceu:
- **RESOLVED**: perguntou ao DNS de fora;
- **CACHED**: respondeu da memória;
- **BLOCKED**: bloqueou.

## 2. Peças

```
relatorio_dns/report.py   leitura do registro, contagens, candidatos e o HTML com os gráficos
relatorio_dns/sample.py   gerador do registro inventado (semente fixa, sempre o mesmo resultado)
relatorio_dns/cli.py      comandos "relatorio" e "exemplo"
```

## 3. O caminho dos dados

1. **`parse`** lê linha a linha e devolve (dia, hora, aparelho, motivo, domínio).
   - Linha quebrada é ignorada.
   - Aparelho sem nome no Blocky aparece pelo IP.
   - O domínio perde o ponto final e vira minúsculo.
2. **`aggregate`** soma tudo em contadores (`collections.Counter`): por aparelho, por hora, por domínio bloqueado e por domínio liberado em cada aparelho.
3. **`candidates`** cruza os domínios liberados com uma lista de bloqueio maior.
4. **`render`** monta o HTML.

Os arquivos são lidos como *stream* (um gerador que devolve linha por linha). Um mês de registro de uma casa movimentada pode ter centenas de MB; nunca precisa caber inteiro na memória.

## 4. Candidatos a bloqueio

Listas como a HaGeZi usam o formato curinga: `*.doubleclick.net` bloqueia o domínio e todos os subdomínios. A função `listed` gera os "pais" do domínio e testa cada um no conjunto (`set`):

```
ad.doubleclick.net -> ad.doubleclick.net, doubleclick.net   (para antes de "net")
```

Busca em `set` é O(1), então checar milhares de domínios contra uma lista de 170 mil nomes leva milissegundos.

Detalhe que os testes guardam: se a lista tem `ads.exemplo.com`, o domínio `exemplo.com` **não** casa. Só o domínio listado e os de baixo dele.

Por que "candidatos" e não bloqueio automático: listas maiores bloqueiam coisas úteis. Um exemplo real é `graph.instagram.com`, que quebra o app. A pessoa revisa antes.

## 5. Gráficos sem biblioteca

Os dois gráficos são SVG escrito à mão, para a página funcionar sozinha, sem internet e sem matplotlib.

- **Coordenadas.** Uma escala linear converte valor em altura: `y(v) = topo + altura_útil × (1 − v / máximo)`.
- **Barras empilhadas.** Liberadas embaixo, bloqueadas em cima, com 2 px de espaço entre as duas partes.
- **Dica ao passar o mouse.** Cada coluna tem um retângulo transparente maior que a barra e um `<title>`, que mostra o número exato.
- **Acessibilidade.**
  - Cada gráfico tem legenda.
  - Cada gráfico tem uma tabela com os mesmos números ("Ver como tabela").
  - A identificação nunca depende só da cor.
- **Cores.** Azul e laranja passaram no validador de daltonismo, que mede a diferença de cor para quem não distingue vermelho e verde.
- **Modo escuro.** Variáveis CSS mudam com `prefers-color-scheme`.
- **Segurança.** Todo texto vindo do registro passa por `html.escape`. Um aparelho chamado `<script>` vira texto, não código. Há teste para isso.

## 6. Dados de exemplo

O gerador cria uma rede fictícia: notebook, celular, TV e um aparelho sem nome.
- Cada aparelho usa domínios plausíveis.
- 12% das consultas vão para domínios de anúncio.
- A noite tem mais movimento.

A semente fixa (`random.Random(42)`) faz o arquivo sair igual em toda execução. Isso deixa os testes estáveis.

## 7. Perguntas prováveis

**Por que não um banco de dados?**
Para um relatório diário, ler o CSV direto é mais simples e rápido o bastante. Com consultas históricas ou painéis ao vivo, valeria jogar os dados no SQLite ou no DuckDB.

**Por que SVG à mão e não uma biblioteca de gráficos?**
O relatório precisa abrir no navegador de qualquer aparelho da casa, sem internet e sem instalar nada no servidor (um celular com pouco espaço). Também deixa claro que entendo o que a biblioteca faria por mim.

**Como isso roda no servidor?**
O cron chama o relatório todo dia às 00:10 com o registro do dia anterior. A versão de casa grava em texto e também baixa as listas maiores, com cópia local para quando a rede falha.

**Qual foi o papel da IA?**
O servidor, o Blocky e o relatório original são do meu uso diário. O Claude Code ajudou a transformar o script em pacote com gráficos, testes e dados de exemplo. Revisei e rodei tudo.
