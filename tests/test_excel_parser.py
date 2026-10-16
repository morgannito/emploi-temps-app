from unittest.mock import patch

import pandas as pd

from excel_parser import ExcelScheduleParser


def _sheet():
    return pd.DataFrame([
        ["LUNDI", None, None, None],
        [None, "Professeur", "Horaire", "Type"],
        [None, "Dupont", "8h-10h", "TD"],
        [None, "Dupont", "25h-26h", "TD"],
        [None, "Martin", "10h-12h", "CM"],
        [None, None, None, None],
        [None, "Apres", "14h-15h", "CM"],
    ])


def test_heure_hors_bornes_renvoie_none():
    assert ExcelScheduleParser("x").parse_time_range("25h-26h") is None


def test_ligne_invalide_ignoree_sans_couper_le_bloc():
    with patch("excel_parser.pd.read_excel", return_value=_sheet()):
        data = ExcelScheduleParser("x").parse_sheet("S1")
    profs = data["professors"]
    assert [c["start_time"] for c in profs["Dupont"]] == ["08:00"]
    assert profs["Martin"][0]["start_time"] == "10:00"
    assert "Apres" not in profs  # ligne vide = fin de bloc
