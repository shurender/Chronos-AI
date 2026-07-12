from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from backend import config
from backend.Ingestion.ingestion_service import ingest_connector_chunks
from backend.ingestion_pipeline.parsers.github_parser import parse_github_commits, parse_github_issues

from ..connector_schema import ConnectorAccount, ConnectorSyncRequest, ConnectorSyncResponse, GithubSource
from ..connector_store import (
    consume_oauth_state,
    create_oauth_state,
    get_account,
    get_selected_sources,
    save_account,
    set_status,
)
from ..sync_state import get_state, update_state

API = "https://api.github.com"


def start() -> RedirectResponse:
    if not config.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.")
    state = create_oauth_state("github")
    params = {
        "client_id": config.GITHUB_CLIENT_ID,
        "redirect_uri": config.GITHUB_REDIRECT_URI,
        "scope": "repo read:user read:org",
        "state": state,
    }
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{httpx.QueryParams(params)}")


def callback(code: str | None, state: str | None) -> RedirectResponse:
    if not code or not consume_oauth_state(state, "github"):
        raise HTTPException(status_code=400, detail="Invalid GitHub OAuth callback.")
    if not config.GITHUB_CLIENT_ID or not config.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured.")

    with httpx.Client(timeout=15.0) as client:
        token_res = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": config.GITHUB_CLIENT_ID,
                "client_secret": config.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": config.GITHUB_REDIRECT_URI,
            },
        )
        token_res.raise_for_status()
        token_body = token_res.json()
        token = token_body.get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="GitHub did not return an access token.")
        user_res = client.get(f"{API}/user", headers=_headers(token))
        user_res.raise_for_status()
        user = user_res.json()

    save_account(
        ConnectorAccount(
            provider="github",
            account_id=str(user.get("id") or ""),
            display_name=user.get("login") or user.get("name") or "GitHub",
            access_token=token,
            scopes=[scope.strip() for scope in (token_body.get("scope") or "").split(",") if scope.strip()],
            expires_at=datetime.utcnow() + timedelta(seconds=int(token_body["expires_in"])) if token_body.get("expires_in") else None,
        )
    )
    return RedirectResponse("http://localhost:5173/?connector=github&status=connected")


def sync(request: ConnectorSyncRequest) -> ConnectorSyncResponse:
    set_status("github", status="syncing", error=None, last_sync_status="running")
    token = (get_account("github").access_token if get_account("github") else None) or config.GITHUB_TOKEN
    if not token:
        set_status("github", status="error", connected=False, error="Connect GitHub or set GITHUB_TOKEN before syncing.")
        raise HTTPException(status_code=401, detail="Connect GitHub or set GITHUB_TOKEN before syncing.")

    try:
        source_ids = request.sourceIds or ([request.repo] if request.repo else None) or get_selected_sources("github")
        if not source_ids:
            message = "Select one or more GitHub repositories before syncing."
            set_status("github", status="error", last_sync_status="failed", error=message)
            raise HTTPException(status_code=422, detail=message)
        repos = [_parse_repo_ref(source_id) for source_id in source_ids]
        chunks: list[dict] = []
        counts: dict[str, int] = {"repos": len(repos)}
        for owner, name in repos:
            repo_label = f"{owner}/{name}"
            state = get_state("github", repo_label)
            since = request.since or state.last_sync_at if state else request.since
            repo_chunks, repo_counts = _fetch_repo_chunks(
                token,
                owner,
                name,
                request.maxItems or request.max_items,
                include_issues=request.includeIssues,
                include_pull_requests=request.includePullRequests,
                since=since,
            )
            for chunk in repo_chunks:
                meta = chunk.setdefault("metadata", {})
                meta.update({
                    "connector_provider": "github",
                    "connector_source_id": repo_label,
                    "source_name": repo_label,
                    "source_auth": "authenticated",
                    "source_live": True,
                    "repo": repo_label,
                })
            chunks.extend(repo_chunks)
            update_state(
                "github",
                repo_label,
                source_name=repo_label,
                last_cursor=since,
                seen_item_ids=[chunk["chunk_id"] for chunk in repo_chunks],
                item_count=len(repo_chunks),
            )
            for key, value in repo_counts.items():
                counts[key] = counts.get(key, 0) + value
        run = ingest_connector_chunks("github", chunks, counts)
        if run.status == "failed":
            raise RuntimeError("; ".join(run.errors) or "GitHub ingestion failed.")
        now = datetime.utcnow().isoformat()
        counts.update({key: value for key, value in run.source_summary.items() if isinstance(value, int)})
        counts.update({"chunks": run.chunks_created, "nodes": run.nodes_created, "edges": run.edges_created, "nodes_created": run.nodes_created, "edges_created": run.edges_created})
        set_status(
            "github",
            status="connected",
            connected=True,
            last_synced=now,
            last_sync_status="succeeded",
            error=None,
            source_counts=counts,
            items_ingested=run.chunks_created,
        )
        return ConnectorSyncResponse(provider="github", status="connected", run=run, last_synced=now, source_counts=counts)
    except Exception as exc:
        message = str(exc)
        set_status("github", status="error", last_sync_status="failed", error=message)
        raise HTTPException(status_code=502, detail=message) from exc


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _parse_repo_ref(repo: str | None) -> tuple[str, str]:
    if not repo:
        raise ValueError("Provide a GitHub repo as owner/repo or connect OAuth to sync recent user repos.")
    ref = repo.strip()
    if ref.startswith(("http://", "https://")):
        parts = [part for part in ref.rstrip("/").split("/") if part]
        return parts[-2], parts[-1].removesuffix(".git")
    owner, name = ref.split("/", 1)
    return owner, name


