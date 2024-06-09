"""
Test the main module.
"""

from pytest_mock import MockerFixture

from robida.main import init_db_sync, load_entries_sync, run


def test_init_db_sync(mocker: MockerFixture) -> None:
    """
    Test the `init_db_sync` function.
    """
    app = mocker.MagicMock()
    create_app = mocker.patch("robida.main.create_app", return_value=app)
    init_db = mocker.patch("robida.main.init_db")

    init_db_sync()

    create_app.assert_called_once()
    init_db.assert_called_once_with(app)


def test_load_entries_sync(mocker: MockerFixture) -> None:
    """
    Test the `load_entries_sync` function.
    """
    app = mocker.MagicMock()
    create_app = mocker.patch("robida.main.create_app", return_value=app)
    load_entries = mocker.patch("robida.main.load_entries")

    load_entries_sync()

    create_app.assert_called_once()
    load_entries.assert_called_once_with(app)


def test_run(mocker: MockerFixture) -> None:
    """
    Test the `run` function.
    """
    app = mocker.MagicMock()
    create_app = mocker.patch("robida.main.create_app", return_value=app)

    run()

    create_app.assert_called_once()
    app.run.assert_called_once()
