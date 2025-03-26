#!/usr/bin/env python3

import subprocess
import json
import sys
import os

def run_command(command):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def check_branch_protection(org_name, repo_name, branch_name):
    """Check if a branch has protection rules enabled"""
    protection = run_command(f'gh api repos/{org_name}/{repo_name}/branches/{branch_name}/protection')
    return protection is not None

def check_required_signatures(org_name, repo_name, branch_name):
    """Check if required signatures are enabled for a branch"""
    signatures = run_command(f'gh api repos/{org_name}/{repo_name}/branches/{branch_name}/protection/required_signatures')
    if signatures:
        try:
            return json.loads(signatures).get('enabled', False)
        except json.JSONDecodeError:
            return False
    return False

def main():
    # Check if organization name is provided
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <organization-name>")
        sys.exit(1)

    org_name = sys.argv[1]
    non_compliant_count = 0

    print(f"Fetching repositories for organization: {org_name}...")

    # Get all repositories in the organization
    repos_json = run_command(f'gh repo list {org_name} --limit 1000 --json name')
    if not repos_json:
        print("No repositories found or error accessing the organization.")
        sys.exit(1)

    repos = json.loads(repos_json)
    total_repos = len(repos)

    print(f"Found {total_repos} repositories. Checking compliance for each repository...")
    print("\nRepositories not meeting requirements:")

    for i, repo in enumerate(repos, 1):
        repo_name = repo['name']
        issues = []

        # Print progress
        sys.stdout.write(f"\rProcessing: {i}/{total_repos} ({repo_name})" + " " * 20)
        sys.stdout.flush()

        # Check main branch first, then master if main doesn't exist
        for branch in ['main', 'master']:
            # Check if branch exists
            branch_exists = run_command(f'gh api repos/{org_name}/{repo_name}/branches/{branch}')
            if branch_exists:
                # Branch exists, check protection
                is_protected = check_branch_protection(org_name, repo_name, branch)
                if not is_protected:
                    issues.append(f"'{branch}' branch is not protected")
                else:
                    # Check for required signatures
                    signatures_required = check_required_signatures(org_name, repo_name, branch)
                    if not signatures_required:
                        issues.append(f"Commit signing not required for '{branch}' branch")

                # We found a primary branch, no need to check the other one
                break
        else:
            # No main or master branch found
            issues.append("No main or master branch found")

        if issues:
            non_compliant_count += 1
            # Clear the progress line
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

            # Print issues for this repository immediately
            print(f"\n{org_name}/{repo_name}:")
            for issue in issues:
                print(f"  - {issue}")

    # Clear the progress line
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

    # Display summary
    if non_compliant_count == 0:
        print("\nAll repositories meet the requirements.")
    else:
        print(f"\nTotal: {non_compliant_count} non-compliant repositories out of {total_repos}")

if __name__ == "__main__":
    main()
