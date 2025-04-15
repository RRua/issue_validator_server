# Issue Validator Server

 This project is a Flask-based server application designed to serve a app that validates fixes of statically-detectable performance issues in open-source Android projects. 

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9 or higher
- Git (for Git operations)
- A virtual environment tool `uv`, `venv` or `conda`

### Installation

1. **Clone the repository:**

```

git clone https://github.com/rrua/issue-validator-server.git
cd issue-validator-server

```

2. **Set up a virtual environment:**


Create a virtual environment with `uv`:

```bash
uv venv
```

This command will create a `.venv` directory in your project folder, which is the virtual environment.

**Activating the Environment:**

- **Unix/macOS:**

```bash
source .venv/bin/activate
```


**Installing Packages:**


```bash
uv pip install 
```


## Usage

This server provides several endpoints for managing and validating issues:

```

python main.py

```
