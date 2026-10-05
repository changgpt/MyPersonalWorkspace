from daybook import create_app

app = create_app()

if __name__ == "__main__":
    # Bound to 127.0.0.1 only: this app is local-only, never exposed on the network.
    app.run(host="127.0.0.1", port=5000, debug=True)
