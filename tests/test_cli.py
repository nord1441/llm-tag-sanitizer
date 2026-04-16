"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from tests.conftest import create_mp3
from llm_tag_sanitizer.cli import main


class TestCLI:
    @patch("llm_tag_sanitizer.cli.OllamaClient")
    def test_dry_run_no_files(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.check_model.return_value = True
        mock_client_cls.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path), "--model", "test"])
        assert result.exit_code == 0
        assert "No music files found" in result.output

    @patch("llm_tag_sanitizer.cli.OllamaClient")
    def test_dry_run_with_files(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.check_model.return_value = True
        mock_client.query_json.return_value = None
        mock_client_cls.return_value = mock_client

        create_mp3(
            tmp_path / "song.mp3",
            {"artist": "Queen", "title": "Test", "album": "Album"},
        )

        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path), "--model", "test"])
        assert result.exit_code == 0

    @patch("llm_tag_sanitizer.cli.OllamaClient")
    def test_model_not_found(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.check_model.return_value = False
        mock_client.list_models.return_value = ["llama3.1:latest"]
        mock_client_cls.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path), "--model", "nonexistent"])
        assert result.exit_code != 0

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert "0.1.0" in result.output

    @patch("llm_tag_sanitizer.cli.OllamaClient")
    def test_unknown_optimizer(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.check_model.return_value = True
        mock_client_cls.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(tmp_path), "--model", "test", "--optimizers", "invalid_opt"],
        )
        assert result.exit_code != 0
