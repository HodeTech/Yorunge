# Referans sözleşmeler

**Durum:** CLI/config/capability yerel alt kümeleri uygulandı; tam yürütme/araç portları tasarım. **Tarih:** 2026-10-27.

| Belge | Kanonik tanım |
|---|---|
| [CLI](cli-contract.md) | Komut aileleri, çıktı ve çıkış kodları |
| [Yapılandırma](configuration.md) | Profil/reçete, öncelik ve doğrulama |
| [Araç sağlayıcısı](tool-provider-contract.md) | Görev, plan, execution ve sonuç sınırı |
| [Yetenek kaydı](capability-record.md) | Destek, kapsam, kanıt ve güncellik |
| [CapabilityScopeV2](capability-scope-v2.md) | Accepted tasarım — ADR-0013'e bağlı kapalı wire, nullability, sıralama ve kanonik anahtar; ürün kabulü sürüyor |
| [Credential binding v1](credential-binding-v1.md) | Uygulandı — ortak hedef/UNIQUE/HMAC, kalıcı gözlem ve byte vektörleri; Accepted ADR-0012 |
| [Yerel state](local-state.md) | Store/migration/backup, açık reset/identity-only restore/recover ve koruma sınırı |

Her belgenin başlangıcı uygulanmış alt kümeyi belirtir; kalan tasarımlar mevcut destek değildir. Çalışan başlangıç [README](../../README.md), kabul kanıtı [P01 kaydındadır](../research/p01-core-validation.md).
