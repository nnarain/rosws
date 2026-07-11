#!/usr/bin/env python3
#
# @author: Natesh Narain
#

#
# Git Worktree and ROS Workspace Management Tool
#

import os
import shutil
import subprocess
from argparse import ArgumentParser
from dataclasses import dataclass
import yaml
from pathlib import Path
from typing import Optional

@dataclass
class Repo:
    # The name of the repository
    name: str
    # distro to branch mapping for the repository
    distros: dict[str, str]

@dataclass
class Config:
    # The location of the source code for the workspace
    source_path: str
    # The location of the workspace itself
    workspace_path: str
    # Repositories to include in the workspace
    repos: dict[str, Repo]

def cmd_create(args):
    config = load_config(args.config)
    repos, branches = parse_repo_args(args.repos)
    create_workspace(args.name, repos, branches, config)

def cmd_add(args):
    config = load_config(args.config)
    repos, branches = parse_repo_args([args.repo])
    add_repo_to_workspace(args.name, repos[0], branches.get(repos[0]), config)

def cmd_rm(args):
    config = load_config(args.config)
    remove_workspace(args.name, config)

def parse_repo_args(repo_args: list[str]) -> tuple[list[str], dict[str, str]]:
    """Parse a list of 'repo' or 'repo:branch' strings.

    Returns a tuple of (repo_names, branch_map) where branch_map maps repo
    names to their explicitly specified branch (if any).
    """
    repos = []
    branches = {}
    for entry in repo_args:
        if ':' in entry:
            repo_name, branch = entry.split(':', 1)
            repo_name = repo_name.strip()
            branch = branch.strip()
            repos.append(repo_name)
            if branch:
                branches[repo_name] = branch
        else:
            repos.append(entry.strip())
    return repos, branches

def create_workspace(name: str, repos: list[str], branches: dict[str, str], config: Config):
    print(f"Creating workspace '{name}' with repositories {repos}")
    print(f"Using source path: {config.source_path}")
    print(f"Using workspace path: {config.workspace_path}")
    # Create the workspace directory under the configured directory for workspaces
    workspace_path = Path(config.workspace_path) / name
    os.makedirs(workspace_path, exist_ok=True)

    # Create the source directory under the configured directory for source code
    workspace_source_path = workspace_path / "src"
    os.makedirs(workspace_source_path, exist_ok=True)

    # Repository source directory is the configured source path
    source_path = Path(config.source_path)
    known_repos = get_all_repos_in_source_path(source_path)

    # Create worktrees for each repository in the source directory
    for repo in repos:
        add_worktree(name, repo, branches.get(repo), source_path, known_repos, workspace_source_path, config)

def add_repo_to_workspace(name: str, repo: str, branch: Optional[str], config: Config):
    workspace_path = Path(config.workspace_path) / name
    if not workspace_path.exists():
        raise ValueError(f"Workspace '{name}' does not exist at '{workspace_path}'")

    workspace_source_path = workspace_path / "src"
    os.makedirs(workspace_source_path, exist_ok=True)

    source_path = Path(config.source_path)
    known_repos = get_all_repos_in_source_path(source_path)

    add_worktree(name, repo, branch, source_path, known_repos, workspace_source_path, config)

def add_worktree(
    workspace_name: str,
    repo: str,
    branch: Optional[str],
    source_path: Path,
    known_repos: set[str],
    workspace_source_path: Path,
    config: Config,
):
    if repo not in known_repos:
        raise ValueError(f"Repository '{repo}' not found in source path '{source_path}'")

    # Path to the repository
    repo_source_path = source_path / repo

    # Determine base branch: explicit > current branch
    base_branch = branch if branch else get_current_branch(repo_source_path)

    # Path to the repository in the workspace
    workspace_repo_path = workspace_source_path / repo
    # Feature branch name for the worktree
    branch_name = workspace_name
    subprocess.run(
        ["git", "-C", str(repo_source_path), "worktree", "add", str(workspace_repo_path), "-b", branch_name, base_branch],
        check=True,
    )

def remove_workspace(name: str, config: Config):
    workspace_path = Path(config.workspace_path) / name
    if not workspace_path.exists():
        raise ValueError(f"Workspace '{name}' does not exist at '{workspace_path}'")

    source_path = Path(config.source_path)
    workspace_source_path = workspace_path / "src"

    # Remove all worktrees associated with this workspace
    if workspace_source_path.exists():
        for repo_path in workspace_source_path.iterdir():
            if repo_path.is_dir():
                repo_name = repo_path.name
                repo_source_path = source_path / repo_name
                if repo_source_path.exists():
                    subprocess.run(
                        ["git", "-C", str(repo_source_path), "worktree", "remove", str(repo_path), "--force"],
                        check=True,
                    )

    # Remove the workspace directory
    shutil.rmtree(workspace_path)
    print(f"Removed workspace '{name}'")

