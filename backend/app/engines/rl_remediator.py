import numpy as np
from typing import List, Dict, Any, Tuple

class QLearningRemediationAgent:
    """
    Q-Learning Agent for Remediation Sequence Optimization.
    Learns the optimal sequence of approved remediation actions to transition
    the cloud infrastructure from a non-compliant state to fully compliant.
    """

    # Approved Remediation Actions
    ACTIONS = [
        {
            "id": "ACT_DISABLE_RDS_PUBLIC",
            "name": "Disable RDS Public Internet Ingress",
            "target_control": "CTRL-AWS-RDS-NO-PUBLIC",
            "cost_penalty": 2,
            "complexity_penalty": 2,
            "hcl_diff": 'resource "aws_db_instance" "postgres" {\n-  publicly_accessible = true\n+  publicly_accessible = false\n}'
        },
        {
            "id": "ACT_ENABLE_RDS_ENC",
            "name": "Enable RDS Storage Encryption at Rest",
            "target_control": "CTRL-AWS-RDS-STORAGE-ENC",
            "cost_penalty": 5,
            "complexity_penalty": 3,
            "hcl_diff": 'resource "aws_db_instance" "postgres" {\n+  storage_encrypted = true\n}'
        },
        {
            "id": "ACT_ENABLE_S3_ENC",
            "name": "Attach S3 Server-Side KMS Encryption",
            "target_control": "CTRL-AWS-S3-ENC",
            "cost_penalty": 3,
            "complexity_penalty": 2,
            "hcl_diff": 'resource "aws_s3_bucket_server_side_encryption_configuration" "enc" {\n+  rule {\n+    apply_server_side_encryption_by_default {\n+      sse_algorithm = "aws:kms"\n+    }\n+  }\n}'
        },
        {
            "id": "ACT_BLOCK_S3_PUBLIC",
            "name": "Apply S3 Public Access Block",
            "target_control": "CTRL-AWS-S3-NO-PUBLIC",
            "cost_penalty": 0,
            "complexity_penalty": 1,
            "hcl_diff": 'resource "aws_s3_bucket_public_access_block" "pab" {\n+  block_public_acls = true\n+  block_public_policy = true\n}'
        },
        {
            "id": "ACT_EXTEND_LOG_RETENTION_180",
            "name": "Set CloudWatch Log Retention to 180 Days (CERT-In)",
            "target_control": "CTRL-AWS-LOG-180D",
            "cost_penalty": 8,
            "complexity_penalty": 1,
            "hcl_diff": 'resource "aws_cloudwatch_log_group" "audit_logs" {\n-  retention_in_days = 30\n+  retention_in_days = 180\n}'
        },
        {
            "id": "ACT_ENABLE_CLOUDTRAIL_MULTI",
            "name": "Enable Multi-Region CloudTrail Trail",
            "target_control": "CTRL-AWS-CLOUDTRAIL-MULTI",
            "cost_penalty": 10,
            "complexity_penalty": 3,
            "hcl_diff": 'resource "aws_cloudtrail" "trail" {\n+  is_multi_region_trail = true\n+  enable_logging = true\n}'
        },
        {
            "id": "ACT_PATCH_SONAR_INJECTION",
            "name": "Parameterize SQL Queries to Eliminate SQLi",
            "target_control": "CTRL-SONAR-INJECTION-FREE",
            "cost_penalty": 0,
            "complexity_penalty": 5,
            "hcl_diff": '// Replace raw String concatenation with PreparedStatement\n- String query = "SELECT * FROM users WHERE id = " + userId;\n+ PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");\n+ ps.setString(1, userId);'
        },
        {
            "id": "ACT_UPGRADE_WEAK_CRYPTO",
            "name": "Upgrade Weak DES/3DES Cipher to Authenticated AES-256-GCM",
            "target_control": "CTRL-SONAR-ZERO-CRITICAL",
            "cost_penalty": 0,
            "complexity_penalty": 4,
            "hcl_diff": '// Replace legacy DES with AES-256-GCM authenticated cipher\n- SecretKeySpec key = new SecretKeySpec(keyBytes, "DES");\n- Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");\n+ SecretKeySpec key = new SecretKeySpec(keyBytes, "AES");\n+ Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");'
        }
    ]

    def __init__(self, alpha: float = 0.2, gamma: float = 0.9, epsilon: float = 0.2):
        self.alpha = alpha       # Learning rate
        self.gamma = gamma       # Discount factor
        self.epsilon = epsilon   # Exploration rate
        self.num_actions = len(self.ACTIONS)
        # Q-table keyed by binary tuple state
        self.q_table: Dict[Tuple[int, ...], np.ndarray] = {}

    def _get_q_row(self, state: Tuple[int, ...]) -> np.ndarray:
        if state not in self.q_table:
            self.q_table[state] = np.zeros(self.num_actions)
        return self.q_table[state]

    def train_simulator(self, episodes: int = 500):
        """
        Trains Q-learning agent in a simulated non-compliant cloud environment.
        """
        for _ in range(episodes):
            # Random initial violation state (vector of 0/1 indicating violation present)
            state = tuple(np.random.choice([0, 1], size=self.num_actions, p=[0.4, 0.6]))
            if sum(state) == 0:
                continue

            for step in range(self.num_actions):
                # Epsilon-greedy action selection
                q_vals = self._get_q_row(state)
                if np.random.uniform(0, 1) < self.epsilon:
                    action_idx = np.random.choice(self.num_actions)
                else:
                    action_idx = np.argmax(q_vals)

                # Environment step
                next_state_list = list(state)
                if next_state_list[action_idx] == 1:
                    # Successfully fixed this violation
                    next_state_list[action_idx] = 0
                    reward = 50 - (self.ACTIONS[action_idx]["cost_penalty"] + self.ACTIONS[action_idx]["complexity_penalty"])
                else:
                    # Redundant action on already compliant control
                    reward = -10

                # If all violations resolved
                if sum(next_state_list) == 0:
                    reward += 100

                next_state = tuple(next_state_list)
                best_next_q = np.max(self._get_q_row(next_state))
                
                # Q-learning Bellman update equation
                self.q_table[state][action_idx] += self.alpha * (
                    reward + self.gamma * best_next_q - self.q_table[state][action_idx]
                )

                state = next_state
                if sum(state) == 0:
                    break

    def recommend_remediations(self, active_violations: List[str]) -> List[Dict[str, Any]]:
        """
        Given a list of active violation control IDs, uses the trained Q-policy
        to generate an optimal, ordered sequence of approved remediation steps.
        """
        # Ensure model is trained
        if not self.q_table:
            self.train_simulator(episodes=300)

        state_list = []
        for a in self.ACTIONS:
            state_list.append(1 if a["target_control"] in active_violations else 0)
        
        current_state = tuple(state_list)
        recommendations = []
        step_num = 1

        for _ in range(self.num_actions):
            if sum(current_state) == 0:
                break
            
            q_vals = self._get_q_row(current_state)
            # Mask out actions for controls that are not currently violated
            masked_q = q_vals.copy()
            for idx, is_violated in enumerate(current_state):
                if not is_violated:
                    masked_q[idx] = -9999.0

            best_action_idx = int(np.argmax(masked_q))
            if masked_q[best_action_idx] <= -9000.0:
                break

            action_data = self.ACTIONS[best_action_idx]
            recommendations.append({
                "step": step_num,
                "action_id": action_data["id"],
                "name": action_data["name"],
                "target_control": action_data["target_control"],
                "cost_impact": f"Low (+{action_data['cost_penalty']}/mo)" if action_data['cost_penalty'] < 5 else f"Medium (+{action_data['cost_penalty']}/mo)",
                "complexity": f"Level {action_data['complexity_penalty']}/5",
                "hcl_diff": action_data["hcl_diff"],
                "q_value_score": round(float(masked_q[best_action_idx]), 2),
                "expected_score_gain": "+15.5%"
            })

            # Transition state
            next_state_list = list(current_state)
            next_state_list[best_action_idx] = 0
            current_state = tuple(next_state_list)
            step_num += 1

        return recommendations
