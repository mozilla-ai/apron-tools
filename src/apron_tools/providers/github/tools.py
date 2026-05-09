"""GitHub tool functions for interacting with the GitHub API via PyGithub."""

from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime
from typing import Any, cast

from github import Github, GithubException

from apron_tools._utils import parse_csv_ids
from apron_tools.tool import tool

from .scopes import SCOPES
from .types import (
    AddIssueCommentItem,
    AddIssueCommentsParams,
    AddIssueCommentsResult,
    BranchSummary,
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
    FileContentEntry,
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
    LabelSummary,
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
    MilestoneSummary,
    PullRequestDetail,
    PullRequestSummary,
    ReleaseAsset,
    ReleaseSummary,
    RepositorySummary,
    RepoTreeEntry,
    UpdateFileParams,
    UpdateFileResult,
    UserSummary,
)

_BASE_URL = "https://api.github.com"


def _build_client(token: str, base_url: str) -> Github:
    """Build a PyGithub client with the given credentials."""
    return Github(login_or_token=token, base_url=base_url)


def _user_summary(user: Any) -> UserSummary | None:
    """Extract a UserSummary from a PyGithub NamedUser or AuthenticatedUser."""
    if user is None:
        return None
    return UserSummary(login=user.login, id=user.id)


def _label_summary(label: Any) -> LabelSummary:
    """Extract a LabelSummary from a PyGithub Label."""
    return LabelSummary(
        name=label.name,
        color=getattr(label, "color", None),
        description=getattr(label, "description", None),
    )


def _milestone_summary(milestone: Any) -> MilestoneSummary | None:
    """Extract a MilestoneSummary from a PyGithub Milestone."""
    if milestone is None:
        return None
    return MilestoneSummary(
        number=milestone.number,
        title=milestone.title,
        state=milestone.state,
        open_issues=milestone.open_issues,
        closed_issues=milestone.closed_issues,
        description=milestone.description,
    )


def _issue_summary(issue: Any) -> IssueSummary:
    """Extract an IssueSummary from a PyGithub Issue."""
    pr_data = None
    if issue.pull_request is not None:
        pr_data = {"url": getattr(issue.pull_request, "raw_data", {}).get("url", "")}
    return IssueSummary(
        number=issue.number,
        title=issue.title,
        state=issue.state,
        body=issue.body,
        user=_user_summary(issue.user),
        labels=[_label_summary(lb) for lb in issue.labels],
        assignees=[s for a in issue.assignees if (s := _user_summary(a)) is not None],
        milestone=_milestone_summary(issue.milestone),
        comments=issue.comments,
        html_url=issue.html_url,
        created_at=issue.created_at.isoformat() + "Z" if issue.created_at else None,
        updated_at=issue.updated_at.isoformat() + "Z" if issue.updated_at else None,
        closed_at=issue.closed_at.isoformat() + "Z" if issue.closed_at else None,
        pull_request=pr_data,
    )


def _pr_summary(pr: Any) -> PullRequestSummary:
    """Extract a PullRequestSummary from a PyGithub PullRequest."""
    from .types import BranchRef

    return PullRequestSummary(
        number=pr.number,
        title=pr.title,
        state=pr.state,
        body=pr.body,
        user=_user_summary(pr.user),
        labels=[_label_summary(lb) for lb in pr.labels],
        head=BranchRef(ref=pr.head.ref, sha=pr.head.sha) if pr.head else None,
        base=BranchRef(ref=pr.base.ref, sha=pr.base.sha) if pr.base else None,
        merged_at=pr.merged_at.isoformat() + "Z" if pr.merged_at else None,
        draft=pr.draft,
        html_url=pr.html_url,
        created_at=pr.created_at.isoformat() + "Z" if pr.created_at else None,
        updated_at=pr.updated_at.isoformat() + "Z" if pr.updated_at else None,
        closed_at=pr.closed_at.isoformat() + "Z" if pr.closed_at else None,
    )


