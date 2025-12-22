# TODO List - Snowflake Marketplace App Template

> Objetivo: Transformar este proyecto en un template reutilizable para cualquier aplicación del Snowflake Marketplace.

## Arquitectura Base del Template

Por defecto el template incluye:
- **Backend** (Python/FastAPI)
- **Frontend** (Vue.js)
- **Router** (NGINX reverse proxy)

Todos los containers están comunicados entre sí a través del router.

---

## Ya Implementado (Validar/Mejorar)

| # | Item | Estado | Ubicación |
|---|------|--------|-----------|
| 1 | Manifest template | ✅ Existe | `templates/manifest_template.yml` |
| 2 | Setup SQL template | ✅ Existe | `templates/setup_template.sql` |
| 3 | Dockerfiles (backend/frontend/router) | ✅ Existe | Templatizar más |
| 4 | CI/CD pipelines (QA/Prod) | ✅ Existe | `.github/workflows/` |
| 5 | External Access Integration | ✅ Parcial | Mejorar con template modular |
| 6 | Secret management básico | ✅ Parcial | Usa env vars y GitHub secrets |
| 7 | Docs de deployment | ✅ Existe | `docs/DEPLOYMENT.md` |
| 8 | Local development guide | ✅ Existe | `docs/LOCAL_DEVELOPMENT.md` |

---

## Por Implementar

### 1. DB Migrations

- [ ] Sistema de migraciones SQL versionadas (`migrations/V001__initial.sql`)
- [ ] Script para aplicar migraciones automáticamente en CI/CD
- [ ] Rollback de migraciones
- [ ] Tracking de versión de schema aplicada
- [ ] Template de migración vacío para nuevos cambios

---

### 2. Autoscale Compute Pool

- [ ] Template de compute pool con autoscaling (`templates/compute_pool_template.sql`)
- [ ] Configuración de MIN/MAX nodes parametrizable
- [ ] Políticas de scaling basadas en métricas
- [ ] Documentación de configuración de compute pool
- [ ] Ejemplos de diferentes tamaños (small/medium/large)

---

### 3. Logging Avanzado

- [ ] Integración con Snowflake Event Tables
- [ ] Log forwarding estructurado (JSON)
- [ ] Niveles de log configurables por ambiente
- [ ] Dashboard/queries para análisis de logs
- [ ] Template de event table

---

### 4. Tracking de Usage (CPU/Memory)

- [ ] Queries para monitorear usage del compute pool
- [ ] Alertas de uso excesivo
- [ ] Dashboard de métricas
- [ ] Histórico de consumo para billing
- [ ] Script de reporte de usage

---

### 5. Secret Management Mejorado

- [ ] Documentación completa de secrets requeridos
- [ ] Template de creación de secrets en Snowflake
- [ ] Rotación de secrets
- [ ] Validación de secrets en startup
- [ ] Script para setup de secrets del provider

---

### 6. External Access Integration (EAI)

#### Template Modular de EAI

- [ ] `templates/eai/external_access_template.sql` - Template base
- [ ] `templates/eai/network_rule_template.sql` - Network rules
- [ ] `templates/eai/secret_template.sql` - Secrets para APIs externas
- [ ] Flag en `setup_template.sql` para incluir/excluir EAI
- [ ] Documentación de cuándo y cómo usar EAI

#### Ejemplos Pre-configurados

- [ ] EAI para APIs REST genéricas
- [ ] EAI para OpenAI/LLM providers
- [ ] EAI para webhooks
- [ ] EAI para servicios de storage externos

#### Instrucciones

- [ ] `docs/EXTERNAL_ACCESS.md` - Guía completa de EAI
- [ ] Diagrama de flujo de configuración
- [ ] Troubleshooting de errores comunes de EAI
- [ ] Checklist de seguridad para EAI

---

### 7. Add Container Script

#### Script de Alta de Containers

- [ ] `scripts/add-container.sh` - Script interactivo para agregar nuevo container

```bash
./scripts/add-container.sh --name api-worker --port 8082 --type python
```

