# 🚀 Guía de Despliegue - Agente Vendedor

## 📋 Checklist Pre-Despliegue

### ✅ Requisitos del Sistema
- [ ] Servidor con Python 3.8+
- [ ] PostgreSQL 13+ (recomendado para producción)
- [ ] OpenAI API Key válida
- [ ] Dominio configurado (opcional)
- [ ] Certificados SSL (para HTTPS)

### ✅ Verificaciones de Código
- [ ] Todos los tests pasan: `python -m pytest tests/`
- [ ] Variables de entorno configuradas
- [ ] Base de datos migrada
- [ ] Logs configurados correctamente

## 🐳 Despliegue con Docker (Recomendado)

### 1. Crear Dockerfile de Producción

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 2. Docker Compose para Producción

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/agente_vendedor
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=False
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - agente_network

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=agente_vendedor
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    networks:
      - agente_network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - agente_network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - agente_network

volumes:
  postgres_data:
  redis_data:

networks:
  agente_network:
    driver: bridge
```

### 3. Variables de Entorno (.env.prod)

```env
# Base de datos
DB_PASSWORD=your_secure_database_password

# OpenAI
OPENAI_API_KEY=sk-your-production-openai-key

# Aplicación
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=your_super_secure_secret_key_here

# CORS (ajustar según tu dominio)
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]

# Performance
WORKERS=4
MAX_CONNECTIONS=100
TIMEOUT=30

# Monitoreo
SENTRY_DSN=your_sentry_dsn_here
```

### 4. Configuración de Nginx

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8001;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

        # API routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Health check
        location /health {
            proxy_pass http://app;
            access_log off;
        }

        # Static files (if any)
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## 🚀 Comandos de Despliegue

### Despliegue Inicial

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd agente_vendedor

# 2. Configurar variables de entorno
cp env.example .env.prod
# Editar .env.prod con valores de producción

# 3. Construir y levantar servicios
docker-compose -f docker-compose.prod.yml up --build -d

# 4. Verificar que todos los servicios estén corriendo
docker-compose -f docker-compose.prod.yml ps

# 5. Ejecutar migraciones de base de datos
docker-compose -f docker-compose.prod.yml exec app python create_and_migrate.py

# 6. Verificar salud del sistema
curl https://yourdomain.com/health
```

### Comandos de Mantenimiento

```bash
# Ver logs en tiempo real
docker-compose -f docker-compose.prod.yml logs -f app

# Backup de base de datos
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres agente_vendedor > backup_$(date +%Y%m%d_%H%M%S).sql

# Actualizar aplicación
git pull origin main
docker-compose -f docker-compose.prod.yml up --build -d

# Reiniciar servicio específico
docker-compose -f docker-compose.prod.yml restart app

# Escalar aplicación (múltiples instancias)
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

## 🔧 Configuración Manual (Sin Docker)

### 1. Preparar Servidor

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip postgresql nginx

# CentOS/RHEL
sudo yum install python3.11 python3-pip postgresql-server nginx
```

### 2. Configurar Base de Datos

```bash
# Crear usuario y base de datos
sudo -u postgres psql

CREATE USER agente_user WITH ENCRYPTED PASSWORD 'secure_password';
CREATE DATABASE agente_vendedor OWNER agente_user;
GRANT ALL PRIVILEGES ON DATABASE agente_vendedor TO agente_user;
\q
```

### 3. Configurar Aplicación

```bash
# Crear usuario para la aplicación
sudo useradd -m -s /bin/bash agente_app

# Cambiar a usuario de aplicación
sudo su - agente_app

# Clonar repositorio
git clone <repository-url>
cd agente_vendedor

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
# Editar .env con configuración de producción

# Ejecutar migraciones
python create_and_migrate.py
```

### 4. Configurar Servicio Systemd

```ini
# /etc/systemd/system/agente-vendedor.service
[Unit]
Description=Agente Vendedor API
After=network.target

[Service]
Type=exec
User=agente_app
Group=agente_app
WorkingDirectory=/home/agente_app/agente_vendedor
Environment=PATH=/home/agente_app/agente_vendedor/venv/bin
ExecStart=/home/agente_app/agente_vendedor/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Activar y iniciar servicio
sudo systemctl enable agente-vendedor
sudo systemctl start agente-vendedor
sudo systemctl status agente-vendedor
```

