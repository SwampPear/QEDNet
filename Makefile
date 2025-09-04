clean:
	lake update
	lake exe cache get

	uv run pytest