- [ ] Genera automáticamente:
  - [ ] `{container_name}/Dockerfile` desde template
  - [ ] Entrada en `docker-compose.yml`
  - [ ] Configuración en `router/nginx.conf`
  - [ ] Entrada en `templates/fullstack_template.yaml`
  - [ ] Variables de entorno en `.env.example`
  - [ ] Entrada en CI/CD (build job)

#### Templates de Containers

- [ ] `templates/containers/python/Dockerfile.template`
- [ ] `templates/containers/node/Dockerfile.template`
- [ ] `templates/containers/go/Dockerfile.template`
- [ ] `templates/containers/nginx.location.template` (para el router)

#### Automatizaciones

- [ ] Auto-registro en el router (nginx.conf)
- [ ] Auto-registro en docker-compose.yml
- [ ] Auto-registro en fullstack_template.yaml
- [ ] Auto-registro en CI/CD pipelines
- [ ] Health check endpoint por defecto
- [ ] Validación de puerto disponible

#### Comandos Adicionales

- [ ] `scripts/remove-container.sh` - Remover container
- [ ] `scripts/list-containers.sh` - Listar containers actuales

---

### 8. Provider Instructions

- [ ] `docs/PROVIDER_SETUP.md` - Guía paso a paso
- [ ] Checklist de pre-requisitos
- [ ] `scripts/provider-init.sh` - Script automatizado de setup
- [ ] Troubleshooting guide
- [ ] Diagrama de arquitectura del provider

---

### 9. Consumer Instructions

- [ ] `docs/CONSUMER_GUIDE.md` - Guía de instalación
- [ ] Configuración post-instalación
- [ ] FAQ de problemas comunes
- [ ] Video/screenshots del proceso
- [ ] Template de `consumer_setup.sql` parametrizable

---

### 10. Template Dockerfiles

- [ ] Dockerfile base parametrizable por lenguaje
- [ ] Multi-stage build optimizado
- [ ] Best practices documentadas
- [ ] ARG/ENV configurables
- [ ] Health check incluido por defecto

---

### 11. How to Run Locally Guide

- [ ] Mejorar `docs/LOCAL_DEVELOPMENT.md`
- [ ] `scripts/local-setup.sh` - Setup one-liner
- [ ] Mock de servicios de Snowflake para testing local
- [ ] Hot-reload habilitado por defecto
- [ ] Instrucciones para debugging

---

### 12. Marketplace Listing Checklist

Crear `checklists/marketplace_listing.md` con todos los campos requeridos:

#### Basic Information

- [ ] App Name
- [ ] Short Description (≤100 chars)
- [ ] Full Description (≤4000 chars)
- [ ] Category
- [ ] Subcategory
- [ ] Tags/Keywords

#### Branding

- [ ] Logo (512x512 PNG)
- [ ] Banner Image (1200x400)
- [ ] Screenshots (min 3, max 10)
- [ ] Demo Video URL (opcional)

#### Documentation Links

- [ ] Documentation URL
- [ ] Support URL
- [ ] Privacy Policy URL
- [ ] Terms of Service URL
- [ ] Release Notes URL

#### Technical Details

- [ ] Minimum Snowflake Edition
- [ ] Required Privileges
- [ ] External Access Requirements
- [ ] Estimated Resource Usage
- [ ] Supported Regions
- [ ] Supported Cloud Providers (AWS/Azure/GCP)

#### Pricing

- [ ] Pricing Model (Free/Paid/Free Trial)
- [ ] Price per month (if paid)
- [ ] Trial duration (if applicable)
- [ ] Usage-based pricing details

#### Support

- [ ] Support Email
- [ ] Support Hours
- [ ] SLA (if applicable)
- [ ] Response Time Commitment

#### Compliance & Security

- [ ] Security Review Completed
- [ ] Data Handling Documentation
- [ ] GDPR Compliance (if applicable)
- [ ] SOC2 Compliance (if applicable)
- [ ] Data Residency Requirements

#### Release Information

- [ ] Initial Version
- [ ] Release Date
- [ ] Changelog documented

