# Incident Observability — Resposta a Incidentes e Postmortem

Projeto acadêmico de Sistemas Distribuídos que demonstra como métricas, alertas e um registro de incidentes podem ajudar a detectar, investigar e acompanhar a resolução de falhas em uma aplicação distribuída.

> **Equipe:** João Pedro Neves de Azevedo Melo · **Docente:** Josino Rodrigues Neto · **Instituição:** IFPE

## 1. Objetivos

- Reproduzir uma falha controlada em uma aplicação distribuída.
- Coletar métricas e visualizar o comportamento de dois serviços HTTP.
- Detectar uma taxa de erro elevada por meio de uma regra Prometheus.
- Encaminhar a notificação por meio do Alertmanager.
- Registrar a abertura e a resolução de um incidente por meio de um webhook.
- Avaliar resultados, limitações e oportunidades de melhoria com um runbook e um postmortem.

## 2. Tecnologias

- Python e FastAPI: Service A, Service B e incident-webhook.
- Docker e Docker Compose: ambiente local com múltiplos containers.
- Prometheus: coleta de métricas e avaliação de alertas.
- Grafana: dashboard de métricas.
- Alertmanager: roteamento de notificações.
- Prometheus Client: exposição de métricas pelos serviços.

## 3. Arquitetura

Service A chama Service B por HTTP. O Service B possui endpoints para ativar/desativar uma falha controlada. O Prometheus coleta `/metrics` nos dois serviços e avalia a regra `ServiceBHighErrorRate`. O Alertmanager encaminha as notificações para `incident-webhook`, que registra incidentes. O Grafana consulta o Prometheus e apresenta seis painéis.

```text
Service A ──HTTP──> Service B
    │                   │
    └──── /metrics ─────┘
             │
             v
         Prometheus ──alerta──> Alertmanager ──POST──> incident-webhook
             ^                                        │
             │                                        v
          Grafana                              Registro do incidente
```

## 4. Estrutura

```text
incident-observability/
├── service-a/
├── service-b/
├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml
├── alertmanager/
│   └── alertmanager.yml
├── incident-webhook/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── docs/
│   ├── evidencias/
│   ├── runbook.md
│   └── postmortem.md
├── .gitignore
├── docker-compose.yml
└── README.md
```

Cada serviço tem seu próprio `Dockerfile`, `requirements.txt` e `.dockerignore`. Os ambientes virtuais locais (`.venv`) não devem ser versionados.

## 5. Executar

Pré-requisitos: Docker e Docker Compose.

Na raiz do projeto, execute:

```bash
docker compose up --build
```

Em outro terminal, para conferir os containers:

```bash
docker compose ps
```

Para acompanhar logs:

```bash
docker compose logs -f incident-webhook
```

Para parar e remover os containers mantendo o volume do Grafana:

```bash
docker compose down
```

Evite `docker compose down -v` se quiser preservar o volume `grafana-data`.

## 6. Endpoints

| Componente | Endereço | Uso |
|---|---|---|
| Service A — Swagger | http://localhost:8000/docs | Fazer requisições ao Service A |
| Service B — Swagger | http://localhost:8001/docs | Ativar/desativar a falha simulada |
| Webhook — Swagger | http://localhost:8002/docs | Consultar/testar endpoints do webhook |
| Lista de incidentes | http://localhost:8002/incidents | Ver registros abertos e resolvidos |
| Prometheus | http://localhost:9090 | Consultas PromQL |
| Prometheus — Targets | http://localhost:9090/targets | Verificar coleta das métricas |
| Prometheus — Alerts | http://localhost:9090/alerts | Acompanhar a regra de alerta |
| Alertmanager | http://localhost:9093 | Consultar alertas recebidos |
| Grafana | http://localhost:3000 | Dashboard de observabilidade |

Login padrão do Grafana, caso não tenha sido alterado: `admin` / `admin`.

## 7. Dashboard

O dashboard `Incident Observability` contém seis painéis:

1. Requisições — Service A (`service_a_requests_total`)
2. Erros — Service A (`service_a_errors_total`)
3. Requisições — Service B (`service_b_requests_total`)
4. Erros — Service B (`service_b_errors_total`)
5. Taxa de erro — Service A
6. Taxa de erro — Service B

A fonte de dados do Grafana aponta para `http://prometheus:9090`, que é o endereço interno do serviço na rede Compose. O intervalo utilizado durante os testes foi Last 15 minutes, com atualização automática a cada 5 segundos.

## 8. Regra de alerta

