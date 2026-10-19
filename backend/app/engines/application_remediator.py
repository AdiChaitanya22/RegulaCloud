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
                            # Conservative, syntax-safe parameterization for supported patterns
                            # If code pattern is ambiguous or complex, safe-skip without mutating.
                            lines = new_content.split('\n')
                            skip_file = False

                            # Check for complex multi-line SQL builders (StringBuilder, StringBuffer)
                            if "StringBuilder" in new_content or "StringBuffer" in new_content:
                                skip_file = True

                            # 1. Detect connection and statement variables across the file
                            # Pattern: Statement <stmt_var> = <conn_var>.createStatement();
                            stmt_conn_matches = list(re.finditer(r'(?:java\.sql\.)?Statement\s+(\w+)\s*=\s*(\w+(?:\.\w+)?)\.createStatement\(\s*\)\s*;', new_content))
                            conn_var_map = {}
                            for scm in stmt_conn_matches:
                                stmt_name = scm.group(1)
                                c_expr = scm.group(2)
                                conn_var_map[stmt_name] = c_expr

                            # Also check method parameter / field declarations for Connection
                            conn_fallback_match = re.search(r'(?:public|private|protected|void|\b)?\s*(?:java\.sql\.)?Connection\s+(\w+)', new_content)
                            default_conn = conn_fallback_match.group(1) if conn_fallback_match else None

                            # 2. Find SQL injection vulnerable assignments
                            sqli_pattern = re.compile(
                                r'String\s+(\w+)\s*=\s*("(?:[^"\\]|\\.)*WHERE\s+[\w.]+\s*=\s*\'?")\s*\+\s*(\w+)(?:\s*\+\s*"\'?"\s*)?\s*;'
                            )

                            sqli_lines = []
                            for i, line in enumerate(lines):
                                stripped = line.strip()
                                if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                                    continue
                                m = sqli_pattern.search(line)
                                if m:
                                    if line.count('+') > 2:
                                        skip_file = True  # Complex multi-variable concatenation -> safe-skip
                                        break
                                    sqli_lines.append((i, m))

                            if not sqli_lines or skip_file:
                                continue

                            # 3. Check for supported statement and execution call sites
                            # If connection cannot be resolved for a statement, or execution call is absent -> safe-skip
                            target_stmt_to_ps = {}  # stmt_var -> (conn_var, ps_name)
                            execution_calls = []    # (line_idx, stmt_var, method)

                            for idx, m in sqli_lines:
                                q_var = m.group(1)
                                found_exec = False
                                for j, line in enumerate(lines):
                                    stripped = line.strip()
                                    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                                        continue
                                    exec_m = re.search(rf'(\w+)\.(executeQuery|execute)\(\s*{q_var}\s*\)', line)
                                    if exec_m:
                                        s_var = exec_m.group(1)
                                        method_name = exec_m.group(2)
                                        found_exec = True
                                        execution_calls.append((j, s_var, method_name))
                                        c_var = conn_var_map.get(s_var, default_conn)
                                        if not c_var:
                                            skip_file = True
                                            break
                                        target_stmt_to_ps[s_var] = (c_var, "ps")

                                if not found_exec or skip_file:
                                    skip_file = True
                                    break

                            if skip_file:
                                continue

                            # 4. Perform consistent, coordinated replacement
                            for idx, m in sqli_lines:
                                q_var = m.group(1)
                                base = m.group(2).rstrip("'\"").rstrip()
                                var_name = m.group(3).strip()

                                c_var = default_conn or "conn"
                                for s_var, (cv, _) in target_stmt_to_ps.items():
                                    c_var = cv
                                    break

                                indent = " " * (len(lines[idx]) - len(lines[idx].lstrip()))
                                lines[idx] = f'{indent}PreparedStatement ps = {c_var}.prepareStatement({base} ?");\n{indent}ps.setString(1, {var_name});'

                            # Remove redundant Statement creation
                            for s_var in target_stmt_to_ps.keys():
                                for j, line in enumerate(lines):
                                    if re.search(rf'(?:java\.sql\.)?Statement\s+{s_var}\s*=\s*\w+(?:\.\w+)?\.createStatement\(\s*\)\s*;', line):
                                        lines[j] = ''

                            # Replace execution call sites consistently
                            for j, s_var, method_name in execution_calls:
                                line = lines[j]
                                if method_name == "executeQuery":
                                    lines[j] = re.sub(rf'\b{s_var}\.executeQuery\(\w+\)', 'ps.executeQuery()', line)
                                elif method_name == "execute":
                                    lines[j] = re.sub(rf'\b{s_var}\.execute\(\w+\)', 'ps.execute()', line)

                            # Ensure java.sql.PreparedStatement is imported
                            lines = cls._ensure_prepared_statement_import(lines)

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

    @staticmethod
    def _ensure_prepared_statement_import(lines: List[str]) -> List[str]:
        content_str = '\n'.join(lines)
        # Check if PreparedStatement is already imported explicitly or via wildcard
        has_explicit = bool(re.search(r'^\s*import\s+java\.sql\.PreparedStatement\s*;', content_str, re.MULTILINE))
        has_wildcard = bool(re.search(r'^\s*import\s+java\.sql\.\*\s*;', content_str, re.MULTILINE))
        if has_explicit or has_wildcard:
            return lines

        import_stmt = "import java.sql.PreparedStatement;"

        # 1. If java.sql imports exist, insert after the last java.sql import
        last_sql_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^\s*import\s+java\.sql\.[^;]+;', line):
                last_sql_idx = i

        if last_sql_idx != -1:
            return lines[:last_sql_idx + 1] + [import_stmt] + lines[last_sql_idx + 1:]

        # 2. Otherwise if other imports exist, insert after the last import
        last_import_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^\s*import\s+[^;]+;', line):
                last_import_idx = i

        if last_import_idx != -1:
            return lines[:last_import_idx + 1] + [import_stmt] + lines[last_import_idx + 1:]

        # 3. Otherwise if package declaration exists, insert after package declaration with valid spacing
        pkg_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^\s*package\s+[^;]+;', line):
                pkg_idx = i
                break

        if pkg_idx != -1:
            res = list(lines[:pkg_idx + 1])
            res.extend(['', import_stmt, ''])
            rem = list(lines[pkg_idx + 1:])
            while rem and rem[0].strip() == '':
                rem.pop(0)
            res.extend(rem)
            return res

        # 4. Otherwise insert before top-level class declaration
        class_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^\s*(?:public\s+|protected\s+|private\s+|abstract\s+|final\s+)*class\s+\w+', line):
                class_idx = i
                break

        if class_idx != -1:
            res = [import_stmt, '']
            res.extend(lines[class_idx:])
            return res

        # 5. Fallback: prepend to top of lines
        return [import_stmt, ''] + lines
