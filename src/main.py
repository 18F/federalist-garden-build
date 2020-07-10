import argparse
import inspect
import json
import os
import shlex

from build import build


def load_vcap():
    vcap_application = json.loads(os.getenv('VCAP_APPLICATION', '{}'))
    vcap_services = json.loads(os.getenv('VCAP_SERVICES', '{}'))

    space = vcap_application['space_name']

    uev_ups = next(
        ups for ups in vcap_services['user-provided']
        if ups['name'] == f'federalist-{space}-uev-key'
    )

    uev_env_var = 'USER_ENVIRONMENT_VARIABLE_KEY'
    os.environ[uev_env_var] = uev_ups['credentials']['key']


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run a federalist build')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-p', '--params', dest='params',
                       help='A JSON encoded string',
                       metavar="'{\"foo\": \"bar\"}'")
    group.add_argument('-f', '--file', dest='file',
                       help='A path to a JSON file', type=argparse.FileType('r'),
                       metavar="./foo.json")
    args = parser.parse_args()

    if args.params:
        params = json.loads(args.params)
    else:
        params = json.load(args.file)

    # TODO - move to env vars in production envs
    if 'FEDERALIST_BUILDER_CALLBACK' in params:
        os.environ['FEDERALIST_BUILDER_CALLBACK'] = params['FEDERALIST_BUILDER_CALLBACK']

    if 'STATUS_CALLBACK' in params:
        os.environ['STATUS_CALLBACK'] = params['STATUS_CALLBACK']

    build_arguments = inspect.getfullargspec(build)[0]
    for k in params:
        if k not in build_arguments:
            # Warn for unused argments, but don't break
            print(f'WARNING - Ignoring unused build argument: {k}')

    kwargs = {k.lower(): v for (k, v) in params.items() if v is not None and k in build_arguments}

    uevs = kwargs['user_environment_variables']
    if uevs and isinstance(uevs, str):
        kwargs['user_environment_variables'] = json.loads(uevs)

    kwargs['branch'] = shlex.quote(kwargs['branch'])
    kwargs['owner'] = shlex.quote(kwargs['owner'])
    kwargs['repository'] = shlex.quote(kwargs['repository'])

    if os.getenv('VCAP_APPLICATION', None):
        load_vcap()

    build(**kwargs)
