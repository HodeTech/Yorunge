---
id: P02-3s
phase: P02
status: draft
size: M
depends_on: [P02-2c]
capabilities: [C03, C04]
---
# P02-3s — Ortak no-clobber artifact yayıncısı (manifest yayıncısı genellemesi)

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 8. Hem indirme hattının (P02-3l son yayın adımı) hem sürüm hattının (P02-3q bağ artifact’ı) ortak ihtiyacıdır; bu yüzden iki hattan bağımsız, yalnız P02-2c’de verified olan P02-1d manifest yayıncısına dayanan küçük bir refaktör kartıdır. Büyüme kuralı: ölçülen büyüklük kartı L yaparsa s–z harfleriyle bölünür ve planda kaydedilir.

## Kullanıcı sonucu ve mevcut eksik

Manifest, sürüm bağı ve indirilen dosya gibi çıktılar aynı güvenli yayın ilkesiyle yazılmalıdır: hedefi ezmeden, çökmeye dayanıklı ve belirsizliği dürüstçe bildirerek. Bu ilke bugün yalnız manifest için yazılmıştır ve `DatasetTree`, `manifest_*` hata kodları ve 30 s dataset bütçesine bağlıdır; ikinci bir kopya yazmak güvenlik davranışını iki yerde tutardı.

## Giren ve girmeyen kapsam

`DatasetManifestWriter` yayın mantığının (no-follow parent zinciri, rastgele adlı `O_CREAT|O_EXCL|O_NOFOLLOW` 0600 stage, sync, son zincir/kimlik denetimi, exclusive `link()`, hedef kimliği ve `nlink` denetimi, stage `unlink`, dizin sync, link başladıktan sonra belirsizlik durumu ve iptal notu) hata kodu ailesinden bağımsız ortak bir artifact yayıncısına çıkarılması girer: hata ailesi enjekte edilir (`manifest_*` bugünkü, `binding_*` P02-3q için; aile “write_failed”, “output_exists”, “write_uncertain” ve yayın öncesi kimlik değişimi kodlarını taşır — manifest’te `input_changed`, indirmede `download_write_failed`/`download_write_uncertain`, bağda `binding_write_failed`/`binding_write_uncertain`), bellekteki baytlar için tam yayın, akışlı yazıcı için ayrı son-yayın yardımcısı (stage’i yazıcı açar ve sync eder; ortak ilke yalnız “doğrula–link–temizle–sync” sırasını ve kimlik denetimlerini sağlar). Manifest davranışı, hata kodları, mesajlar ve testleri değişmez: `DatasetManifestWriter._check_stage` ve `_publish_link` bugünkü adlarıyla **gerçek kanca (seam) olarak kalır** (ince delege; mevcut testler bu iki yönteme monkeypatch ile ölüm/yarış/ikame enjekte eder) ve manifest stage adı kalıbı `.yorunge-manifest-*.tmp` aynı kalır. Yeni public yüzey, yeni hata kodu, indirme sidecar/resume ve `DatasetTree` bağı girmez.

## Bağımlılıklar ve kararlar

P02-2c verified ve development’tadır (P02-1d manifest yayıncısı dahil). Yeni karar gerekmez: davranış değişmez; kullanımı ADR-0032 ve ADR-0033’tedir. Bu kart onlardan bağımsız yürüyebilir; böylece sürüm hattı indirme ADR’sine bağlı kalmaz.

## Sözleşme ve uygulama sınırı

Ortak yayıncı manifest yayıncısıyla aynı güvenlik ilkelerini uygular ([manifest sözleşmesi](../../reference/dataset-manifest.md#dosya-yayını-ve-hata-önceliği)); hata kodu ailesi ve mesajlar çağıranın sözleşmesindedir. Sürüm hattı rastgele adlı stage kullanır; deterministik stage/sidecar/flock yalnız P02-3l’nin akışlı yazıcısına aittir ve bu kartın kapsamı dışındadır.

## Kabul

1. Manifest yayıncısının mevcut bütün testleri (yarış, kill, belirsizlik, iptal, hedef var, dangling symlink, parent swap, stage ikamesi) **değiştirilmeden** geçer; hata kodu/mesaj/exit değişmez. **İçi boş yeşil yok:** kancalar ortak yayıncı yolunda gerçekten çağrılır — kill testi (`_publish_link` yerine geçen süreç) `returncode == -SIGKILL` gözler, yarış/ikame testleri enjekte edilen yöntemi yürütür (kanca çağrılmazsa test kırmızıdır; bu bir kabul oracle’ıdır).
2. Ortak yayıncı aynı yarış/kill/belirsizlik matrisini farklı bir hata ailesiyle (örn. sahte `binding_*` seti) bağımsız olarak geçer; link başladıktan sonraki her belirsizlik ailenin “uncertain” koduna, kesin EEXIST ailenin “exists” koduna eşlenir.
3. Akışlı yazıcı için son-yayın yardımcısı: stage kimliği ve `nlink` denetimi, `link()`/EEXIST ve sahipliği kanıtlı temizlik kancası, dizin sync ve hedef kimliği kontrolü gerçek SIGKILL adımlarıyla sınanır.
4. Strict mypy ve Ruff geçer; yeni public sembol yok.

## Doğrulama

Mevcut dataset yayın testleri, yeni ortak yayıncı integration/race/kill testleri, Ruff, strict mypy ve `git diff --check`.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
