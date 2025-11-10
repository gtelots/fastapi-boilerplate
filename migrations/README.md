# Database Migrations

This directory contains Alembic database migrations.

## Creating a new migration

```bash
task db:revision -- "description of changes"
```

## Running migrations

```bash
task db:migrate
```

## Recreating the database (development only)

```bash
task db:recreate
```