def _fetch_user_repos(token: str, limit: int) -> list[tuple[str, str]]:
    with httpx.Client(timeout=15.0, headers=_headers(token)) as client:
        res = client.get(f"{API}/user/repos", params={"per_page": limit, "sort": "updated", "affiliation": "owner,collaborator,organization_member"})
        res.raise_for_status()
        repos = res.json()
    return [(repo["owner"]["login"], repo["name"]) for repo in repos[:limit]]


def sources() -> list[GithubSource]:
    if not config.GITHUB_ALLOW_REPO_DISCOVERY:
        raise HTTPException(
            status_code=403,
            detail="GitHub repository discovery is disabled for this public demo. Paste a public owner/repo instead.",
        )
    token = (get_account("github").access_token if get_account("github") else None) or config.GITHUB_TOKEN
    if not token:
        raise HTTPException(status_code=401, detail="Connect GitHub or set GITHUB_TOKEN before listing repositories.")
    selected = set(get_selected_sources("github"))
    with httpx.Client(timeout=15.0, headers=_headers(token)) as client:
        res = client.get(
            f"{API}/user/repos",
            params={"per_page": 100, "sort": "updated", "affiliation": "owner,collaborator,organization_member"},
        )
        res.raise_for_status()
        repos = res.json()
    return [
        GithubSource(
            id=repo.get("full_name") or str(repo.get("id")),
            name=repo.get("name") or "",
            full_name=repo.get("full_name") or "",
            private=bool(repo.get("private")),
            html_url=repo.get("html_url"),
            updated_at=repo.get("updated_at"),
            default_branch=repo.get("default_branch"),
            selected=(repo.get("full_name") or str(repo.get("id"))) in selected,
        )
        for repo in repos
    ]


