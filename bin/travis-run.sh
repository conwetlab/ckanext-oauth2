#!/usr/bin/env bash

if [ "${INTEGRATION_TEST}" = "true" ]; then
    xvfb-run --server-args="-screen 0 1280x1024x24" python setup.py nosetests
else
    python setup.py nosetests
fi
