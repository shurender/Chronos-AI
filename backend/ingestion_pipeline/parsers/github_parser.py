import uuid

def parse_github_commits(commits_data, repo_name="default-repo"):
    chunks = []
    for commit in commits_data:
        sha = commit.get("sha", f"mock-sha-{uuid.uuid4().hex[:8]}")
        author = commit.get("author", "unknown-author")
        timestamp = commit.get("timestamp")  # ISO-8601 UTC string or None
        message = commit.get("message", "")
        diff = commit.get("diff", "")
        
        # Keep the commit message and its diff content within one chunk
        raw_text = f"GitHub Commit: {sha}\nAuthor: {author}\nMessage: {message}\nChanges:\n{diff}"
        
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "source_type": "github_commit",
            "source_id": sha,
            "raw_text": raw_text.strip(),
            "author": author,
            "timestamp": timestamp,
            "project": repo_name,
            "metadata": {
                "repo_name": repo_name,
                "sha": sha,
                "message_length": len(message)
            }
        })
    return chunks

def parse_github_issues(issues_data, repo_name="default-repo"):
    chunks = []
    for issue in issues_data:
        issue_id = str(issue.get("id", f"mock-issue-{uuid.uuid4().hex[:8]}"))
        number = issue.get("number", 1)
        title = issue.get("title", "")
        body = issue.get("body", "")
        author = issue.get("author", "unknown-author")
        timestamp = issue.get("timestamp")
        
        # Base issue chunk
        raw_text = f"GitHub Issue #{number}: {title}\nAuthor: {author}\nDescription:\n{body}"
        
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "source_type": "github_issue",
            "source_id": issue_id,
            "raw_text": raw_text.strip(),
            "author": author,
            "timestamp": timestamp,
            "project": repo_name,
            "metadata": {
                "repo_name": repo_name,
                "issue_number": number,
                "title": title
            }
        })
        
        # Preserve comment nested replies
        comments = issue.get("comments", [])
        for comment in comments:
            comment_id = str(comment.get("id", f"mock-comment-{uuid.uuid4().hex[:8]}"))
            comment_body = comment.get("body", "")
            comment_author = comment.get("author", "unknown-author")
            comment_timestamp = comment.get("timestamp")
            
            raw_comment_text = f"Comment on Issue #{number} ({title}) by {comment_author}:\n{comment_body}"
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_type": "github_issue",
                "source_id": comment_id,
                "raw_text": raw_comment_text.strip(),
                "author": comment_author,
                "timestamp": comment_timestamp,
                "project": repo_name,
                "metadata": {
                    "repo_name": repo_name,
                    "issue_number": number,
                    "comment_id": comment_id
                }
            })
    return chunks