## 📊 Monitoreo y Logs

### 1. Configurar Logs

```python
# app/core/logging_config.py
import logging
import logging.handlers
import os

def setup_logging():
    # Crear directorio de logs
    log_dir = "/var/log/agente_vendedor"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar logger principal
    logger = logging.getLogger("agente_vendedor")
    logger.setLevel(logging.INFO)
    
    # Handler para archivo
    file_handler = logging.handlers.RotatingFileHandler(
        f"{log_dir}/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

### 2. Health Checks

```python
# app/api/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
import os

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Endpoint de health check para monitoring"""
    try:
        # Verificar conexión a base de datos
        db.execute("SELECT 1")
        
        # Verificar variables de entorno críticas
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise Exception("OpenAI API Key not configured")
        
        return {
            "status": "healthy",
            "database": "connected",
            "openai": "configured",
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/metrics")
async def metrics():
    """Endpoint para métricas básicas"""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }
```

### 3. Script de Monitoreo

```bash
#!/bin/bash
# scripts/monitor.sh

# Verificar salud del servicio
HEALTH_URL="https://yourdomain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✅ Service is healthy"
else
    echo "❌ Service is unhealthy (HTTP $RESPONSE)"
    # Reiniciar servicio si es necesario
    sudo systemctl restart agente-vendedor
    
    # Enviar notificación (opcional)
    # curl -X POST "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" \
    #      -H 'Content-type: application/json' \
    #      --data '{"text":"Agente Vendedor service restarted due to health check failure"}'
fi

# Verificar espacio en disco
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️  Disk usage is at ${DISK_USAGE}%"
fi

# Verificar logs por errores recientes
ERROR_COUNT=$(tail -1000 /var/log/agente_vendedor/app.log | grep -c "ERROR")
if [ $ERROR_COUNT -gt 10 ]; then
    echo "⚠️  Found $ERROR_COUNT errors in recent logs"
fi
```

## 🔄 Proceso de CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  release:
    types: [ published ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    
    - name: Run security checks
      run: |
        pip install bandit safety
        bandit -r app/
        safety check

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /home/agente_app/agente_vendedor
          git pull origin main
          source venv/bin/activate
          pip install -r requirements.txt
          sudo systemctl restart agente-vendedor
          
          # Verificar que el servicio esté funcionando
          sleep 10
          curl -f http://localhost:8001/health || exit 1
```

## 🔐 Configuración de Seguridad

### 1. SSL/TLS con Let's Encrypt

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renovación
sudo crontab -e
# Agregar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw --force enable

# Bloquear acceso directo al puerto de la aplicación
sudo ufw deny 8001/tcp
```

### 3. Backup Automático

```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="agente_vendedor"

# Backup de base de datos
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Backup de logs
tar -czf $BACKUP_DIR/logs_backup_$DATE.tar.gz /var/log/agente_vendedor/

# Limpiar backups antiguos (mantener últimos 7 días)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

## 🎯 Checklist Post-Despliegue

### ✅ Verificaciones Funcionales
- [ ] Health check responde correctamente
- [ ] API endpoints funcionan
- [ ] Base de datos accesible
- [ ] Logs se generan correctamente
- [ ] SSL/HTTPS configurado

### ✅ Verificaciones de Performance
- [ ] Tiempo de respuesta < 3 segundos
- [ ] Memoria utilizada < 512MB
- [ ] CPU utilización < 30%
- [ ] Conexiones de BD estables

### ✅ Verificaciones de Seguridad
- [ ] Firewall configurado
- [ ] Certificados SSL válidos
- [ ] Variables de entorno protegidas
- [ ] Usuarios no-root
- [ ] Logs sin información sensible

### ✅ Monitoreo y Backup
- [ ] Scripts de monitoreo funcionando
- [ ] Backups automáticos configurados
- [ ] Alertas configuradas
- [ ] Documentación actualizada

---

**Guía de Despliegue Completa**  
**Versión**: 2.0.0  
**Actualizada**: Diciembre 2024  
**Estado**: ✅ Lista para Producción 