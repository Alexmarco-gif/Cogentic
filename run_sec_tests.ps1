$tests = @(
    "tests/test_security.py::TestWebhookHMAC::test_wrong_signature_returns_401",
    "tests/test_security.py::TestWebhookHMAC::test_tampered_body_rejected",
    "tests/test_security.py::TestOrgIsolation::test_cannot_create_key_for_other_org"
)
& ".\.venv\Scripts\python.exe" -m pytest @tests --tb=short -v 2>&1
