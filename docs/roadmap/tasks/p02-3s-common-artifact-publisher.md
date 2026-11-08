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

**Gerçekleşen kapsam (P02-3s).** `adapters/artifact_publisher.py`: `ArtifactCodes` (hata ailesi: `failed`, `exists`, `uncertain`, `changed`, `unreadable`), `PublicationState(codes)`, `PublishLocation` protokolü ve şablon-yöntem sınıfı `ArtifactPublisher`: `publish_bytes(content)` ve bir akışlı yazıcının kendi açıp doldurup sync ettiği stage için `publish_stage(stage, descriptor, size)`; adımlar (`_check_stage`, `_publish_link`, `_check_target`, `_remove_stage`, `_sync`, `_write`) çağıranın alt sınıfta değiştirebileceği yöntemler olarak kalır. `dataset_reports.DatasetManifestWriter` ince alt sınıftır (`MANIFEST_CODES`, `.yorunge-manifest-` öneki, `publish(manifest)` ve bu modülün `full_sync` kancası); `dataset_reports.PublicationState` manifest ailesini varsayılan alır; `api.py` ve uygulama katmanı değişmedi. Akışlı yayın hata yolunun tek sahibi `_discard(error)` kancasıdır: varsayılan stage’i kimliğiyle siler (bellekteki bayt yeniden yazılabilir); akışlı bir yazıcı (P02-3l) uzun bir indirmenin tek kopyası olan tamamlanmış stage’i G/Ç hatasında, deadline’da, kesintide ve link hatasında tutar, yalnız kesin reddi (hedef var, stage beyan edilen bayt değil) siler (ADR-0032 §3.6). Giriş tek bir stage adı ister (`/` ve `.`/`..` reddedilir), stage’in kimliği alınamazsa ailenin `failed` kodu verilir ve hiçbir şey silinmez; `prefix` ve `check_source` yalnız `publish_bytes` içindir (varsayılanlar boş). Bir stage beyan edilen boyutta değilse `changed` verilir; bu denetim kaynak ve yer denetimlerinden sonra çalışır ve bayt yolunda da görünür: senkrondan sonra yarışla kısaltılmış bir manifest eskiden link edilip `manifest_write_uncertain`/5 olurdu, şimdi link’ten önce `input_changed`/2 olur ve hiçbir şey yayımlanmaz (manifest yolundaki tek bilinçli davranış farkı; testli, referansta). `ArtifactCodes` kapalı kodlar ve exit 5 veren bir `uncertain` ister; `dataset_reports.PublicationState` ailesini yalnız anahtar sözcükle alır (konumsal sıra tabandaki gibi). Betimleyiciyi kapatan `close_descriptor`/`owned_descriptor` `input_files`a taşındı (yayıncı artık `DatasetTree` tarafına bağlı değil; `dataset_files` yeniden dışa aktarır). Parent zincirinin açılması ve yeniden denetimi (`PublishLocation.recheck`) çağıranındır: manifest `DatasetLocation`ı, indirme (P02-3l) kendi konumunu `input_files.directory_chain` ile kurar; bağ artifact’ı için aynı (P02-3q). Link sonrası ikinci `full_sync`, manifest yolunun son kalıcılık adımıdır ve akış için de korunur (temiz dosyada ucuzdur; ADR adım 12’deki `full_sync` çağıranın link öncesi sync’idir). Mevcut manifest ve dataset testleri değiştirilmeden geçer; kancaların ortak yolda sırayla çağrıldığı ve her adımda gerçek SIGKILL'in hedefi yok ya da bütün bıraktığı `tests/integration/test_artifact_publisher.py`dedir (sahte bir hata ailesiyle, iki girişte).

## Bağımlılıklar ve kararlar

P02-2c verified ve development’tadır (P02-1d manifest yayıncısı dahil). Yeni karar gerekmez: davranış değişmez; kullanımı ADR-0032 ve ADR-0033’tedir. Bu kart onlardan bağımsız yürüyebilir; böylece sürüm hattı indirme ADR’sine bağlı kalmaz.

## Sözleşme ve uygulama sınırı

Ortak yayıncı manifest yayıncısıyla aynı güvenlik ilkelerini uygular ([manifest sözleşmesi](../../reference/dataset-manifest.md#dosya-yayını-ve-hata-önceliği)); hata kodu ailesi ve mesajlar çağıranın sözleşmesindedir. Sürüm hattı rastgele adlı stage kullanır; deterministik stage/sidecar/flock yalnız P02-3l’nin akışlı yazıcısına aittir ve bu kartın kapsamı dışındadır.

## Kabul

1. Manifest yayıncısının mevcut bütün testleri (yarış, kill, belirsizlik, iptal, hedef var, dangling symlink, parent swap, stage ikamesi) **değiştirilmeden** geçer; hata kodu/mesaj/exit değişmez (tek istisna: senkrondan sonra kısaltılan/büyütülen stage artık link edilmez, yukarıdaki farkı). **İçi boş yeşil yok:** kancalar ortak yayıncı yolunda gerçekten çağrılır — kill testi (`_publish_link` yerine geçen süreç) `returncode == -SIGKILL` gözler, yarış/ikame testleri enjekte edilen yöntemi yürütür (kanca çağrılmazsa test kırmızıdır; bu bir kabul oracle’ıdır).
2. Ortak yayıncı aynı yarış/kill/belirsizlik matrisini farklı bir hata ailesiyle (örn. sahte `binding_*` seti) bağımsız olarak geçer; link başladıktan sonraki her belirsizlik ailenin “uncertain” koduna, kesin EEXIST ailenin “exists” koduna eşlenir.
3. Akışlı yazıcı için son-yayın yardımcısı: stage kimliği ve `nlink` denetimi, `link()`/EEXIST ve sahipliği kanıtlı temizlik kancası, dizin sync ve hedef kimliği kontrolü gerçek SIGKILL adımlarıyla sınanır.
4. Strict mypy ve Ruff geçer; yeni public sembol yok.

## Doğrulama

Mevcut dataset yayın testleri, yeni ortak yayıncı integration/race/kill testleri, Ruff, strict mypy ve `git diff --check`.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
