# Remove .gitkeep files to avoid marker trying to analyze them
rm -f data/pdfs/by-doi/.gitkeep

DETECTOR_BATCH_SIZE=8 RECOGNITION_BATCH_SIZE=64 uv run --group ingest marker data/pdfs/by-doi --output_format markdown --disable_image_extraction --output_dir data/processed/markdown --pdftext_workers 2 --skip_existing || echo "Warning: marker command failed with exit code $?"

# These will run regardless of whether the uv command succeeded
touch data/pdfs/by-doi/.gitkeep
