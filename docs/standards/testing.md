# Test ve kabul standardı

**Durum:** Etkin — yerel CLI/SQLite, çok süreç/lease/unknown/reset, gerçek TLS/stream ve SIGKILL sınırları; [güncel üç ortam kaynak/kurulum kabulü](../research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı). **Tarih:** 2026-10-30. Önceki kaynak kabulleri tarihsel kalır. Süreç öldürme fiziksel güç kesintisi değildir; canlı EVREN, minimum SQLite 3.37 ve gerçek Windows koşusu bu kabulde yoktur.

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

## CI’da paralel yürütme ve belge-only hat

Tam suite CI’da `pytest -n auto --dist loadfile` ile koşar ([ADR-0034](../decisions/0034-ci-duration-docs-lane-and-parallel-suite.md)); yerelde `-n` varsayılan değildir ve tek süreç de geçerlidir. Bunun testlere sözleşmesi:

- **Parametre kimlikleri deterministik olur.** `pytest.mark.parametrize` değerleri `uuid4()`, saat, rastgele sayı veya ortama bağlı bir değer olamaz: her işçi aynı test kimliklerini toplamalıdır, aksi hâlde xdist toplama aşamasında durur. Rastgele değer gerekiyorsa gövdede üretilir ya da `ids=` ile sabitlenir.
- **Dosyalar arasında sıra bağımlılığı olmaz.** Bir dosya bütünüyle tek işçide koşar ama hangi dosyalarla birlikte ve hangi sırayla koşacağı değişir; modül fixture’ı dosya başınadır; oturum kapsamlı fixture’lar işçi (süreç) başına kurulur ve işçiler arasında paylaşılmaz.
- **Belgeyi okuyan test bunu kodunda belirtir.** Belge-only PR’lar yalnız belgeye başvuran testleri koşturur: `docs/…` yolu, belge dosya adı (`README.md`, `CHANGELOG.md` vb.) ya da `.md` kod satırında geçmelidir (yalnız yorum satırı sayılmaz). Belge okuyan bir yardımcı/fixture/`conftest` varsa seçim bütün `tests` ağacına düşer; bu güvenlidir ama hattı yavaşlatır. `tests/contracts/test_ci_changes.py` sözdizimi ağacıyla depodaki her belge okuyan testin seçimde olduğunu doğrular.
- **Zamana duyarlı testler paylaşılan CPU’ya dayanıklı olur:** olay/koşul tabanlı beklemeler, geniş ama anlamlı paylar; duvar saati payına güvenen test yük altında düşer (bkz. Linux 3.14’te düşen `test_platform_total_deadline_is_shared_across_reads` [kaydı](../research/p02-3-implementation-validation.md#pr-15-üç-dış-inceleme-raporu-ürün-kusurları-ve-son-kaynak-referans-serisi--7)).

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
