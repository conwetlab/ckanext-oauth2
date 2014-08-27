import sqlalchemy as sa

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
            sa.Column('user_name', sa.types.UnicodeText, primary_key=True),
            sa.Column('access_token', sa.types.UnicodeText),
            sa.Column('token_type', sa.types.UnicodeText),
            sa.Column('refresh_token', sa.types.UnicodeText),
            sa.Column('expires_in', sa.types.UnicodeText)
        )

        # Create the table only if it does not exist
        user_token_table.create(checkfirst=True)

        model.meta.mapper(UserToken, user_token_table)
