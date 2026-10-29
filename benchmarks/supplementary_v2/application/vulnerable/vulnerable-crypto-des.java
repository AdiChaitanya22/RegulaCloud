package com.regulacloud.benchmark;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

class VulnerableCryptoDes {
    public Cipher initCipher(byte[] keyBytes) throws Exception {
        SecretKeySpec key = new SecretKeySpec(keyBytes, "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher;
    }
}
