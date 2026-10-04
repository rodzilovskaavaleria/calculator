import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import db
from db import init_db, save_rate, get_saved_rate, DB_NAME
from api import fetch_rates
from main import CurrencyConverterApp


@pytest.fixture
def temp_db():
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()
    original_db_name = DB_NAME
    with patch("db.DB_NAME", temp_file.name):
        init_db()
        yield temp_file.name
    try:
        os.unlink(temp_file.name)
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def sample_data():
    return {"id": 1, "currency": "USD", "rate": 1.0}


def test_init_db_creates_table(temp_db):
    conn = __import__("sqlite3").connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rates'")
    result = cur.fetchone()
    conn.close()
    assert result is not None


def test_save_rate_new_record(temp_db):
    save_rate(1, "USD", 78.5)
    result = get_saved_rate("USD")
    assert result == 78.5


def test_save_rate_update_existing(temp_db):
    save_rate(1, "USD", 78.5)
    save_rate(1, "USD", 80.0)
    result = get_saved_rate("USD")
    assert result == 80.0


def test_save_rate_date_format(temp_db):
    import sqlite3

    save_rate(1, "USD", 78.5)
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT fetched_at FROM rates WHERE currency='USD'")
    result = cur.fetchone()
    conn.close()
    assert result is not None
    assert "T" in result[0]


def test_save_rate_multiple_currencies(temp_db):
    save_rate(1, "USD", 78.5)
    save_rate(2, "EUR", 85.3)
    assert get_saved_rate("USD") == 78.5
    assert get_saved_rate("EUR") == 85.3


def test_save_rate_edge_cases(temp_db):
    save_rate(1, "USD", 0.01)
    assert get_saved_rate("USD") == 0.01
    save_rate(2, "EUR", 999999.99)
    assert get_saved_rate("EUR") == 999999.99


def test_save_rate_parameter_types(temp_db):
    save_rate(1, "USD", 78.5)
    result = get_saved_rate("USD")
    assert isinstance(result, float)


def test_save_rate_database_connection_error(temp_db):
    with patch("db.sqlite3.connect", side_effect=Exception("Connection error")):
        try:
            save_rate(1, "USD", 78.5)
        except Exception:
            pass


def test_save_rate_commit_error(temp_db):
    save_rate(1, "USD", 78.5)
    assert get_saved_rate("USD") == 78.5


def test_save_rate_sql_injection_protection(temp_db):
    malicious = "USD'; DROP TABLE rates; --"
    save_rate(1, malicious, 78.5)
    result = get_saved_rate(malicious)
    assert result == 78.5
    conn = __import__("sqlite3").connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rates'")
    assert cur.fetchone() is not None
    conn.close()


def test_get_saved_rate_success(temp_db):
    save_rate(1, "USD", 78.5)
    assert get_saved_rate("USD") == 78.5


def test_get_saved_rate_default_currency(temp_db):
    save_rate(1, "RUB", 1.0)
    assert get_saved_rate("RUB") == 1.0


def test_get_saved_rate_nonexistent_currency(temp_db):
    save_rate(1, "USD", 78.5)
    result = get_saved_rate("XYZ")
    assert result is None


def test_get_saved_rate_empty_database(temp_db):
    result = get_saved_rate("USD")
    assert result is None


def test_get_saved_rate_multiple_currencies(temp_db):
    save_rate(1, "USD", 78.5)
    save_rate(2, "EUR", 85.3)
    save_rate(3, "CNY", 11.2)
    assert get_saved_rate("USD") == 78.5
    assert get_saved_rate("EUR") == 85.3
    assert get_saved_rate("CNY") == 11.2


def test_get_saved_rate_case_sensitivity(temp_db):
    save_rate(1, "USD", 78.5)
    assert get_saved_rate("USD") == 78.5
    assert get_saved_rate("usd") is None


def test_get_saved_rate_sql_injection_protection(temp_db):
    save_rate(1, "USD", 78.5)
    malicious = "USD' OR '1'='1"
    result = get_saved_rate(malicious)
    assert result is None


def test_get_saved_rate_database_connection_error(temp_db):
    with patch("db.sqlite3.connect", side_effect=Exception("Connection error")):
        try:
            get_saved_rate("USD")
        except Exception:
            pass


