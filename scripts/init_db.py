import subprocess


def main() -> None:
    subprocess.run(
        ["alembic", "upgrade", "head"],
        check=True,
    )
    print("Database migrations applied successfully.")


if __name__ == "__main__":
    main()
