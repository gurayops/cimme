import yaml
import docker
import tempfile
import jinja2
import falcon
import threading
from wsgiref.simple_server import make_server

# Constants
restartPolicy = {'Name': 'on-failure', 'MaximumRetryCount': 0}

volumeDict = {'bind': '/tmp/workon', 'mode': 'rw'}

volumeDockerSocket = {'bind': '/var/run/docker.sock', 'mode': 'rw'}


class BuiltinVars:
    COMMIT_HASH = None
    REPO_CLONE_URL = ''


def get_vars(**kwargs):
    print(kwargs)
    vars = BuiltinVars()
    for k, v in kwargs.items():
        vars.__setattr__(k, v)
    return vars


def get_pipeline(pipelineTemplate, vars):
    # Render and load the pipeline YAML
    renderedPipeline = jinja2.Template(pipelineTemplate).render(builtins=vars)
    return yaml.safe_load(renderedPipeline)


def is_pipeline(pipeline):
    # Check the type to ensure
    if pipeline['type'] != 'pipeline':
        print('type of YAML is not pipeline. Exiting with error.')
        return False
    return True


def streamLogs(container):
    for logLine in container.logs(stream=True, timestamps=True):
        print(logLine.decode(), end='')


def executeStep(client, step, workspace):
    # Prepare Docker environment details for execution
    stepImage = step['environment']
    stepCommand = step.get('command')
    stepEnvironments = step.get('params')
    stepUser = step.get('user') or 0
    volumesToMount = {workspace: volumeDict}

    # Only mount Docker socket when explicitly requested
    if step.get('dockersocket'):
        volumesToMount['/var/run/docker.sock'] = volumeDockerSocket

    # Run the step
    stepContainer = client.containers.run(
        stepImage,
        command=stepCommand,
        stderr=True,
        remove=False,
        detach=True,
        user=stepUser,
        volumes=volumesToMount,
        working_dir='/tmp/workon',
        environment=stepEnvironments,
    )

    return stepContainer


def executePipeline(client, pipeline):
    if not is_pipeline(pipeline):
        from sys import exit

        exit(1)

    workspace = tempfile.mkdtemp(dir='/tmp')

    # Get and run the steps
    steps = pipeline['steps']
    for number, step in enumerate(steps):
        print(f'**  Executing: {number + 1}/{len(steps)}', step['name'], '**')

        stepContainer = executeStep(client, step, workspace)
        # Print logs realtime
        streamLogs(stepContainer)
        print('=' * 50, '\n')
        # Evaluate exit code
        result = stepContainer.wait()
        if result['StatusCode'] != 0 or result['Error']:
            print(
                'Pipeline last step caused an error. See details in the log.\nExiting...'
            )
            break


def startABuild(repoURL, commitID):
    examplePipeline = '''
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
    '''
    # Initialize Docker client
    client = docker.from_env()

    # Get vars and render pipeline template
    print(commitID)
    vars = get_vars(COMMIT_HASH=commitID, REPO_CLONE_URL=repoURL)
    pipeline = get_pipeline(examplePipeline, vars)

    # Execute pipeline template
    executePipeline(client, pipeline)


class PipelineExecution:
    def __init__(self):
        super().__init__()

    def on_get(self, req, resp):
        '''Handles GET requests'''
        msg = {
            'message': (
                'please use post method to trigger'
            )
        }
        resp.media = msg

    def on_post(self, req, resp):
        gitData = req.media

        try:
            commitID = gitData['commits'][0]['id']
            repoURL = gitData['repository']['clone_url']
        except:
            resp.media = {'Status': 1,
                          'Detail': 'Cannot process because no key commits[0].id and repository.clone_url'}
            resp.status = falcon.HTTP_422
            return
        t = threading.Thread(target=startABuild,
                             args=(repoURL, commitID)).start()
        resp.media = {'Status': 0, 'Detail': 'Pipeline started.'}


api = falcon.API()
api.add_route('/', PipelineExecution())


if __name__ == '__main__':
    with make_server('', 8000, api) as httpd:
        print('Serving on port 8000...')

        # Serve until process is killed
        httpd.serve_forever()
