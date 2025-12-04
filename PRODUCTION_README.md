# 🚀 Production Deployment Guide

Questa guida copre il deployment completo in produzione del Trading Agent con alta disponibilità, sicurezza e monitoraggio.

## 📋 Prerequisiti

### Sistema
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **SSL Certificates**: Let's Encrypt o certificati validi
- **Domain**: Dominio registrato con DNS configurato
- **Server**: 4GB RAM minimo, 2 vCPU, 50GB storage

### Sicurezza
- **Firewall**: Aperti solo porte 80, 443
- **SSH**: Configurato con chiavi, no password
- **Updates**: Sistema aggiornato regolarmente

## 🔧 Setup Iniziale

### 1. Clona e configura
```bash
git clone <repository>
cd trading-agent

# Copia configurazione produzione
cp env.prod.example .env.prod

# Modifica con i tuoi valori
nano .env.prod
```

### 2. Configura SSL
```bash
# Crea directory SSL
mkdir -p ssl/production

# Ottieni certificati Let's Encrypt (esempio)
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# Copia certificati
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/production/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/production/
```

### 3. Configura Nginx
```bash
# Modifica nginx.conf con il tuo dominio
nano nginx/nginx.conf
# Cambia 'server_name _;' con 'server_name yourdomain.com;'
```

## 🚀 Deployment

### Deploy Automatico (Raccomandato)
```bash
# Deploy completo con backup e health checks
./production-deploy.sh
```

### Deploy Manuale
```bash
# Build e avvia
export TAG=$(date +%Y%m%d-%H%M%S)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d

# Verifica
docker compose -f docker-compose.prod.yml ps
curl -f https://yourdomain.com/api/health
```

## 📊 Monitoraggio

### Accessi
- **App**: https://yourdomain.com
- **Grafana**: https://yourdomain.com:3000 (admin / password da .env.prod)
- **Prometheus**: https://yourdomain.com:9090

### Metriche Chiave
- **Uptime**: Applicazione sempre online
- **Response Time**: < 500ms API calls
- **Error Rate**: < 1% errori
- **Database**: Connessioni attive, query lente

### Alert Configurazione
```yaml
# monitoring/prometheus/alert_rules.yml
groups:
  - name: trading_alerts
    rules:
      - alert: AppDown
        expr: up{job="trading-agent"} == 0
        for: 5m
        labels:
          severity: critical
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
```

## 🔒 Sicurezza

### Best Practices Implementate
- ✅ **User non-root**: Container gira con user limitato
- ✅ **Read-only filesystem**: No scrittura su filesystem
- ✅ **Security headers**: XSS, CSRF, frame protection
- ✅ **Rate limiting**: Protezione DDoS
- ✅ **SSL/TLS**: Crittografia end-to-end
- ✅ **Secrets**: Password in environment variables

### Ulteriori Misure
```bash
# Scansiona vulnerabilità
docker scan trading-agent:latest

# Audit container
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive trading-agent:latest

# Security scan
trivy image trading-agent:latest
```

## 🔄 Backup & Recovery

### Backup Automatico
```bash
# Configura cron per backup giornaliero
crontab -e
# Aggiungi: 0 2 * * * cd /path/to/trading-agent && docker compose -f docker-compose.prod.yml run --rm backup
```

### Recovery
```bash
# Stop app
docker compose -f docker-compose.prod.yml stop app

# Restore database
docker compose -f docker-compose.prod.yml exec db psql -U trading_user trading_db < backup.sql

# Restart
docker compose -f docker-compose.prod.yml start app
```

## 📈 Scalabilità

### Horizontal Scaling
```yaml
# docker-compose.prod.override.yml
services:
  app:
    deploy:
      replicas: 3  # Aumenta per più traffico
      placement:
        constraints:
          - node.role == worker
```

### Vertical Scaling
```bash
# Aumenta risorse container
docker compose -f docker-compose.prod.yml up -d --scale app=3
```

## 🔧 Manutenzione

### Update Routine
```bash
# 1. Backup
./production-deploy.sh  # Include backup automatico

# 2. Deploy nuova versione
git pull origin main
./production-deploy.sh

# 3. Verifica
curl -f https://yourdomain.com/api/health
```

### Log Rotation
```bash
# Configurato automaticamente in docker-compose.prod.yml
# Logs ruotati ogni 50MB, mantenuti ultimi 10 file
```

### Performance Monitoring
```bash
# CPU/Memory usage
docker stats

# Container logs
docker compose -f docker-compose.prod.yml logs -f app

# Database performance
docker compose -f docker-compose.prod.yml exec db psql -U trading_user -c "SELECT * FROM pg_stat_activity;"
```

## 🚨 Troubleshooting

### App non si avvia
```bash
# Controlla logs
docker compose -f docker-compose.prod.yml logs app

# Verifica health
docker compose -f docker-compose.prod.yml exec app curl http://localhost:5611/api/health

# Debug mode
docker compose -f docker-compose.prod.yml exec app bash
```

### Database problemi
```bash
# Controlla connessione
docker compose -f docker-compose.prod.yml exec db pg_isready -U trading_user

# Logs database
docker compose -f docker-compose.prod.yml logs db
```

### Alta latenza
```bash
# Profile app
docker compose -f docker-compose.prod.yml exec app py-spy top --pid $(pgrep -f uvicorn)

# Database slow queries
docker compose -f docker-compose.prod.yml exec db psql -U trading_user -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## 📞 Supporto

### Log Locations
- **App**: `/app/logs/trading_agent.log`
- **Nginx**: `/var/log/nginx/`
- **Database**: PostgreSQL logs interni

### Useful Commands
```bash
# Full restart
docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d

# Update singolo servizio
docker compose -f docker-compose.prod.yml up -d app

# Backup manuale
docker compose -f docker-compose.prod.yml run --rm backup
```

## 🎯 Checklist Deploy

- [ ] `.env.prod` configurato
- [ ] SSL certificates installati
- [ ] Domain DNS configurato
- [ ] Firewall configurato (solo 80,443)
- [ ] Backup iniziale creato
- [ ] Monitoring configurato
- [ ] Health checks funzionanti
- [ ] Primo deploy completato
- [ ] Accesso verificato

---

**🚀 Pronto per produzione!** Il sistema è configurato per alta disponibilità, sicurezza e monitoraggio completo.
