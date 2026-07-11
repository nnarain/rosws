# rosws

Git Worktree and ROS Workspace Management Tool

## Installation

```bash
pip install .
```

## Usage

```
rosws [-c CONFIG] <command> [options]
```

### Commands

**create** – Create a new workspace with git worktrees for the specified repositories:

```bash
rosws create <name> [repo[:branch] ...]
```

**add** – Add a repository worktree to an existing workspace:

```bash
rosws add <name> <repo[:branch]>
```

**rm** – Remove a workspace and all its associated worktrees:

```bash
rosws rm <name>
```

## Configuration

By default, `rosws` reads its configuration from `~/.config/rosws/config.yaml`.
A custom path can be supplied with the `--config`/`-c` flag.

Example configuration:

```yaml
workspace: ~/workspaces

repos:
  source: ~/src
  repos:
    my_package:
      distros:
        ros2: main
```
