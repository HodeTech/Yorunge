# Referans sözleşmeler

**Durum:** CLI/config/capability yerel alt kümeleri uygulandı; tam yürütme/araç portları tasarım. **Tarih:** 2026-10-27.

| Belge | Kanonik tanım |
|---|---|
| [CLI](cli-contract.md) | Komut aileleri, çıktı ve çıkış kodları |
| [Yapılandırma](configuration.md) | Profil/reçete, öncelik ve doğrulama |
| [Araç sağlayıcısı](tool-provider-contract.md) | Görev, plan, execution ve sonuç sınırı |
| [Yetenek kaydı](capability-record.md) | Destek, kapsam, kanıt ve güncellik |
| [Credential binding v1](credential-binding-v1.md) | Benimsenmiş — ortak hedef eşlemesi, özel UNIQUE/HMAC alanları ve byte vektörleri; Accepted ADR-0012, henüz uygulanmadı |
| [Yerel state](local-state.md) | Açık store oluşturma/doğrulama, path/süre/hata, snapshot ve henüz uygulanmayan recovery sınırı |

Her belgenin başlangıcı uygulanmış alt kümeyi belirtir; kalan tasarımlar mevcut destek değildir. Çalışan başlangıç [README](../../README.md), kabul kanıtı [P01 kaydındadır](../research/p01-core-validation.md).
