import os
import hashlib

def compute_application_hash(source_dir: str) -> str:
    if not source_dir or not os.path.exists(source_dir):
        return "empty_or_missing_source"
    
    sha256 = hashlib.sha256()
    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        files.sort()
        for f in files:
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, source_dir)
            sha256.update(rel_path.encode('utf-8'))
            with open(file_path, 'rb') as f_obj:
                while chunk := f_obj.read(8192):
                    sha256.update(chunk)
    return sha256.hexdigest()

def compute_infrastructure_hash(hcl_content: str) -> str:
    if not hcl_content:
        return "empty_hcl"
    return hashlib.sha256(hcl_content.encode('utf-8')).hexdigest()
