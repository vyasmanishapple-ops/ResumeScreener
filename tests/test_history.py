from database.repositories import normalize_email

def test_normalize_email():
    assert normalize_email(
        " Test@Example.COM "
    ) == "test@example.com"
