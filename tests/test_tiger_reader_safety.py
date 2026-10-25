from pathlib import Path

from data.tiger import main


def test_connection_valueerror_is_redacted(monkeypatch,capsys):
    import data.tiger as tiger
    def bad_connection(*args,**kwargs):
        raise ValueError('postgres://login:PRIVATE-PASSWORD@private-host/db')
    monkeypatch.setattr(tiger,'connect',bad_connection)
    assert main(['check'])==1
    output=capsys.readouterr().out
    assert 'PRIVATE-PASSWORD' not in output and 'private-host' not in output
    assert 'ValueError' in output
