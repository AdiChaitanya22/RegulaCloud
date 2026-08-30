package com.regulacloud.health.security;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;

public class EncryptionService {

    // SECURE: Authenticated AES-256-GCM Encryption (DPDP Act Sec 8(5) / CWE-327 compliant)
    private static final int GCM_TAG_LENGTH = 128;
    private static final int IV_LENGTH_BYTE = 12;

    public byte[] encryptPatientMetadata(byte[] data, byte[] keyBytes) throws Exception {
        byte[] iv = new byte[IV_LENGTH_BYTE];
        SecureRandom random = new SecureRandom();
        random.nextBytes(iv);

        SecretKeySpec key = new SecretKeySpec(keyBytes, "AES");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.ENCRYPT_MODE, key, gcmSpec);

        byte[] cipherText = cipher.doFinal(data);
        byte[] output = new byte[iv.length + cipherText.length];
        System.arraycopy(iv, 0, output, 0, iv.length);
        System.arraycopy(cipherText, 0, output, iv.length, cipherText.length);
        return output;
    }
}
