from backend.storage import parse_gcs_path


def test_parse_gs_uri():
    parsed = parse_gcs_path("gs://cogent-docs/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.name == "org/file.pdf"


def test_parse_storage_googleapis_path_uri():
    parsed = parse_gcs_path("https://storage.googleapis.com/cogent-docs/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.name == "org/file.pdf"


def test_parse_virtual_hosted_storage_uri():
    parsed = parse_gcs_path("https://cogent-docs.storage.googleapis.com/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.name == "org/file.pdf"


def test_parse_rejects_non_gcs_uri():
    assert parse_gcs_path("https://example.com/file.pdf") is None
