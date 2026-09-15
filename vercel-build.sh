#!/usr/bin/env bash
set -e
# Install OS dependencies needed by WeasyPrint
apt-get update -y
apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev
# Install Python dependencies
pip install -r requirements.txt
