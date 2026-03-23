"""Configuración compartida de pytest — CCHEN Observatory"""
import sys
from pathlib import Path

# Asegura que Dashboard/ esté en el path para todos los tests
sys.path.insert(0, str(Path(__file__).parent.parent / "Dashboard"))
