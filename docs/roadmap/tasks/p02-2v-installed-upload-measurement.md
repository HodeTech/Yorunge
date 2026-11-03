---
id: P02-2v
phase: P02
status: verified
size: M
depends_on: [P02-2w]
capabilities: [C03, C12, C13]
---
# P02-2v — Kurulu upload native ölçüm araçları

**Tarih:** 2026-11-03. Üst c kabulünün ölçüm kodu birimidir; aynı dal/tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

İstemci, dosya boyutu ve envanter büyürken byte doğruluğunu, bounded worker/buffer kullanımını ve ilan edilen süre/bellek bütçelerini korumalıdır. Mevcut raw download ve yerel hash araçları gerçek upload tüketicisini ölçmez.

## Giren ve girmeyen kapsam

V.1 ayrı süreçte streaming TLS sink, ortak test-only network mapping ve kurulu public API worker; v.2 kaynak/wheel/runtime eşliği, kapalı rapor/bağımsız verifier/kayıpsız katalog ve anlamlı negatif vektörler. Her dilimde iki fresh tur. Sentetik loopback ölçümü canlı sağlayıcı/hız/ücret veya fiziksel RAM attestasyonu değildir. Eğitim/büyük üçüncü taraf bağımlılığı, yeni ürün flag’i, gerçek anahtar ve sağlayıcı çağrısı yoktur.

## Bağımlılıklar ve kararlar

U ve W verified; mevcut [performans](../../standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) ve [kanıt](../../standards/research-evidence.md) standardı uygulanır. Önceden sabitlenen ölçüm yöntemi [upload kabul planındadır](../../research/p02-2-upload-measurement-plan.md). Yeni ürün sözleşmesi/ADR gerekmez; kaynak yöntemi veya güven sınırı değişirse önce değerlendirilir.

## Sözleşme ve uygulama sınırı

Scripts ve tests/fixtures; gerçek production API/consumer üzerinde yalnız private loopback TLS yönlendirmesi. Runtime-only wheel, isolated -I worker, controller/server/client farklı PID; installed provenance/marker/metadata ve kaynak before/after eşliği. Body biriktiren genel küçük UploadProvider yerine sınırlı hash/sayaç sink’i kullanılır. Ürün çağrıları grant/fiyat/proof injection almaz.

## Kabul

16/256/1024 MiB ve 128 dosya fixture’ları, her biri üç fresh worker ile seri; 1 GiB üç dosyada dosya başına 500.000.000 byte sınırını korur. Her süreçte sabit 1 MiB/üç dosya warm workflow sonra B/H0/H1 ve U/L; her U≤64 MiB, üç boyutun farklı-label bütün aralıklarında G≤8 MiB. Tam prepare/approve/start public akışı, exact independent server byte/SHA oracle, accepted graph ve metadata seviyesi; fiyat/yetki/remote downloaded bytes iddiası yoktur. Request/effect/connection/chunk/worker sınırları ve client/server PID ayrımı raporlanır. Sabit bağımsız path/size/SHA/manifest vektörleri producer/server self-consistency’sinden ayrı doğrulanır. Her başarısız koşu/çıktı kayıpsız diagnostic arşive alınır; saklama hatası açık kabul engelidir; örnek seçimi/threshold gevşetme yoktur. Verifier eksik/duplicate/bool/nonfinite/fazla alan, native interval/growth/provenance/byte/count/decision uyuşmazlığını reddeder; dürüst başarısız bütçe raporu saklanabilir.

## Doğrulama

Ölçüm araçlarının küçük gerçek TLS/kurulu worker smoke’u ve bağımsız sabit negatif vektörler; uygun Ruff/type/doc/skill/evidence/diff. Ağır native ölçüm ancak bütün runtime/test/script/workflow kaynakları son halini aldıktan ve dış yoğun işler bitince seri yapılır. Linux 3.11 source CI’da upload native koşusu mevcut ölçümlerle seri, M5 upload reference kaynak denetimi zorunlu olacak şekilde V.3’te bağlanır. Yalnız Linux 3.11 job scheduling timeout’u 45 dakika, diğer hücreler 25 dakika olur; bu 12×900 saniyelik teorik pencereyi veya fiziksel süreyi garanti etmez. Ürün 900/120 saniye sınırları değişmez; kesilmiş koşular başarısız/diagnostic ve açık saklama takibi kalır; üç ortam CI/altı kurulumun gerçek sonucu ve live üst c’de ayrıca kapanır.

## Teslim kaydı

- PR/commit: [V.1](https://github.com/HodeTech/Yorunge/commit/6fb5b9b), [V.2](https://github.com/HodeTech/Yorunge/commit/4df5081), [V.3](https://github.com/HodeTech/Yorunge/commit/d160244), [R2 düzeltmesi](https://github.com/HodeTech/Yorunge/commit/8d24847); aynı dal/tek nihai PR.
- Sonuç: V.1/V.2/V.3 bütün kod dilimleri iki farklı fresh review turu ve doğrulanmış P2 fix teyitleriyle yerel verified. V.3 iki gerçek geliştirme wheel/sdist kurulumu, zorunlu upload_smoke ve kapalı installation_v3 geçti; aggregate ve iki accepted=false/unverified smoke kayıpsız arşivlenip saklama takibi kapandı. Toplam 382 arşiv doğrulandı. Süreç cleanup’ında SIGTERM, abrupt controller, parent EOF ve kesin child.close kesinti regresyonları geçti. Ayrıntılı [kabul kaydı](../../research/p02-2-implementation-validation.md#p02-2v3--sürümlü-kurulum-güncel-kaynak-kapısı-ve-gerçek-ci-ölçüm-bağlantısı) kanoniktir.

- Kalan sınır: Bu araç teslimi nihai kaynak/native/altı kurulum/üç ortam CI/ayrı canlı kabulü değildir; üst c’de kalır. Yeni dört kaynak referansı bütün kaynaklar ve canlı kabul aracı sabitlendikten sonra ölçülecek. Üst a/b/c ve epik draft; yeni canlı write yetkisi yoktur.