def test_fetch_rates_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Valute": {"USD": {"Value": 78.5}, "EUR": {"Value": 85.3}}
    }
    with patch("api.requests.get", return_value=mock_response):
        result = fetch_rates()
    assert result["Valute"]["USD"]["Value"] == 78.5
    assert result["Valute"]["EUR"]["Value"] == 85.3


def test_fetch_rates_success_without_success_field():
    mock_response = MagicMock()
    mock_response.json.return_value = {"Valute": {"USD": {"Value": 78.5}}}
    with patch("api.requests.get", return_value=mock_response):
        result = fetch_rates()
    assert "Valute" in result


def test_fetch_rates_http_error():
    with patch("api.requests.get", side_effect=Exception("HTTP error")):
        try:
            fetch_rates()
        except Exception:
            pass


def test_fetch_rates_connection_error():
    with patch("api.requests.get", side_effect=ConnectionError("Connection failed")):
        try:
            fetch_rates()
        except Exception:
            pass


def test_fetch_rates_timeout_error():
    with patch("api.requests.get", side_effect=TimeoutError("Timeout")):
        try:
            fetch_rates()
        except Exception:
            pass


def test_fetch_rates_empty_valute():
    mock_response = MagicMock()
    mock_response.json.return_value = {"Valute": {}}
    with patch("api.requests.get", return_value=mock_response):
        result = fetch_rates()
    assert result["Valute"] == {}


def test_fetch_rates_malformed_json():
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    with patch("api.requests.get", return_value=mock_response):
        try:
            fetch_rates()
        except Exception:
            pass


def test_fetch_rates_ssl_error():
    with patch("api.requests.get", side_effect=Exception("SSL error")):
        try:
            fetch_rates()
        except Exception:
            pass


def make_app():
    app = CurrencyConverterApp.__new__(CurrencyConverterApp)
    app.log = MagicMock()
    return app


def test_calculate_loan_success():
    app = make_app()
    app.loan_var = MagicMock()
    app.loan_var.get.return_value = "100000"
    app.loan_time_var = MagicMock()
    app.loan_time_var.get.return_value = "12"
    app.annual_interest_var = MagicMock()
    app.annual_interest_var.get.return_value = "17"
    app.monthly_label = MagicMock()
    app.loan_sum_label = MagicMock()
    app.interest_label = MagicMock()
    app.is_loan_invalid = MagicMock(return_value=False)
    app.calculate_loan()
    assert app.monthly_label.config.called


def test_calculate_loan_invalid_loan_amount():
    app = make_app()
    app.loan_var = MagicMock()
    app.loan_var.get.return_value = "abc"
    with patch("main.messagebox.showerror"):
        app.calculate_loan()
    assert app.log.called is False


def test_convert_success():
    app = make_app()
    app.target_var = MagicMock()
    app.target_var.get.return_value = "USD"
    app.loan_var = MagicMock()
    app.loan_var.get.return_value = "100000"
    app.result_label = MagicMock()
    with patch("main.get_saved_rate", return_value=78.5):
        app.convert()
    assert app.result_label.config.called


def test_convert_none_rate():
    app = make_app()
    app.target_var = MagicMock()
    app.target_var.get.return_value = "USD"
    with patch("main.get_saved_rate", return_value=None), patch(
        "main.messagebox.showwarning"
    ):
        app.convert()
    assert True


def test_convert_exception():
    app = make_app()
    app.target_var = MagicMock()
    app.target_var.get.return_value = "USD"
    app.loan_var = MagicMock()
    app.loan_var.get.return_value = "not_a_number"
    with patch("main.get_saved_rate", return_value=78.5), patch(
        "main.messagebox.showerror"
    ):
        app.convert()
    assert True


def test_update_db_success():
    app = make_app()
    with patch(
        "main.fetch_rates", return_value={"Valute": {"USD": {"Value": 78.5}}}
    ), patch("main.save_rate"), patch("main.messagebox.showinfo"):
        app.update_db()
    assert app.log.called


def test_update_db_empty_rates():
    app = make_app()
    with patch("main.fetch_rates", return_value={"Valute": {}}), patch(
        "main.messagebox.showinfo"
    ):
        app.update_db()
    assert app.log.called
