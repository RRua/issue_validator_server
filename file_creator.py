import requests
import os

def get_tps():
    # get tps from http://127.0.0.1:5000/get_true_positives
    url = "http://127.0.0.1:5000/get_true_positives"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json()['content']  # Assuming the response is in JSON format
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching true positives: {e}")
        return None

def get_git_diffs(tp):
    url = "http://127.0.0.1:5000/get_git_diff"
    params = {
        "repo_dir": tp.get("repo_dir"),
        "curr_commit": tp.get("fix_commit_hash"),
        "issue_file": tp.get("issue_location").replace("file:", "").replace("|", "")[0],
        "issue_name": tp.get("issue_name")
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json()['content']  # Assuming the response is in JSON format
    except Exception as e:
        print(f"An error occurred while fetching git diff: {e}")
        return None


def get_file_content(tp):
    url = "http://127.0.0.1:5000/get_issue_file"
    params = {
        "repo_dir": tp.get("repo_dir"),
        "curr_commit": tp.get("fix_commit_hash"),
        "issue_file": tp.get("issue_location").replace("file:", "").split("|")[0],
        "issue_name": tp.get("issue_name")
    }
    print(params)
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json()['content']  # Assuming the response is in JSON format
    except Exception as e:
        print(f"An error occurred while getting file content: {e}")
        return None

def main():
    tps = get_tps()
    print(len(tps))
    for tp in tps:
        try:
            iss_file = os.path.basename(tp['issue_location'].replace("file:", "").split("|")[0])
        except:
            iss_file = "unknown"
        key = f"{tp['issue_name']}_{tp['prev_commit_hash']}_{tp['fix_commit_hash']}_{iss_file}.txt"
        git_diff = get_git_diffs(tp)
        if git_diff is not None and len(git_diff) > 0:
            diff_path = os.path.join("git_diffs", key)
            os.makedirs(os.path.dirname(diff_path), exist_ok=True)
            with open(diff_path, 'w') as f:
                f.write(git_diff)
        file_content = get_file_content(tp)
        if file_content is not None and len(file_content) > 256:
            file_path = os.path.join("files_content", key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(file_content)

if __name__ == '__main__':
    main()