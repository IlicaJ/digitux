#!/bin/bash
# Lanzador portable: usa el directorio donde está este script
cd "$(dirname "$0")"
exec python3 -m nexus.ui.main