A regra `ServiceBHighErrorRate` dispara quando a taxa de erro do Service B supera 20%:

```promql
100 *
(
  rate(service_b_errors_total[1m])
  /
  rate(service_b_requests_total[1m])
) > 20
```

O Prometheus coleta métricas e avalia regras a cada 5 segundos. A regra usa `for: 0s`. O Alertmanager utiliza `group_wait: 5s`, `group_interval: 15s` e `repeat_interval: 1h`, conforme a configuração do projeto.

**Limitação:** sem tráfego ou amostras suficientes, `rate()` pode ficar indefinido, fazendo a expressão deixar de retornar uma série. Ausência de alerta, isoladamente, não comprova recuperação.

## 9. Reproduzir a demonstração

1. Inicie os serviços e verifique `/targets` no Prometheus.
2. Abra o Service B no Swagger e execute `POST /admin/failure/on`.
3. Gere várias requisições por um endpoint do Service A que chama o Service B. Para estudar tempos de recuperação, mantenha tráfego contínuo durante todo o teste.
4. Em `/alerts`, confirme `ServiceBHighErrorRate` em `FIRING`.
5. Verifique o alerta no Alertmanager, os logs do webhook e o incidente em `/incidents`.
6. Execute `POST /admin/failure/off` no Service B enquanto mantém as requisições.
7. Confirme que a taxa de erro se normaliza, o alerta deixa de estar `FIRING` e o incidente muda para `RESOLVED`.

## 10. Resultados experimentais

Em um teste controlado de 20/10/2026, foram coletados os seguintes timestamps. `activeAt` é proveniente da API do Prometheus; os timestamps do webhook não indicam fuso explicitamente e foram interpretados como UTC com base no relógio do container.

| Evento | Horário apresentado em UTC |
|---|---|
| Falha simulada ativada | 17:36:55.513 |
| Condição do alerta ativa | 17:37:42.075 |
| `INC-002` aberto | 17:37:52.046808 |
| `INC-002` registrado como `RESOLVED` | 17:39:07.044737 |
| Comando de desativação registrado no PowerShell | 17:39:13.136 |

Deltas calculados entre timestamps:

- Falha ativada → condição do alerta ativa: **46,562 s**.
- Detecção → incidente aberto: **9,972 s**.
- Falha ativada → incidente aberto: **56,534 s**.
- `OPEN` → `RESOLVED`: **74,998 s**.
- Falha ativada → timestamp de resolução: **131,532 s**.

**Inconsistência a investigar:** `resolved_at` aparece 6,091 segundos antes do horário registrado para o comando de desativação. Portanto, esta execução não comprova que o comando de desativação causou a resolução. Os deltas são diferenças entre timestamps observados, não uma medição confirmada de recuperação; repetir o ensaio em ordem temporal verificada é necessário.

Esses valores são de uma execução, não médias estatísticas de MTTD ou MTTR.

## 11. Runbook, postmortem e evidências

- `docs/runbook.md`: procedimento de confirmação, investigação, mitigação e validação da recuperação.
- `docs/postmortem.md`: linha do tempo, resultados, limitações e plano de ação.
- `docs/evidencias/`: capturas do Grafana, Prometheus, Alertmanager e registro do incidente.

## 12. Limitações conhecidas

- O webhook mantém incidentes em memória; recriar o container perde o histórico.
- Notificações `firing` repetidas podem gerar registros duplicados; falta idempotência/correlação por fingerprint.
- A taxa de erro pode ficar indefinida sem tráfego suficiente.
- Os timestamps do webhook não incluem fuso horário explícito.
- Traces distribuídos não foram instrumentados neste protótipo; podem ser adicionados com OpenTelemetry.
- O Prometheus não usa volume persistente para o histórico de métricas; dados históricos podem ser perdidos quando seu container é removido/recriado.
- A demonstração utiliza uma falha controlada e dois serviços; não comprova prontidão para produção.

## 13. Referências

- Prometheus. *Instrumentation*. https://prometheus.io/docs/practices/instrumentation/
- Prometheus. *Alertmanager configuration*. https://prometheus.io/docs/alerting/latest/configuration/
- Grafana Labs. *Prometheus data source*. https://grafana.com/docs/grafana/latest/datasources/prometheus/
- OpenTelemetry. *Signals*. https://opentelemetry.io/docs/concepts/signals/
- Google SRE. *Postmortem Culture: Learning from Failure*. https://sre.google/resources/book-update/postmortem-culture/
- Docker. *How Compose works*. https://docs.docker.com/compose/intro/compose-application-model/