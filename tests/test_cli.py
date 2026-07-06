import main


def test_no_args_is_non_fatal(capsys):
    assert main.main([]) == 0
    captured = capsys.readouterr()
    assert "Auto Takeoff Agent is installed and ready." in captured.out
    assert "--input INPUT" in captured.out
