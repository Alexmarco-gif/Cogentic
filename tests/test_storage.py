from backend.storage import parse_s3_path


def test_parse_s3_uri():
    parsed = parse_s3_path("s3://cogent-docs/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.key == "org/file.pdf"


def test_parse_s3_path_style_uri():
    parsed = parse_s3_path("https://s3.amazonaws.com/cogent-docs/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.key == "org/file.pdf"


def test_parse_s3_virtual_hosted_uri():
    parsed = parse_s3_path("https://cogent-docs.s3.amazonaws.com/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.key == "org/file.pdf"


def test_parse_s3_regional_virtual_hosted_uri():
    parsed = parse_s3_path("https://cogent-docs.s3.eu-west-2.amazonaws.com/org/file.pdf")

    assert parsed is not None
    assert parsed.bucket == "cogent-docs"
    assert parsed.key == "org/file.pdf"


def test_parse_rejects_non_s3_uri():
    assert parse_s3_path("https://example.com/file.pdf") is None
