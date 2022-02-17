# -*- coding: utf-8 -*-

import click
import ckanext.oauth2.utils as utils


@click.group()
def oauth2():
    """Oauth2 management commands.
    """
    pass


def get_commands():
    return [oauth2]
