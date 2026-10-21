# Runbook — ServiceBHighErrorRate

## 1. Objetivo

Definir o procedimento de investigação, mitigação e resolução do alerta `ServiceBHighErrorRate`, emitido quando a taxa de erro do Service B ultrapassa 20%.

## 2. Condição do alerta

- **Alerta:** `ServiceBHighErrorRate`
- **Serviço afetado:** Service B
- **Severidade:** Critical
- **Condição:** taxa de erro superior a 20%
- **Janela de cálculo:** 1 minuto
- **Ferramentas:** Prometheus, Grafana, Alertmanager e incident-webhook.

## 3. Procedimento de resposta

### Etapa 1 — Confirmar o incidente

1. Acesse o [Prometheus — Alerts](http://localhost:9090/alerts).
2. Localize `ServiceBHighErrorRate`.
3. Verifique se o alerta está em estado `FIRING`.
4. Acesse o [registro de incidentes](http://localhost:8002/incidents) e confirme se o incidente foi criado.

### Etapa 2 — Investigar o problema

1. Abra o [dashboard do Grafana](http://localhost:3000).
2. Analise os painéis de requisições e erros dos Services A e B.
3. Examine as taxas de erro para identificar quando o comportamento anormal começou.
4. Consulte os logs dos serviços, do Prometheus, do Alertmanager e do webhook, quando necessário:

   ```bash
   docker compose logs --tail=100 service-a service-b prometheus alertmanager incident-webhook
   ```

5. Compare as evidências para verificar se os erros estão associados à falha simulada no Service B.

**Importante:** um gráfico de taxa vazio não comprova que o serviço está saudável. Verifique também o tráfego recebido e os logs.

### Etapa 3 — Mitigar a falha simulada

1. Acesse o [Swagger do Service B](http://localhost:8001/docs).
2. Execute `POST /admin/failure/off` para desativar a falha simulada.
3. Acesse o [Swagger do Service A](http://localhost:8000/docs).
4. Gere novas requisições pelo endpoint que chama o Service B.
5. Observe as métricas no Grafana e aguarde a atualização do alerta.

### Etapa 4 — Confirmar a recuperação

1. Volte ao [Prometheus — Alerts](http://localhost:9090/alerts).
2. Confirme que o alerta deixou de estar em `FIRING`.
3. Verifique se o Alertmanager encaminhou a notificação de resolução.
4. Consulte o [registro de incidentes](http://localhost:8002/incidents).
5. Confirme que o incidente correspondente passou para `RESOLVED`.

Se o alerta continuar ativo, não considere o incidente resolvido. Continue a investigação e verifique as métricas, o tráfego e os logs.

## 4. Evidências a registrar

Para cada execução, registre:

- Horário de início da falha.
- Horário de detecção do alerta.
- Horário de abertura do incidente.
- Evidências observadas no Grafana e nos logs.
- Ação de mitigação executada.
- Horário de resolução.
- Duração total do incidente.

## 5. Encerramento

O incidente pode ser encerrado operacionalmente quando a falha tiver sido mitigada, o sistema apresentar comportamento compatível com a operação normal e a notificação de resolução tiver sido processada.

A causa raiz definitiva e as medidas preventivas devem ser documentadas no postmortem, com base nas evidências coletadas.