NEEDS_ATTENTION_SUBJECT = "{provider} integration needs attention"
NEEDS_ATTENTION_BODY = (
    "The {provider} integration for {project} failed {count} times in a row, "
    "so sending is paused.\n\n"
    "Open the project's integration settings, check the delivery log and "
    "reconnect it: {frontend_url}/projects/{project_id}/integrations\n"
)
