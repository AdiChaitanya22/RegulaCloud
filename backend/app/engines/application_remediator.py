import os
import re
from typing import List, Tuple

import hashlib
import tempfile
import shutil

class ApplicationRemediator:
    """
    Applies deterministic code patches to uploaded project source files.
    """

    SUPPORTED_ACTIONS = {"ACT_UPGRADE_WEAK_CRYPTO", "ACT_PARAMETERIZE_SQL_QUERIES", "ACT_PATCH_SONAR_INJECTION"}

    @classmethod
    def apply_source_actions(cls, source_path: str, action_ids: List[str], db=None, actor="system") -> Tuple[List[str], List[str], List[str]]:
        if not source_path or not os.path.exists(source_path):
            return [], [f"{a}: No application source path found." for a in action_ids], []

        applied_actions = []
        skipped_actions = []
        changed_files = set()
        
        from backend.app.db.models import AuditLog

        for action in action_ids:
            if action not in cls.SUPPORTED_ACTIONS:
                skipped_actions.append(f"{action}: Unsupported application remediation.")
                continue

            action_applied = False
            for root, _, files in os.walk(source_path):
                for file in files:
                    if file.endswith(".java"):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, source_path)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        before_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                        new_content = content

                        if action == "ACT_UPGRADE_WEAK_CRYPTO":
                            # Syntax-safety: skip commented lines
                            lines = new_content.split('\n')
                            for i, line in enumerate(lines):
                                if line.strip().startswith("//") or line.strip().startswith("*"):
                                    continue
                                
                                if "SecretKeySpec" in line and '"DES"' in line:
                                    lines[i] = re.sub(r'new\s+SecretKeySpec\s*\(\s*([^,]+)\s*,\s*"DES"\s*\)', r'new SecretKeySpec(\1, "AES")', line)
                                if "Cipher.getInstance" in line:
                                    lines[i] = re.sub(r'Cipher\.getInstance\s*\(\s*"DES/ECB/PKCS5Padding"\s*\)', r'Cipher.getInstance("AES/GCM/NoPadding")', lines[i])
                                    lines[i] = re.sub(r'Cipher\.getInstance\s*\(\s*"DES"\s*\)', r'Cipher.getInstance("AES/GCM/NoPadding")', lines[i])
                                    lines[i] = re.sub(r'Cipher\.getInstance\s*\(\s*"3DES[^"]*"\s*\)', r'Cipher.getInstance("AES/GCM/NoPadding")', lines[i])
                            
                            new_content = '\n'.join(lines)

                        elif action in ("ACT_PARAMETERIZE_SQL_QUERIES", "ACT_PATCH_SONAR_INJECTION"):
                            # Regex is brittle, doing line-by-line syntax-aware parsing where possible
                            lines = new_content.split('\n')
                            skip_file = False
                            for i, line in enumerate(lines):
                                if line.strip().startswith("//") or line.strip().startswith("*"):
                                    continue
                                
                                # Check if string contains multiple sql statements or complex variables
                                if re.search(r'String\s+\w+\s*=\s*"(?:[^"\\]|\\.)*WHERE\s+[\w.]+\s*=\s*\'?"\s*\+\s*\w+', line):
                                    if line.count('+') > 2:
                                        skip_file = True # Too complex to safely rewrite with regex
                                        continue
                                    
                                    # Safe rewrite
                                    def replace_sqli(match):
                                        base = match.group(1).rstrip("'\"").rstrip()
                                        var_name = match.group(2).strip()
                                        return f'PreparedStatement ps = conn.prepareStatement({base} ?");\n        ps.setString(1, {var_name});'

                                    sqli_pattern = re.compile(
                                        r'String\s+\w+\s*=\s*("(?:[^"\\]|\\.)*WHERE\s+[\w.]+\s*=\s*\'?")\s*\+\s*(\w+)(?:\s*\+\s*"\'?"\s*)?\s*;'
                                    )
                                    lines[i] = sqli_pattern.sub(replace_sqli, line)
                                
                                # Replace executeQuery
                                if "executeQuery(" in line and "ps.executeQuery" not in line and "PreparedStatement" not in line:
                                    lines[i] = re.sub(r'\w+\.executeQuery\(\w+\)', r'ps.executeQuery()', line)
                                    
                                if "Statement" in line and ".createStatement()" in line:
                                    lines[i] = '' # Remove unused Statement

                            if skip_file:
                                continue
                            new_content = '\n'.join(lines)

                        # Check for changes
                        if new_content != content:
                            after_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
                            
                            # Atomic file write with rollback
                            fd, temp_path = tempfile.mkstemp(dir=root)
                            try:
                                with os.fdopen(fd, 'w', encoding="utf-8") as f:
                                    f.write(new_content)
                                os.replace(temp_path, file_path)
                                
                                changed_files.add(file_path)
                                action_applied = True
                                
                                if db:
                                    AuditLog.create_entry(
                                        session=db,
                                        actor=actor,
                                        action="APPLICATION_REMEDIATION",
                                        resource_type="SOURCE_FILE",
                                        resource_id=rel_path,
                                        severity="Medium",
                                        details={
                                            "action_id": action,
                                            "relative_path": rel_path,
                                            "before_hash": before_hash,
                                            "after_hash": after_hash,
                                            "status": "SUCCESS"
                                        }
                                    )
                                
                            except Exception as e:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                if db:
                                    AuditLog.create_entry(
                                        session=db,
                                        actor=actor,
                                        action="APPLICATION_REMEDIATION",
                                        resource_type="SOURCE_FILE",
                                        resource_id=rel_path,
                                        severity="High",
                                        details={
                                            "action_id": action,
                                            "relative_path": rel_path,
                                            "status": "FAILED",
                                            "error": str(e)
                                        }
                                    )
                                raise e

            if action_applied:
                applied_actions.append(action)
            else:
                skipped_actions.append(f"{action}: No vulnerable code found or skipped due to complexity.")

        return applied_actions, skipped_actions, list(changed_files)
