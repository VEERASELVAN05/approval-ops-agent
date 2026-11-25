ROLE_LIMITS = {
    "requester": {"max_vms": 8, "max_days": 30},
    "approver": {"max_vms": 8, "max_days": 30},
    "admin": {"max_vms": 20, "max_days": 90},
}

TOOL_ROLES = {
    "check_capacity": {"requester", "approver", "admin"},
    "create_request": {"requester", "admin"},
    "provision": {"requester", "admin"},
    "release": {"requester", "admin"},
}

RISKY_TOOLS = {"provision", "release"}