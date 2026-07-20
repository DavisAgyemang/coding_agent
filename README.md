# 🤖 CodeMan: Advanced Multi-Provider LLM & Secure Sandboxed Execution Harness

CodeMan is a modular, production-grade AI developer assistant that integrates directly with local file systems to inspect, write, and self-correct code execution chains. By coupling dynamic tree-sitter repository mapping with an isolated sandbox container, CodeMan can validate its code edits natively in real-time before finalizing file alterations.

---

## 🚀 Core Features

* **Multi-Provider Architecture:** Seamlessly routes between Azure OpenAI (including Passwordless Microsoft Entra ID authentication), Anthropic Claude, Standard OpenAI GPT-4o, and local air-gapped Ollama installations.
* **Level 4 Self-Healing Mandate:** When modifying workspace structures, CodeMan runs an automated feedback loop—writing files, validating execution inside an isolated container, analyzing compiler error diagnostics, and self-correcting until successful.
* **Tree-Sitter Workspace Mapping:** Leverages a custom abstract syntax tree (AST) parser to build structural maps of the target repository, passing precise logical layouts down to the LLM context.
* **Ephemeral Sandboxing Engine:** Executes lint, syntax checks, or unit testing routines completely isolated from the host operating system.
* **Zero-Leak Enterprise Security:** Credentials and communication histories are bound dynamically to transient volatile operating system environment arrays or localized machine home configurations, completely segregated from Git repository tracking workflows.

---

## 🛠️ Sandbox Setup: Docker vs. Podman Alternatives

To leverage CodeMan's secure code execution validation framework, you must have a container runtime platform active locally on your host machine. CodeMan uses the standard Docker API client under the hood, allowing it to seamlessly talk to either **Docker Desktop** or **Podman**.

Choose the installation path below that fits your local system permissions:

### Option A: Standard Path via Docker Desktop

Follow these steps to configure Docker Desktop natively from scratch:

#### 1. Download the Installer
Head to the official [Docker Download Page](https://www.docker.com/products/docker-desktop/) and select the package matching your Operating System:
* **Windows:** Click *Download for Windows*.
* **Mac:** Select *Mac with Intel Chip* or *Mac with Apple Chip* (M1/M2/M3/M4) depending on your computer's processor.
* **Linux:** Choose your distribution package format (Ubuntu, Debian, Fedora).

#### 2. Operating System Installation
* **For Windows (WSL 2 Backend):**
  1. Open PowerShell as an Administrator and ensure WSL is fully updated: `wsl --update`
  2. Launch `Docker Desktop Installer.exe`.
  3. When prompted, ensure **"Use WSL 2 instead of Hyper-V"** is checked.
  4. Complete the wizard and reboot your PC.
* **For macOS:**
  1. Open the downloaded `Docker.dmg` file.
  2. Drag and drop the **Docker icon** directly into your **Applications** folder.
  3. Double-click Docker in your Applications folder to run it.

#### 3. Run the Engine & Verify
1. Open the **Docker Desktop** app. Accept the Service Agreement if prompted.
2. Verify the status indicator light in the bottom-left corner turns **Green** (indicating the engine is active).
3. Open your terminal and confirm connection end-to-end by running:
   ```bash
   docker version
   docker run hello-world
   

##  Running the Secure Sandbox with Podman (Rootless/No-Admin Path)

If you are on a corporate laptop or do not have administrator permissions to install Docker Desktop, you can use **Podman** as a drop-in, rootless replacement. Your coding agent will run seamlessly inside a secure, containerized environment without requiring root access.

---

###  First-Time Podman Setup

If you don't have Podman installed yet, open your terminal and run the following commands to initialize it:

1. **Install Podman via Homebrew** (Installs completely within your user directory):
   ```bash
   brew install podman
   
    podman machine init --provider applehv

    podman machine start

### 🔌 Connect the Docker API Client Bridge

Look closely at the terminal output from the previous step. At the very bottom, Podman will print a dynamic helper path line that looks like this:

```bash
export DOCKER_HOST='unix:///var/folders/.../podman-machine-default-api.sock'
```

# Replace the path below with the exact string your 'podman machine start' command outputs!
```bash
echo "export DOCKER_HOST='unix:///YOUR_SPECIFIC_PODMAN_PATH_HERE.sock'" >> ~/.zshrc
source ~/.zshrc
```

### Run the CodeMan Agent Framework
in your terminal do run this:
```bash
pip install -r requirements.txt
 
python main.py
```
### how to run Codeman from anywhere
run the command below and you can use codeman everywhere on your pc
```bash
pip install -e .
```