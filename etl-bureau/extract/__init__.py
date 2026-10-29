"""Extractores ETL: se importan como `from extract import <modulo>`.

Re-exports explicitos para resolucion estatica (pyright) de los
modulos agregados en la rotacion del 28-oct; el resto se resuelve
como submodulos por compatibilidad historica.
"""

from extract import aerocivil_flota as aerocivil_flota
from extract import aire_med as aire_med
from extract import eurostat_capacity as eurostat_capacity
from extract import eurostat_demanda as eurostat_demanda
from extract import rnt_antioquia as rnt_antioquia
from extract import terminales_med as terminales_med
from extract import wb_departures as wb_departures
