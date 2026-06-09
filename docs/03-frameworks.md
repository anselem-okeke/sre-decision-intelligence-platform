# Frameworks and Technology Choices

## API framework

### FastAPI

FastAPI is used for the API layer.

Reasons:

- clean Python API design
- automatic OpenAPI documentation
- strong Pydantic integration
- good async support
- easy testing with pytest

## Schema validation

### Pydantic

Pydantic is used for request and response models.

It defines the structure of:

- signals
- incidents
- evidence
- decisions
- SLOs
- safe actions

This keeps the Decision Intelligence output stable and predictable.

## HTTP client

### httpx

httpx is used for external API calls.

Initial targets:

- Prometheus HTTP API
- OpenSearch API
- Argo CD API later

## Kubernetes integration

### kubernetes Python client

The Kubernetes Python client is used to query runtime state.

Initial objects:

- Services
- Endpoints
- Pods
- Deployments

This allows the platform to detect situations such as:

```text
frontend pod is running
but frontend Service has no endpoints
```

## Database

### PostgreSQL

PostgreSQL is the only database used for persistence.

The platform may store:

- incident records
- collected signals
- evidence snapshots
- decision outputs
- rule evaluation history

SQLite is intentionally not used.

## ORM

### SQLAlchemy

SQLAlchemy is used for the database access layer.

It provides:

- model definitions
- query abstraction
- repository layer support

## Database migrations

### Alembic

Alembic is used for database schema migrations.

This allows the schema to evolve safely as the platform grows.

## Rule system

### YAML rules plus Python evaluator

The first version uses simple YAML-based rules and a Python evaluator.

This keeps the system transparent and easy to explain.

Example rule logic:

```text
IF probe_success = 0
AND frontend endpoints are empty
AND frontend pod is running
THEN likely root cause = Service selector mismatch
```

## Testing

### pytest

pytest is used for unit and integration tests.

Initial tests:

- health endpoint test
- Prometheus collector test
- Kubernetes collector test
- correlation rule test
- decision engine test

## Local runtime

### Docker Compose

Docker Compose is used for local development.

Initial services:

- decision-intelligence-api
- PostgreSQL

Later, mock services may be added for Prometheus and OpenSearch test scenarios.
