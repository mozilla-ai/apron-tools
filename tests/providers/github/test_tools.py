"""Tests for GitHub tool functions with mocked PyGithub client."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from apron_tools.providers.github.tools import (
    github_add_issue_comment,
    github_create_branch,
    github_create_issue,
    github_create_pull_request,
    github_create_release,
    github_explore_releases,
    github_fork_repository,
    github_generate_release_notes,
    github_get_file_content,
    github_get_issue,
    github_get_pull_request,
    github_get_repo_tree,
    github_get_repository,
    github_list_branches,
    github_list_issues,
    github_list_milestones,
    github_list_pull_requests,
    github_list_repositories,
    github_update_file,
)
from apron_tools.providers.github.types import (
    AddIssueCommentParams,
    AddIssueCommentResult,
    CreateBranchParams,
    CreateBranchResult,
    CreateIssueParams,
    CreateIssueResult,
    CreatePullRequestParams,
    CreatePullRequestResult,
    CreateReleaseParams,
    CreateReleaseResult,
    ExploreReleasesParams,
    ExploreReleasesResult,
    ForkRepositoryParams,
    ForkRepositoryResult,
    GenerateReleaseNotesParams,
    GenerateReleaseNotesResult,
    GetFileContentParams,
    GetFileContentResult,
    GetIssueParams,
    GetIssueResult,
    GetPullRequestParams,
    GetPullRequestResult,
    GetRepositoryParams,
    GetRepositoryResult,
    GetRepoTreeParams,
    GetRepoTreeResult,
    ListBranchesParams,
    ListBranchesResult,
    ListIssuesParams,
    ListIssuesResult,
    ListMilestonesParams,
    ListMilestonesResult,
    ListPullRequestsParams,
    ListPullRequestsResult,
    ListRepositoriesParams,
    ListRepositoriesResult,
    UpdateFileParams,
    UpdateFileResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "ghp_test_token_abc123"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


def _dt(iso: str) -> datetime:
    """Parse an ISO 8601 timestamp string into a datetime object."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=UTC)


def _mock_user(login: str = "octocat", uid: int = 1) -> MagicMock:
    """Build a mock PyGithub NamedUser."""
    user = MagicMock()
    user.login = login
    user.id = uid
    return user


def _mock_label(name: str = "bug", color: str = "f29513", description: str = "Something isn't working") -> MagicMock:
    """Build a mock PyGithub Label."""
    label = MagicMock()
    label.name = name
    label.color = color
    label.description = description
    return label


def _mock_milestone(
    number: int = 1,
    title: str = "v1.0",
    state: str = "open",
    open_issues: int = 4,
    closed_issues: int = 8,
    description: str = "Tracking milestone for version 1.0",
) -> MagicMock:
    """Build a mock PyGithub Milestone."""
    ms = MagicMock()
    ms.number = number
    ms.title = title
    ms.state = state
    ms.open_issues = open_issues
    ms.closed_issues = closed_issues
    ms.description = description
    return ms


def _mock_repo_obj(data: dict) -> MagicMock:
    """Build a mock PyGithub Repository from testdata dict."""
    repo = MagicMock()
    repo.id = data["id"]
    repo.name = data["name"]
    repo.full_name = data["full_name"]
    repo.private = data.get("private", False)
    repo.description = data.get("description")
    repo.language = data.get("language")
    repo.stargazers_count = data.get("stargazers_count", 0)
    repo.forks_count = data.get("forks_count", 0)
    repo.open_issues_count = data.get("open_issues_count", 0)
    repo.default_branch = data.get("default_branch", "main")
    repo.topics = data.get("topics", [])
    repo.owner = _mock_user(
        data.get("owner", {}).get("login", "octocat"),
        data.get("owner", {}).get("id", 1),
    )
    repo.html_url = data.get("html_url", "")
    repo.created_at = _dt(data["created_at"]) if data.get("created_at") else None
    repo.updated_at = _dt(data["updated_at"]) if data.get("updated_at") else None
    return repo


