import tempfile
import unittest
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

    def test_main_passes_description_to_create_workspace(self):
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


if __name__ == "__main__":
    unittest.main()
