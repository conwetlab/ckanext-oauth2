# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of OAuth2 CKAN Extension.

# OAuth2 CKAN Extension is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OAuth2 CKAN Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with OAuth2 CKAN Extension.  If not, see <http://www.gnu.org/licenses/>.

import logging

import sqlalchemy as sa
import ckan.model as model
from ckan.model import domain_object

log = logging.getLogger(__name__)

_mapper_registry = sa.orm.registry()

UserToken = None


def init_db():
    """Initialize the user_token table and ORM mapping.

    Table creation is handled by Alembic migrations. This function only
    sets up the ORM mapping so that UserToken can be used as a model class.
    """
    global UserToken
    if UserToken is not None:
        return

    class _UserToken(domain_object.DomainObject):

        @classmethod
        def by_user_name(cls, user_name):
            return model.Session.query(cls).filter_by(user_name=user_name).first()

    UserToken = _UserToken

    user_token_table = sa.Table(
        'user_token', model.meta.metadata,
        sa.Column('user_name', sa.UnicodeText, primary_key=True),
        sa.Column('access_token', sa.UnicodeText),
        sa.Column('token_type', sa.UnicodeText),
        sa.Column('refresh_token', sa.UnicodeText),
        sa.Column('expires_in', sa.UnicodeText),
        extend_existing=True,
    )

    _mapper_registry.map_imperatively(UserToken, user_token_table)