def _mock_issue(data: dict) -> MagicMock:
    """Build a mock PyGithub Issue from testdata dict."""
    issue = MagicMock()
    issue.number = data["number"]
    issue.title = data["title"]
    issue.state = data["state"]
    issue.body = data.get("body")
    issue.user = _mock_user(
        data.get("user", {}).get("login", "octocat"),
        data.get("user", {}).get("id", 1),
    )
    issue.labels = [
        _mock_label(lb.get("name", ""), lb.get("color", ""), lb.get("description", "")) for lb in data.get("labels", [])
    ]
    issue.assignees = [_mock_user(a.get("login", ""), a.get("id", 0)) for a in data.get("assignees", [])]
    issue.milestone = (
        _mock_milestone(
            data["milestone"]["number"],
            data["milestone"]["title"],
            data["milestone"]["state"],
            data["milestone"].get("open_issues", 0),
            data["milestone"].get("closed_issues", 0),
            data["milestone"].get("description", ""),
        )
        if data.get("milestone")
        else None
    )
    issue.comments = data.get("comments", 0)
    issue.html_url = data.get("html_url", "")
    issue.created_at = _dt(data["created_at"]) if data.get("created_at") else None
    issue.updated_at = _dt(data["updated_at"]) if data.get("updated_at") else None
    issue.closed_at = _dt(data["closed_at"]) if data.get("closed_at") else None
    issue.pull_request = None
    return issue


def _mock_comment(data: dict) -> MagicMock:
    """Build a mock PyGithub IssueComment from testdata dict."""
    comment = MagicMock()
    comment.id = data["id"]
    comment.body = data["body"]
    comment.user = _mock_user(
        data.get("user", {}).get("login", "octocat"),
        data.get("user", {}).get("id", 1),
    )
    comment.html_url = data.get("html_url", "")
    comment.created_at = _dt(data["created_at"]) if data.get("created_at") else None
    comment.updated_at = _dt(data["updated_at"]) if data.get("updated_at") else None
    return comment


def _mock_branch_ref(data: dict | None) -> MagicMock | None:
    """Build a mock PyGithub branch head/base."""
    if data is None:
        return None
    ref = MagicMock()
    ref.ref = data.get("ref", "")
    ref.sha = data.get("sha", "")
    return ref


def _mock_pull_request(data: dict) -> MagicMock:
    """Build a mock PyGithub PullRequest from testdata dict."""
    pr = MagicMock()
    pr.number = data["number"]
    pr.title = data["title"]
    pr.state = data["state"]
    pr.body = data.get("body")
    pr.user = _mock_user(
        data.get("user", {}).get("login", "octocat"),
        data.get("user", {}).get("id", 1),
    )
    pr.labels = [
        _mock_label(lb.get("name", ""), lb.get("color", ""), lb.get("description", "")) for lb in data.get("labels", [])
    ]
    pr.head = _mock_branch_ref(data.get("head"))
    pr.base = _mock_branch_ref(data.get("base"))
    pr.merged_at = _dt(data["merged_at"]) if data.get("merged_at") else None
    pr.draft = data.get("draft", False)
    pr.html_url = data.get("html_url", "")
    pr.created_at = _dt(data["created_at"]) if data.get("created_at") else None
    pr.updated_at = _dt(data["updated_at"]) if data.get("updated_at") else None
    pr.closed_at = _dt(data["closed_at"]) if data.get("closed_at") else None
    pr.merged = data.get("merged", False)
    pr.mergeable = data.get("mergeable")
    pr.additions = data.get("additions", 0)
    pr.deletions = data.get("deletions", 0)
    pr.changed_files = data.get("changed_files", 0)
    pr.commits = data.get("commits", 0)
    pr.comments = data.get("comments", 0)
    return pr


def _mock_branch(data: dict) -> MagicMock:
    """Build a mock PyGithub Branch from testdata dict."""
    branch = MagicMock()
    branch.name = data["name"]
    branch.protected = data.get("protected", False)
    return branch


def _mock_release_asset(data: dict) -> MagicMock:
    """Build a mock PyGithub GitReleaseAsset."""
    asset = MagicMock()
    asset.name = data["name"]
    asset.size = data.get("size", 0)
    asset.download_count = data.get("download_count", 0)
    asset.browser_download_url = data.get("browser_download_url", "")
    return asset


