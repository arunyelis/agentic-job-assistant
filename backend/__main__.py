import uvicorn

from backend.config import load_config


def main() -> None:
    config = load_config()
    uvicorn.run("backend.app:app", host="127.0.0.1", port=config.port)


if __name__ == "__main__":
    main()
