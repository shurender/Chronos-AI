import uuid
from datetime import datetime

def parse_slack_export(slack_data, channel_name="general"):
    chunks = []
    threads = {}
    
    # Identify parents and cluster replies together
    for msg in slack_data:
        ts = msg.get("ts")
        thread_ts = msg.get("thread_ts")
        
        if thread_ts and ts == thread_ts:
            threads[thread_ts] = {"parent": msg, "replies": []}
        elif thread_ts:
            if thread_ts not in threads:
                threads[thread_ts] = {"parent": None, "replies": []}
            threads[thread_ts]["replies"].append(msg)

    # Process each entry 
    for msg in slack_data:
        ts = msg.get("ts")
        thread_ts = msg.get("thread_ts")
        user = msg.get("user", "unknown-user")
        text = msg.get("text", "")
        
        # Safe datetime timestamp string translation
        timestamp = None
        if ts:
            try:
                timestamp = datetime.fromtimestamp(float(ts)).isoformat() + "Z"
            except Exception:
                timestamp = None

        if thread_ts and thread_ts in threads:
            parent = threads[thread_ts]["parent"]
            if parent and ts == thread_ts:
                # Merge replies together within parent chunk context
                replies_text = ""
                for reply in threads[thread_ts]["replies"]:
                    r_user = reply.get("user", "unknown-user")
                    r_text = reply.get("text", "")
                    replies_text += f"\n  - [{r_user}]: {r_text}"
                
                combined_text = f"Slack Thread in #{channel_name}\n[{user}]: {text}\nReplies:{replies_text}"
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "source_type": "slack_message",
                    "source_id": ts,
                    "raw_text": combined_text.strip(),
                    "author": user,
                    "timestamp": timestamp,
                    "project": channel_name,
                    "metadata": {
                        "channel_name": channel_name,
                        "thread_ts": thread_ts,
                        "reply_count": len(threads[thread_ts]["replies"])
                    }
                })
            elif not parent:
                # Fallback to single message parsing if the parent thread trace is missing
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "source_type": "slack_message",
                    "source_id": ts,
                    "raw_text": f"Slack Message in #{channel_name}\n[{user}]: {text}",
                    "author": user,
                    "timestamp": timestamp,
                    "project": channel_name,
                    "metadata": {
                        "channel_name": channel_name,
                        "ts": ts
                    }
                })
        else:
            # Standalone direct channel messages
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_type": "slack_message",
                "source_id": ts,
                "raw_text": f"Slack Message in #{channel_name}\n[{user}]: {text}",
                "author": user,
                "timestamp": timestamp,
                "project": channel_name,
                "metadata": {
                    "channel_name": channel_name,
                    "ts": ts
                }
            })
            
    return chunks