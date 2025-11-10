#!/bin/bash

# Exit script as soon as a command fails.
set -e

echo "-----------------------------------------------------"
echo "STARTING FASTAPI ENTRYPOINT $(date)"
echo "-----------------------------------------------------"

echo "-----------------------------------------------------"
echo "FINISHED FASTAPI ENTRYPOINT $(date)"
echo "-----------------------------------------------------"

# Run the CMD - use "$@" to properly pass all arguments
echo "Executing command: $@"
exec "$@"
