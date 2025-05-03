from flask import Flask, request, jsonify
import csv
import os
import re
from datetime import datetime
import subprocess
import signal
import time
from enum import Enum
import json
import traceback
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DEFAULT_LLM_VALIDATED_FILE = "reclassified_true_positives.csv"


class COMMAND_RESULT(object):
    def __init__(self, res, out, err):
        self.return_code = res
        self.output = out
        self.errors = err

    def validate(self, e=None):
        if int(self.return_code) != 0:
            if len(self.errors) > 2:
                if e is None:
                    print(self)
                    return False
                elif isinstance(e, Exception):
                    print(self)
                    raise e
                else:
                    loge(e)
                    print(self)
                    return False
            else:
                #print(self)
                return True
        else:
            return True

    def __str__(self):
        return str(
            {'return_code': self.return_code,
             'output': self.output,
             'errors': self.errors
             })


def execute_shell_command(cmd, args=(), timeout=None):
    command = cmd + " " + " ".join(args) if len(args) > 0 else cmd
    out = bytes()
    err = bytes()

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as e:
        print(f"Command {cmd} timed out")
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # Kill the whole process group
        proc.returncode = 1
    return COMMAND_RESULT(proc.returncode, out.decode("utf-8", errors='replace'), err.decode('utf-8', errors='replace'))

def get_file_content(repo_dir, curr_commit, issue_file, issue_spec, def_null_value="No info available"):
    issue_file = get_issue_file(repo_dir, curr_commit, issue_file)
    if issue_file is None:
        return def_null_value
    cont_cmd = f'cd {repo_dir} && git show {curr_commit}:{issue_file.strip()}'
    #print(cont_cmd)
    file_content_res = execute_shell_command(cont_cmd)
    file_content_res.validate()
    #ret_file_code = file_content_res.return_code
    file_content = file_content_res.output
    if file_content.strip() == "":
        file_content = def_null_value
    return file_content

def cat_file(filepath):
    file_content_res = execute_shell_command(f'cat {filepath}')
    #ret_file_code = file_content_res.return_code
    file_content = file_content_res.output
    print(filepath)
    if file_content.strip() == "":
        file_content = "Not available"
    return file_content


def load_issue_specification(filename="performance_issues_list.csv"):
    issues = {}
    with open(filename, 'r') as file:
        reader = csv.reader(file, delimiter=';')
        next(reader)
        for i, row in enumerate(reader):
            #print(i)
            issue_name = row[0].strip()
            if issue_name.strip() == '' or len(row) < 16:
                continue
            issues[issue_name] = {
                'description': row[14],
                'sample': row[15],
                'expected_fix': row[16],
                'file_extensions': row[17].strip().split(','),
                'severity': row[18],
                'example_1': row[19].strip(),
                'example_2': row[20].strip(),
            }
    return issues


def load_labels(filename=DEFAULT_LLM_VALIDATED_FILE):
    labels = {}
    if not os.path.exists(filename):
        return labels
    with open(filename, 'r') as file:
        reader = csv.reader(file, delimiter=';')
        for row in reader:
            # gen_label_key(reg['repo_dir'], reg['prev_commit_hash'], reg['commit_hash'], issue_name)
            key = gen_label_key(row[1], row[3], row[4], row[0])
            labels[key] = {
                'issue_name': row[0],
                'repo_dir': row[1],
                'issue_location': row[2],
                'prev_commit_hash': row[3],
                'fix_commit_hash': row[4],
                'commit_message': row[5],
                'sub_git_diff': row[6],
                'sub_file_ctnt': row[7],
                'pre_label': row[8],
                'llm_label': row[9],
                'llm_label_2': row[9] if len(row) < 11 else row[10]
            }
    return labels

def gen_label_key(repo_dir, prev_commit_hash, commit_hash, issue_name):
    return '-'.join([repo_dir, prev_commit_hash, commit_hash, issue_name])

def load_positive_labels(filename=DEFAULT_LLM_VALIDATED_FILE, classified=False):
    labels = {}
    if not os.path.exists(filename):
        return labels
    with open(filename, 'r') as file:
        reader = csv.reader(file, delimiter=';')
        for row in reader:
            if len(row) < 4:
                continue
            if not row[9].lower().startswith("true"):
                continue
            # gen_label_key(reg['repo_dir'], reg['prev_commit_hash'], reg['commit_hash'], issue_name)
            key = gen_label_key(row[1], row[3], row[4], row[0])
            v = {
                'issue_name': row[0],
                'repo_dir': row[1],
                'issue_location': row[2],
                'prev_commit_hash': row[3],
                'fix_commit_hash': row[4],
                'commit_message': row[5],
                'sub_git_diff': row[6],
                'sub_file_ctnt': row[7],
                'pre_label': row[8],
                'llm_label': row[9],
                'llm_label': row[9],
                'llm_label_2': row[9] if len(row) < 12 else row[10]
                
            }
            if classified:
                v['manual_label'] = row[10] if len(row) < 12 else row[11]
            labels[key] = v
    return labels

def save_label(issue, manual_label, file_path):
    with open(file_path, 'a+') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow([issue['issue_name'], issue['repo_dir'], issue['issue_location'], issue['prev_commit_hash'],
                            issue['fix_commit_hash'], issue['commit_message'], issue['sub_git_diff'], issue['sub_file_ctnt'],
                            issue['pre_label'],issue['llm_label'], manual_label
                        ])

