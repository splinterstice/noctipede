# Noctipede Service - Static Requirements

## Project Overview
- **Service Name**: Noctipede
- **Project Path**: ~/sources/splinter/noctipede
- **Service Type**: Tor/I2P/Clearnet Crawler with AI Analysis
- **Last Updated**: 2025-07-08

## Non-Negotiable Constants
<!-- These values must NEVER change during development -->

### Core Architecture
- [x] Service type/pattern: Multi-network crawler (Tor/I2P/Clearnet) with AI analysis
- [x] Configuration source: k8s/configmap.yaml (NEVER change this file name/location)
- [x] Deployment method: `make ghcr-deploy` followed by k8s/destroy.sh then k8s/deploy.sh
- [x] Readiness endpoint: `/api/readiness` (crawler dependency)

### Network Requirements (CRITICAL)
- [x] Clearnet crawling: MUST ALWAYS use Tor proxy (NEVER direct clearnet access)
- [x] Simultaneous crawling: Tor AND I2P must crawl simultaneously (no idle tunnels)
- [x] Site distribution: Multiple different sites, NOT same site multiple times

### API Specifications (DO NOT RENAME)
- [x] Dashboard API: Nearly complete - AVOID renaming any existing endpoints
- [x] Readiness check: `/api/readiness`
- [x] Base URL pattern: (preserve existing structure)

### AI Analysis Requirements
- [x] AI models: Defined in configmap.yaml - NEVER change these models
- [x] Concurrent operation: AI analysis must run simultaneously with crawler
- [x] Database safety: Must avoid MariaDB errors during concurrent AI analysis

### Scaling Constraints
- [x] Maximum instances: 10 crawler instances supported
- [x] Instance distribution: Each instance crawls different sites
- [x] Concurrent processing: Crawler + AI analysis must run together safely

### Database Requirements
- [x] Database type: MariaDB
- [x] Concurrency handling: Must prevent errors during simultaneous crawler/AI operations
- [x] Connection management: Handle multiple crawler instances safely

## Configuration Values
<!-- Static configuration that should remain consistent -->

### Critical File Names (NEVER RENAME)
- [x] Configuration: `k8s/configmap.yaml`
- [x] Deployment script: `k8s/deploy.sh`
- [x] Destruction script: `k8s/destroy.sh`
- [x] Build command: `make ghcr-deploy`
- [x] Kubernetes services: DO NOT rename any existing services

### Deployment Workflow (FIXED SEQUENCE)
1. Make changes to application
2. Run `make ghcr-deploy` (builds and pushes image)
3. Wait for GitHub push completion
4. Run `k8s/destroy.sh`
5. Run `k8s/deploy.sh`

### Network Configuration
- [x] Tor proxy: Required for ALL clearnet traffic
- [x] I2P tunnel: Must remain active during crawling
- [x] Simultaneous operation: Both networks crawl concurrently

### AI Models (FROM CONFIGMAP.YAML - DO NOT MODIFY)
```yaml
# Models are defined in k8s/configmap.yaml
# These model configurations must NEVER change
# (Actual model list to be preserved from existing configmap.yaml)
```

## Development Guidelines
<!-- Rules for maintaining consistency -->

### Code Standards
- [ ] Coding style/linting rules:
- [ ] Testing requirements:
- [ ] Documentation standards:

### Deployment Constraints
- [ ] Target environment:
- [ ] Resource allocation:
- [ ] Scaling policies:

---
## Usage Instructions
1. Fill out the checkboxes above with your specific requirements
2. Reference this file at the start of each development session
3. Update the "Last Updated" date when making changes
4. Never modify values marked as "Non-Negotiable" without explicit discussion

## Quick Reference Command
To have Amazon Q read this file: Ask me to read `~/sources/splinter/noctipede/SERVICE_REQUIREMENTS.md`
