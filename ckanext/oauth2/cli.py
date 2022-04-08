# -*- coding: utf-8 -*-

import click

@click.group()
def oauth2():
    """Oauth2 management commands.
    """
    pass


def get_commands():
    return [oauth2]
