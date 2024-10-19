from app import app

if __name__ == "__main__":
    # Run the app on all available interfaces (0.0.0.0) and port 5000
    # This allows the application to be accessible externally
    app.run(host='0.0.0.0', port=5000)