def _pr_detail(pr: Any) -> PullRequestDetail:
    """Extract a PullRequestDetail from a PyGithub PullRequest."""
    from .types import BranchRef

    return PullRequestDetail(
        number=pr.number,
        title=pr.title,
        state=pr.state,
        body=pr.body,
        user=_user_summary(pr.user),
        labels=[_label_summary(lb) for lb in pr.labels],
        head=BranchRef(ref=pr.head.ref, sha=pr.head.sha) if pr.head else None,
        base=BranchRef(ref=pr.base.ref, sha=pr.base.sha) if pr.base else None,
        merged_at=pr.merged_at.isoformat() + "Z" if pr.merged_at else None,
        merged=pr.merged,
        mergeable=pr.mergeable,
        draft=pr.draft,
        additions=pr.additions,
        deletions=pr.deletions,
        changed_files=pr.changed_files,
        commits=pr.commits,
        comments=pr.comments,
        html_url=pr.html_url,
        created_at=pr.created_at.isoformat() + "Z" if pr.created_at else None,
        updated_at=pr.updated_at.isoformat() + "Z" if pr.updated_at else None,
        closed_at=pr.closed_at.isoformat() + "Z" if pr.closed_at else None,
    )


def _resolve_existing_file_sha(repo: Any, path: str, branch: str) -> str | None:
    """Return the blob SHA of an existing file, or None when the path is absent.

    ``repo.get_contents`` raises ``GithubException`` with status 404 when the
    file does not yet exist, which is the signal to create rather than update
    the file. Any other error propagates to the caller.
    """
    try:
        existing = repo.get_contents(path, ref=branch)
    except GithubException as exc:
        if exc.status == 404:
            return None
        raise
    if isinstance(existing, list):
        raise GithubException(
            422,
            {"message": f"'{path}' is a directory, not a file."},
            None,
        )
    return cast(str, existing.sha)


def _release_summary(release: Any) -> ReleaseSummary:
    """Extract a ReleaseSummary from a PyGithub GitRelease."""
    return ReleaseSummary(
        tag_name=release.tag_name,
        name=release.title,
        body=release.body,
        draft=release.draft,
        prerelease=release.prerelease,
        published_at=(release.published_at.isoformat() + "Z" if release.published_at else None),
        author=_user_summary(release.author),
        assets=[
            ReleaseAsset(
                name=a.name,
                size=a.size,
                download_count=a.download_count,
                browser_download_url=a.browser_download_url,
            )
            for a in release.assets
        ],
        html_url=release.html_url,
    )