def _fetch_repo_chunks(
    token: str,
    owner: str,
    name: str,
    max_items: int,
    *,
    include_issues: bool,
    include_pull_requests: bool,
    since: str | None,
) -> tuple[list[dict], dict[str, int]]:
    per_page = max(1, min(max_items, 200))
    headers = _headers(token)
    base = f"{API}/repos/{owner}/{name}"
    with httpx.Client(timeout=20.0, headers=headers) as client:
        commit_params = {"per_page": per_page}
        if since:
            commit_params["since"] = since
        commits = _json(client.get(f"{base}/commits", params=commit_params))
        issues = (
            [item for item in _json(client.get(f"{base}/issues", params={"per_page": per_page, "state": "all"})) if "pull_request" not in item]
            if include_issues
            else []
        )
        pulls = (
            _json(client.get(f"{base}/pulls", params={"per_page": min(per_page, 50), "state": "all"}))
            if include_pull_requests
            else []
        )
        comments: list[dict[str, Any]] = []
        for issue in issues[: min(10, len(issues))]:
            comments.extend(_json(client.get(f"{base}/issues/{issue.get('number')}/comments", params={"per_page": 20})))

    repo_label = f"{owner}/{name}"
    chunks = parse_github_commits(_map_commits(commits), repo_label)
    chunks.extend(parse_github_issues(_map_issues(issues, comments), repo_label))
    chunks.extend(_map_pull_chunks(pulls, repo_label))
    for chunk in chunks:
        meta = chunk.setdefault("metadata", {})
        if chunk.get("source_type") == "github_commit":
            meta["entity_type"] = "commit"
            if meta.get("sha"):
                chunk["chunk_id"] = f"github:{repo_label}:{meta['sha']}"
                meta["external_id"] = meta["sha"]
                meta["source_url"] = f"https://github.com/{repo_label}/commit/{meta['sha']}"
                meta["url"] = meta["source_url"]
        elif meta.get("comment_id"):
            meta["entity_type"] = "comment"
            chunk["chunk_id"] = f"github:{repo_label}:issue:{meta.get('issue_number')}:comment:{meta.get('comment_id')}"
            meta["external_id"] = str(meta.get("comment_id"))
            meta["source_url"] = f"https://github.com/{repo_label}/issues/{meta.get('issue_number')}#issuecomment-{meta.get('comment_id')}"
            meta["url"] = meta["source_url"]
        elif chunk.get("source_type") == "github_issue":
            meta["entity_type"] = "issue"
            chunk["chunk_id"] = f"github:{repo_label}:issue:{meta.get('issue_number')}"
            meta["external_id"] = str(meta.get("issue_number"))
            meta["source_url"] = f"https://github.com/{repo_label}/issues/{meta.get('issue_number')}"
            meta["url"] = meta["source_url"]
    return chunks, {"commits": len(commits), "issues": len(issues), "pull_requests": len(pulls), "comments": len(comments)}


def _json(response: httpx.Response) -> list[dict]:
    response.raise_for_status()
    body = response.json()
    return body if isinstance(body, list) else []


def _map_commits(raw: list[dict]) -> list[dict]:
    return [
        {
            "sha": item.get("sha"),
            "author": ((item.get("commit") or {}).get("author") or {}).get("name") or "unknown",
            "timestamp": ((item.get("commit") or {}).get("author") or {}).get("date"),
            "message": (item.get("commit") or {}).get("message", ""),
            "diff": item.get("html_url") or "",
        }
        for item in raw
    ]


def _map_issues(raw: list[dict], comments: list[dict]) -> list[dict]:
    by_issue_url: dict[str, list[dict]] = {}
    for comment in comments:
        by_issue_url.setdefault(comment.get("issue_url", ""), []).append(
            {
                "id": comment.get("id"),
                "body": comment.get("body") or "",
                "author": (comment.get("user") or {}).get("login", "unknown"),
                "timestamp": comment.get("created_at"),
            }
        )
    return [
        {
            "id": item.get("id"),
            "number": item.get("number"),
            "title": item.get("title", ""),
            "body": item.get("body") or "",
            "author": (item.get("user") or {}).get("login", "unknown"),
            "timestamp": item.get("created_at"),
            "comments": by_issue_url.get(item.get("url", ""), []),
        }
        for item in raw
    ]


def _map_pull_chunks(raw: list[dict], repo_label: str) -> list[dict]:
    chunks = []
    for pr in raw:
        chunks.append(
            {
                "chunk_id": f"github:{repo_label}:pr:{pr.get('number')}",
                "source_type": "github_pull_request",
                "source_id": str(pr.get("id")),
                "raw_text": f"GitHub Pull Request #{pr.get('number')}: {pr.get('title')}\nAuthor: {(pr.get('user') or {}).get('login', 'unknown')}\nState: {pr.get('state')}\n{pr.get('body') or ''}",
                "author": (pr.get("user") or {}).get("login", "unknown"),
                "timestamp": pr.get("created_at"),
                "project": repo_label,
                "metadata": {
                    "repo_name": repo_label,
                    "url": pr.get("html_url"),
                    "source_url": pr.get("html_url"),
                    "external_id": str(pr.get("number")),
                    "entity_type": "pr",
                },
            }
        )
    return chunks
