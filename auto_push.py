#!/usr/bin/env python3
import os, sys, time, subprocess, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Set
import logging

CHECK_INTERVAL = 60
AUTO_COMMIT_MESSAGE = 'auto: periodic update'
IGNORE_DIRS = {'.git', '.kilo', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
IGNORE_EXTENSIONS = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('auto_push.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

class AutoPush:
    def __init__(self, repo_path='.'):
        self.repo_path = Path(repo_path).absolute()
        self.file_hashes = {}
    def should_ignore(self, path):
        for part in path.parts:
            if part in IGNORE_DIRS:
                return True
        if path.suffix in IGNORE_EXTENSIONS:
            return True
        if path.name.startswith('.') and path.name not in ['.env', '.gitignore']:
            return True
        return False
    def get_changed_files(self):
        changed = set()
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], cwd=self.repo_path, capture_output=True, text=True, check=True)
            for line in result.stdout.strip().split('\n'):
                if line:
                    filename = line[3:]
                    filepath = self.repo_path / filename
                    if not self.should_ignore(filepath):
                        changed.add(filepath)
        except subprocess.CalledProcessError as e:
            logger.error(f'Failed to check git status: {e}')
        return changed
    def stage_files(self, files):
        if not files:
            return True
        try:
            for filepath in files:
                if filepath.exists():
                    subprocess.run(['git', 'add', str(filepath.relative_to(self.repo_path))], cwd=self.repo_path, check=True)
                    logger.info(f'Staged: {filepath.relative_to(self.repo_path)}')
                else:
                    subprocess.run(['git', 'add', '-u', str(filepath.relative_to(self.repo_path))], cwd=self.repo_path, check=True)
                    logger.info(f'Staged deletion: {filepath.relative_to(self.repo_path)}')
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f'Failed to stage files: {e}')
            return False
    def commit(self, message=None):
        if message is None:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = f'{AUTO_COMMIT_MESSAGE} - {timestamp}'
        try:
            result = subprocess.run(['git', 'commit', '-m', message], cwd=self.repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f'Committed: {message}')
                return True
            else:
                if 'nothing to commit' in result.stderr.lower():
                    logger.debug('Nothing to commit')
                else:
                    logger.error(f'Commit failed: {result.stderr}')
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f'Failed to commit: {e}')
            return False
    def push(self):
        try:
            result = subprocess.run(['git', 'push', 'origin', 'main'], cwd=self.repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info('Pushed to remote repository')
                return True
            else:
                logger.error(f'Push failed: {result.stderr}')
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f'Failed to push: {e}')
            return False
    def run_once(self):
        changed_files = self.get_changed_files()
        if not changed_files:
            logger.debug('No changes detected')
            return False
        logger.info(f'Detected {len(changed_files)} changed file(s)')
        if not self.stage_files(changed_files):
            return False
        if not self.commit():
            return False
        if not self.push():
            return False
        return True
    def run_continuous(self, interval=CHECK_INTERVAL):
        logger.info(f'Starting auto-commit and push service (every {interval}s)')
        logger.info(f'Repository: {self.repo_path}')
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info('Service stopped')

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Auto-commit and push changes')
    parser.add_argument('--once', action='store_true', help='Run once')
    parser.add_argument('--interval', type=int, default=CHECK_INTERVAL, help='Interval in seconds')
    args = parser.parse_args()
    auto_push = AutoPush()
    if args.once:
        auto_push.run_once()
    else:
        auto_push.run_continuous(args.interval)

if __name__ == '__main__':
    main()
