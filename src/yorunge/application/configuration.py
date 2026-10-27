from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Configuration


def activate(configuration: Configuration, name: str) -> Configuration:
    if name not in configuration.profiles:
        raise YorungeError("profile_not_found")
    return Configuration.model_validate({**configuration.model_dump(), "active_profile": name})


def project_selection(
    configuration: Configuration, name: str, project: str | None
) -> Configuration:
    profiles = {key: value.model_dump() for key, value in configuration.profiles.items()}
    profiles[name]["project_id"] = project
    return Configuration.model_validate({**configuration.model_dump(), "profiles": profiles})
