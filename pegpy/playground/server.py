#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess
import codecs
import json
import platform
import tempfile
from pathlib import Path
from datetime import datetime

from bottle import Bottle, request, static_file

#Server settings
app = Bottle()
rootPath = str(Path(__file__).resolve().parent)
root = datetime.now().strftime('?%Y%m%d%H%M%S')
url = 'http://0.0.0.0:3000' + root
save_name = ''
input_name = ''
new_input_name = ''
comp = None
p_arg = None
cmd = []
init_cmd = ''

#Server routings
@app.get('/')
def indexfile():
    return static_file('index.html', root=rootPath)

@app.post('/compile')
def compile():
    if not hasattr(request, 'json'):
        return createResponseJson('', '', 'content error: not json type')
    req = request.json

    file = tempfile.NamedTemporaryFile(mode='w', suffix='.zen', prefix='tmp', dir='/tmp')
    name = file.name
    file.close() #tempfile cannot use utf-8 in python 2.7, so need to reopen

    createSourceFile(name, req['source'])

    try:
        return createResponseJson('', compileCommand(name, cmd), '')
    except Exception as e:
        return createResponseJson('', 'compile error in python\n\n' + str(e), str(e))

@app.post('/command')
def command():
    if not hasattr(request, 'json'): return createResponseJson('', 'ajex error', 'content error: not json type')
    req = request.json

    file = tempfile.NamedTemporaryFile(mode='w', suffix='.zen', prefix='tmp', dir='/tmp')
    name = file.name
    file.close() #tempfile cannot use utf-8 in python 2.7, so need to reopen

    global cmd, input_name
    cmd2 = (req['cmd']).strip().split(' ')
    cmd = cmd2[:2] + restore_arg(p_arg(cmd2[2:]))

    if new_input_name != input_name:
        input_name = new_input_name
        write_inputs([input_name])
        with file_search('input.k').open() as f:
            input = f.read()
            createSourceFile(name, input)
    else:
        input = ''
        createSourceFile(name, req['source'])

    try:
        return createResponseJson(input, compileCommand(name, cmd), '')
    except Exception as e:
        return createResponseJson(input, 'compile error in python\n\n' + str(e), str(e))

@app.route('/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=rootPath)

@app.post('/close')
def close():
    app.close()
    write_inputs([])
    write_inputs([], 'output.k')
    sys.stderr.close()

@app.post('/save')
def save():
    if not hasattr(request, 'json'): return
    with file_search(save_name).open('w') as f:
        f.write(request.json['source'])

@app.post('/init')
def init():
    with file_search('input.k').open() as f:
        input = f.read()
    return json.dumps({'cmd': init_cmd, 'input': input})

def createResponseJson(input, output, error):
    return json.dumps({'input': input, 'output': output, 'error': error})

def createSourceFile(name, contents):
    with codecs.open(name, 'w', 'utf-8') as f:
        f.write(contents)

def compileCommand(name, cmd):
    d = p_arg(cmd[2:])
    w = comp(cmd[:2] + restore_arg(d) + ([name] if 'output' in d else ['-o', str(file_search('output.k')), name]))
    w.file.seek(0)
    cont = w.file.read()
    w.file.close()
    return cont

def file_search(file, subdir = 'sample'):
    return Path(__file__).resolve().parent / subdir / file

def write_inputs(datas, name = 'input.k'):
    text = ''
    for d in datas:
        if d == 'edit': continue

        path = Path(d)
        if path.exists():
            with path.open() as f: text += f.read() + '\n'
            continue

        path = file_search(d)
        if path.exists():
            with path.open() as f: text += f.read() + '\n'
            continue

        path = file_search(d, subdir='../grammar')
        if path.exists():
            with path.open() as f: text += f.read() + '\n'
            continue

        text += d + '\n'

    with file_search(name).open(mode = 'w') as f:
        f.write(text)

restore_data = {
    'grammar': '-g',
    'start': '-s',
    'output': '-o',
    'extension': '-X',
    'option': '-D',
    'inputs': '',
}

def parse_name(name):
    global new_input_name, save_name
    if ':' in name:
        id, name = name.split(':')
        new_input_name = name
        if id == 'edit': save_name = name
    return name

def restore_arg(d, data = restore_data):
    arg = []
    for key, pre in data.items():
        if key in d:
            if pre:
                arg.append(pre)
                arg.append(parse_name(d[key]))
            else:
                for name in d[key]:
                    if ':' in name: parse_name(name)
                    elif name: arg.append(name)
    return arg

def playground(argv, main, parse_arg):
    global comp, cmd, p_arg, input_name, new_input_name, init_cmd
    init_cmd = ' '.join(argv)
    arg = parse_arg(argv[2:])
    cmd = argv[:2] + restore_arg(arg)
    input_name = new_input_name
    write_inputs([input_name] if input_name else arg.get('inputs', []))
    comp = main
    p_arg = parse_arg

    if platform.system() == 'Darwin':
        try:
            subprocess.check_call(['open', url])
        except:
            pass
    app.run(host='0.0.0.0', port=3000)
    write_inputs([])
    write_inputs([], 'output.k')
