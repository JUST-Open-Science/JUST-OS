# Remove .gitkeep files to avoid markers trying to analyze them
rm -f data/pdfs/by-doi/.gitkeep
rm -f data/processed/markdown/.gitkeep

DETECTOR_BATCH_SIZE=8 RECOGNITION_BATCH_SIZE=64 uv run marker data/pdfs/by-doi --output_dir data/markdown --pdftext_workers 2 --skip_existing || echo "Warning: marker command failed with exit code $?"

# These will run regardless of whether the uv command succeeded
touch data/pdfs/by-doi/.gitkeep
touch data/processed/markdown/.gitkeep
