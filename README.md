# cimme

** It is not ready to be used right now. Consider only using it for testing it. **

Declarative, YAML formatted, immutable, container based CI/CD engine with Python and Docker

Cimme has started as an example CI/CD engine to create a demo with Docker, Python, and docker-py module.
Currently it is integrated with Gitea.

## Install

Running Cimme inside a Docker container, and providing Docker socket is enough to get started:

```bash
docker run -d -p 8000:8000 --name cimme -v /var/run/docker.sock:/var/run/docker.sock guray/cimme:0.1
```

Just add Gitea to its IP:8000 as a webhook and you are ready.

## Example Usage

YAML formatted pipelines can be used to declare steps. Example:

```yaml
---
type: pipeline
steps:
  - name: Clone repo
    environment: peptrnet/git:latest
    params:
      REPO_URL: https://github.com/gurayyildirim/rastgelesayi.git
  - name: Check whether requirements installable
    environment: python:3-alpine
    command: pip install -r requirements.txt
  - name: Build Docker image
    environment: docker:stable
    dockersocket: true
    command: docker build -t 127.0.0.1:5000/guray/random:{{ builtins.COMMIT_HASH }} .
  - name: Push Docker image
    environment: docker:stable
    dockersocket: true
    command: docker push 127.0.0.1:5000/guray/random:{{ builtins.COMMIT_HASH }}
```

For now, the pipeline should be defined in the code. It will be able to read it from repo and config files in the future.

More features will likely be added soon.