@tool(
    scopes=SCOPES["github_list_repositories"],
    api_docs="https://docs.github.com/en/rest/repos/repos#list-repositories-for-the-authenticated-user",
    provider="github",
)
async def github_list_repositories(
    params: ListRepositoriesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListRepositoriesResult:
    """List repositories for the authenticated GitHub user."""

    def _call() -> ListRepositoriesResult:
        g = _build_client(token, base_url)
        try:
            user = cast(Any, g.get_user())
            repos = user.get_repos(
                visibility=params.visibility,
                sort=params.sort,
            )
            items = []
            for repo in repos[: params.limit]:
                items.append(
                    RepositorySummary(
                        id=repo.id,
                        name=repo.name,
                        full_name=repo.full_name,
                        private=repo.private,
                        description=repo.description,
                        language=repo.language,
                        stargazers_count=repo.stargazers_count,
                        forks_count=repo.forks_count,
                        open_issues_count=repo.open_issues_count,
                        default_branch=repo.default_branch,
                        topics=repo.topics,
                        owner=_user_summary(repo.owner),
                        html_url=repo.html_url,
                        created_at=(repo.created_at.isoformat() + "Z" if repo.created_at else None),
                        updated_at=(repo.updated_at.isoformat() + "Z" if repo.updated_at else None),
                    )
                )
            return ListRepositoriesResult(success=True, repositories=items)
        except GithubException as exc:
            return ListRepositoriesResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_get_repository"],
    api_docs="https://docs.github.com/en/rest/repos/repos#get-a-repository",
    provider="github",
)
async def github_get_repository(
    params: GetRepositoryParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetRepositoryResult:
    """Retrieve detailed information about a specific GitHub repository."""

    def _call() -> GetRepositoryResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            summary = RepositorySummary(
                id=repo.id,
                name=repo.name,
                full_name=repo.full_name,
                private=repo.private,
                description=repo.description,
                language=repo.language,
                stargazers_count=repo.stargazers_count,
                forks_count=repo.forks_count,
                open_issues_count=repo.open_issues_count,
                default_branch=repo.default_branch,
                topics=repo.topics,
                owner=_user_summary(repo.owner),
                html_url=repo.html_url,
                created_at=(repo.created_at.isoformat() + "Z" if repo.created_at else None),
                updated_at=(repo.updated_at.isoformat() + "Z" if repo.updated_at else None),
            )
            return GetRepositoryResult(success=True, repository=summary)
        except GithubException as exc:
            return GetRepositoryResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_list_issues"],
    api_docs="https://docs.github.com/en/rest/issues/issues#list-repository-issues",
    provider="github",
)
async def github_list_issues(
    params: ListIssuesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListIssuesResult:
    """List issues for a GitHub repository, newest-updated first."""

    def _call() -> ListIssuesResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            kwargs: dict = {
                "state": params.state,
                "sort": "updated",
                "direction": "desc",
            }
            if params.labels:
                label_objects = [repo.get_label(name.strip()) for name in params.labels.split(",")]
                kwargs["labels"] = label_objects
            if params.milestone is not None:
                if params.milestone == "*":
                    kwargs["milestone"] = "*"
                elif params.milestone == "none":
                    kwargs["milestone"] = "none"
                else:
                    kwargs["milestone"] = repo.get_milestone(int(params.milestone))
            if params.since is not None:
                from datetime import datetime

                kwargs["since"] = datetime.fromisoformat(params.since.replace("Z", "+00:00")).replace(tzinfo=UTC)
            issues = repo.get_issues(**kwargs)
            items = []
            for issue in issues[: params.limit]:
                summary = _issue_summary(issue)
                if summary.pull_request is not None:
                    continue
                items.append(summary)
            return ListIssuesResult(success=True, issues=items)
        except GithubException as exc:
            return ListIssuesResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_get_issue"],
    api_docs="https://docs.github.com/en/rest/issues/issues#get-an-issue",
    provider="github",
)
async def github_get_issue(
    params: GetIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetIssueResult:
    """Retrieve detailed information about a specific GitHub issue."""

    def _call() -> GetIssueResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            issue = repo.get_issue(params.issue_number)
            summary = _issue_summary(issue)
            comments = []
            for comment in issue.get_comments():
                comments.append(
                    IssueCommentSummary(
                        id=comment.id,
                        body=comment.body,
                        user=_user_summary(comment.user),
                        html_url=comment.html_url,
                        created_at=(comment.created_at.isoformat() + "Z" if comment.created_at else None),
                        updated_at=(comment.updated_at.isoformat() + "Z" if comment.updated_at else None),
                    )
                )
            return GetIssueResult(success=True, issue=summary, comments_list=comments)
        except GithubException as exc:
            return GetIssueResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_create_issue"],
    api_docs="https://docs.github.com/en/rest/issues/issues#create-an-issue",
    provider="github",
)
async def github_create_issue(
    params: CreateIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateIssueResult:
    """Create a new issue in a GitHub repository."""

    def _call() -> CreateIssueResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            kwargs: dict = {"title": params.title}
            if params.body:
                kwargs["body"] = params.body
            if params.labels:
                kwargs["labels"] = [label.strip() for label in params.labels.split(",")]
            if params.assignees:
                kwargs["assignees"] = [a.strip() for a in params.assignees.split(",")]
            issue = repo.create_issue(**kwargs)
            summary = _issue_summary(issue)
            return CreateIssueResult(success=True, issue=summary)
        except GithubException as exc:
            return CreateIssueResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_add_issue_comments"],
    api_docs="https://docs.github.com/en/rest/issues/comments#create-an-issue-comment",
    provider="github",
)
async def github_add_issue_comments(
    params: AddIssueCommentsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> AddIssueCommentsResult:
    """Add the same comment to one or more existing GitHub issues."""
    raw_numbers = parse_csv_ids(params.issue_numbers)
    if not raw_numbers:
        return AddIssueCommentsResult(success=False, error="No issue numbers provided.")

    parsed_numbers: list[int] = []
    for token_str in raw_numbers:
        try:
            parsed_numbers.append(int(token_str))
        except ValueError:
            return AddIssueCommentsResult(
                success=False,
                error=f"Invalid issue number: {token_str!r}",
            )

    def _add_one(repo: Any, issue_number: int) -> AddIssueCommentItem:
        try:
            issue = repo.get_issue(issue_number)
            comment = issue.create_comment(params.body)
            summary = IssueCommentSummary(
                id=comment.id,
                body=comment.body,
                user=_user_summary(comment.user),
                html_url=comment.html_url,
                created_at=(comment.created_at.isoformat() + "Z" if comment.created_at else None),
                updated_at=(comment.updated_at.isoformat() + "Z" if comment.updated_at else None),
            )
            return AddIssueCommentItem(issue_number=issue_number, success=True, comment=summary)
        except GithubException as exc:
            return AddIssueCommentItem(
                issue_number=issue_number,
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )

    def _call() -> AddIssueCommentsResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            items = [_add_one(repo, num) for num in parsed_numbers]
            return AddIssueCommentsResult(success=True, items=items)
        except GithubException as exc:
            return AddIssueCommentsResult(
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_list_pull_requests"],
    api_docs="https://docs.github.com/en/rest/pulls/pulls#list-pull-requests",
    provider="github",
)
async def github_list_pull_requests(
    params: ListPullRequestsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListPullRequestsResult:
    """List pull requests for a GitHub repository."""

    def _call() -> ListPullRequestsResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            kwargs: dict = {
                "state": params.state,
                "sort": params.sort,
                "direction": "desc",
            }
            if params.base is not None:
                kwargs["base"] = params.base
            pulls = repo.get_pulls(**kwargs)
            items = [_pr_summary(pr) for pr in pulls[: params.limit]]
            return ListPullRequestsResult(success=True, pull_requests=items)
        except GithubException as exc:
            return ListPullRequestsResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_get_pull_request"],
    api_docs="https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request",
    provider="github",
)
async def github_get_pull_request(
    params: GetPullRequestParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetPullRequestResult:
    """Retrieve detailed information about a specific GitHub pull request."""

    def _call() -> GetPullRequestResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            pr = repo.get_pull(params.pr_number)
            detail = _pr_detail(pr)
            return GetPullRequestResult(success=True, pull_request=detail)
        except GithubException as exc:
            return GetPullRequestResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_list_milestones"],
    api_docs="https://docs.github.com/en/rest/issues/milestones#list-milestones",
    provider="github",
)
async def github_list_milestones(
    params: ListMilestonesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListMilestonesResult:
    """List milestones for a GitHub repository."""

    def _call() -> ListMilestonesResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            milestones = repo.get_milestones(state=params.state)
            items = [s for ms in milestones if (s := _milestone_summary(ms)) is not None]
            return ListMilestonesResult(success=True, milestones=items)
        except GithubException as exc:
            return ListMilestonesResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_get_file_content"],
    api_docs="https://docs.github.com/en/rest/repos/contents#get-repository-content",
    provider="github",
)
async def github_get_file_content(
    params: GetFileContentParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetFileContentResult:
    """Retrieve file content or directory listing from a GitHub repository."""

    def _call() -> GetFileContentResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            kwargs: dict = {}
            if params.ref is not None:
                kwargs["ref"] = params.ref
            raw_contents = repo.get_contents(params.path, **kwargs)
            if isinstance(raw_contents, list):
                contents_list = cast(list[Any], raw_contents)
                entries = [
                    FileContentEntry(
                        name=entry.name,
                        path=entry.path,
                        type=entry.type,
                        size=entry.size,
                        sha=entry.sha,
                        html_url=entry.html_url,
                    )
                    for entry in contents_list
                ]
                dir_entry = FileContentEntry(
                    name=params.path.rsplit("/", 1)[-1] if "/" in params.path else params.path,
                    path=params.path,
                    type="dir",
                )
                return GetFileContentResult(
                    success=True,
                    file=dir_entry,
                    directory_entries=entries,
                    is_directory=True,
                )
            contents = cast(Any, raw_contents)
            decoded = None
            if contents.content is not None:
                try:
                    decoded = base64.b64decode(contents.content).decode("utf-8")
                except (UnicodeDecodeError, Exception):
                    decoded = f"(binary file, {contents.size} bytes)"
            entry = FileContentEntry(
                name=contents.name,
                path=contents.path,
                type=contents.type,
                size=contents.size,
                content=contents.content,
                encoding=contents.encoding,
                sha=contents.sha,
                html_url=contents.html_url,
            )
            return GetFileContentResult(
                success=True,
                file=entry,
                decoded_content=decoded,
            )
        except GithubException as exc:
            return GetFileContentResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_list_branches"],
    api_docs="https://docs.github.com/en/rest/branches/branches#list-branches",
    provider="github",
)
async def github_list_branches(
    params: ListBranchesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListBranchesResult:
    """List branches in a GitHub repository."""

    def _call() -> ListBranchesResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            branches = repo.get_branches()
            items = [BranchSummary(name=b.name, protected=b.protected) for b in branches]
            return ListBranchesResult(success=True, branches=items)
        except GithubException as exc:
            return ListBranchesResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


def _commit_summary(commit: Any) -> CommitSummary:
    """Extract a CommitSummary from a PyGithub Commit."""
    inner = commit.commit
    author = getattr(inner, "author", None)
    author_name = getattr(author, "name", None) if author is not None else None
    author_email = getattr(author, "email", None) if author is not None else None
    author_dt = getattr(author, "date", None) if author is not None else None
    author_date = author_dt.isoformat() + "Z" if author_dt else None
    sha = commit.sha
    return CommitSummary(
        sha=sha,
        short_sha=sha[:7],
        message=inner.message,
        author_name=author_name,
        author_email=author_email,
        author_date=author_date,
        html_url=commit.html_url,
    )


@tool(
    scopes=SCOPES["github_list_commits"],
    api_docs="https://docs.github.com/en/rest/commits/commits#list-commits",
    provider="github",
)
async def github_list_commits(
    params: ListCommitsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListCommitsResult:
    """List commits in a GitHub repository, in reverse chronological order."""

    def _call() -> ListCommitsResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            kwargs: dict[str, Any] = {}
            if params.sha:
                kwargs["sha"] = params.sha
            if params.path:
                kwargs["path"] = params.path
            if params.author:
                kwargs["author"] = params.author
            if params.since:
                kwargs["since"] = datetime.fromisoformat(params.since.replace("Z", "+00:00")).replace(tzinfo=UTC)
            if params.until:
                kwargs["until"] = datetime.fromisoformat(params.until.replace("Z", "+00:00")).replace(tzinfo=UTC)
            commits = repo.get_commits(**kwargs)
            items = [_commit_summary(c) for c in commits[: params.limit]]
            return ListCommitsResult(success=True, commits=items)
        except GithubException as exc:
            return ListCommitsResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_explore_releases"],
    api_docs="https://docs.github.com/en/rest/releases/releases#list-releases",
    provider="github",
)
async def github_explore_releases(
    params: ExploreReleasesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ExploreReleasesResult:
    """Explore releases for a GitHub repository."""

    def _call() -> ExploreReleasesResult:
        g = _build_client(token, base_url)
        try:
            repo = g.get_repo(f"{params.owner}/{params.repo}")
            if params.tag:
                release = repo.get_release(params.tag)
                summary = _release_summary(release)
                return ExploreReleasesResult(success=True, single_release=summary)
            releases = repo.get_releases()
            items = [_release_summary(r) for r in releases[: params.limit]]
            return ExploreReleasesResult(success=True, releases=items)
        except GithubException as exc:
            return ExploreReleasesResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_create_branch"],
    api_docs="https://docs.github.com/en/rest/git/refs#create-a-reference",
    provider="github",
)
async def github_create_branch(
    params: CreateBranchParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateBranchResult:
    """Create a new branch in a repository from an existing source branch."""

    def _call() -> CreateBranchResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            source_ref = repo.get_git_ref(f"heads/{params.source_branch}")
            sha = source_ref.object.sha
            repo.create_git_ref(ref=f"refs/heads/{params.branch_name}", sha=sha)
            repo_html_url = str(repo.html_url).rstrip("/")
            url = f"{repo_html_url}/tree/{params.branch_name}"
            return CreateBranchResult(
                success=True,
                branch_name=params.branch_name,
                source_branch=params.source_branch,
                sha=sha,
                url=url,
            )
        except GithubException as exc:
            return CreateBranchResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_update_file"],
    api_docs="https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents",
    provider="github",
)
async def github_update_file(
    params: UpdateFileParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateFileResult:
    """Create or update a file in a repository, committing directly to a branch."""

    def _call() -> UpdateFileResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            existing_sha = _resolve_existing_file_sha(repo, params.path, params.branch)
            if existing_sha is None:
                result = repo.create_file(
                    path=params.path,
                    message=params.commit_message,
                    content=params.content,
                    branch=params.branch,
                )
            else:
                result = repo.update_file(
                    path=params.path,
                    message=params.commit_message,
                    content=params.content,
                    sha=existing_sha,
                    branch=params.branch,
                )
            content_file = result["content"]
            commit = result["commit"]
            return UpdateFileResult(
                success=True,
                path=params.path,
                branch=params.branch,
                commit_sha=commit.sha,
                url=content_file.html_url,
            )
        except GithubException as exc:
            return UpdateFileResult(success=False, error=f"GitHub API error {exc.status}: {exc.data}")
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_create_pull_request"],
    api_docs="https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request",
    provider="github",
)
async def github_create_pull_request(
    params: CreatePullRequestParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreatePullRequestResult:
    """Create a pull request in a repository."""

    def _call() -> CreatePullRequestResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            kwargs: dict[str, Any] = {
                "base": params.base,
                "head": params.head,
                "title": params.title,
                "draft": params.draft,
            }
            if params.body:
                kwargs["body"] = params.body
            pr = repo.create_pull(**kwargs)
            return CreatePullRequestResult(success=True, pull_request=_pr_detail(pr))
        except GithubException as exc:
            return CreatePullRequestResult(
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )
        finally:
            g.close()

    return await asyncio.to_thread(_call)


def _release_notes_mode(generate: bool, body: str) -> str:
    """Describe how notes were composed for a release.

    GitHub prepends ``body`` to auto-generated notes when both are provided,
    so we surface that combination explicitly for the tool caller.
    """
    if generate and body:
        return "manual + auto-generated"
    if generate:
        return "auto-generated"
    if body:
        return "manual"
    return "none"


@tool(
    scopes=SCOPES["github_create_release"],
    api_docs="https://docs.github.com/en/rest/releases/releases#create-a-release",
    provider="github",
)
async def github_create_release(
    params: CreateReleaseParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateReleaseResult:
    """Create a GitHub release, optionally auto-generating release notes."""

    def _call() -> CreateReleaseResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            kwargs: dict[str, Any] = {
                "tag": params.tag_name,
                "draft": params.draft,
                "prerelease": params.prerelease,
                "generate_release_notes": params.generate_release_notes,
            }
            if params.release_title:
                kwargs["name"] = params.release_title
            if params.release_notes:
                kwargs["message"] = params.release_notes
            if params.target_commitish:
                kwargs["target_commitish"] = params.target_commitish
            release = repo.create_git_release(**kwargs)
            return CreateReleaseResult(
                success=True,
                release=_release_summary(release),
                target_commitish=params.target_commitish or None,
                notes_mode=_release_notes_mode(
                    params.generate_release_notes,
                    params.release_notes,
                ),
            )
        except GithubException as exc:
            return CreateReleaseResult(
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_generate_release_notes"],
    api_docs=("https://docs.github.com/en/rest/releases/releases#generate-release-notes-content-for-a-release"),
    provider="github",
)
async def github_generate_release_notes(
    params: GenerateReleaseNotesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GenerateReleaseNotesResult:
    """Preview auto-generated release notes without creating a release."""

    def _call() -> GenerateReleaseNotesResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            kwargs: dict[str, Any] = {"tag_name": params.tag_name}
            if params.target_commitish:
                kwargs["target_commitish"] = params.target_commitish
            if params.previous_tag_name:
                kwargs["previous_tag_name"] = params.previous_tag_name
            if params.configuration_file_path:
                kwargs["configuration_file_path"] = params.configuration_file_path
            notes = repo.generate_release_notes(**kwargs)
            return GenerateReleaseNotesResult(
                success=True,
                owner=params.owner,
                repo=params.repo,
                tag_name=params.tag_name,
                release_title=notes.name or params.tag_name,
                target_commitish=params.target_commitish or None,
                previous_tag_name=params.previous_tag_name or None,
                notes=notes.body,
            )
        except GithubException as exc:
            return GenerateReleaseNotesResult(
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_fork_repository"],
    api_docs="https://docs.github.com/en/rest/repos/forks#create-a-fork",
    provider="github",
)
async def github_fork_repository(
    params: ForkRepositoryParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ForkRepositoryResult:
    """Fork a repository into the authenticated user's account or an organization."""

    def _call() -> ForkRepositoryResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            kwargs: dict[str, Any] = {}
            if params.organization:
                kwargs["organization"] = params.organization
            if params.name:
                kwargs["name"] = params.name
            if params.default_branch_only:
                kwargs["default_branch_only"] = True
            fork = repo.create_fork(**kwargs)
            return ForkRepositoryResult(
                success=True,
                fork_full_name=fork.full_name,
                source_full_name=f"{params.owner}/{params.repo}",
                html_url=fork.html_url,
            )
        except GithubException as exc:
            return ForkRepositoryResult(
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )
        finally:
            g.close()

    return await asyncio.to_thread(_call)


@tool(
    scopes=SCOPES["github_get_repo_tree"],
    api_docs="https://docs.github.com/en/rest/git/trees#get-a-tree",
    provider="github",
)
async def github_get_repo_tree(
    params: GetRepoTreeParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetRepoTreeResult:
    """Return the recursive file tree of a repository for a ref or default branch."""

    def _call() -> GetRepoTreeResult:
        g = _build_client(token, base_url)
        try:
            repo = cast(Any, g.get_repo(f"{params.owner}/{params.repo}"))
            commit_ref = params.ref or repo.default_branch
            commit = repo.get_commit(commit_ref)
            tree = repo.get_git_tree(commit.commit.tree.sha, recursive=True)
            files: list[RepoTreeEntry] = []
            for entry in tree.tree:
                if entry.type != "blob":
                    continue
                if params.path_filter and not entry.path.startswith(params.path_filter):
                    continue
                files.append(
                    RepoTreeEntry(
                        path=entry.path,
                        size=entry.size or 0,
                        sha=entry.sha,
                    )
                )
            return GetRepoTreeResult(
                success=True,
                owner=params.owner,
                repo=params.repo,
                ref=params.ref or None,
                path_filter=params.path_filter or None,
                files=files,
                truncated=bool(getattr(tree, "truncated", False)),
            )
        except GithubException as exc:
            return GetRepoTreeResult(
                success=False,
                error=f"GitHub API error {exc.status}: {exc.data}",
            )
        finally:
            g.close()

    return await asyncio.to_thread(_call)
