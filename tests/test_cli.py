import tempfile
import unittest
import unittest.mock
from pathlib import Path
from unittest.mock import patch

import yaml

from rosws import cli


class CreateWorkspaceTests(unittest.TestCase):
    def test_create_workspace_writes_metadata_with_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = cli.Config(
                source_path=str(tmp_path / "source"),
                workspace_path=str(tmp_path / "workspaces"),
                repos={},
            )

            (tmp_path / "source").mkdir()

            cli.create_workspace("demo", [], {}, config, "Example workspace")

            metadata_path = tmp_path / "workspaces" / "demo" / "metadata.yaml"
            self.assertTrue(metadata_path.exists())
            self.assertEqual(
                yaml.safe_load(metadata_path.read_text(encoding="utf-8")),
                {"name": "demo", "description": "Example workspace"},
            )

    def test_create_workspace_writes_metadata_without_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = cli.Config(
                source_path=str(tmp_path / "source"),
                workspace_path=str(tmp_path / "workspaces"),
                repos={},
            )

            (tmp_path / "source").mkdir()

            cli.create_workspace("demo", [], {}, config)

            metadata_path = tmp_path / "workspaces" / "demo" / "metadata.yaml"
            self.assertTrue(metadata_path.exists())
            self.assertEqual(
                yaml.safe_load(metadata_path.read_text(encoding="utf-8")),
                {"name": "demo"},
            )

    def test_cli_passes_description_argument(self):
        with patch("rosws.cli.load_config") as load_config, patch("rosws.cli.create_workspace") as create_workspace:
            load_config.return_value = cli.Config(source_path="/tmp/source", workspace_path="/tmp/workspaces", repos={})

            with patch(
                "sys.argv",
                ["rosws", "create", "demo", "--description", "Example workspace", "repo1:main"],
            ):
                cli.main()

            create_workspace.assert_called_once_with(
                "demo",
                ["repo1"],
                {"repo1": "main"},
                load_config.return_value,
                "Example workspace",
            )


class ListWorkspacesTests(unittest.TestCase):
    def _printed_lines(self, mock_print):
        return [str(c.args[0]) for c in mock_print.call_args_list]

    def test_list_workspaces_with_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            workspaces_path = tmp_path / "workspaces"
            config = cli.Config(
                source_path=str(tmp_path / "source"),
                workspace_path=str(workspaces_path),
                repos={},
            )

            ws1 = workspaces_path / "alpha"
            ws1.mkdir(parents=True)
            (ws1 / "metadata.yaml").write_text(
                "name: alpha\ndescription: Alpha workspace\n", encoding="utf-8"
            )

            ws2 = workspaces_path / "beta"
            ws2.mkdir()
            (ws2 / "metadata.yaml").write_text("name: beta\n", encoding="utf-8")

            with patch("builtins.print") as mock_print:
                cli.list_workspaces(config)

            calls = self._printed_lines(mock_print)
            self.assertIn("alpha - Alpha workspace", calls)
            self.assertIn("beta", calls)
            # alpha should appear before beta (sorted)
            self.assertLess(calls.index("alpha - Alpha workspace"), calls.index("beta"))

    def test_list_workspaces_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            workspaces_path = tmp_path / "workspaces"
            workspaces_path.mkdir()
            config = cli.Config(
                source_path=str(tmp_path / "source"),
                workspace_path=str(workspaces_path),
                repos={},
            )

            with patch("builtins.print") as mock_print:
                cli.list_workspaces(config)

            mock_print.assert_called_once_with("No workspaces found.")

    def test_list_workspaces_invalid_path(self):
        config = cli.Config(
            source_path="/nonexistent/source",
            workspace_path="/nonexistent/workspaces",
            repos={},
        )
        with self.assertRaises(ValueError):
            cli.list_workspaces(config)

    def test_cli_list_command(self):
        with patch("rosws.cli.load_config") as load_config, patch("rosws.cli.list_workspaces") as list_workspaces:
            load_config.return_value = cli.Config(
                source_path="/tmp/source", workspace_path="/tmp/workspaces", repos={}
            )

            with patch("sys.argv", ["rosws", "list"]):
                cli.main()

            list_workspaces.assert_called_once_with(load_config.return_value)

    def test_cli_ls_alias(self):
        with patch("rosws.cli.load_config") as load_config, patch("rosws.cli.list_workspaces") as list_workspaces:
            load_config.return_value = cli.Config(
                source_path="/tmp/source", workspace_path="/tmp/workspaces", repos={}
            )

            with patch("sys.argv", ["rosws", "ls"]):
                cli.main()

            list_workspaces.assert_called_once_with(load_config.return_value)


class WorkspaceCompleterTests(unittest.TestCase):
    def _write_config(self, config_path: Path, workspaces_path: Path, source_path: Path):
        config_path.write_text(
            f"workspace: {workspaces_path}\nrepos:\n  source: {source_path}\n  repos: {{}}\n",
            encoding="utf-8",
        )

    def test_completer_returns_matching_workspaces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            workspaces_path = tmp_path / "workspaces"
            (workspaces_path / "alpha").mkdir(parents=True)
            (workspaces_path / "beta").mkdir()
            (workspaces_path / "gamma").mkdir()

            config_path = tmp_path / "config.yaml"
            self._write_config(config_path, workspaces_path, tmp_path / "source")

            parsed_args = unittest.mock.Mock(config=str(config_path))
            result = cli.workspace_completer("al", parsed_args)
            self.assertEqual(result, ["alpha"])

    def test_completer_returns_all_workspaces_on_empty_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            workspaces_path = tmp_path / "workspaces"
            (workspaces_path / "alpha").mkdir(parents=True)
            (workspaces_path / "beta").mkdir()

            config_path = tmp_path / "config.yaml"
            self._write_config(config_path, workspaces_path, tmp_path / "source")

            parsed_args = unittest.mock.Mock(config=str(config_path))
            result = sorted(cli.workspace_completer("", parsed_args))
            self.assertEqual(result, ["alpha", "beta"])

    def test_completer_returns_empty_on_config_error(self):
        parsed_args = unittest.mock.Mock(config="/nonexistent/config.yaml")
        result = cli.workspace_completer("", parsed_args)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
