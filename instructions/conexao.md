# Instruções de Engenharia para Integração com Polymarket

Para controlar a conta e operar no Polymarket, o bot deve interagir com dois sistemas principais: o **CLOB (Central Limit Order Book)** para execução de ordens e o **Gamma** para dados de mercado. Siga as especificações abaixo:

## 1. Configuração e Autenticação (Controle da Conta)

Para "controlar" a conta (enviar transações e ordens), você deve focar na API do CLOB e na gestão de chaves.

*   **Autenticação do CLOB:** Implemente o fluxo de autenticação especificado na documentação do CLOB [1]. Isso é obrigatório para qualquer ação de escrita ou trading.
*   **Gerenciamento de Chaves:** Utilize o *Builder Profile & Keys* para gerenciar as credenciais de acesso necessárias para assinar as transações [2].
*   **Proxy Wallets:** Configure o suporte para *Proxy Wallets*, que são frequentemente utilizadas para facilitar a interação com os contratos inteligentes da plataforma [3].
*   **Restrições Geográficas:** O bot deve verificar e respeitar as *Geographic Restrictions* impostas pelo CLOB antes de tentar operar [1].

## 2. Execução de Ordens (Trading)

O núcleo operacional do bot será o **Central Limit Order Book (CLOB)**.

*   **Setup Inicial:** Consulte o *Developer Quickstart* e a seção *Placing Your First Order* para estruturar a primeira chamada de API de negociação [2].
*   **Endpoints de Trading:** Utilize os endpoints do CLOB para criar, cancelar e gerenciar ordens [1].
*   **Condições de Token:** Entenda o *Conditional Token Framework*, incluindo como funciona a divisão (*Splitting*), fusão (*Merging*) e resgate (*Redeeming*) de tokens, pois isso afeta o saldo e a posição da conta [1].

## 3. Ingestão de Dados e "Vibe" do Mercado

Para que o bot tome decisões (a parte de "vibe coding"), ele precisa de dados ricos e em tempo real.

*   **Gamma API (Metadados de Mercado):** Utilize a estrutura **Gamma**. Ela é um serviço hospedado que indexa dados on-chain e fornece metadados essenciais (como categorização e volume indexado) através de uma API REST [3].
    *   *Uso:* Ideal para buscar mercados (*Fetching Markets*) e alimentar sistemas de trading automatizado [3].
*   **Websockets (Tempo Real):** Para reagir instantaneamente, implemente conexões WSS (*Websocket*):
    *   **User Channel:** Para monitorar atualizações específicas da sua conta (preenchimento de ordens, saldo) [1].
    *   **Market Channel:** Para monitorar o livro de ofertas e negociações em tempo real [1].
*   **Real Time Data Stream (RTDS):** Considere integrar o RTDS para obter preços de cripto (*RTDS Crypto Prices*) e comentários (*RTDS Comments*) se a estratégia do bot depender de sentimento ou preços externos [1].

## 4. Referência de Desenvolvimento

*   **Glossário e Limites:** Consulte o *Glossary* para terminologia específica e respeite os *API Rate Limits* para evitar bloqueios temporários do bot [2].
*   **Resolução de Mercados:** Mantenha um monitoramento sobre o status de *Resolution* dos mercados para saber quando os eventos foram concluídos e os pagamentos processados [1].