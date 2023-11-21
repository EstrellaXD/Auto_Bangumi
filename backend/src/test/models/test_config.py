from module.models.config import ExperimentalOpenAI


def test_experimental_openai_validate_api_base():
    config = ExperimentalOpenAI(api_type="openai", api_base="https://api.openai.com/")
    assert config.api_base == "https://api.openai.com/v1"

    config = ExperimentalOpenAI(api_base="https://api.openai.com/")
    assert config.api_base == "https://api.openai.com/v1"

    config = ExperimentalOpenAI(
        api_type="azure", api_base="https://custom-api-base.com"
    )
    assert config.api_base == "https://custom-api-base.com"
