# Copyright 2019 Simone Rubino - Agile Business Group
# Distributed under the MIT License (http://opensource.org/licenses/MIT).

import json
import shutil
import subprocess

import pytest

from oca_github_bot import config
from oca_github_bot.github import git_get_current_branch
from oca_github_bot.tasks.mention_maintainer import mention_maintainer

from .common import make_addon, set_config


@pytest.mark.vcr()
def test_maintainer_mentioned(git_clone, mocker):
    github_mock = mocker.patch("oca_github_bot.tasks.mention_maintainer.github")
    github_mock.temporary_clone.return_value.__enter__.return_value = str(git_clone)
    pr_mock = github_mock.login.return_value.__enter__.return_value.pull_request
    pr_mock.return_value.base.ref = git_get_current_branch(git_clone)

    addon_name = "addon1"
    addon_dir = make_addon(git_clone, addon_name, maintainers=["themaintainer"])

    modified_addons_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.git_modified_addon_dirs"
    )
    modified_addons_mock.return_value = [addon_dir], False, {addon_name}
    mocker.patch("oca_github_bot.tasks.mention_maintainer.check_call")
    mention_maintainer("org", "repo", "pr")

    github_mock.gh_call.assert_called_once()
    assert "@themaintainer" in github_mock.gh_call.mock_calls[0][1][1]


@pytest.mark.vcr()
def test_added_maintainer_not_mentioned(git_clone, mocker):
    """Only maintainers existing before the PR will be mentioned."""
    github_mock = mocker.patch("oca_github_bot.tasks.mention_maintainer.github")
    github_mock.temporary_clone.return_value.__enter__.return_value = str(git_clone)
    pr_mock = github_mock.login.return_value.__enter__.return_value.pull_request
    pr_mock.return_value.base.ref = git_get_current_branch(git_clone)

    addon_name = "addon1"
    pre_pr_addon = make_addon(git_clone, addon_name, maintainers=["themaintainer"])
    pre_pr_addon_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.addon_dirs_in"
    )

    def pr_edited_addon(_args, **_kwargs):
        shutil.rmtree(pre_pr_addon)
        edited_addon = make_addon(
            git_clone, addon_name, maintainers=["themaintainer", "added_maintainer"]
        )
        return [str(edited_addon)]

    pre_pr_addon_mock.side_effect = pr_edited_addon
    pre_pr_addon_mock.return_value = [pre_pr_addon], False

    modified_addons_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.git_modified_addon_dirs"
    )
    modified_addons_mock.return_value = [pre_pr_addon], False, {addon_name}

    mocker.patch("oca_github_bot.tasks.mention_maintainer.check_call")

    mention_maintainer("org", "repo", "pr")

    github_mock.gh_call.assert_called_once()
    assert "@themaintainer" in github_mock.gh_call.mock_calls[0][1][1]
    assert "@added_maintainer" in github_mock.gh_call.mock_calls[0][1][1]


@pytest.mark.vcr()
def test_multi_maintainer_one_mention(git_clone, mocker):
    github_mock = mocker.patch("oca_github_bot.tasks.mention_maintainer.github")
    github_mock.temporary_clone.return_value.__enter__.return_value = str(git_clone)
    pr_mock = github_mock.login.return_value.__enter__.return_value.pull_request
    pr_mock.return_value.base.ref = git_get_current_branch(git_clone)

    addon_dirs = list()
    addon_names = ["addon1", "addon2"]
    themaintainer = "themaintainer"
    for addon_name in addon_names:
        addon_dir = make_addon(git_clone, addon_name, maintainers=[themaintainer])
        addon_dirs.append(addon_dir)

    modified_addons_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.git_modified_addon_dirs"
    )
    modified_addons_mock.return_value = addon_dirs, False, set(addon_names)
    mocker.patch("oca_github_bot.tasks.mention_maintainer.check_call")
    mention_maintainer("org", "repo", "pr")

    github_mock.gh_call.assert_called_once()
    comment = github_mock.gh_call.mock_calls[0][1][1]
    assert comment.count(themaintainer) == 1


