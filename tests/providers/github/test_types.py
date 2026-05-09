"""Tests for GitHub provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from apron_tools.providers.github.types import (
    AddIssueCommentItem,
    AddIssueCommentsParams,
    AddIssueCommentsResult,
    CommitSummary,
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
    IssueCommentSummary,
    IssueSummary,
    ListBranchesParams,
    ListBranchesResult,
    ListCommitsParams,
    ListCommitsResult,
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
    RepoTreeEntry,
    UpdateFileParams,
    UpdateFileResult,
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


class TestAddIssueCommentsParams:
    def test_required_fields(self):
        params = AddIssueCommentsParams(owner="octocat", repo="Hello-World", issue_numbers="1347", body="Me too")
        assert params.body == "Me too"
        assert params.issue_numbers == "1347"

    def test_csv_input(self):
        params = AddIssueCommentsParams(owner="octocat", repo="Hello-World", issue_numbers="1,2,3", body="hi")
        assert params.issue_numbers == "1,2,3"


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


class TestListCommitsParams:
    def test_defaults(self) -> None:
        params = ListCommitsParams(owner="octocat", repo="Hello-World")
        assert params.sha is None
        assert params.path is None
        assert params.author is None
        assert params.since is None
        assert params.until is None
        assert params.limit == 30

    def test_limit_clamped(self) -> None:
        try:
            ListCommitsParams(owner="o", repo="r", limit=0)
        except ValidationError:
            pass
        else:
            raise AssertionError("limit=0 should fail validation")
        try:
            ListCommitsParams(owner="o", repo="r", limit=101)
        except ValidationError:
            pass
        else:
            raise AssertionError("limit=101 should fail validation")


class TestExploreReleasesParams:
    def test_defaults(self):
        params = ExploreReleasesParams(owner="octocat", repo="Hello-World")
        assert params.tag is None
        assert params.limit == 30


class TestCreateBranchParams:
    def test_defaults(self):
        params = CreateBranchParams(owner="octocat", repo="Hello-World", branch_name="feature/x")
        assert params.source_branch == "main"


class TestUpdateFileParams:
    def test_defaults(self):
        params = UpdateFileParams(
            owner="octocat",
            repo="Hello-World",
            path="a.txt",
            content="hi",
            commit_message="add",
        )
        assert params.branch == "main"


class TestCreatePullRequestParams:
    def test_defaults(self):
        params = CreatePullRequestParams(
            owner="octocat",
            repo="Hello-World",
            title="t",
            head="feat",
        )
        assert params.base == "main"
        assert params.draft is False
        assert params.body == ""


class TestCreateReleaseParams:
    def test_defaults(self):
        params = CreateReleaseParams(owner="octocat", repo="Hello-World", tag_name="v1.0.0")
        assert params.draft is False
        assert params.prerelease is False
        assert params.generate_release_notes is False


class TestGenerateReleaseNotesParams:
    def test_defaults(self):
        params = GenerateReleaseNotesParams(owner="octocat", repo="Hello-World", tag_name="v1.0.0")
        assert params.target_commitish == ""
        assert params.previous_tag_name == ""
        assert params.configuration_file_path == ""


class TestForkRepositoryParams:
    def test_defaults(self):
        params = ForkRepositoryParams(owner="octocat", repo="Hello-World")
        assert params.organization == ""
        assert params.name == ""
        assert params.default_branch_only is False


class TestGetRepoTreeParams:
    def test_defaults(self):
        params = GetRepoTreeParams(owner="octocat", repo="Hello-World")
        assert params.ref == ""
        assert params.path_filter == ""


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
# AddIssueCommentsResult
# ---------------------------------------------------------------------------


class TestAddIssueCommentsResult:
    def test_str_lists_per_issue_outcomes(self):
        data = _load_json("add_issue_comment.json")
        comment = IssueCommentSummary.model_validate(data)
        result = AddIssueCommentsResult(
            success=True,
            items=[
                AddIssueCommentItem(issue_number=1347, success=True, comment=comment),
                AddIssueCommentItem(issue_number=1348, success=True, comment=comment),
            ],
        )
        text = str(result)

        assert "Issue #1347" in text
        assert "Issue #1348" in text
        assert "issuecomment-1" in text

    def test_str_marks_per_issue_failures(self):
        data = _load_json("add_issue_comment.json")
        comment = IssueCommentSummary.model_validate(data)
        result = AddIssueCommentsResult(
            success=True,
            items=[
                AddIssueCommentItem(issue_number=1347, success=True, comment=comment),
                AddIssueCommentItem(issue_number=9999, success=False, error="HTTP 404"),
            ],
        )
        text = str(result)

        assert "Issue #1347" in text
        assert "Issue #9999" in text
        assert "HTTP 404" in text

    def test_str_on_top_level_error(self):
        result = AddIssueCommentsResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_with_no_items(self):
        result = AddIssueCommentsResult(success=True, items=[])
        assert str(result) == "No issues processed."


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
# ListCommitsResult
# ---------------------------------------------------------------------------


class TestListCommitsResult:
    def test_str_output(self) -> None:
        commits = [
            CommitSummary(
                sha="aa11bb22cc33",
                short_sha="aa11bb2",
                message="Fix all the bugs",
                author_name="Monalisa Octocat",
                author_email="support@github.com",
                author_date="2011-04-14T16:00:49Z",
                html_url="https://github.com/octocat/Hello-World/commit/aa11bb2",
            ),
        ]
        result = ListCommitsResult(success=True, commits=commits)
        text = str(result)

        assert "1 commit(s)" in text
        assert "aa11bb2 Fix all the bugs" in text
        assert "Monalisa Octocat" in text

    def test_str_uses_first_line_of_multiline_message(self) -> None:
        commits = [
            CommitSummary(
                sha="aa11bb22",
                short_sha="aa11bb2",
                message="Subject line\n\nBody paragraph that should not appear.",
            ),
        ]
        result = ListCommitsResult(success=True, commits=commits)
        text = str(result)

        assert "Subject line" in text
        assert "Body paragraph" not in text

    def test_str_on_error(self) -> None:
        result = ListCommitsResult(success=False, error="Not found")
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


# ---------------------------------------------------------------------------
# CreateBranchResult
# ---------------------------------------------------------------------------


class TestCreateBranchResult:
    def test_str_output(self):
        result = CreateBranchResult(
            success=True,
            branch_name="feature/x",
            source_branch="main",
            sha="aa218f56",
            url="https://github.com/octocat/Hello-World/tree/feature/x",
        )
        text = str(result)
        assert "Branch created successfully!" in text
        assert "feature/x" in text
        assert "main" in text

    def test_str_on_error(self):
        result = CreateBranchResult(success=False, error="already exists")
        assert str(result) == "Error: already exists"


# ---------------------------------------------------------------------------
# UpdateFileResult
# ---------------------------------------------------------------------------


class TestUpdateFileResult:
    def test_str_output(self):
        result = UpdateFileResult(
            success=True,
            path="notes/hello.txt",
            branch="main",
            commit_sha="abcdef0123456789abcdef0123456789abcdef01",  # pragma: allowlist secret
            url="https://github.com/octocat/Hello-World/blob/main/notes/hello.txt",
        )
        text = str(result)
        assert "File updated successfully!" in text
        assert "notes/hello.txt" in text
        # Only the 8-char short form is surfaced, not the full 40-char SHA.
        assert "abcdef0123456789" not in text
        assert "abcdef01" in text

    def test_str_on_error(self):
        result = UpdateFileResult(success=False, error="Conflict")
        assert str(result) == "Error: Conflict"


# ---------------------------------------------------------------------------
# CreatePullRequestResult
# ---------------------------------------------------------------------------


class TestCreatePullRequestResult:
    def test_str_output(self):
        data = _load_json("get_pull_request.json")
        pr = PullRequestDetail.model_validate(data)
        result = CreatePullRequestResult(success=True, pull_request=pr)
        text = str(result)
        assert "Pull request created successfully!" in text
        assert "#1347" in text
        assert "new-topic -> Base: master" in text

    def test_str_on_error(self):
        result = CreatePullRequestResult(success=False, error="Validation Failed")
        assert str(result) == "Error: Validation Failed"


# ---------------------------------------------------------------------------
# CreateReleaseResult
# ---------------------------------------------------------------------------


class TestCreateReleaseResult:
    def test_str_output(self):
        data = _load_json("get_release_by_tag.json")
        release = ReleaseSummary.model_validate(data)
        result = CreateReleaseResult(
            success=True,
            release=release,
            target_commitish="master",
            notes_mode="manual",
        )
        text = str(result)
        assert "Release created successfully!" in text
        assert "v1.0.0" in text
        assert "Target: master" in text
        assert "Notes: manual" in text

    def test_str_on_error(self):
        result = CreateReleaseResult(success=False, error="already exists")
        assert str(result) == "Error: already exists"


# ---------------------------------------------------------------------------
# GenerateReleaseNotesResult
# ---------------------------------------------------------------------------


class TestGenerateReleaseNotesResult:
    def test_str_output(self):
        data = _load_json("generate_release_notes.json")
        result = GenerateReleaseNotesResult(
            success=True,
            owner="octocat",
            repo="Hello-World",
            tag_name="v1.0.0",
            release_title=data["name"],
            previous_tag_name="v0.9.0",
            notes=data["body"],
        )
        text = str(result)
        assert "Generated Release Notes for octocat/Hello-World" in text
        assert "**Tag:** v1.0.0" in text
        assert "**Previous Tag:** v0.9.0" in text
        assert "What's Changed" in text

    def test_str_on_error(self):
        result = GenerateReleaseNotesResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ForkRepositoryResult
# ---------------------------------------------------------------------------


class TestForkRepositoryResult:
    def test_str_output(self):
        result = ForkRepositoryResult(
            success=True,
            fork_full_name="peter-forker/Hello-World",
            source_full_name="octocat/Hello-World",
            html_url="https://github.com/peter-forker/Hello-World",
        )
        text = str(result)
        assert "Repository forked successfully!" in text
        assert "peter-forker/Hello-World" in text
        assert "octocat/Hello-World" in text

    def test_str_on_error(self):
        result = ForkRepositoryResult(success=False, error="forbidden")
        assert str(result) == "Error: forbidden"


# ---------------------------------------------------------------------------
# GetRepoTreeResult
# ---------------------------------------------------------------------------


class TestGetRepoTreeResult:
    def test_str_output(self):
        entries = [
            RepoTreeEntry(path="README.md", size=42, sha="aa"),
            RepoTreeEntry(path="src/main.py", size=2048, sha="bb"),
            RepoTreeEntry(path="assets/image.png", size=2_097_152, sha="cc"),
        ]
        result = GetRepoTreeResult(
            success=True,
            owner="octocat",
            repo="Hello-World",
            ref="develop",
            path_filter=None,
            files=entries,
            truncated=False,
        )
        text = str(result)
        assert "# Repository tree: octocat/Hello-World (ref: develop)" in text
        assert "Found 3 files." in text
        assert "README.md (42 B)" in text
        assert "src/main.py (2.0 KB)" in text
        assert "assets/image.png (2.0 MB)" in text

    def test_str_output_default_ref_and_truncated(self):
        result = GetRepoTreeResult(
            success=True,
            owner="octocat",
            repo="Hello-World",
            ref=None,
            path_filter="src",
            files=[RepoTreeEntry(path="src/main.py", size=10, sha="bb")],
            truncated=True,
        )
        text = str(result)
        assert "(ref: default branch)" in text
        assert "Filtered to: src/" in text
        assert "truncated" in text

    def test_str_on_error(self):
        result = GetRepoTreeResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"
