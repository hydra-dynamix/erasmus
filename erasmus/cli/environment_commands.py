from erasmus.environment import EnvironmentConfig
import typer

environment_app = typer.Typer(name="environment", help="Manage environment variables")


@environment_app.command(name="list")
def list_environment_variables() -> None:
    """List all environment variables."""
    env_config = EnvironmentConfig()


if __name__ == "__main__":
    environment_app()