---

### 13. Testing Framework

- [ ] Tests de integración para el native app
- [ ] Tests de smoke post-deployment
- [ ] Validación automática de permisos
- [ ] Test de conectividad entre containers

---

### 14. Versioning Strategy

- [ ] Semantic versioning automatizado
- [ ] Changelog generation automático
- [ ] Release notes template
- [ ] Script de bump version

---

### 15. Health Checks Avanzados

- [ ] Endpoint de health check completo (`/health`, `/ready`, `/live`)
- [ ] Verificación de conectividad a Snowflake
- [ ] Status de dependencias externas
- [ ] Health check agregado en el router

---

### 16. Configuration Management

- [ ] Template de `.env` con todas las variables documentadas
- [ ] Validación de configuración al inicio
- [ ] `configure.sh` mejorado (wizard interactivo)
- [ ] Generación automática de `.env` desde template

---

### 17. Security Hardening

- [ ] `checklists/security_review.md`
- [ ] Scan de vulnerabilidades en CI/CD
- [ ] OWASP guidelines checklist
- [ ] Dependabot/Renovate configurado

---

### 18. Consumer Onboarding Automation

- [ ] Script de first-time setup para consumers
- [ ] Wizard interactivo de configuración
- [ ] Validación de setup completo
- [ ] Welcome message/tutorial en la app

---

## Estructura Propuesta del Template

```
marketplace-app-template/
├── .github/
│   └── workflows/
│       ├── deploy-qa.yml
│       └── deploy-prod.yml
├── app/
│   └── src/                    # Generated files
├── backend/                    # Default backend container
│   ├── Dockerfile
│   └── app/
├── frontend/                   # Default frontend container
│   ├── Dockerfile
│   └── src/
├── router/                     # NGINX reverse proxy
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/
│   ├── sql/
│   │   └── migrations/         # DB Migrations
│   ├── add-container.sh        # Add new container
│   ├── remove-container.sh     # Remove container
│   ├── list-containers.sh      # List containers
│   ├── provider-init.sh        # Provider setup
│   └── local-setup.sh          # One-liner local setup
├── templates/
│   ├── manifest_template.yml
│   ├── setup_template.sql
│   ├── fullstack_template.yaml
│   ├── compute_pool_template.sql
│   ├── eai/                            # External Access
│   │   ├── external_access_template.sql
│   │   ├── network_rule_template.sql
│   │   └── secret_template.sql
│   └── containers/                     # Container templates
│       ├── python/
│       │   └── Dockerfile.template
│       ├── node/
│       │   └── Dockerfile.template
│       └── nginx.location.template
├── docs/
│   ├── PROVIDER_SETUP.md
│   ├── CONSUMER_GUIDE.md
│   ├── EXTERNAL_ACCESS.md
│   ├── MONITORING.md
│   ├── DEPLOYMENT.md
│   └── LOCAL_DEVELOPMENT.md
├── checklists/
│   ├── marketplace_listing.md
│   ├── security_review.md
│   └── pre_release.md
├── docker-compose.yml
├── Makefile
├── configure.sh                # Wizard de configuración
├── .env.example
└── README.md
```

---

## Resumen

| Categoría | Items |
|-----------|-------|
| Infraestructura Base (existente) | 8 |
| DB Migrations | 5 |
| Autoscale Compute Pool | 5 |
| Logging | 5 |
| Usage Tracking | 5 |
| Secret Management | 5 |
| External Access Integration | 13 |
| Add Container Script | 15 |
| Provider/Consumer Docs | 10 |
| Template Dockerfiles | 5 |
| Local Development | 5 |
| Marketplace Listing Checklist | 25+ |
| Testing/Versioning/Security | 15 |
| **TOTAL** | **~120 items** |

---

## Notas

- Los items marcados con ✅ ya existen pero pueden necesitar mejoras para ser más genéricos/templatizables.
- La prioridad de implementación puede variar según las necesidades del proyecto.
- Este documento debe actualizarse a medida que se completan los items.
