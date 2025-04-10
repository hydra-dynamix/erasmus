# Docker Testing Environment

This directory contains the Docker configuration for testing the Erasmus installer in a clean environment.

## Prerequisites

- Docker
- Docker Compose (using `docker compose` command)

## Files

- `Dockerfile`: Defines a basic Python container with necessary dependencies
- `docker-compose.yml`: Orchestrates the container build and run process
- `../test_installer.sh`: Script to automate the testing process

## Testing Process

The testing process involves:

1. Building the release package (if not already built)
2. Building a Docker container with a clean Python environment
3. Running the installer inside the container
4. Verifying the installation

## Usage

To run the tests:

```bash
# From the project root
./build/test_installer.sh
```

The script will:
1. Check for Docker and Docker Compose
2. Build the release package if needed
3. Build and run the Docker container using `docker compose`
4. Execute the installer with automatic confirmation
5. Report the test results

## Environment Variables

- `IDE_ENV`: Set to `cursor` for testing

## Troubleshooting

If the test fails:

1. Check Docker and Docker Compose installation (using `docker compose` command)
2. Verify the release package exists in `release/v0.0.1/`
3. Check Docker logs for detailed error messages
4. Ensure the installer script has execute permissions

## Notes

- The container mounts the project directory as a volume for easy debugging
- The installer runs with automatic confirmation (`yes | installer.sh`)
- The container is ephemeral and will be removed after testing
- We use `docker compose` (not `docker-compose`) for all Docker Compose operations 