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

import sqlalchemy as sa
import sqlalchemy.orm as orm

UserToken = None


def init_db(model):

    global UserToken
    if UserToken is None:

        class _UserToken(model.DomainObject):

            @classmethod
            def by_user_name(cls, user_name):
                return model.Session.query(cls).filter_by(user_name=user_name).first()

        UserToken = _UserToken

        user_token_table = sa.Table('user_token', model.meta.metadata,
            sa.Column('user_name', sa.UnicodeText, primary_key=True),
            sa.Column('access_token', sa.UnicodeText),
            sa.Column('token_type', sa.UnicodeText),
            sa.Column('refresh_token', sa.UnicodeText),
            sa.Column('expires_in', sa.UnicodeText)
        )

        # Create the table only if it does not exist
        user_token_table.create(checkfirst=True)

        try:
            model.meta.mapper(UserToken, user_token_table)
        except Exception:
            # In newer SQLAlchemy, use orm.mapper if model.meta.mapper is not available
            orm.mapper(UserToken, user_token_table)
