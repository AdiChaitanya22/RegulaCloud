package com.regulacloud.health.security;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class EncryptionService {

    // SECURITY FLAW: CWE-327 (Broken or Risky Cryptographic Algorithm)
    // SonarQube Rule: javasecurity:S5542
    public byte[] encryptPatientMetadata(byte[] data, byte[] keyBytes) throws Exception {
        // Insecure DES/3DES algorithm used instead of AES-256-GCM
        SecretKeySpec key = new SecretKeySpec(keyBytes, "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(data);
    }
}
