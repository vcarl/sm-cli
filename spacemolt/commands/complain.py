import json
import os
from datetime import datetime, timezone

COMPLAINT_LOG = "/tmp/sm-complaints.jsonl"


def cmd_complain(api, args):
    """Log a complaint about the sm client's usability or intuitiveness."""
    text = getattr(args, "complaint_text", None)
    if not text:
        print("Usage: sm complain \"your complaint here\"")
        return

    # Get player identity if available
    session = None
    try:
        session = api.get_session_id()
    except Exception:
        pass

    username = api.username
    if not username and session:
        try:
            resp = api._post("get_status")
            username = resp.get("result", {}).get("player", {}).get("username")
        except Exception:
            pass

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": "complaint",
        "text": text,
    }
    if username:
        record["player"] = username
    if session:
        record["session"] = session

    # Log locally
    try:
        with open(COMPLAINT_LOG, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError:
        pass

    # Send to metrics server
    from spacemolt.api import _report_metric
    _report_metric(
        session or "?",
        "complain",
        username=username,
        command="complain",
        command_args=[text],
        extra={"complaint": text},
    )

    who = f" ({username})" if username else ""
    print(f"Complaint logged{who}. Thanks for the feedback!")
