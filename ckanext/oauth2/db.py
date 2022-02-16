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
import ckan.model.meta as meta
import logging
from ckan.model.domain_object import DomainObject
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)

Base = declarative_base()
metadata = Base.metadata


class UserToken(Base, DomainObject):
    __tablename__ = 'user_token'

    def __init__(self, user_name, access_token, token_type, refresh_token, expires_in):
        self.user_name = user_name
        self.access_token = access_token
        self.token_type = token_type
        self.refresh_token = refresh_token
        self.expires_in = expires_in

    @classmethod
    def by_user_name(cls, user_name):
        return meta.Session.query(cls).filter_by(user_name=user_name).first()


    user_name = sa.Column(sa.types.UnicodeText, primary_key=True)
    access_token = sa.Column(sa.types.UnicodeText)
    token_type = sa.Column(sa.types.UnicodeText)
    refresh_token = sa.Column(sa.types.UnicodeText)
    expires_in = sa.Column(sa.types.UnicodeText)