def get_current_branch(repo_path: Path) -> str:
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_path}")
    if not (repo_path / ".git").exists():
        raise ValueError(f"Repository path is not a git repository: {repo_path}")

    result = subprocess.run(
        ["git", "-C", str(repo_path), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not result:
        raise RuntimeError(f"Failed to get current branch for repository at {repo_path}")
    return result

def get_all_repos_in_source_path(source_path: str) -> set[str]:
    source_path = Path(source_path)
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"Source path does not exist or is not a directory: {source_path}")

    repos = set([])
    for item in source_path.iterdir():
        if item.is_dir() and (item / ".git").exists():
            repos.add(Path(item).name)
    return repos

def load_config(config_path: Optional[str]) -> Config:
    default_config_path = Path.home() / ".config" / "rosws" / "config.yaml"
    resolved_config_path = Path(config_path).expanduser() if config_path else default_config_path

    if not resolved_config_path.exists():
        raise FileNotFoundError(f"Config file not found: {resolved_config_path}")

    with resolved_config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Config file must contain a YAML mapping at the top level")

    repos_config = config.get("repos")
    workspace_path = config.get("workspace")

    if not isinstance(repos_config, dict):
        raise ValueError("Config value 'repos' must be a mapping")

    source_path = repos_config.get("source")
    repos = repos_config.get("repos")

    if not isinstance(source_path, str) or not source_path.strip():
        raise ValueError("Config value 'repos.source' must be a non-empty string")
    if not isinstance(workspace_path, str) or not workspace_path.strip():
        raise ValueError("Config value 'workspace' must be a non-empty string")
    if not isinstance(repos, dict):
        raise ValueError("Config value 'repos.repos' must be a mapping")

    parsed_repos = {}
    for repo_name, repo_config in repos.items():
        if not isinstance(repo_name, str) or not repo_name.strip():
            raise ValueError("Repository names in 'repos.repos' must be non-empty strings")
        if not isinstance(repo_config, dict):
            raise ValueError(f"Config for repository '{repo_name}' must be a mapping")

        distros = repo_config.get("distros")
        if not isinstance(distros, dict):
            raise ValueError(f"Config value 'repos.repos.{repo_name}.distros' must be a mapping")

        normalized_distros = {}
        for distro_name, branch_name in distros.items():
            if not isinstance(distro_name, str) or not distro_name.strip():
                raise ValueError(f"Distro names for repository '{repo_name}' must be non-empty strings")
            if not isinstance(branch_name, str) or not branch_name.strip():
                raise ValueError(
                    f"Branch name for repository '{repo_name}' distro '{distro_name}' must be a non-empty string"
                )
            normalized_distros[distro_name] = branch_name

        parsed_repos[repo_name] = Repo(name=repo_name, distros=normalized_distros)

    return Config(source_path=source_path, workspace_path=workspace_path, repos=parsed_repos)

def main():
    parser = ArgumentParser(description='rosws command line tool')
    parser.add_argument('--config', '-c', type=str, help='Path to the user configuration file', required=False)

    subparsers = parser.add_subparsers(dest='command', metavar='<command>')
    subparsers.required = True

    # create subcommand
    create_parser = subparsers.add_parser('create', help='Create a new workspace')
    create_parser.add_argument('name', type=str, help='Name of the workspace')
    create_parser.add_argument(
        'repos',
        nargs='*',
        metavar='repo[:branch]',
        help='Repositories to include; optionally specify a base branch with repo:branch',
    )
    create_parser.set_defaults(func=cmd_create)

    # add subcommand
    add_parser = subparsers.add_parser('add', help='Add a repository to an existing workspace')
    add_parser.add_argument('name', type=str, help='Name of the workspace')
    add_parser.add_argument(
        'repo',
        type=str,
        metavar='repo[:branch]',
        help='Repository to add; optionally specify a base branch with repo:branch',
    )
    add_parser.set_defaults(func=cmd_add)

    # rm subcommand
    rm_parser = subparsers.add_parser('rm', help='Remove a workspace and its worktrees')
    rm_parser.add_argument('name', type=str, help='Name of the workspace to remove')
    rm_parser.set_defaults(func=cmd_rm)

    args = parser.parse_args()

    try:
        args.func(args)
    except Exception as e:
        print("Error: %s" % e)
        exit(1)

if __name__ == '__main__':
    main()
