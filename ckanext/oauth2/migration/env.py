"""Alembic environment for ckanext-oauth2 migrations."""

from alembic import context

# This env.py follows the CKAN extension migration pattern.
# Migrations are invoked via: ckan db upgrade -p oauth2


def run_migrations_offline():
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = context.config.attributes.get("connection")
    if connectable is None:
        raise RuntimeError("No connection provided to migration context")

    context.configure(connection=connectable, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
