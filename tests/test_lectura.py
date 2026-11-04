import pytest

from trueprofit.lectura import ErrorDeFormato, leer_pedidos, leer_publicidad

CSV_OK = (
    "id_orden,fecha,estatus,producto,cantidad,total_orden,precio_flete,costo_proveedor\n"
    "1,2026-10-01,ENTREGADO,Lámpara,1,89900,15000,32000\n"
    "2,2026-10-01,DEVOLUCION,Lámpara,2,159800,16000,64000\n"
)


def test_lee_csv_valido_con_bom_de_excel():
    lineas = leer_pedidos(("﻿" + CSV_OK).encode("utf-8"))
    assert len(lineas) == 2
    assert lineas[1].cantidad == 2
    assert lineas[0].producto == "Lámpara"


def test_acepta_punto_y_coma_como_separador():
    lineas = leer_pedidos(CSV_OK.replace(",", ";"))
    assert lineas[0].total_orden == 89_900


def test_columna_faltante_da_error_claro():
    with pytest.raises(ErrorDeFormato, match="costo_proveedor"):
        leer_pedidos("id_orden,estatus,producto,cantidad,total_orden,precio_flete\n1,X,A,1,1,1\n")


def test_numero_invalido_indica_la_fila():
    malo = CSV_OK.replace("89900", "ochenta")
    with pytest.raises(ErrorDeFormato, match="Fila 2"):
        leer_pedidos(malo)


def test_publicidad_suma_varias_filas_del_mismo_producto():
    gasto = leer_publicidad("producto,gasto\nA,1000\nB,500\nA,250\n")
    assert gasto == {"A": 1250, "B": 500}
