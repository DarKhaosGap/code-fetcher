# Fetch Resource

A Python CLI that fetches a Java class and its direct project dependencies, then writes the
successful responses to a text file.

## Setup

Create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set the required connection variables:

```powershell
$env:RESOURCE_DOMAIN = "repo.example.com"
$env:RESOURCE_VERSION = "27.1.0"
$env:RESOURCE_USERNAME = "your-username"
$env:RESOURCE_PASSWORD = "your-password"
```

`RESOURCE_PROTOCOL` is optional and defaults to `https`.

The domain may include a safe base path. For example, setting
`$env:RESOURCE_DOMAIN = "repo.example.com/other"` places that base path before the version and
class resource path, producing a URL such as
`https://repo.example.com/other/25.6.7/com/test/Test.java`.

## Usage

Pass a fully qualified class name. The script converts package separators to `/`, fetches the
class and its direct project imports, and writes the results to a text file:

```powershell
python .\fetch_resource.py com.example.Example --output dependencies.txt
```

Each source is preceded by a fully qualified class-name header. Missing dependency requests produce
warnings; failure to fetch the requested root class exits with an error.

To prefer sources from a local project, pass its root folder. The script searches recursively, so
standard layouts such as `src/main/java/com/example/Example.java` are supported. Classes that are
not present locally continue to use the configured remote endpoint:

```powershell
python .\fetch_resource.py com.example.Example `
  --source-folder C:\Projects\example `
  --output dependencies.txt
```

View all command-line options:

```powershell
python .\fetch_resource.py --help
```

## Configuration Overrides

Protocol, domain, version, timeout, and output path can also be supplied on the command line:

```powershell
python .\fetch_resource.py `
  com.example.Example `
  --protocol https `
  --domain repo.example.com/other `
  --version 27.1.0 `
  --timeout 30 `
  --source-folder C:\Projects\example `
  --output dependencies.txt
```
