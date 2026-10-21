# Postmortem — Alta taxa de erros no Service B

## 1. Informações do incidente

- **Identificador:** `INC-002`
- **Alerta:** `ServiceBHighErrorRate`
- **Serviço:** `service-b`
- **Severidade:** `critical`
- **Tipo:** falha simulada para fins acadêmicos
- **Resultado observado:** o registro do webhook chegou a `RESOLVED`; a sequência temporal em relação à solicitação de desativação precisa ser confirmada em uma nova execução.

## 2. Resumo executivo

Foi provocada uma falha controlada no Service B para validar o fluxo de detecção, notificação e registro de incidentes. O Prometheus avaliou a taxa de erro e ativou a regra `ServiceBHighErrorRate`; o Alertmanager encaminhou as notificações ao `incident-webhook`, que registrou `INC-002` como aberto e posteriormente como resolvido.

A execução validou a abertura do incidente, mas as evidências de horário contêm uma inconsistência: `resolved_at` foi registrado antes do timestamp associado ao comando de desativação da falha. Por isso, não se deve concluir que essa ação provocou a resolução sem repetir o ensaio e verificar a ordem dos eventos.

## 3. Impacto observado

- Serviço afetado no teste: Service B.
- Comportamento: aumento de erros durante o cenário de falha controlada.
- Detecção: regra `ServiceBHighErrorRate` em `FIRING`.
- Notificação: encaminhamento por Alertmanager ao webhook.
- Registro: `INC-002` registrado como `OPEN` e depois `RESOLVED`.
- Impacto em usuários reais: não aplicável, pois o teste foi executado localmente em cenário simulado.

## 4. Linha do tempo

Todos os horários abaixo estão apresentados em UTC. `activeAt` vem da API do Prometheus. O webhook não inclui explicitamente um fuso horário em `started_at`/`resolved_at`; neste teste, seus horários foram interpretados como UTC com base no relógio do container.

| Evento | Horário | Evidência |
|---|---|---|
| Falha simulada ativada | 17:36:55.513 | Resposta de `POST /admin/failure/on` e registro no PowerShell |
| Condição do alerta ficou ativa | 17:37:42.075 | API do Prometheus, campo `activeAt` |
| `INC-002` aberto | 17:37:52.046808 | `started_at` do webhook |
| `INC-002` registrado como resolvido | 17:39:07.044737 | `resolved_at` do webhook |
| Comando de desativação registrado | 17:39:13.136 | Timestamp capturado no PowerShell imediatamente antes da solicitação `POST /admin/failure/off` |

### Deltas observados

- Ativação da falha → condição do alerta ativa: **46,562 segundos**.
- Condição ativa → registro de abertura: **9,972 segundos**.
- Ativação da falha → abertura do incidente: **56,534 segundos**.
- Registro de abertura → registro de resolução: **74,998 segundos**.
- Ativação da falha → timestamp de resolução: **131,532 segundos**.
- O timestamp de resolução antecede o registro do comando de desativação em **6,091 segundos**.

Esses valores são diferenças entre timestamps observados numa única execução. Não são médias estatísticas de MTTD ou MTTR. Em particular, a sequência registrada não comprova a latência real de recuperação após desativar a falha.

## 5. Detecção e diagnóstico

O alerta é baseado na seguinte expressão PromQL:

```promql
100 *
(
  rate(service_b_errors_total[1m])
  /
  rate(service_b_requests_total[1m])
) > 20
```

A regra utiliza uma janela de um minuto e está configurada com `for: 0s`. A avaliação foi configurada a cada cinco segundos. A investigação foi apoiada por métricas no Grafana, estado da regra no Prometheus, alertas no Alertmanager e registros do webhook.

A taxa pode ficar indefinida quando não existem amostras suficientes ou quando a taxa de requisições é zero. Por isso, o alerta sair de `FIRING` não deve ser usado isoladamente como prova de recuperação.

