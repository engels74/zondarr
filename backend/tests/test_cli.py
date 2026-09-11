"""The wheel's advertised console entry point must be callable."""

import pytest

from zondarr.cli import main


def test_cli_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["zondarr", "--help"])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    assert "Usage: zondarr" in capsys.readouterr().out
