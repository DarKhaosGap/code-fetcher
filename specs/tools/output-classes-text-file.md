# Output Classes As Text

## Summary
Replace ZIP archive output with one UTF-8 text file containing every successfully resolved Java class.

## Requirements
- Write the requested class and all successfully resolved direct dependencies to one text file.
- Separate class bodies with fully qualified class-name headers.
- Default the output path to `dependencies.txt` while preserving the `--output` override.
- Report output filesystem errors as configuration errors.
- Remove ZIP-specific filename collision behavior because classes are identified by headers.

## Scope
- `fetch_resource.py`: replace ZIP serialization with combined text output.
- `tests/test_fetch_resource.py`: verify formatted UTF-8 text output.
- `README.md`: document text output and examples.

## Implementation
`write_sources_text()` uses the existing `format_class_sources()` representation and writes it with
UTF-8 encoding. The ZIP writer, ZIP import, simple filename conversion, and duplicate filename
check were removed. `main()` now calls the text writer and `--output` defaults to
`dependencies.txt`.

## Validation
- `python -m unittest discover -s tests -v` passed with seven tests.
- The text writer test verifies multiple class-name headers, source bodies, and UTF-8 content.

## Status
Complete.
