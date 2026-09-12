import os
import re
from typing import List, Tuple

class ApplicationRemediator:
    """
    Applies deterministic code patches to uploaded project source files.
    """

    @classmethod
    def apply_source_actions(cls, source_path: str, action_ids: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """
        Scans and deterministically patches files in source_path for the requested action_ids.
        Returns: (applied_actions, skipped_actions, changed_files)
        """
        if not source_path or not os.path.exists(source_path):
            return [], [f"{a}: No application source path found." for a in action_ids], []

        applied_actions = []
        skipped_actions = []
        changed_files = set()

        for action in action_ids:
            if action == "ACT_UPGRADE_WEAK_CRYPTO":
                # Upgrades DES/3DES usage to AES/GCM in Java files
                action_applied = False
                for root, _, files in os.walk(source_path):
                    for file in files:
                        if file.endswith(".java"):
                            file_path = os.path.join(root, file)
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()

                            new_content = content
                            # Replace DES SecretKeySpec
                            new_content = re.sub(
                                r'new\s+SecretKeySpec\s*\(\s*([^,]+)\s*,\s*"DES"\s*\)',
                                r'new SecretKeySpec(\1, "AES")',
                                new_content
                            )
                            # Replace DES/ECB Cipher instantiation
                            new_content = re.sub(
                                r'Cipher\.getInstance\s*\(\s*"DES/ECB/PKCS5Padding"\s*\)',
                                r'Cipher.getInstance("AES/GCM/NoPadding")',
                                new_content
                            )
                            # Also match Cipher.getInstance("DES") directly
                            new_content = re.sub(
                                r'Cipher\.getInstance\s*\(\s*"DES"\s*\)',
                                r'Cipher.getInstance("AES/GCM/NoPadding")',
                                new_content
                            )
                            # Also match Cipher.getInstance("3DES") or TripleDES
                            new_content = re.sub(
                                r'Cipher\.getInstance\s*\(\s*"3DES[^"]*"\s*\)',
                                r'Cipher.getInstance("AES/GCM/NoPadding")',
                                new_content
                            )

                            if new_content != content:
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(new_content)
                                changed_files.add(file_path)
                                action_applied = True

                if action_applied:
                    applied_actions.append(action)
                else:
                    skipped_actions.append(f"{action}: No vulnerable DES/3DES patterns found to patch.")

            elif action in ("ACT_PARAMETERIZE_SQL_QUERIES", "ACT_PATCH_SONAR_INJECTION"):
                # Parameterizes vulnerable SQL concatenation in Java files.
                # Handles patterns like:
                #   String query = "SELECT ... WHERE col = '" + var + "'";
                #   String query = "SELECT ... WHERE col = " + var;
                action_applied = False
                for root, _, files in os.walk(source_path):
                    for file in files:
                        if file.endswith(".java"):
                            file_path = os.path.join(root, file)
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()

                            new_content = content

                            # Broad pattern: String <varname> = "<query... WHERE col =" + <javaExpr>;
                            # Handles: trailing + "'" or no trailing part
                            sqli_pattern = re.compile(
                                r'String\s+\w+\s*=\s*("(?:[^"\\]|\\.)*WHERE\s+[\w.]+\s*=\s*\'?")'
                                r'\s*\+\s*'
                                r'(\w+)'          # the interpolated variable
                                r'(?:\s*\+\s*"\'?"\s*)?'  # optional trailing + "'" or + "'"
                                r'\s*;',
                                re.DOTALL
                            )

                            def replace_sqli(match, _action=action):
                                base = match.group(1).rstrip("'\"").rstrip()
                                var_name = match.group(2).strip()
                                return f'PreparedStatement ps = conn.prepareStatement({base} ?");\n        ps.setString(1, {var_name});'

                            patched = sqli_pattern.sub(replace_sqli, new_content)
                            if patched != new_content:
                                new_content = patched
                                # Replace any <statement>.executeQuery(<queryVar>) → ps.executeQuery()
                                new_content = re.sub(
                                    r'\w+\.executeQuery\(\w+\)',
                                    r'ps.executeQuery()',
                                    new_content
                                )
                                # Remove now-unused Statement instantiation if present
                                new_content = re.sub(
                                    r'[ \t]*Statement\s+\w+\s*=\s*\w+\.createStatement\(\);\n?',
                                    '',
                                    new_content
                                )

                            if new_content != content:
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(new_content)
                                changed_files.add(file_path)
                                action_applied = True

                if action_applied:
                    applied_actions.append(action)
                else:
                    skipped_actions.append(f"{action}: No vulnerable SQL injection patterns found to patch.")

            else:
                skipped_actions.append(f"{action}: Unsupported application remediation.")

        return applied_actions, skipped_actions, list(changed_files)
