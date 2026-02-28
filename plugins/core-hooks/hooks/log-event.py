#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Observer hook for PermissionRequest and Notification events.

Returns {} so run-with-fallback.sh captures and logs the full event input
(including tool_name, tool_input, permission_suggestions for PermissionRequest;
message, title, notification_type for Notification) without making any decision.
"""
import json

print(json.dumps({}))