@pytest.mark.vcr()
def test_pr_by_maintainer_no_mention(git_clone, mocker):
    themaintainer = "themaintainer"
    github_mock = mocker.patch("oca_github_bot.tasks.mention_maintainer.github")
    github_mock.temporary_clone.return_value.__enter__.return_value = str(git_clone)
    pr_mock = github_mock.login.return_value.__enter__.return_value.pull_request
    pr_mock.return_value.user.login = themaintainer
    pr_mock.return_value.base.ref = git_get_current_branch(git_clone)

    addon_dirs = list()
    addon_names = ["addon1", "addon2"]
    for addon_name in addon_names:
        addon_dir = make_addon(git_clone, addon_name, maintainers=[themaintainer])
        addon_dirs.append(addon_dir)

    modified_addons_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.git_modified_addon_dirs"
    )
    modified_addons_mock.return_value = addon_dirs, False, set(addon_names)
    mocker.patch("oca_github_bot.tasks.mention_maintainer.check_call")
    mention_maintainer("org", "repo", "pr")

    github_mock.gh_call.assert_not_called()


@pytest.mark.vcr()
def test_no_maintainer_adopt_module(git_clone, mocker):
    github_mock = mocker.patch("oca_github_bot.tasks.mention_maintainer.github")
    github_mock.temporary_clone.return_value.__enter__.return_value = str(git_clone)
    pr_mock = github_mock.login.return_value.__enter__.return_value.pull_request
    pr_mock.return_value.base.ref = git_get_current_branch(git_clone)

    addon_name = "addon1"
    addon_dir = make_addon(git_clone, addon_name)

    modified_addons_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.git_modified_addon_dirs"
    )
    modified_addons_mock.return_value = [addon_dir], False, {addon_name}
    mocker.patch("oca_github_bot.tasks.mention_maintainer.check_call")

    with set_config(ADOPT_AN_ADDON_MENTION="Hi {pr_opener}, would you like to adopt?"):
        mention_maintainer("org", "repo", "pr")

    github_mock.gh_call.assert_called_once()


@pytest.mark.vcr()
def test_mention_maintainer_other_branches(git_clone, mocker):
    addon_name = "addon_maintainer_other_branches"

    # create `addon_name` on `other_branch` with maintainer `maintainer`
    maintainer = "maintainer"
    maintainer_branch = "other_branch_maintainer"
    subprocess.check_call(["git", "checkout", "-b", maintainer_branch], cwd=git_clone)
    addon1_dir = git_clone / addon_name
    addon1_dir.mkdir(exist_ok=True)
    manifest = {
        "name": addon_name,
        "maintainers": [
            maintainer,
        ],
    }
    (addon1_dir / "__manifest__.py").write_text(json.dumps(manifest))
    subprocess.check_call(["git", "add", addon_name], cwd=git_clone)
    subprocess.check_call(
        ["git", "commit", "-m", "[BOT] Add with maintainer"], cwd=git_clone
    )

    # create `addon_name` on current branch with no maintainers
    branch = "current_branch_no_maintainer"
    subprocess.check_call(["git", "checkout", "-b", branch], cwd=git_clone)
    addon1_dir = git_clone / addon_name
    addon1_dir.mkdir(exist_ok=True)
    manifest = {
        "name": addon_name,
    }
    (addon1_dir / "__manifest__.py").write_text(json.dumps(manifest))
    subprocess.check_call(["git", "add", addon_name], cwd=git_clone)
    subprocess.check_call(
        ["git", "commit", "-m", "[BOT] Add without maintainer"], cwd=git_clone
    )

    github_mock = mocker.patch("oca_github_bot.tasks.mention_maintainer.github")
    github_mock.temporary_clone.return_value.__enter__.return_value = str(git_clone)
    pr_mock = github_mock.login.return_value.__enter__.return_value.pull_request
    pr_mock.return_value.base.ref = git_get_current_branch(git_clone)

    modified_addons_mock = mocker.patch(
        "oca_github_bot.tasks.mention_maintainer.git_modified_addon_dirs"
    )
    modified_addons_mock.return_value = [git_clone / addon_name], False, {addon_name}
    mocker.patch("oca_github_bot.tasks.mention_maintainer.check_call")

    config.MAINTAINER_CHECK_ODOO_RELEASES = [maintainer_branch]
    mention_maintainer("org", "repo", "pr")
    config.MAINTAINER_CHECK_ODOO_RELEASES = []

    assert "@" + maintainer in github_mock.gh_call.mock_calls[0][1][1]
