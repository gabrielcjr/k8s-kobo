import uuid
import pytest
from app.database import (
    parse_geopoint,
    insert_submission,
    get_all_submissions,
    get_submission_by_uuid,
    get_stats
)

def test_parse_geopoint_all_cases():
    """
    Test coordinate parsing for standard OpenRosa 4-element, 2-element,
    empty strings, and edge cases.
    """
    # Standard 4 components: lat, lon, alt, acc
    lat, lon, alt, acc = parse_geopoint("-12.2570 -38.9640 130.5 4.2")
    assert lat == pytest.approx(-12.2570)
    assert lon == pytest.approx(-38.9640)
    assert alt == pytest.approx(130.5)
    assert acc == pytest.approx(4.2)

    # 2 components (lat, lon)
    lat, lon, alt, acc = parse_geopoint("-12.2570 -38.9640")
    assert lat == pytest.approx(-12.2570)
    assert lon == pytest.approx(-38.9640)
    assert alt is None
    assert acc is None

    # None and empty strings
    assert parse_geopoint(None) == (None, None, None, None)
    assert parse_geopoint("") == (None, None, None, None)
    assert parse_geopoint("   ") == (None, None, None, None)

    # Whitespace padding
    lat, lon, alt, acc = parse_geopoint("  -12.100  -38.200   50.0   2.0  ")
    assert lat == pytest.approx(-12.100)
    assert lon == pytest.approx(-38.200)
    assert alt == pytest.approx(50.0)
    assert acc == pytest.approx(2.0)

def test_database_insert_and_retrieve():
    """
    Test inserting records and verifying retrieval by UUID and list.
    """
    unique_id = f"unit-{uuid.uuid4()}"
    row_id = insert_submission(
        uuid=unique_id,
        form_id="a7FqboN3tiXKPo6hSc8MzJ",
        version="32 (2025-09-12 17:50:03)",
        data_date="2026-10-13",
        nome="Lucas Gabriel",
        idade=29,
        telefone="75988110022",
        genero="Masculino",
        recebeu_jesus="Sim",
        endereco="Rua Teste, 42",
        geopoint="-12.2570 -38.9640 100.0 5.0",
        observacoes="Validação de persistência",
        missionario="Missionário Thiago",
        device_id="test-runner",
        submitted_by="renovamechurch",
        source="kobo_collect",
        raw_xml="<xml>test</xml>"
    )
    assert row_id > 0

    record = get_submission_by_uuid(unique_id)
    assert record is not None
    assert record["id"] == row_id
    assert record["nome"] == "Lucas Gabriel"
    assert record["idade"] == 29
    assert record["telefone"] == "75988110022"
    assert record["missionario"] == "Missionário Thiago"
    assert record["raw_xml"] == "<xml>test</xml>"

def test_database_replace_on_duplicate_uuid():
    """
    OpenRosa/KoBo submissions with duplicate UUID should update/replace rather than crashing.
    """
    shared_uuid = f"dup-{uuid.uuid4()}"
    insert_submission(
        uuid=shared_uuid,
        form_id="a7FqboN3tiXKPo6hSc8MzJ",
        version="32",
        data_date="2026-10-13",
        nome="Primeira Versão",
        idade=20,
        telefone="75999991111",
        genero="Masculino",
        recebeu_jesus="Sim",
        endereco="Rua 1",
        geopoint=None,
        observacoes="Antes",
        missionario="Missionário A",
        device_id="dev-1"
    )

    # Insert again with same UUID and new name
    insert_submission(
        uuid=shared_uuid,
        form_id="a7FqboN3tiXKPo6hSc8MzJ",
        version="32",
        data_date="2026-10-13",
        nome="Segunda Versão Atualizada",
        idade=21,
        telefone="75999991111",
        genero="Masculino",
        recebeu_jesus="Sim",
        endereco="Rua 1",
        geopoint=None,
        observacoes="Depois",
        missionario="Missionário A",
        device_id="dev-1"
    )

    record = get_submission_by_uuid(shared_uuid)
    assert record is not None
    assert record["nome"] == "Segunda Versão Atualizada"
    assert record["idade"] == 21

def test_database_stats_calculation():
    """
    Verify get_stats aggregates counts, dates, decisions, and top missionaries.
    """
    stats = get_stats()
    assert isinstance(stats, dict)
    assert "total" in stats
    assert "today" in stats
    assert "jesus_stats" in stats
    assert "gender_stats" in stats
    assert "top_missionaries" in stats
    
    assert stats["total"] >= 1
    assert isinstance(stats["jesus_stats"], dict)
    assert isinstance(stats["top_missionaries"], list)
    if stats["top_missionaries"]:
        first = stats["top_missionaries"][0]
        assert "name" in first
        assert "count" in first
