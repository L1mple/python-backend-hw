from pytest_asyncio.plugin import Mode

def pytest_configure(config):
    config.option.asyncio_mode = Mode.AUTO