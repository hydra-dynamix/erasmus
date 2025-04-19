from erasmus.environment import EnvironmentConfig
import typer

app = typer.Typer(name="environment", help="Manage environment variables")


@app.command(name="list")
def list_environment_variables() -> None:
    """List all environment variables."""
    env_config = EnvironmentConfig()


if __name__ == "__main__":
    app()