def _mock_release(data: dict) -> MagicMock:
    """Build a mock PyGithub GitRelease from testdata dict."""
    release = MagicMock()
    release.tag_name = data["tag_name"]
    release.title = data.get("name")
    release.body = data.get("body")
    release.draft = data.get("draft", False)
    release.prerelease = data.get("prerelease", False)
    release.published_at = _dt(data["published_at"]) if data.get("published_at") else None
    release.author = _mock_user(
        data.get("author", {}).get("login", "octocat"),
        data.get("author", {}).get("id", 1),
    )
    release.assets = [_mock_release_asset(a) for a in data.get("assets", [])]
    release.html_url = data.get("html_url", "")
    return release


def _mock_content_file(data: dict) -> MagicMock:
    """Build a mock PyGithub ContentFile from testdata dict."""
    cf = MagicMock()
    cf.name = data["name"]
    cf.path = data["path"]
    cf.type = data["type"]
    cf.size = data.get("size", 0)
    cf.content = data.get("content")
    cf.encoding = data.get("encoding")
    cf.sha = data.get("sha")
    cf.html_url = data.get("html_url")
    return cf


# ---------------------------------------------------------------------------
# github_list_repositories
# ---------------------------------------------------------------------------


class TestListRepositories:
    async def test_success(self) -> None:
        data = _load_json("list_repositories.json")
        mock_repos = [_mock_repo_obj(r) for r in data]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_user.return_value.get_repos.return_value.__getitem__ = lambda self, s: (
                mock_repos[s] if isinstance(s, slice) else mock_repos[s]
            )

            result = await github_list_repositories(ListRepositoriesParams(), token=_TOKEN)

        assert isinstance(result, ListRepositoriesResult)
        assert result.success is True
        assert len(result.repositories) == 1
        assert result.repositories[0].name == "Hello-World"
        assert result.repositories[0].full_name == "octocat/Hello-World"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_user.side_effect = GithubException(401, {"message": "Bad credentials"}, None)

            result = await github_list_repositories(ListRepositoriesParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_list_repositories._tool_definition
        assert defn.name == "github_list_repositories"
        assert defn.provider == "github"
        assert defn.scopes == ["repo"]


# ---------------------------------------------------------------------------
# github_get_repository
# ---------------------------------------------------------------------------


class TestGetRepository:
    async def test_success(self) -> None:
        data = _load_json("get_repository.json")
        mock_repo = _mock_repo_obj(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.return_value = mock_repo

            result = await github_get_repository(
                GetRepositoryParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, GetRepositoryResult)
        assert result.success is True
        assert result.repository is not None
        assert result.repository.full_name == "octocat/Hello-World"
        assert result.repository.stargazers_count == 80

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_get_repository(
                GetRepositoryParams(owner="octocat", repo="missing"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_get_repository._tool_definition
        assert defn.name == "github_get_repository"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_list_issues
# ---------------------------------------------------------------------------


class TestListIssues:
    async def test_success(self) -> None:
        data = _load_json("list_issues.json")
        mock_issues = [_mock_issue(i) for i in data]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_issues.return_value.__getitem__ = lambda self, s: (
                mock_issues[s] if isinstance(s, slice) else mock_issues[s]
            )

            result = await github_list_issues(
                ListIssuesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, ListIssuesResult)
        assert result.success is True
        assert len(result.issues) == 1
        assert result.issues[0].number == 1347
        assert result.issues[0].title == "Found a bug"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(403, {"message": "Forbidden"}, None)

            result = await github_list_issues(
                ListIssuesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_list_issues._tool_definition
        assert defn.name == "github_list_issues"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    async def test_success(self) -> None:
        data = _load_json("get_issue.json")
        mock_issue = _mock_issue(data)
        comment_data = _load_json("add_issue_comment.json")
        mock_comment = _mock_comment(comment_data)
        mock_issue.get_comments.return_value = [mock_comment]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_issue.return_value = mock_issue

            result = await github_get_issue(
                GetIssueParams(owner="octocat", repo="Hello-World", issue_number=1347),
                token=_TOKEN,
            )

        assert isinstance(result, GetIssueResult)
        assert result.success is True
        assert result.issue is not None
        assert result.issue.number == 1347
        assert len(result.comments_list) == 1
        assert result.comments_list[0].body == "Me too"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_issue.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_get_issue(
                GetIssueParams(owner="octocat", repo="Hello-World", issue_number=9999),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_get_issue._tool_definition
        assert defn.name == "github_get_issue"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    async def test_success(self) -> None:
        data = _load_json("create_issue.json")
        mock_issue = _mock_issue(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_issue.return_value = mock_issue

            result = await github_create_issue(
                CreateIssueParams(
                    owner="octocat",
                    repo="Hello-World",
                    title="Found a bug",
                    body="I'm having a problem with this.",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, CreateIssueResult)
        assert result.success is True
        assert result.issue is not None
        assert result.issue.number == 1347

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_issue.side_effect = GithubException(422, {"message": "Validation Failed"}, None)

            result = await github_create_issue(
                CreateIssueParams(owner="octocat", repo="Hello-World", title=""),
                token=_TOKEN,
            )

        assert result.success is False
        assert "422" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_create_issue._tool_definition
        assert defn.name == "github_create_issue"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_add_issue_comment
# ---------------------------------------------------------------------------


class TestAddIssueComment:
    async def test_success(self) -> None:
        data = _load_json("add_issue_comment.json")
        mock_comment = _mock_comment(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_issue = MagicMock()
            mock_repo.get_issue.return_value = mock_issue
            mock_issue.create_comment.return_value = mock_comment

            result = await github_add_issue_comment(
                AddIssueCommentParams(
                    owner="octocat",
                    repo="Hello-World",
                    issue_number=1347,
                    body="Me too",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, AddIssueCommentResult)
        assert result.success is True
        assert result.comment is not None
        assert result.comment.body == "Me too"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_issue.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_add_issue_comment(
                AddIssueCommentParams(
                    owner="octocat",
                    repo="Hello-World",
                    issue_number=9999,
                    body="test",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_add_issue_comment._tool_definition
        assert defn.name == "github_add_issue_comment"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_list_pull_requests
# ---------------------------------------------------------------------------


class TestListPullRequests:
    async def test_success(self) -> None:
        data = _load_json("list_pull_requests.json")
        mock_prs = [_mock_pull_request(pr) for pr in data]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_pulls.return_value.__getitem__ = lambda self, s: (
                mock_prs[s] if isinstance(s, slice) else mock_prs[s]
            )

            result = await github_list_pull_requests(
                ListPullRequestsParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, ListPullRequestsResult)
        assert result.success is True
        assert len(result.pull_requests) == 1
        assert result.pull_requests[0].number == 1347
        assert result.pull_requests[0].title == "Amazing new feature"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_list_pull_requests(
                ListPullRequestsParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_list_pull_requests._tool_definition
        assert defn.name == "github_list_pull_requests"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_get_pull_request
# ---------------------------------------------------------------------------


class TestGetPullRequest:
    async def test_success(self) -> None:
        data = _load_json("get_pull_request.json")
        mock_pr = _mock_pull_request(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock_pr

            result = await github_get_pull_request(
                GetPullRequestParams(owner="octocat", repo="Hello-World", pr_number=1347),
                token=_TOKEN,
            )

        assert isinstance(result, GetPullRequestResult)
        assert result.success is True
        assert result.pull_request is not None
        assert result.pull_request.number == 1347
        assert result.pull_request.additions == 100
        assert result.pull_request.deletions == 3
        assert result.pull_request.changed_files == 5

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_pull.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_get_pull_request(
                GetPullRequestParams(owner="octocat", repo="Hello-World", pr_number=9999),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_get_pull_request._tool_definition
        assert defn.name == "github_get_pull_request"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_list_milestones
# ---------------------------------------------------------------------------


class TestListMilestones:
    async def test_success(self) -> None:
        data = _load_json("list_milestones.json")
        mock_milestones = [
            _mock_milestone(
                **{
                    "number": ms["number"],
                    "title": ms["title"],
                    "state": ms["state"],
                    "open_issues": ms.get("open_issues", 0),
                    "closed_issues": ms.get("closed_issues", 0),
                    "description": ms.get("description", ""),
                }
            )
            for ms in data
        ]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_milestones.return_value = mock_milestones

            result = await github_list_milestones(
                ListMilestonesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, ListMilestonesResult)
        assert result.success is True
        assert len(result.milestones) == 1
        assert result.milestones[0].title == "v1.0"
        assert result.milestones[0].open_issues == 4

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_list_milestones(
                ListMilestonesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_list_milestones._tool_definition
        assert defn.name == "github_list_milestones"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_get_file_content
# ---------------------------------------------------------------------------


class TestGetFileContent:
    async def test_success_file(self) -> None:
        data = _load_json("get_file_content.json")
        mock_cf = _mock_content_file(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_contents.return_value = mock_cf

            result = await github_get_file_content(
                GetFileContentParams(owner="octocat", repo="Hello-World", path="README.md"),
                token=_TOKEN,
            )

        assert isinstance(result, GetFileContentResult)
        assert result.success is True
        assert result.file is not None
        assert result.file.name == "README.md"
        assert result.decoded_content == "Hello World!"
        assert result.is_directory is False

    async def test_success_directory(self) -> None:
        entry1 = _mock_content_file(
            {"name": "main.py", "path": "src/main.py", "type": "file", "size": 100, "sha": "abc", "html_url": ""}
        )
        entry2 = _mock_content_file(
            {"name": "utils", "path": "src/utils", "type": "dir", "size": 0, "sha": "def", "html_url": ""}
        )

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_contents.return_value = [entry1, entry2]

            result = await github_get_file_content(
                GetFileContentParams(owner="octocat", repo="Hello-World", path="src"),
                token=_TOKEN,
            )

        assert result.success is True
        assert result.is_directory is True
        assert len(result.directory_entries) == 2

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_contents.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_get_file_content(
                GetFileContentParams(owner="octocat", repo="Hello-World", path="missing.txt"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_get_file_content._tool_definition
        assert defn.name == "github_get_file_content"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_list_branches
# ---------------------------------------------------------------------------


class TestListBranches:
    async def test_success(self) -> None:
        data = _load_json("list_branches.json")
        mock_branches = [_mock_branch(b) for b in data]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_branches.return_value = mock_branches

            result = await github_list_branches(
                ListBranchesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, ListBranchesResult)
        assert result.success is True
        assert len(result.branches) == 2
        assert result.branches[0].name == "master"
        assert result.branches[0].protected is True

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_list_branches(
                ListBranchesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_list_branches._tool_definition
        assert defn.name == "github_list_branches"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_explore_releases
# ---------------------------------------------------------------------------


class TestExploreReleases:
    async def test_success_list(self) -> None:
        data = _load_json("list_releases.json")
        mock_releases = [_mock_release(r) for r in data]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_releases.return_value.__getitem__ = lambda self, s: (
                mock_releases[s] if isinstance(s, slice) else mock_releases[s]
            )

            result = await github_explore_releases(
                ExploreReleasesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, ExploreReleasesResult)
        assert result.success is True
        assert len(result.releases) == 1
        assert result.releases[0].tag_name == "v1.0.0"

    async def test_success_single(self) -> None:
        data = _load_json("get_release_by_tag.json")
        mock_release = _mock_release(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_release.return_value = mock_release

            result = await github_explore_releases(
                ExploreReleasesParams(owner="octocat", repo="Hello-World", tag="v1.0.0"),
                token=_TOKEN,
            )

        assert result.success is True
        assert result.single_release is not None
        assert result.single_release.tag_name == "v1.0.0"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_explore_releases(
                ExploreReleasesParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_explore_releases._tool_definition
        assert defn.name == "github_explore_releases"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_create_branch
# ---------------------------------------------------------------------------


def _mock_git_ref(data: dict) -> MagicMock:
    """Build a mock PyGithub GitRef from testdata dict."""
    ref = MagicMock()
    ref.ref = data["ref"]
    obj = MagicMock()
    obj.sha = data["object"]["sha"]
    ref.object = obj
    return ref


class TestCreateBranch:
    async def test_success(self) -> None:
        source_ref = _mock_git_ref(_load_json("create_branch_ref.json"))

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_git_ref.return_value = source_ref

            result = await github_create_branch(
                CreateBranchParams(
                    owner="octocat",
                    repo="Hello-World",
                    branch_name="feature/x",
                    source_branch="main",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, CreateBranchResult)
        assert result.success is True
        assert result.branch_name == "feature/x"
        assert result.source_branch == "main"
        assert result.sha == "aa11bb22"
        assert result.url == "https://github.com/octocat/Hello-World/tree/feature/x"
        mock_repo.get_git_ref.assert_called_once_with("heads/main")
        mock_repo.create_git_ref.assert_called_once_with(
            ref="refs/heads/feature/x",
            sha="aa11bb22",
        )

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_git_ref.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_create_branch(
                CreateBranchParams(
                    owner="octocat",
                    repo="Hello-World",
                    branch_name="feature/x",
                    source_branch="missing",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_create_branch._tool_definition
        assert defn.name == "github_create_branch"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_update_file
# ---------------------------------------------------------------------------


def _mock_update_file_result(data: dict) -> dict:
    """Build the dict PyGithub returns from create_file / update_file."""
    content_file = MagicMock()
    content_file.name = data["content"]["name"]
    content_file.path = data["content"]["path"]
    content_file.sha = data["content"]["sha"]
    content_file.html_url = data["content"]["html_url"]
    commit = MagicMock()
    commit.sha = data["commit"]["sha"]
    return {"content": content_file, "commit": commit}


class TestUpdateFile:
    async def test_success_creates_when_missing(self) -> None:
        from github import GithubException

        update_payload = _mock_update_file_result(_load_json("update_file.json"))

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            # Simulate a missing file so the tool picks the create path.
            mock_repo.get_contents.side_effect = GithubException(404, {"message": "Not Found"}, None)
            mock_repo.create_file.return_value = update_payload

            result = await github_update_file(
                UpdateFileParams(
                    owner="octocat",
                    repo="Hello-World",
                    path="notes/hello.txt",
                    content="Hello!",
                    commit_message="Add hello.txt",
                    branch="main",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, UpdateFileResult)
        assert result.success is True
        assert result.path == "notes/hello.txt"
        assert result.branch == "main"
        assert result.commit_sha == "cc33dd44"
        assert result.url.endswith("notes/hello.txt")
        mock_repo.create_file.assert_called_once()
        mock_repo.update_file.assert_not_called()

    async def test_success_updates_when_present(self) -> None:
        existing = MagicMock()
        existing.sha = "existing-blob-sha"
        update_payload = _mock_update_file_result(_load_json("update_file.json"))

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_contents.return_value = existing
            mock_repo.update_file.return_value = update_payload

            result = await github_update_file(
                UpdateFileParams(
                    owner="octocat",
                    repo="Hello-World",
                    path="notes/hello.txt",
                    content="Hello!",
                    commit_message="Update hello.txt",
                    branch="main",
                ),
                token=_TOKEN,
            )

        assert result.success is True
        mock_repo.update_file.assert_called_once()
        assert mock_repo.update_file.call_args.kwargs["sha"] == "existing-blob-sha"
        mock_repo.create_file.assert_not_called()

    async def test_rejects_directory_path(self) -> None:
        directory_contents = [MagicMock(), MagicMock()]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_contents.return_value = directory_contents

            result = await github_update_file(
                UpdateFileParams(
                    owner="octocat",
                    repo="Hello-World",
                    path="notes",
                    content="Hello!",
                    commit_message="x",
                    branch="main",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "422" in result.error

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_update_file(
                UpdateFileParams(
                    owner="octocat",
                    repo="missing",
                    path="a.txt",
                    content="x",
                    commit_message="x",
                    branch="main",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_update_file._tool_definition
        assert defn.name == "github_update_file"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_create_pull_request
# ---------------------------------------------------------------------------


class TestCreatePullRequest:
    async def test_success(self) -> None:
        data = _load_json("get_pull_request.json")
        mock_pr = _mock_pull_request(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_pull.return_value = mock_pr

            result = await github_create_pull_request(
                CreatePullRequestParams(
                    owner="octocat",
                    repo="Hello-World",
                    title="Amazing new feature",
                    head="new-topic",
                    base="master",
                    body="Please pull these awesome changes in!",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, CreatePullRequestResult)
        assert result.success is True
        assert result.pull_request is not None
        assert result.pull_request.number == 1347
        assert result.pull_request.title == "Amazing new feature"
        mock_repo.create_pull.assert_called_once()
        call_kwargs = mock_repo.create_pull.call_args.kwargs
        assert call_kwargs["title"] == "Amazing new feature"
        assert call_kwargs["head"] == "new-topic"
        assert call_kwargs["base"] == "master"
        assert call_kwargs["draft"] is False
        assert call_kwargs["body"] == "Please pull these awesome changes in!"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_pull.side_effect = GithubException(422, {"message": "Validation Failed"}, None)

            result = await github_create_pull_request(
                CreatePullRequestParams(
                    owner="octocat",
                    repo="Hello-World",
                    title="bad",
                    head="missing",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "422" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_create_pull_request._tool_definition
        assert defn.name == "github_create_pull_request"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_create_release
# ---------------------------------------------------------------------------


class TestCreateRelease:
    async def test_success_manual_notes(self) -> None:
        data = _load_json("get_release_by_tag.json")
        mock_release = _mock_release(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_git_release.return_value = mock_release

            result = await github_create_release(
                CreateReleaseParams(
                    owner="octocat",
                    repo="Hello-World",
                    tag_name="v1.0.0",
                    release_title="v1.0.0",
                    release_notes="Description of the release",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, CreateReleaseResult)
        assert result.success is True
        assert result.release is not None
        assert result.release.tag_name == "v1.0.0"
        assert result.notes_mode == "manual"

    async def test_success_auto_generated_notes(self) -> None:
        data = _load_json("get_release_by_tag.json")
        mock_release = _mock_release(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_git_release.return_value = mock_release

            result = await github_create_release(
                CreateReleaseParams(
                    owner="octocat",
                    repo="Hello-World",
                    tag_name="v1.0.0",
                    generate_release_notes=True,
                ),
                token=_TOKEN,
            )

        assert result.success is True
        assert result.notes_mode == "auto-generated"
        call_kwargs = mock_repo.create_git_release.call_args.kwargs
        assert call_kwargs["generate_release_notes"] is True

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_git_release.side_effect = GithubException(422, {"message": "already_exists"}, None)

            result = await github_create_release(
                CreateReleaseParams(
                    owner="octocat",
                    repo="Hello-World",
                    tag_name="v1.0.0",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "422" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_create_release._tool_definition
        assert defn.name == "github_create_release"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_generate_release_notes
# ---------------------------------------------------------------------------


class TestGenerateReleaseNotes:
    async def test_success(self) -> None:
        data = _load_json("generate_release_notes.json")
        mock_notes = MagicMock()
        mock_notes.name = data["name"]
        mock_notes.body = data["body"]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.generate_release_notes.return_value = mock_notes

            result = await github_generate_release_notes(
                GenerateReleaseNotesParams(
                    owner="octocat",
                    repo="Hello-World",
                    tag_name="v1.0.0",
                    previous_tag_name="v0.9.0",
                ),
                token=_TOKEN,
            )

        assert isinstance(result, GenerateReleaseNotesResult)
        assert result.success is True
        assert result.tag_name == "v1.0.0"
        assert result.release_title == data["name"]
        assert result.notes == data["body"]
        assert result.previous_tag_name == "v0.9.0"
        call_kwargs = mock_repo.generate_release_notes.call_args.kwargs
        assert call_kwargs["tag_name"] == "v1.0.0"
        assert call_kwargs["previous_tag_name"] == "v0.9.0"

    async def test_falls_back_to_tag_name_when_title_empty(self) -> None:
        mock_notes = MagicMock()
        mock_notes.name = None
        mock_notes.body = "body"

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.generate_release_notes.return_value = mock_notes

            result = await github_generate_release_notes(
                GenerateReleaseNotesParams(
                    owner="octocat",
                    repo="Hello-World",
                    tag_name="v2.0.0",
                ),
                token=_TOKEN,
            )

        assert result.success is True
        assert result.release_title == "v2.0.0"

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_generate_release_notes(
                GenerateReleaseNotesParams(
                    owner="octocat",
                    repo="missing",
                    tag_name="v1.0.0",
                ),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_generate_release_notes._tool_definition
        assert defn.name == "github_generate_release_notes"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_fork_repository
# ---------------------------------------------------------------------------


class TestForkRepository:
    async def test_success_default(self) -> None:
        data = _load_json("fork_repository.json")
        mock_fork = MagicMock()
        mock_fork.full_name = data["full_name"]
        mock_fork.html_url = data["html_url"]

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_fork.return_value = mock_fork

            result = await github_fork_repository(
                ForkRepositoryParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, ForkRepositoryResult)
        assert result.success is True
        assert result.fork_full_name == "peter-forker/Hello-World"
        assert result.source_full_name == "octocat/Hello-World"
        assert result.html_url == "https://github.com/peter-forker/Hello-World"
        assert mock_repo.create_fork.call_args.kwargs == {}

    async def test_success_forwards_options(self) -> None:
        mock_fork = MagicMock()
        mock_fork.full_name = "my-org/Hello-World"
        mock_fork.html_url = "https://github.com/my-org/Hello-World"

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.create_fork.return_value = mock_fork

            await github_fork_repository(
                ForkRepositoryParams(
                    owner="octocat",
                    repo="Hello-World",
                    organization="my-org",
                    name="Hello-World",
                    default_branch_only=True,
                ),
                token=_TOKEN,
            )

        kwargs = mock_repo.create_fork.call_args.kwargs
        assert kwargs["organization"] == "my-org"
        assert kwargs["name"] == "Hello-World"
        assert kwargs["default_branch_only"] is True

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_fork_repository(
                ForkRepositoryParams(owner="octocat", repo="missing"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_fork_repository._tool_definition
        assert defn.name == "github_fork_repository"
        assert defn.provider == "github"


# ---------------------------------------------------------------------------
# github_get_repo_tree
# ---------------------------------------------------------------------------


def _mock_tree_entry(data: dict) -> MagicMock:
    """Build a mock PyGithub GitTreeElement from a tree entry dict."""
    entry = MagicMock()
    entry.path = data["path"]
    entry.type = data["type"]
    entry.sha = data["sha"]
    entry.size = data.get("size")
    return entry


def _mock_git_tree(data: dict) -> MagicMock:
    """Build a mock PyGithub GitTree from testdata dict."""
    tree = MagicMock()
    tree.tree = [_mock_tree_entry(e) for e in data["tree"]]
    tree.truncated = data.get("truncated", False)
    return tree


def _mock_commit_with_tree(tree_sha: str) -> MagicMock:
    """Build a mock PyGithub Commit whose commit.tree.sha is tree_sha."""
    commit = MagicMock()
    commit.commit.tree.sha = tree_sha
    return commit


class TestGetRepoTree:
    async def test_success_default_branch(self) -> None:
        data = _load_json("get_repo_tree.json")
        git_tree = _mock_git_tree(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.default_branch = "main"
            mock_repo.get_commit.return_value = _mock_commit_with_tree(data["sha"])
            mock_repo.get_git_tree.return_value = git_tree

            result = await github_get_repo_tree(
                GetRepoTreeParams(owner="octocat", repo="Hello-World"),
                token=_TOKEN,
            )

        assert isinstance(result, GetRepoTreeResult)
        assert result.success is True
        # Only blob entries should be returned; the "tree" entry in src/ is dropped.
        assert [f.path for f in result.files] == [
            "README.md",
            "src/main.py",
            "docs/index.md",
        ]
        assert result.files[0].size == 42
        assert result.truncated is False
        mock_repo.get_commit.assert_called_once_with("main")
        mock_repo.get_git_tree.assert_called_once_with(data["sha"], recursive=True)

    async def test_success_with_ref_and_path_filter(self) -> None:
        data = _load_json("get_repo_tree.json")
        git_tree = _mock_git_tree(data)

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_repo = MagicMock()
            mock_g.get_repo.return_value = mock_repo
            mock_repo.get_commit.return_value = _mock_commit_with_tree(data["sha"])
            mock_repo.get_git_tree.return_value = git_tree

            result = await github_get_repo_tree(
                GetRepoTreeParams(
                    owner="octocat",
                    repo="Hello-World",
                    ref="develop",
                    path_filter="src",
                ),
                token=_TOKEN,
            )

        assert result.success is True
        assert [f.path for f in result.files] == ["src/main.py"]
        assert result.ref == "develop"
        assert result.path_filter == "src"
        mock_repo.get_commit.assert_called_once_with("develop")

    async def test_error(self) -> None:
        from github import GithubException

        with patch("apron_tools.providers.github.tools._build_client") as mock_build:
            mock_g = MagicMock()
            mock_build.return_value = mock_g
            mock_g.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

            result = await github_get_repo_tree(
                GetRepoTreeParams(owner="octocat", repo="missing"),
                token=_TOKEN,
            )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = github_get_repo_tree._tool_definition
        assert defn.name == "github_get_repo_tree"
        assert defn.provider == "github"
