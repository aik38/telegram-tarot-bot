param (
    [string]$Port = "8000"
)

Write-Output "Starting ngrok for port $Port (http://localhost:$Port)..."

ngrok http $Port