## 6. Causa e fatores contribuintes

**Causa no cenário simulado:** a falha foi ativada deliberadamente no Service B.

**Causa de falha real:** não avaliada por este experimento.

Fatores técnicos relevantes incluem dependência HTTP entre os serviços, janela de cálculo das métricas, intervalos de avaliação/notificação e ausência de persistência do registro de incidentes.

## 7. Resposta e recuperação

O webhook recebeu uma notificação de alerta e criou o registro `INC-002`. Mais tarde, registrou o mesmo incidente como `RESOLVED`. Entretanto, `resolved_at` aparece às 17:39:07.044737 e o timestamp registrado para o comando `POST /admin/failure/off` é 17:39:13.136.

Essa ordem temporal é inconsistente com a hipótese de que o comando OFF causou a resolução. O teste precisa ser repetido mantendo requisições contínuas, capturando os horários em uma única fonte temporal consistente e confirmando, na ordem: desativação, normalização da taxa, alerta fora de `FIRING` e incidente `RESOLVED`.

## 8. O que funcionou bem

- Coleta de métricas dos dois serviços pelo Prometheus.
- Visualização de contadores e taxas no Grafana.
- Detecção de uma condição de erro pelo Prometheus.
- Encaminhamento de notificações pelo Alertmanager.
- Criação e atualização do registro pelo webhook.
- Existência de procedimento operacional e documentação de limitações.

## 9. Limitações técnicas

1. **Persistência:** a lista de incidentes fica em memória e se perde quando o webhook é reiniciado/recriado.
2. **Idempotência:** alertas repetidos podem criar múltiplos registros para uma mesma condição; falta correlação por fingerprint.
3. **Ausência de tráfego:** o cálculo de taxa pode ficar indefinido; disponibilidade deve ser monitorada separadamente.
4. **Consistência temporal:** timestamps do webhook não incluem fuso explícito.
5. **Tracing:** traces distribuídos não foram instrumentados; adicionar OpenTelemetry permitiria observar spans do caminho Service A → Service B.
6. **Escopo:** o experimento considera dois serviços e uma falha controlada; não representa todos os cenários de produção.
7. **Persistência do Prometheus:** sem volume de dados configurado, o histórico pode ser perdido quando o container é removido/recriado.

## 10. Plano de ação

| Ação | Prioridade | Status |
|---|---|---|
| Repetir o ensaio e validar a ordem dos timestamps de recuperação | Alta | Pendente |
| Persistir incidentes em SQLite/PostgreSQL | Média | Pendente |
| Correlacionar notificações por fingerprint e tornar operações idempotentes | Alta | Pendente |
| Tratar explicitamente ausência de tráfego e monitorar disponibilidade | Alta | Pendente |
| Padronizar timestamps em UTC com fuso explícito | Média | Pendente |
| Instrumentar traces distribuídos com OpenTelemetry | Média | Pendente |
| Repetir os ensaios para obter mais de uma amostra por cenário | Média | Pendente |

## 11. Conclusão

O protótipo demonstrou o fluxo de coleta de métricas, detecção de alerta, roteamento de notificação e registro do ciclo de vida de um incidente. A evidência atual comprova a abertura e a existência de um registro resolvido, mas não confirma que a resolução foi causada pela solicitação de desativação, devido à inconsistência de seis segundos na ordem dos timestamps. Uma nova execução medida é necessária para confirmar a recuperação e calcular tempos confiáveis de resolução.

## Referências

- PROMETHEUS. *Instrumentation*. https://prometheus.io/docs/practices/instrumentation/
- PROMETHEUS. *Alertmanager configuration*. https://prometheus.io/docs/alerting/latest/configuration/
- OPENTELEMETRY. *Signals*. https://opentelemetry.io/docs/concepts/signals/
- GOOGLE SRE. *Postmortem Culture: Learning from Failure*. https://sre.google/resources/book-update/postmortem-culture/
