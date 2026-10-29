# Test ve kabul standardı

**Durum:** Etkin — yerel şema/CLI/SQLite, çok süreç/lease/unknown/reset, gerçek TLS/stream ve SIGKILL kesinti sınırlarında. **Tarih:** 2026-10-29. [İlk kabul](../research/p01-core-validation.md), [P01-4 merge kabulü](../research/p01-4-implementation-validation.md#development-merge-kapanışı), [çalışma dalında P01 faz/CI/kurulum kabulü](../research/p01-remaining-implementation-validation.md#faz-kapanışı-ve-gerçek-ci). Süreç öldürme fiziksel güç kesintisi değildir; gerçek EVREN ve minimum SQLite/Windows kabulü bu matrisin dışında kalır.

Testler kullanıcı sözleşmesini ve hata sınırını doğrular. Uygulamayı satır satır tekrar eden düşük etkili test yerine maliyet, veri kaybı, yanlış başarı, seçim ve toparlanma senaryolarına öncelik verilir.

## Katmanlar

| Katman | Zorunlu odak |
|---|---|
| Unit | Plan/parametre çözümleme, tip/sonluluk, durum geçişi, varsayılan ve açık seçim |
| Contract | Hizmet/araç adaptörleri ortak görev, hata, deadline, çıktı ve destek sözleşmesine uyuyor mu? |
| Integration | Loopback HTTP, geçici dosya/SQLite, sahte alt süreç ve kesinti/restart |
| End-to-end | Kullanıcı yolculuğu girdiden doğrulanmış artefakta ulaşıyor mu? |
| Performance | Başlangıç, bellek, ağ çağrısı ve bounded concurrency bütçeleri |

Varsayılan testler çevrimdışı ve sentetik veriyle çalışır. Gerçek anahtar, kullanıcı verisi veya ücretli hesap CI fixture'ı olmaz. Canlı sözleşme canary'si ancak ayrı yetkili, kapsamı/maliyeti açık bir süreçle eklenir; offline yeşil sonuç canlı destek diye sunulmaz.

## İlk zorunlu negatif senaryolar

- Aynı boyutta değişmiş dosya, symlink/kök dışı yol, değişen manifest ve kesik günlük.
- Cross-origin redirect ve sır yansıması; hata/başarılı yanıt/akışta redaksiyon.
- Aynı profil adı altında origin/API kökü, hesap/proje, anahtar veya izin değişiminde eski planın yürütülmemesi; aynı env referansında anahtar değişiminin yakalanması; iki anahtar arasında capability cache ayrımı.
- NaN/sonsuz/uygunsuz negatif tahmin, malformed envelope ve HTTP 2xx içindeki mantıksal hata.
- Yan etki sonrası yanıt kaybı; unknown durumunda ikinci iş başlatılmaması.
- Araç bulunamaması, seçilen araca çevrilemeyen parametre, alternatifin sessizce seçilmemesi.
- Alt süreç iptali, uzak işin devam etmesi, lease kaybı ve yeniden bağlanma.
- `submitted`/`unknown` işin uzlaştırmada doğrulanmış iptali; yalnız iptal isteği kabulünün veya işin bulunamamasının `cancelled` sayılmaması.
- Eğitim başarılı ama artefakt eksik; integrity uyuşmazlığının başarı sayılmaması.
- Non-TTY onay, makine stdout'una ilerleme metni sızması ve yarım akış.

Adapter testleri yalnız sahte adaptörün kendisine karşı yazılmaz; ortak port sözleşmesi ve en az bir gerçek süreç/taşıma sınırını da çalıştırır. Kapsama yüzdesi tek başına kabul değildir. Uygulama fazı; geçen, başarısız, atlanan ve çalıştırılmayan kontrolleri açık kaydeder.
