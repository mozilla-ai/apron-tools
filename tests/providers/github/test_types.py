"""Tests for GitHub provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.github.types import (
    AddIssueCommentParams,
    AddIssueCommentResult,
    CreateIssueParams,
    CreateIssueResult,
    ExploreReleasesParams,
    ExploreReleasesResult,
    GetFileContentParams,
    GetFileContentResult,
    GetIssueParams,
    GetIssueResult,
    GetPullRequestParams,
    GetPullRequestResult,
    GetRepositoryParams,
    GetRepositoryResult,
    IssueCommentSummary,
    IssueSummary,
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
    PullRequestDetail,
    ReleaseSummary,
    RepositorySummary,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListRepositoriesParams:
    def test_defaults(self):
        params = ListRepositoriesParams()
        assert params.visibility == "all"
        assert params.sort == "updated"
        assert params.limit == 30

    def test_custom_values(self):
        params = ListRepositoriesParams(visibility="private", sort="created", limit=10)
        assert params.visibility == "private"
        assert params.sort == "created"
        assert params.limit == 10


class TestGetRepositoryParams:
    def test_required_fields(self):
        params = GetRepositoryParams(owner="octocat", repo="Hello-World")
        assert params.owner == "octocat"
        assert params.repo == "Hello-World"


class TestListIssuesParams:
    def test_defaults(self):
        params = ListIssuesParams(owner="octocat", repo="Hello-World")
        assert params.state == "open"
        assert params.labels == ""
        assert params.milestone is None
        assert params.limit == 30
        assert params.since is None


class TestGetIssueParams:
    def test_required_fields(self):
        params = GetIssueParams(owner="octocat", repo="Hello-World", issue_number=1347)
        assert params.issue_number == 1347


class TestCreateIssueParams:
    def test_defaults(self):
        params = CreateIssueParams(owner="octocat", repo="Hello-World", title="Bug")
        assert params.body == ""
        assert params.labels == ""
        assert params.assignees == ""


class TestAddIssueCommentParams:
    def test_required_fields(self):
        params = AddIssueCommentParams(owner="octocat", repo="Hello-World", issue_number=1347, body="Me too")
        assert params.body == "Me too"


class TestListPullRequestsParams:
    def test_defaults(self):
        params = ListPullRequestsParams(owner="octocat", repo="Hello-World")
        assert params.state == "open"
        assert params.base is None
        assert params.sort == "created"
        assert params.limit == 30


class TestGetPullRequestParams:
    def test_required_fields(self):
        params = GetPullRequestParams(owner="octocat", repo="Hello-World", pr_number=1347)
        assert params.pr_number == 1347


class TestListMilestonesParams:
    def test_defaults(self):
        params = ListMilestonesParams(owner="octocat", repo="Hello-World")
        assert params.state == "open"


class TestGetFileContentParams:
    def test_defaults(self):
        params = GetFileContentParams(owner="octocat", repo="Hello-World", path="README.md")
        assert params.ref is None

    def test_with_ref(self):
        params = GetFileContentParams(owner="octocat", repo="Hello-World", path="README.md", ref="main")
        assert params.ref == "main"


class TestListBranchesParams:
    def test_required_fields(self):
        params = ListBranchesParams(owner="octocat", repo="Hello-World")
        assert params.owner == "octocat"


class TestExploreReleasesParams:
    def test_defaults(self):
        params = ExploreReleasesParams(owner="octocat", repo="Hello-World")
        assert params.tag is None
        assert params.limit == 30


# ---------------------------------------------------------------------------
# ListRepositoriesResult
# ---------------------------------------------------------------------------


class TestListRepositoriesResult:
    def test_parse_api_response(self):
        data = _load_json("list_repositories.json")
        repos = [RepositorySummary.model_validate(r) for r in data]
        result = ListRepositoriesResult(success=True, repositories=repos)

        assert result.success is True
        assert len(result.repositories) == 1
        assert result.repositories[0].name == "Hello-World"
        assert result.repositories[0].full_name == "octocat/Hello-World"
        assert result.repositories[0].stargazers_count == 80

    def test_str_output(self):
        data = _load_json("list_repositories.json")
        repos = [RepositorySummary.model_validate(r) for r in data]
        result = ListRepositoriesResult(success=True, repositories=repos)
        text = str(result)

        assert "1 repository(ies)" in text
        assert "Hello-World" in text
        assert "octocat/Hello-World" in text

    def test_str_on_error(self):
        result = ListRepositoriesResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


# ---------------------------------------------------------------------------
# GetRepositoryResult
# ---------------------------------------------------------------------------


class TestGetRepositoryResult:
    def test_parse_api_response(self):
        data = _load_json("get_repository.json")
        repo = RepositorySummary.model_validate(data)
        result = GetRepositoryResult(success=True, repository=repo)

        assert result.success is True
        assert result.repository is not None
        assert result.repository.full_name == "octocat/Hello-World"
        assert result.repository.stargazers_count == 80
        assert result.repository.language == "Ruby"
        assert result.repository.default_branch == "master"
        assert "octocat" in result.repository.topics

    def test_str_output(self):
        data = _load_json("get_repository.json")
        repo = RepositorySummary.model_validate(data)
        result = GetRepositoryResult(success=True, repository=repo)
        text = str(result)

        assert "octocat/Hello-World" in text
        assert "Ruby" in text
        assert "Stars: 80" in text

    def test_str_on_error(self):
        result = GetRepositoryResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ListIssuesResult
# ---------------------------------------------------------------------------


class TestListIssuesResult:
    def test_parse_api_response(self):
        data = _load_json("list_issues.json")
        issues = [IssueSummary.model_validate(i) for i in data]
        result = ListIssuesResult(success=True, issues=issues)

        assert result.success is True
        assert len(result.issues) == 1
        assert result.issues[0].number == 1347
        assert result.issues[0].title == "Found a bug"
        assert result.issues[0].state == "open"
        assert len(result.issues[0].labels) == 1
        assert result.issues[0].labels[0].name == "bug"

    def test_milestone_field(self):
        data = _load_json("list_issues.json")
        issues = [IssueSummary.model_validate(i) for i in data]
        assert issues[0].milestone is not None
        assert issues[0].milestone.title == "v1.0"

    def test_str_output(self):
        data = _load_json("list_issues.json")
        issues = [IssueSummary.model_validate(i) for i in data]
        result = ListIssuesResult(success=True, issues=issues)
        text = str(result)

        assert "1 issue(s)" in text
        assert "#1347" in text
        assert "Found a bug" in text
        assert "bug" in text

    def test_str_on_error(self):
        result = ListIssuesResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# GetIssueResult
# ---------------------------------------------------------------------------


class TestGetIssueResult:
    def test_parse_api_response(self):
        data = _load_json("get_issue.json")
        issue = IssueSummary.model_validate(data)
        result = GetIssueResult(success=True, issue=issue)

        assert result.success is True
        assert result.issue is not None
        assert result.issue.number == 1347
        assert result.issue.title == "Found a bug"
        assert result.issue.body == "I'm having a problem with this."

    def test_assignees(self):
        data = _load_json("get_issue.json")
        issue = IssueSummary.model_validate(data)
        assert len(issue.assignees) == 1
        assert issue.assignees[0].login == "octocat"

    def test_str_output(self):
        data = _load_json("get_issue.json")
        issue = IssueSummary.model_validate(data)
        result = GetIssueResult(success=True, issue=issue)
        text = str(result)

        assert "Issue #1347" in text
        assert "Found a bug" in text
        assert "octocat" in text
        assert "I'm having a problem with this." in text

    def test_str_on_error(self):
        result = GetIssueResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# CreateIssueResult
# ---------------------------------------------------------------------------


class TestCreateIssueResult:
    def test_parse_api_response(self):
        data = _load_json("create_issue.json")
        issue = IssueSummary.model_validate(data)
        result = CreateIssueResult(success=True, issue=issue)

        assert result.success is True
        assert result.issue is not None
        assert result.issue.number == 1347
        assert result.issue.title == "Found a bug"

    def test_str_output(self):
        data = _load_json("create_issue.json")
        issue = IssueSummary.model_validate(data)
        result = CreateIssueResult(success=True, issue=issue)
        text = str(result)

        assert "Issue created successfully!" in text
        assert "#1347" in text

    def test_str_on_error(self):
        result = CreateIssueResult(success=False, error="Validation failed")
        assert str(result) == "Error: Validation failed"


# ---------------------------------------------------------------------------
# AddIssueCommentResult
# ---------------------------------------------------------------------------


class TestAddIssueCommentResult:
    def test_parse_api_response(self):
        data = _load_json("add_issue_comment.json")
        comment = IssueCommentSummary.model_validate(data)
        result = AddIssueCommentResult(success=True, comment=comment)

        assert result.success is True
        assert result.comment is not None
        assert result.comment.body == "Me too"
        assert result.comment.user is not None
        assert result.comment.user.login == "octocat"

    def test_str_output(self):
        data = _load_json("add_issue_comment.json")
        comment = IssueCommentSummary.model_validate(data)
        result = AddIssueCommentResult(success=True, comment=comment)
        text = str(result)

        assert "Comment added successfully!" in text
        assert "issuecomment-1" in text

    def test_str_on_error(self):
        result = AddIssueCommentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ListPullRequestsResult
# ---------------------------------------------------------------------------


class TestListPullRequestsResult:
    def test_parse_api_response(self):
        data = _load_json("list_pull_requests.json")
        from apron_tools.providers.github.types import PullRequestSummary

        prs = [PullRequestSummary.model_validate(pr) for pr in data]
        result = ListPullRequestsResult(success=True, pull_requests=prs)

        assert result.success is True
        assert len(result.pull_requests) == 1
        assert result.pull_requests[0].number == 1347
        assert result.pull_requests[0].title == "Amazing new feature"

    def test_head_base_refs(self):
        data = _load_json("list_pull_requests.json")
        from apron_tools.providers.github.types import PullRequestSummary

        prs = [PullRequestSummary.model_validate(pr) for pr in data]
        pr = prs[0]
        assert pr.head is not None
        assert pr.head.ref == "new-topic"
        assert pr.base is not None
        assert pr.base.ref == "master"

    def test_str_output(self):
        data = _load_json("list_pull_requests.json")
        from apron_tools.providers.github.types import PullRequestSummary

        prs = [PullRequestSummary.model_validate(pr) for pr in data]
        result = ListPullRequestsResult(success=True, pull_requests=prs)
        text = str(result)

        assert "1 pull request(s)" in text
        assert "#1347" in text
        assert "Amazing new feature" in text
        assert "master <- new-topic" in text

    def test_str_on_error(self):
        result = ListPullRequestsResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# GetPullRequestResult
# ---------------------------------------------------------------------------


class TestGetPullRequestResult:
    def test_parse_api_response(self):
        data = _load_json("get_pull_request.json")
        pr = PullRequestDetail.model_validate(data)
        result = GetPullRequestResult(success=True, pull_request=pr)

        assert result.success is True
        assert result.pull_request is not None
        assert result.pull_request.number == 1347
        assert result.pull_request.additions == 100
        assert result.pull_request.deletions == 3
        assert result.pull_request.changed_files == 5
        assert result.pull_request.mergeable is True

    def test_str_output(self):
        data = _load_json("get_pull_request.json")
        pr = PullRequestDetail.model_validate(data)
        result = GetPullRequestResult(success=True, pull_request=pr)
        text = str(result)

        assert "Pull Request #1347" in text
        assert "Amazing new feature" in text
        assert "+100 -3" in text
        assert "Mergeable: Yes" in text

    def test_str_on_error(self):
        result = GetPullRequestResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ListMilestonesResult
# ---------------------------------------------------------------------------


class TestListMilestonesResult:
    def test_parse_api_response(self):
        data = _load_json("list_milestones.json")
        from apron_tools.providers.github.types import MilestoneSummary

        milestones = [MilestoneSummary.model_validate(ms) for ms in data]
        result = ListMilestonesResult(success=True, milestones=milestones)

        assert result.success is True
        assert len(result.milestones) == 1
        assert result.milestones[0].number == 1
        assert result.milestones[0].title == "v1.0"
        assert result.milestones[0].open_issues == 4
        assert result.milestones[0].closed_issues == 8

    def test_str_output(self):
        data = _load_json("list_milestones.json")
        from apron_tools.providers.github.types import MilestoneSummary

        milestones = [MilestoneSummary.model_validate(ms) for ms in data]
        result = ListMilestonesResult(success=True, milestones=milestones)
        text = str(result)

        assert "1 milestone(s)" in text
        assert "v1.0" in text
        assert "Open issues: 4" in text

    def test_str_on_error(self):
        result = ListMilestonesResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# GetFileContentResult
# ---------------------------------------------------------------------------


class TestGetFileContentResult:
    def test_parse_file_response(self):
        data = _load_json("get_file_content.json")
        from apron_tools.providers.github.types import FileContentEntry

        entry = FileContentEntry.model_validate(data)
        result = GetFileContentResult(
            success=True,
            file=entry,
            decoded_content="Hello World!",
        )

        assert result.success is True
        assert result.file is not None
        assert result.file.name == "README.md"
        assert result.file.path == "README.md"
        assert result.decoded_content == "Hello World!"

    def test_str_output_file(self):
        data = _load_json("get_file_content.json")
        from apron_tools.providers.github.types import FileContentEntry

        entry = FileContentEntry.model_validate(data)
        result = GetFileContentResult(
            success=True,
            file=entry,
            decoded_content="Hello World!",
        )
        text = str(result)

        assert "File: README.md" in text
        assert "Hello World!" in text

    def test_str_output_directory(self):
        from apron_tools.providers.github.types import FileContentEntry

        dir_entry = FileContentEntry(name="src", path="src", type="dir")
        entries = [
            FileContentEntry(name="main.py", path="src/main.py", type="file"),
            FileContentEntry(name="utils", path="src/utils", type="dir"),
        ]
        result = GetFileContentResult(
            success=True,
            file=dir_entry,
            directory_entries=entries,
            is_directory=True,
        )
        text = str(result)

        assert "Directory: src/" in text
        assert "main.py (file)" in text
        assert "utils/ (dir)" in text

    def test_str_on_error(self):
        result = GetFileContentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ListBranchesResult
# ---------------------------------------------------------------------------


class TestListBranchesResult:
    def test_parse_api_response(self):
        data = _load_json("list_branches.json")
        from apron_tools.providers.github.types import BranchSummary

        branches = [BranchSummary.model_validate(b) for b in data]
        result = ListBranchesResult(success=True, branches=branches)

        assert result.success is True
        assert len(result.branches) == 2
        assert result.branches[0].name == "master"
        assert result.branches[0].protected is True
        assert result.branches[1].name == "feature/new-ui"
        assert result.branches[1].protected is False

    def test_str_output(self):
        data = _load_json("list_branches.json")
        from apron_tools.providers.github.types import BranchSummary

        branches = [BranchSummary.model_validate(b) for b in data]
        result = ListBranchesResult(success=True, branches=branches)
        text = str(result)

        assert "2 branch(es)" in text
        assert "master (protected)" in text
        assert "feature/new-ui" in text

    def test_str_on_error(self):
        result = ListBranchesResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ExploreReleasesResult
# ---------------------------------------------------------------------------


class TestExploreReleasesResult:
    def test_parse_list_response(self):
        data = _load_json("list_releases.json")
        releases = [ReleaseSummary.model_validate(r) for r in data]
        result = ExploreReleasesResult(success=True, releases=releases)

        assert result.success is True
        assert len(result.releases) == 1
        assert result.releases[0].tag_name == "v1.0.0"
        assert result.releases[0].name == "v1.0.0"
        assert len(result.releases[0].assets) == 1
        assert result.releases[0].assets[0].name == "example.zip"

    def test_parse_single_release(self):
        data = _load_json("get_release_by_tag.json")
        release = ReleaseSummary.model_validate(data)
        result = ExploreReleasesResult(success=True, single_release=release)

        assert result.success is True
        assert result.single_release is not None
        assert result.single_release.tag_name == "v1.0.0"
        assert result.single_release.body == "Description of the release"

    def test_str_output_list(self):
        data = _load_json("list_releases.json")
        releases = [ReleaseSummary.model_validate(r) for r in data]
        result = ExploreReleasesResult(success=True, releases=releases)
        text = str(result)

        assert "1 release(s)" in text
        assert "v1.0.0" in text
        assert "octocat" in text

    def test_str_output_single(self):
        data = _load_json("get_release_by_tag.json")
        release = ReleaseSummary.model_validate(data)
        result = ExploreReleasesResult(success=True, single_release=release)
        text = str(result)

        assert "Release: v1.0.0" in text
        assert "Description of the release" in text
        assert "example.zip" in text

    def test_str_on_error(self):
        result = ExploreReleasesResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"