def get_issue_file(repo_dir, curr_commit, issue_filepath):
    if issue_filepath is None:
        return None
    file_cmd = f'cd {repo_dir} ; git checkout {curr_commit} > /dev/null 2>&1 ; find . -type f -name {os.path.basename(issue_filepath)} | head -1'
    #print("file comd", file_cmd)
    file_find = execute_shell_command(file_cmd)
    file_find.validate()
    return file_find.output.strip() if file_find.output.strip() != "" else None


def get_code_diff(repo_dir, curr_commit, issue_filepath, def_null_value="No info available", optimize_token_count=True,
                  extensions=None):
    code_diff_target_extensions = '-- ' + ' '.join(list(map(lambda x: f'\"{x}\"', extensions.split(" ")))).replace("\"\"", "") if extensions is not None else DEFAULT_ISSUE_FILE_EXTENSIONS
    issue_file = get_issue_file(repo_dir, curr_commit, issue_filepath)
    print('issue file', issue_file)
    if issue_file is not None and issue_file.strip() != '':
        diff_cmd = f"cd {repo_dir} ; git checkout {curr_commit}; git diff HEAD^ {'-- ' + issue_file}"
    else:
        diff_cmd = f"cd {repo_dir} ; git checkout {curr_commit}; git diff HEAD^ {code_diff_target_extensions}"
    print("performing", diff_cmd)
    code_diff_res = execute_shell_command(diff_cmd)
    code_diff_res.validate()
    #print(code_diff_res)
    #print(issue)
    diff_output = code_diff_res.output if code_diff_res.output.strip() != "" else def_null_value
    return diff_output



@app.route('/get_true_positives', methods=['GET'])
def load_true_positives():
    labels = load_positive_labels()
    already_classified_labels = load_positive_labels('true_positives_validated.csv', classified=True)
    # Find keys in `labels` but not in `already_classified_labels`
    diff_keys = set(labels.keys()) - set(already_classified_labels.keys())
    diff_labels = {key: labels[key] for key in diff_keys}
    try:
        return jsonify({"status": "success", "content": list(diff_labels.values())})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/save_classified', methods=['POST'])
def save_classified():
    data = request.json
    print(data)
    issue_data = data.get('issue_data')
    classification = data.get('classification')
    if issue_data is None or classification is None:
        return jsonify({"status": "error", "message": "No issue data provided"})
    file_path = data.get('file_path', "true_positives_validated.csv")
    try:
        save_label(issue_data, classification, file_path)
        print("saved")
        return jsonify({"status": "success", "message": "Info saved successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_issues_specification', methods=['GET'])
def load_issue_list():
    issues = ISSUE_SPECS if len(ISSUE_SPECS) > 0 else load_issue_specification()
    try:
        return jsonify({"status": "success", "content": issues})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/get_issue_file', methods=['GET'])
def get_i_file():
    repo_dir = request.args.get('repo_dir')
    curr_commit = request.args.get('curr_commit')
    issue_file = request.args.get('issue_file', '').replace("file:", "")
    print(request.args)
    issue_name = request.args.get('issue_name')
    issue_spec = ISSUE_SPECS.get(issue_name)
    if issue_spec is None:
        return jsonify({"status": "error", "message": "Issue not found"})
    
    try:
        file_content = get_file_content(repo_dir, curr_commit, issue_file, issue_spec)
        return jsonify({"status": "success", "content": file_content})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_example_file', methods=['GET'])
def get_example_file():
    example_filename = request.args.get('example_filename')
    filepath = os.path.join("issue_examples", example_filename)
    print(filepath)
    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found"})
    try:
        with open(filepath, 'r') as file:
            file_content = file.read()
        if file_content.strip() == "":
            file_content = "No info available"
        return jsonify({"status": "success", "content": file_content})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_git_diff', methods=['GET'])
def get_git_diff():
    repo_dir = request.args.get('repo_dir')
    curr_commit = request.args.get('curr_commit')
    issue_file = request.args.get('issue_file', '').replace("file:", "")
    issue_name = request.args.get('issue_name')
    issue = ISSUE_SPECS.get(issue_name)
    if issue is None:
        return jsonify({"status": "error", "message": "Issue not found"})
    extensions = ' '.join(issue.get('file_extensions', None))
    print("extensions", extensions)
    try:
        diff_output = get_code_diff(repo_dir, curr_commit, issue_file, extensions=extensions)
        return jsonify({"status": "success", "content": diff_output})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_git_diff_remote', methods=['GET'])
def get_git_diff_remote():
    repo_dir = request.args.get('repo_dir')
    curr_commit = request.args.get('curr_commit')
    prev_commit = request.args.get('prev_commit')
    issue_file = request.args.get('issue_file', '').replace("file:", "")
    issue_name = request.args.get('issue_name')
    key = f"{issue_name}_{prev_commit}_{curr_commit}_{issue_file.split("/")[-1]}.txt"
    try:
        diff_output = cat_file(os.path.join("git_diffs", key))
        return jsonify({"status": "success", "content": diff_output})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_issue_file_remote', methods=['GET'])
def get_issue_file_remote():
    repo_dir = request.args.get('repo_dir')
    curr_commit = request.args.get('curr_commit')
    prev_commit = request.args.get('prev_commit')
    issue_file = request.args.get('issue_file', '').replace("file:", "")
    issue_name = request.args.get('issue_name')
    key = f"{issue_name}_{prev_commit}_{curr_commit}_{issue_file.split("/")[-1]}.txt"
    try:
        diff_output = cat_file(os.path.join("files_content", key))
        return jsonify({"status": "success", "content": diff_output})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    ISSUE_SPECS = load_issue_specification()
    app.run(host='0.0.0.0', port=5000, debug=True)
